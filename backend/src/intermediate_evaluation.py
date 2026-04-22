from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

import ollama

from models import IntermediateEvaluationRequest, IntermediateEvaluationResponse


INTERMEDIATE_EVALUATION_MODEL = "gemma2:2b"

POLICY_LABELS = {
    "planting_trees_amount": "植林・森林保全",
    "house_migration_amount": "住宅移転",
    "dam_levee_construction_cost": "河川堤防",
    "paddy_dam_construction_cost": "田んぼダム",
    "agricultural_RnD_cost": "高温耐性品種",
    "capacity_building_cost": "防災訓練・啓発",
    "transportation_invest": "交通投資",
    "cp_climate_params": "RCPシナリオ",
}

POLICY_UNITS = {
    "planting_trees_amount": "千本/年",
    "house_migration_amount": "戸/年",
    "dam_levee_construction_cost": "投資単位/年",
    "paddy_dam_construction_cost": "投資単位/年",
    "agricultural_RnD_cost": "投資単位/年",
    "capacity_building_cost": "投資単位/年",
    "transportation_invest": "投資単位/年",
    "cp_climate_params": "",
}

POLICY_MECHANISM_NOTES = {
    "planting_trees_amount": "植林は planting_history に積み上がるが、森林面積への反映は tree_growup_year=30 のため約30年遅れで効く。",
    "house_migration_amount": "住宅移転は risky_house_total を毎年直接減らし、洪水被害を受けやすい世帯を減らす。",
    "dam_levee_construction_cost": "河川堤防は累積投資がしきい値を超えた年に levee_level が段階的に上がる。即効ではなく遅れて効く。",
    "paddy_dam_construction_cost": "田んぼダムは面積が毎年積み上がり、水害の緩和と農業への影響が比較的早く表れやすい。",
    "agricultural_RnD_cost": "高温耐性品種は累積投資がしきい値を超えると high_temp_tolerance_level が上がる。効果は段階的に出る。",
    "capacity_building_cost": "防災訓練・啓発は resident_capacity を徐々に高めるが、毎年少しずつ減衰もする。",
    "transportation_invest": "交通投資は urban_level に影響するが、この画面では通常0のまま使われることが多い。",
}

SNAPSHOT_POLICY_KEYS = {
    "植林・森林保全": "planting_trees_amount",
    "住宅移転": "house_migration_amount",
    "河川堤防": "dam_levee_construction_cost",
    "田んぼダム": "paddy_dam_construction_cost",
    "高温耐性品種": "agricultural_RnD_cost",
    "防災訓練・啓発": "capacity_building_cost",
}

POLICY_SCORE_MAX = {
    "planting_trees_amount": 100.0,
    "house_migration_amount": 100.0,
    "dam_levee_construction_cost": 2.0,
    "paddy_dam_construction_cost": 10.0,
    "agricultural_RnD_cost": 10.0,
    "capacity_building_cost": 10.0,
    "transportation_invest": 10.0,
}

METRIC_SPECS = [
    ("Flood Damage", "洪水被害"),
    ("Crop Yield", "収穫量"),
    ("Ecosystem Level", "生態系"),
    ("Municipal Cost", "自治体コスト"),
    ("Resident Burden", "住民負担"),
    ("Levee Level", "堤防レベル"),
    ("Resident capacity", "住民防災能力"),
    ("Forest Area", "森林面積"),
    ("available_water", "利用可能水量"),
    ("risky_house_total", "高リスク住宅数"),
    ("paddy_dam_area", "田んぼダム面積"),
    ("Temperature (℃)", "年平均気温"),
    ("Extreme Precip Frequency", "極端降水回数"),
]

NEWSPAPER_KEYS = (
    "headline",
    "subheadline",
    "lead",
    "expert_comment",
    "policy_assessment",
    "article_body",
)

SYSTEM_PROMPT_JA = """
あなたは地域新聞の一面を作る編集AIです。
与えられた25年分のシミュレーション結果だけを根拠に、読み手が中学生でも理解できる日本語で新聞記事を作ってください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。前置き、説明、Markdown、コードフェンスは禁止です。
- 必ず次のキーを含めてください:
  headline, subheadline, lead, expert_comment, policy_assessment, article_body
- 見出しは短く、本文は3〜5文程度にしてください。
- subheadline は観測結果に即した文にし、毎回同じ定型句は使わないでください。
- expert_comment は、識者がズバッと言い切る明快な1文にしてください。
- 将来の助言や「次にすべきこと」は書かないでください。
- このシミュレータにおける政策の効き方メモと矛盾しないでください。
- データに見えにくい効果は「この25年では確認しにくい」と表現してください。
- 生活者に伝わる平易な語彙を使ってください。
- 少なくとも2つ以上の具体的な年または数値を記事全体に入れてください。
""".strip()

SYSTEM_PROMPT_EN = """
You are the front-page editor AI for a local newspaper.
Use only the provided 25-year simulation results and write clear plain English for general readers.

Required rules:
- Output only one JSON object. No preface, no explanation, no markdown, no code fences.
- Include exactly these keys:
  headline, subheadline, lead, expert_comment, policy_assessment, article_body
- Keep the headline short and the body to about 3-5 sentences.
- Make the subheadline specific to the observed 25-year results, not a stock phrase.
- Make expert_comment one sharp, clear sentence.
- Do not give future advice or recommendations.
- Do not contradict the simulator notes about how each policy works.
- If an effect is not yet visible, say it is hard to confirm within this 25-year period.
- Include at least two concrete years or numbers across the article.
""".strip()

EXPERT_COMMENT_SYSTEM_PROMPT_JA = """
あなたは地域新聞の「識者コメント」欄を書く編集AIです。
与えられた25年分のシミュレーション結果だけを根拠に、明快でズバッと言える日本語1文を作ってください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。前置き、説明、Markdown、コードフェンスは禁止です。
- キーは expert_comment だけにしてください。
- expert_comment は1文だけにしてください。
- 回りくどい言い方や抽象論は禁止です。
- 将来の助言や提案は禁止です。
- この25年で見えた差、時差、転換点、見えにくさのどれかを必ず指摘してください。
- このシミュレータにおける政策の効き方メモと矛盾しないでください。
- 政策名や指標名は必要なものだけを1〜3個まで使ってください。
""".strip()

EXPERT_COMMENT_SYSTEM_PROMPT_EN = """
You write the expert comment box for a local newspaper.
Use only the provided 25-year simulation results and produce one sharp, plain-English sentence.

Required rules:
- Output only one JSON object. No preface, no explanation, no markdown, no code fences.
- Use only one key: expert_comment.
- expert_comment must be exactly one sentence.
- Avoid vague abstraction or padded phrasing.
- Do not give future advice or recommendations.
- Point out one of these clearly: a contrast, a timing gap, a turning point, or an effect that is still hard to confirm.
- Do not contradict the simulator notes about how each policy works.
- Mention only the 1-3 most relevant policy or metric names.
""".strip()

POLICY_SHORT_LABELS = {
    "planting_trees_amount": {"ja": "植林", "en": "planting"},
    "house_migration_amount": {"ja": "住宅移転", "en": "relocation"},
    "dam_levee_construction_cost": {"ja": "堤防整備", "en": "levee upgrades"},
    "paddy_dam_construction_cost": {"ja": "田んぼダム", "en": "paddy dams"},
    "agricultural_RnD_cost": {"ja": "高温耐性品種", "en": "heat-tolerant crops"},
    "capacity_building_cost": {"ja": "防災訓練", "en": "preparedness"},
    "transportation_invest": {"ja": "交通投資", "en": "transport investment"},
}

FAST_RESPONSE_POLICY_KEYS = (
    "house_migration_amount",
    "capacity_building_cost",
    "paddy_dam_construction_cost",
)

SLOW_RESPONSE_POLICY_KEYS = (
    "planting_trees_amount",
    "dam_levee_construction_cost",
    "agricultural_RnD_cost",
)

CANNED_SUBHEADLINES_JA = {
    "短期で効く防災策と時間差のある土地・生態系施策の差が表れた。",
    "2026年から2050年までの25年では、短期で効く防災策と時間差のある土地・生態系施策の差が表れた。",
}

CANNED_SUBHEADLINES_EN = {
    "From 2026 to 2050, short-term disaster measures showed earlier movement than slower land and ecosystem measures.",
    "short-term disaster measures showed earlier movement than slower land and ecosystem measures.",
}


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _mean(values: Iterable[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def _format_number(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    if abs(value) >= 1000:
        return f"{value:,.{digits}f}"
    return f"{value:.{digits}f}"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip()).strip()
    return str(value).strip()


def _to_sentence(text: Any, is_english: bool) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    compact = re.sub(r"\s+", " ", cleaned).strip().strip('"').strip("'")
    if not compact:
        return ""

    if is_english:
        match = re.search(r"(.+?[.!?])(?:\s|$)", compact)
        sentence = match.group(1).strip() if match else compact.rstrip(".!?") + "."
        return sentence

    match = re.search(r"(.+?[。！？])(?:\s|$)", compact)
    sentence = match.group(1).strip() if match else compact.rstrip("。！？.!?") + "。"
    return sentence


def _extract_json_object(text: str) -> Dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def _build_policy_summary(decision_var: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for key in (
        "planting_trees_amount",
        "house_migration_amount",
        "dam_levee_construction_cost",
        "paddy_dam_construction_cost",
        "agricultural_RnD_cost",
        "capacity_building_cost",
        "transportation_invest",
        "cp_climate_params",
    ):
        label = POLICY_LABELS[key]
        unit = POLICY_UNITS.get(key, "")
        raw_value = _to_float(decision_var.get(key))
        value_text = _format_number(raw_value, digits=2) if raw_value is not None else "n/a"
        suffix = f" {unit}" if unit else ""
        lines.append(f"- {label}: {value_text}{suffix}")
    return lines


def _build_mechanism_notes(decision_var: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    for key, note in POLICY_MECHANISM_NOTES.items():
        amount = _to_float(decision_var.get(key, 0))
        if amount is None:
            continue
        if key == "transportation_invest" and amount == 0:
            continue
        notes.append(f"- {POLICY_LABELS[key]}: {note}")
    return notes


def _build_metric_summary(rows: List[Dict[str, Any]]) -> List[str]:
    summaries: List[str] = []
    for key, label in METRIC_SPECS:
        values = [_to_float(row.get(key)) for row in rows]
        numeric_values = [value for value in values if value is not None]
        if not numeric_values:
            continue
        first = numeric_values[0]
        last = numeric_values[-1]
        mean_value = _mean(numeric_values)
        min_value = min(numeric_values)
        max_value = max(numeric_values)
        summaries.append(
            f"- {label}: 初年={_format_number(first)}, 最終年={_format_number(last)}, "
            f"平均={_format_number(mean_value)}, 最小={_format_number(min_value)}, 最大={_format_number(max_value)}"
        )
    return summaries


def _top_rows_by_metric(rows: List[Dict[str, Any]], key: str, count: int = 3, reverse: bool = True) -> List[Dict[str, Any]]:
    sortable_rows = [row for row in rows if _to_float(row.get(key)) is not None]
    return sorted(sortable_rows, key=lambda row: _to_float(row.get(key)) or 0.0, reverse=reverse)[:count]


def _find_first_change_year(rows: List[Dict[str, Any]], key: str) -> int | None:
    if not rows:
        return None

    baseline = _to_float(rows[0].get(key))
    if baseline is None:
        return None

    for row in rows[1:]:
        value = _to_float(row.get(key))
        if value is None:
            continue
        if abs(value - baseline) > 1e-9:
            return int(row["Year"])
    return None


def _build_policy_effect_snapshots(rows: List[Dict[str, Any]], decision_var: Dict[str, Any]) -> List[str]:
    if not rows:
        return []

    first_row = rows[0]
    last_row = rows[-1]
    midpoint = len(rows) // 2
    early_rows = rows[:midpoint] or rows
    late_rows = rows[midpoint:] or rows

    def avg(rows_subset: List[Dict[str, Any]], key: str) -> float | None:
        return _mean(_to_float(row.get(key)) for row in rows_subset)

    snapshots = [
        (
            "植林・森林保全",
            "森林面積 {start} -> {end}. ただし新規植林の成熟反映は約30年後なので、この25年では直接効果を確認しにくい。".format(
                start=_format_number(_to_float(first_row.get("Forest Area"))),
                end=_format_number(_to_float(last_row.get("Forest Area"))),
            ),
        ),
        (
            "住宅移転",
            "高リスク住宅 {start} -> {end}. 洪水被害の前半平均 {early_flood}、後半平均 {late_flood}.".format(
                start=_format_number(_to_float(first_row.get("risky_house_total"))),
                end=_format_number(_to_float(last_row.get("risky_house_total"))),
                early_flood=_format_number(avg(early_rows, "Flood Damage")),
                late_flood=_format_number(avg(late_rows, "Flood Damage")),
            ),
        ),
        (
            "河川堤防",
            "堤防レベル {start} -> {end}. 最初の変化年 {change_year}.".format(
                start=_format_number(_to_float(first_row.get("Levee Level"))),
                end=_format_number(_to_float(last_row.get("Levee Level"))),
                change_year=_find_first_change_year(rows, "Levee Level") or "変化なし",
            ),
        ),
        (
            "田んぼダム",
            "田んぼダム面積 {start} -> {end}. 収穫量の前半平均 {early_crop}、後半平均 {late_crop}.".format(
                start=_format_number(_to_float(first_row.get("paddy_dam_area"))),
                end=_format_number(_to_float(last_row.get("paddy_dam_area"))),
                early_crop=_format_number(avg(early_rows, "Crop Yield")),
                late_crop=_format_number(avg(late_rows, "Crop Yield")),
            ),
        ),
        (
            "高温耐性品種",
            "高温耐性レベル {start} -> {end}. 最初の変化年 {change_year}.".format(
                start=_format_number(_to_float(first_row.get("High Temp Tolerance Level"))),
                end=_format_number(_to_float(last_row.get("High Temp Tolerance Level"))),
                change_year=_find_first_change_year(rows, "High Temp Tolerance Level") or "変化なし",
            ),
        ),
        (
            "防災訓練・啓発",
            "住民防災能力 {start} -> {end}. 最初の変化年 {change_year}.".format(
                start=_format_number(_to_float(first_row.get("Resident capacity")), digits=2),
                end=_format_number(_to_float(last_row.get("Resident capacity")), digits=2),
                change_year=_find_first_change_year(rows, "Resident capacity") or "変化なし",
            ),
        ),
    ]

    active_snapshots: List[str] = []
    for key, sentence in snapshots:
        amount = _to_float(decision_var.get(SNAPSHOT_POLICY_KEYS[key], 0))
        if amount is None or amount <= 0:
            continue
        active_snapshots.append(f"- {key}: {sentence}")

    return active_snapshots


def _build_event_highlights(rows: List[Dict[str, Any]]) -> List[str]:
    highlights: List[str] = []

    for row in _top_rows_by_metric(rows, "Flood Damage", count=3, reverse=True):
        highlights.append(
            "洪水被害が大きい年: "
            f"{int(row['Year'])}年, 洪水被害={_format_number(_to_float(row.get('Flood Damage')))}, "
            f"極端降水回数={_format_number(_to_float(row.get('Extreme Precip Frequency')), digits=0)}, "
        )

    for row in _top_rows_by_metric(rows, "Crop Yield", count=2, reverse=False):
        highlights.append(
            "収穫量が低い年: "
            f"{int(row['Year'])}年, 収穫量={_format_number(_to_float(row.get('Crop Yield')))}, "
            f"利用可能水量={_format_number(_to_float(row.get('available_water')))}, "
            f"気温={_format_number(_to_float(row.get('Temperature (℃)')))}"
        )

    ecosystem_first = _to_float(rows[0].get("Ecosystem Level")) if rows else None
    ecosystem_last = _to_float(rows[-1].get("Ecosystem Level")) if rows else None
    if ecosystem_first is not None and ecosystem_last is not None:
        delta = ecosystem_last - ecosystem_first
        direction = "上昇" if delta >= 0 else "低下"
        highlights.append(
            f"生態系の期間変化: {_format_number(ecosystem_first)} から {_format_number(ecosystem_last)} へ {direction} "
            f"(差分 {_format_number(delta)})"
        )

    return highlights


def _build_yearly_timeline(rows: List[Dict[str, Any]]) -> List[str]:
    timeline: List[str] = []
    for row in rows:
        timeline.append(
            "| {year} | 洪水被害 {flood} | 収穫量 {crop} | 生態系 {eco} | 堤防 {levee} | 防災能力 {capacity} | 森林 {forest} |".format(
                year=int(row["Year"]),
                flood=_format_number(_to_float(row.get("Flood Damage"))),
                crop=_format_number(_to_float(row.get("Crop Yield"))),
                eco=_format_number(_to_float(row.get("Ecosystem Level"))),
                levee=_format_number(_to_float(row.get("Levee Level"))),
                capacity=_format_number(_to_float(row.get("Resident capacity")), digits=2),
                forest=_format_number(_to_float(row.get("Forest Area"))),
            )
        )
    return timeline


def _extract_message_content(response: Any) -> str:
    if isinstance(response, dict):
        return str(response.get("message", {}).get("content", "")).strip()

    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", "")
        return str(content).strip()

    return str(response).strip()


def _describe_change_ja(label: str, start: float | None, end: float | None, lower_is_better: bool = False) -> str:
    if start is None or end is None:
        return f"{label}は判断材料が不足した"
    delta = end - start
    threshold = max(abs(start) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return f"{label}はおおむね横ばいだった"
    improved = delta < 0 if lower_is_better else delta > 0
    if improved:
        return f"{label}は{_format_number(start)}から{_format_number(end)}へ改善した"
    return f"{label}は{_format_number(start)}から{_format_number(end)}へ悪化した"


def _describe_change_en(label: str, start: float | None, end: float | None, lower_is_better: bool = False) -> str:
    if start is None or end is None:
        return f"{label} had limited evidence"
    delta = end - start
    threshold = max(abs(start) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return f"{label} stayed broadly flat"
    improved = delta < 0 if lower_is_better else delta > 0
    if improved:
        return f"{label} improved from {_format_number(start)} to {_format_number(end)}"
    return f"{label} worsened from {_format_number(start)} to {_format_number(end)}"


def _headline_phrase_ja(start: float | None, end: float | None, lower_is_better: bool, positive: str, negative: str, neutral: str) -> str:
    if start is None or end is None:
        return neutral
    delta = end - start
    threshold = max(abs(start) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return neutral
    improved = delta < 0 if lower_is_better else delta > 0
    return positive if improved else negative


def _headline_phrase_en(start: float | None, end: float | None, lower_is_better: bool, positive: str, negative: str, neutral: str) -> str:
    if start is None or end is None:
        return neutral
    delta = end - start
    threshold = max(abs(start) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return neutral
    improved = delta < 0 if lower_is_better else delta > 0
    return positive if improved else negative


def _normalize_policy_value(decision_var: Dict[str, Any], key: str) -> float:
    raw_value = _to_float(decision_var.get(key, 0)) or 0.0
    max_value = POLICY_SCORE_MAX.get(key, 1.0)
    if max_value <= 0:
        return 0.0
    return min(raw_value / max_value, 1.0)


def _format_label_list(labels: List[str], is_english: bool) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        conjunction = " and " if is_english else "や"
        return f"{labels[0]}{conjunction}{labels[1]}"
    if is_english:
        return f"{', '.join(labels[:-1])}, and {labels[-1]}"
    return f"{'、'.join(labels[:-1])}や{labels[-1]}"


def _policy_short_label(key: str, is_english: bool) -> str:
    language_key = "en" if is_english else "ja"
    return POLICY_SHORT_LABELS.get(key, {}).get(language_key, POLICY_LABELS.get(key, key))


def _active_policy_labels(
    decision_var: Dict[str, Any],
    keys: Iterable[str],
    is_english: bool,
) -> List[str]:
    return [
        _policy_short_label(key, is_english)
        for key in keys
        if (_to_float(decision_var.get(key, 0)) or 0.0) > 0
    ]


def _change_state(start: float | None, end: float | None, lower_is_better: bool = False) -> str:
    if start is None or end is None:
        return "unknown"
    delta = end - start
    threshold = max(abs(start) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return "flat"
    improved = delta < 0 if lower_is_better else delta > 0
    return "improved" if improved else "worsened"


def _is_canned_subheadline(text: str, is_english: bool) -> bool:
    normalized = re.sub(r"\s+", "", _clean_text(text))
    if not normalized:
        return False
    candidates = CANNED_SUBHEADLINES_EN if is_english else CANNED_SUBHEADLINES_JA
    return normalized in {re.sub(r"\s+", "", candidate) for candidate in candidates}


def _build_fallback_subheadline(req: IntermediateEvaluationRequest) -> str:
    rows = req.simulation_rows
    decision_var = req.decision_var.model_dump()
    is_english = req.language.lower().startswith("en")

    first_row = rows[0]
    last_row = rows[-1]
    flood_state = _change_state(
        _to_float(first_row.get("Flood Damage")),
        _to_float(last_row.get("Flood Damage")),
        lower_is_better=True,
    )
    crop_state = _change_state(
        _to_float(first_row.get("Crop Yield")),
        _to_float(last_row.get("Crop Yield")),
    )
    ecosystem_state = _change_state(
        _to_float(first_row.get("Ecosystem Level")),
        _to_float(last_row.get("Ecosystem Level")),
    )
    levee_change_year = _find_first_change_year(rows, "Levee Level")
    capacity_change_year = _find_first_change_year(rows, "Resident capacity")

    fast_labels = _active_policy_labels(decision_var, FAST_RESPONSE_POLICY_KEYS, is_english)
    slow_labels = _active_policy_labels(decision_var, SLOW_RESPONSE_POLICY_KEYS, is_english)
    fast_text = _format_label_list(fast_labels[:2], is_english)
    slow_text = _format_label_list(slow_labels[:2], is_english)

    if is_english:
        if fast_text and slow_text and flood_state == "improved" and ecosystem_state != "improved":
            return (
                f"From {req.period_start_year} to {req.period_end_year}, {fast_text} showed up earlier, "
                f"while {slow_text} remained harder to read in the data."
            )
        if slow_text and ecosystem_state == "improved":
            return (
                f"From {req.period_start_year} to {req.period_end_year}, ecological recovery started to surface, "
                f"but the payoff from {slow_text} was still uneven across indicators."
            )
        if levee_change_year and flood_state == "improved":
            return (
                f"From {req.period_start_year} to {req.period_end_year}, flood conditions shifted after the levee changes visible around {levee_change_year}."
            )
        if capacity_change_year and flood_state in {"flat", "worsened"}:
            return (
                f"From {req.period_start_year} to {req.period_end_year}, preparedness moved by {capacity_change_year}, "
                f"but flood losses still swung sharply year to year."
            )
        if flood_state == "improved" and crop_state == "worsened":
            return (
                f"From {req.period_start_year} to {req.period_end_year}, lower flood damage did not translate into steadier harvests."
            )
        if flood_state == "worsened" and ecosystem_state == "improved":
            return (
                f"From {req.period_start_year} to {req.period_end_year}, ecological recovery advanced even as flood pressure stayed high."
            )
        return (
            f"From {req.period_start_year} to {req.period_end_year}, flood damage, crop yield, and ecology did not move in step."
        )

    if fast_text and slow_text and flood_state == "improved" and ecosystem_state != "improved":
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、{fast_text}が先に動き、"
            f"{slow_text}はまだデータで読み切りにくかった。"
        )
    if slow_text and ecosystem_state == "improved":
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、生態系は持ち直し始めた一方、"
            f"{slow_text}の効き方は指標ごとにまだらだった。"
        )
    if levee_change_year and flood_state == "improved":
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、{levee_change_year}年ごろの堤防変化を境に洪水被害の見え方が変わった。"
        )
    if capacity_change_year and flood_state in {"flat", "worsened"}:
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、{capacity_change_year}年ごろに防災能力は動いたが、水害はなお年ごとの振れが大きかった。"
        )
    if flood_state == "improved" and crop_state == "worsened":
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、洪水被害が和らいでも収穫量までは素直に持ち直さなかった。"
        )
    if flood_state == "worsened" and ecosystem_state == "improved":
        return (
            f"{req.period_start_year}年から{req.period_end_year}年では、生態系が上向く一方で洪水圧力は重いままだった。"
        )
    return (
        f"{req.period_start_year}年から{req.period_end_year}年では、洪水被害と収穫量と生態系が同じ方向には動かなかった。"
    )


def _build_fallback_expert_comment(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    is_english = req.language.lower().startswith("en")

    fast_labels = _active_policy_labels(decision_var, FAST_RESPONSE_POLICY_KEYS, is_english)
    slow_labels = _active_policy_labels(decision_var, SLOW_RESPONSE_POLICY_KEYS, is_english)

    if is_english:
        if fast_labels and slow_labels:
            return (
                f"This 25-year window made the timing gap clear: {_format_label_list(fast_labels[:2], True)} "
                f"moved sooner, while {_format_label_list(slow_labels[:2], True)} remained slower to confirm."
            )
        if fast_labels:
            return (
                f"This 25-year window showed {_format_label_list(fast_labels[:2], True)} as the measures that moved first."
            )
        if slow_labels:
            return (
                f"This 25-year window was still too short to read the full effect of "
                f"{_format_label_list(slow_labels[:2], True)}."
            )
        return "This 25-year window was shaped more by year-to-year swings than by any single policy turning point."

    if fast_labels and slow_labels:
        return (
            f"この25年は、{_format_label_list(fast_labels[:2], False)}のような比較的早く効く対策と、"
            f"{_format_label_list(slow_labels[:2], False)}のように時間差の大きい対策の差が見えやすい期間だった。"
        )
    if fast_labels:
        return f"この25年は、{_format_label_list(fast_labels[:2], False)}のような比較的早く効く対策が先に動きやすい期間だった。"
    if slow_labels:
        return f"この25年は、{_format_label_list(slow_labels[:2], False)}のような時間差の大きい対策を読み切るにはまだ短い期間だった。"
    return "この25年は、大きな政策差よりも洪水被害や収穫量の年ごとの振れ幅が前に出た期間だった。"


def _pick_policy_assessment(decision_var: Dict[str, Any], is_english: bool) -> str:
    flood_focus = (
        _normalize_policy_value(decision_var, "house_migration_amount")
        + _normalize_policy_value(decision_var, "dam_levee_construction_cost")
        + _normalize_policy_value(decision_var, "capacity_building_cost")
    )
    agriculture_focus = (
        _normalize_policy_value(decision_var, "paddy_dam_construction_cost")
        + _normalize_policy_value(decision_var, "agricultural_RnD_cost")
    )
    ecosystem_focus = _normalize_policy_value(decision_var, "planting_trees_amount")
    active_count = sum(
        1 for key in POLICY_SCORE_MAX if (_to_float(decision_var.get(key, 0)) or 0.0) > 0
    )

    if active_count == 0:
        return "Minimal intervention" if is_english else "低介入型"

    category_scores = {
        "flood": flood_focus,
        "agriculture": agriculture_focus,
        "ecosystem": ecosystem_focus,
    }
    sorted_scores = sorted(category_scores.values(), reverse=True)
    if active_count >= 3 and len(sorted_scores) >= 2 and abs(sorted_scores[0] - sorted_scores[1]) < 0.4:
        return "Balanced package" if is_english else "複合バランス型"

    top_category = max(category_scores, key=category_scores.get)
    if top_category == "flood":
        return "Flood-defense first" if is_english else "防災先行型"
    if top_category == "agriculture":
        return "Agricultural stability first" if is_english else "農業安定重視型"
    return "Ecosystem recovery first" if is_english else "生態系回復重視型"


def _build_fallback_article(
    req: IntermediateEvaluationRequest,
    event_highlights: List[str],
    fallback_subheadline: str,
    fallback_expert_comment: str,
) -> Dict[str, str]:
    rows = req.simulation_rows
    decision_var = req.decision_var.model_dump()
    is_english = req.language.lower().startswith("en")

    first_row = rows[0]
    last_row = rows[-1]

    flood_start = _to_float(first_row.get("Flood Damage"))
    flood_end = _to_float(last_row.get("Flood Damage"))
    crop_start = _to_float(first_row.get("Crop Yield"))
    crop_end = _to_float(last_row.get("Crop Yield"))
    ecosystem_start = _to_float(first_row.get("Ecosystem Level"))
    ecosystem_end = _to_float(last_row.get("Ecosystem Level"))
    levee_change_year = _find_first_change_year(rows, "Levee Level")
    capacity_change_year = _find_first_change_year(rows, "Resident capacity")

    if is_english:
        headline = (
            f"{req.checkpoint_year}: "
            f"{_headline_phrase_en(flood_start, flood_end, True, 'flood losses ease', 'flood losses stay heavy', 'flood risk stays mixed')}, "
            f"{_headline_phrase_en(ecosystem_start, ecosystem_end, False, 'while ecosystems recover', 'while ecosystems remain under strain', 'with ecology still mixed')}"
        )
        subheadline = fallback_subheadline
        lead = (
            f"In this 25-year phase, {_describe_change_en('flood damage', flood_start, flood_end, lower_is_better=True)}, "
            f"while {_describe_change_en('ecosystem conditions', ecosystem_start, ecosystem_end)}."
        )
        expert_comment = fallback_expert_comment
        article_body = " ".join(
            sentence
            for sentence in [
                f"{_describe_change_en('Crop yield', crop_start, crop_end)} across the period.",
                (
                    f"Levee conditions first moved in {levee_change_year}."
                    if levee_change_year
                    else "No clear levee step-up was confirmed in this 25-year window."
                ),
                (
                    f"Resident preparedness began to shift in {capacity_change_year}."
                    if capacity_change_year
                    else "Resident preparedness changed only gradually within the period."
                ),
                event_highlights[0] + "." if event_highlights else "",
            ]
            if sentence
        )
    else:
        headline = (
            f"{req.checkpoint_year}年、"
            f"{_headline_phrase_ja(flood_start, flood_end, True, '洪水被害は抑制方向', '洪水被害は重いまま', '洪水リスクは拮抗')}"
            f"一方で、"
            f"{_headline_phrase_ja(ecosystem_start, ecosystem_end, False, '生態系は持ち直し', '生態系回復は足踏み', '生態系は横ばい')}"
        )
        subheadline = fallback_subheadline
        lead = (
            f"この期間は、{_describe_change_ja('洪水被害', flood_start, flood_end, lower_is_better=True)}一方で、"
            f"{_describe_change_ja('生態系', ecosystem_start, ecosystem_end)}ことが目立った。"
        )
        expert_comment = fallback_expert_comment
        article_body = " ".join(
            sentence
            for sentence in [
                f"{_describe_change_ja('収穫量', crop_start, crop_end)}。",
                (
                    f"堤防レベルのはっきりした変化は{levee_change_year}年に現れた。"
                    if levee_change_year
                    else "堤防レベルの段階的な上昇は、この25年でははっきり確認しにくかった。"
                ),
                (
                    f"住民防災能力の変化は{capacity_change_year}年ごろから見え始めた。"
                    if capacity_change_year
                    else "住民防災能力は少しずつ動いたが、大きな転換点は読み取りにくかった。"
                ),
                event_highlights[0] + "。" if event_highlights else "",
            ]
            if sentence
        )

    return {
        "headline": headline,
        "subheadline": subheadline,
        "lead": lead,
        "expert_comment": expert_comment,
        "policy_assessment": _pick_policy_assessment(decision_var, is_english),
        "article_body": article_body.strip(),
    }


def _normalize_article_payload(
    llm_payload: Dict[str, Any] | None,
    fallback_article: Dict[str, str],
) -> Dict[str, str]:
    normalized = dict(fallback_article)
    if not isinstance(llm_payload, dict):
        return normalized

    for key in NEWSPAPER_KEYS:
        cleaned = _clean_text(llm_payload.get(key))
        if cleaned:
            normalized[key] = cleaned

    return normalized


def _build_expert_comment_prompt(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    mechanism_notes = _build_mechanism_notes(decision_var)
    policy_effect_snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    event_highlights = _build_event_highlights(req.simulation_rows)

    if req.language.lower().startswith("en"):
        return f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}

Policies:
{chr(10).join(policy_summary)}

How these policies work in the simulator:
{chr(10).join(mechanism_notes)}

Observed evidence from the 25-year data:
{chr(10).join(policy_effect_snapshots)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Write only the expert_comment.
Make it one sharp sentence that says what this 25-year window revealed most clearly.
Return JSON only.
""".strip()

    return f"""
評価時点: {req.checkpoint_year}年
対象期間: {req.period_start_year}年-{req.period_end_year}年
評価対象段階: 第{req.stage_index}段階

政策一覧:
{chr(10).join(policy_summary)}

政策の効き方メモ:
{chr(10).join(mechanism_notes)}

25年データから見えた観測証拠:
{chr(10).join(policy_effect_snapshots)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

expert_comment だけを作ってください。
この25年で何がいちばんはっきり見えたかを、ズバッと言い切る1文にしてください。
JSONのみを返してください。
""".strip()


def _generate_expert_comment(
    req: IntermediateEvaluationRequest,
    fallback_comment: str,
) -> str:
    is_english = req.language.lower().startswith("en")

    try:
        response = ollama.chat(
            model=INTERMEDIATE_EVALUATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": EXPERT_COMMENT_SYSTEM_PROMPT_EN if is_english else EXPERT_COMMENT_SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": _build_expert_comment_prompt(req)},
            ],
            options={"temperature": 0.3, "num_predict": 120},
        )
    except Exception:
        return fallback_comment

    response_text = _extract_message_content(response)
    payload = _extract_json_object(response_text)
    generated = ""
    if isinstance(payload, dict):
        generated = _to_sentence(payload.get("expert_comment"), is_english)
    if not generated:
        generated = _to_sentence(response_text, is_english)
    return generated or fallback_comment


def _compose_feedback(article: Dict[str, str], is_english: bool) -> str:
    if is_english:
        return "\n".join(
            [
                f"Headline: {article['headline']}",
                f"Subheadline: {article['subheadline']}",
                f"Lead: {article['lead']}",
                f"Policy Assessment: {article['policy_assessment']}",
                f"Expert Comment: {article['expert_comment']}",
                "",
                article["article_body"],
            ]
        ).strip()

    return "\n".join(
        [
            f"見出し: {article['headline']}",
            f"サブ見出し: {article['subheadline']}",
            f"リード: {article['lead']}",
            f"政策評価: {article['policy_assessment']}",
            f"コメント: {article['expert_comment']}",
            "",
            article["article_body"],
        ]
    ).strip()


def build_intermediate_evaluation_prompt(req: IntermediateEvaluationRequest) -> tuple[str, List[str], List[str]]:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    mechanism_notes = _build_mechanism_notes(decision_var)
    metric_summary = _build_metric_summary(req.simulation_rows)
    event_highlights = _build_event_highlights(req.simulation_rows)
    policy_effect_snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    yearly_timeline = _build_yearly_timeline(req.simulation_rows)

    is_english = req.language.lower().startswith("en")
    if is_english:
        user_prompt = f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}

Policies selected at the beginning of this period:
{chr(10).join(policy_summary)}

How each policy works in this simulator:
{chr(10).join(mechanism_notes)}

Policy evidence snapshots from the 25-year data:
{chr(10).join(policy_effect_snapshots)}

25-year outcome summary:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {highlight}" for highlight in event_highlights)}

Yearly timeline:
| Year | Indicator summary |
| --- | --- |
{chr(10).join(yearly_timeline)}

Output requirements:
- Return only one JSON object
- policy_assessment must be a short label, not a sentence
- Make the subheadline data-specific and avoid stock wording
- expert_comment must be one sharp sentence
- Keep the whole article compact and specific
- Mention concrete years or numbers where useful
- Write like a newspaper front page, not like a policy memo
- No future advice
""".strip()
    else:
        user_prompt = f"""
評価時点: {req.checkpoint_year}年
対象期間: {req.period_start_year}年-{req.period_end_year}年
評価対象段階: 第{req.stage_index}段階

プレイヤーが期間開始時に選んだ政策と投下量:
{chr(10).join(policy_summary)}

このシミュレータにおける政策の効き方メモ:
{chr(10).join(mechanism_notes)}

25年データから先に抽出した政策ごとの観測証拠:
{chr(10).join(policy_effect_snapshots)}

25年の実績サマリー:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {highlight}" for highlight in event_highlights)}

年次データ:
| 年 | 指標の要約 |
| --- | --- |
{chr(10).join(yearly_timeline)}

出力条件:
- JSON オブジェクトのみを返す
- 見出しは短く、本文は3〜5文程度
- 見出しで分かる様にする
- subheadline は観測結果に即した文にし、定型句をそのまま繰り返さない
- expert_comment は、識者がズバッと言う1文にする
- 新聞一面の語り口で書く
- 中学生にも分かるやさしい日本語にする
- 今後の助言は禁止
- 具体的な年や数値を記事全体で2つ以上入れる
- policy_assessment は短いラベルだけにする
""".strip()

    return user_prompt, policy_summary, event_highlights


def generate_intermediate_evaluation(
    req: IntermediateEvaluationRequest,
) -> IntermediateEvaluationResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    user_prompt, policy_summary, event_highlights = build_intermediate_evaluation_prompt(req)
    fallback_subheadline = _build_fallback_subheadline(req)
    fallback_expert_comment = _build_fallback_expert_comment(req)
    fallback_article = _build_fallback_article(
        req,
        event_highlights,
        fallback_subheadline,
        fallback_expert_comment,
    )

    try:
        response = ollama.chat(
            model=INTERMEDIATE_EVALUATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.2, "num_predict": 260},
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama evaluation failed: {exc}") from exc

    feedback_text = _extract_message_content(response)
    article = _normalize_article_payload(_extract_json_object(feedback_text), fallback_article)
    if _is_canned_subheadline(article["subheadline"], req.language.lower().startswith("en")):
        article["subheadline"] = fallback_subheadline
    article["expert_comment"] = _generate_expert_comment(req, article["expert_comment"])
    feedback = _compose_feedback(article, req.language.lower().startswith("en"))

    return IntermediateEvaluationResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=INTERMEDIATE_EVALUATION_MODEL,
        feedback=feedback,
        policy_summary=policy_summary,
        event_highlights=event_highlights,
        headline=article["headline"],
        subheadline=article["subheadline"],
        lead=article["lead"],
        expert_comment=article["expert_comment"],
        policy_assessment=article["policy_assessment"],
        article_body=article["article_body"],
    )
