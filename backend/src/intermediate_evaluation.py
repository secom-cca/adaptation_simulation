from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

import ollama

from models import IntermediateEvaluationRequest, IntermediateEvaluationResponse


INTERMEDIATE_EVALUATION_MODEL = "gemma4:e2b" # "gemma4:e4b" # "gemma2:2b"
OLLAMA_TIMEOUT_SECONDS = 30.0

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
- headline と subheadline は同じ文にしないでください。
- headline は短く、読者が一目で「何が山場だったか」分かる結論にしてください。
- subheadline は headline を繰り返さず、「なぜそう読めるか」「どの政策効果を見るべきか」を1文で補足してください。
- 本文は3〜5文程度にしてください。
- lead は、重大イベント年の被害と政策状態から読み手に役立つフィードバックを1文で書いてください。
- policy_assessment は、政策タイプだけでなく、重大イベント時に政策がどう見えたかまで含む短い評価句にしてください。
- article_body は、指標の数値を並べるのではなく、「何が要因で、何を読み取るべきか」が直感的に分かる2〜4文にしてください。
- article_body は必ず「主因」「政策効果」「伝えたいこと」が読み取れる文章にしてください。抽象的な状況説明だけで終わらせないでください。
- article_body では、実際に効いた政策、どう効いたか、逆にどの政策は足りなかったかを読者が直感的に分かる文章で書いてください。
- article_body では具体的な数字や変化量を書かず、参考になる指標名を括弧で引用する形にしてください。
- article_body では、参照すべきグラフ名を必ず括弧で書いてください。例: (収穫量)(利用可能水量)
- article_body では、少なくとも1つの中間年の重大イベントと、その時点の政策状態を必ず結びつけてください。
- 重大な被害イベントがある場合、「指標は概ね横ばい」といった総括を中心にしないでください。被害年を主語にして、政策が効いた点・足りなかった点・効果が確認しにくい点を評価してください。
- 「収穫量はAからBへ改善した」のような期間始点・終点の数値比較文は禁止です。必ず被害イベント年の指標と政策状態を結びつけてください。
- expert_comment は、識者がズバッと言い切る明快な1文にしてください。
- 将来の助言や「次にすべきこと」は書かないでください。
- このシミュレータにおける政策の効き方メモと矛盾しないでください。
- データに見えにくい効果は「この25年では確認しにくい」と表現してください。
- 生活者に伝わる平易な語彙を使ってください。
- 具体的な数値は本文に出さないでください。詳しい数字を知りたい読者は括弧内の指標グラフを見る、という役割分担にしてください。
""".strip()

SYSTEM_PROMPT_EN = """
You are the front-page editor AI for a local newspaper.
Use only the provided 25-year simulation results and write clear plain English for general readers.

Required rules:
- Output only one JSON object. No preface, no explanation, no markdown, no code fences.
- Include exactly these keys:
  headline, subheadline, lead, expert_comment, policy_assessment, article_body
- Do not make headline and subheadline the same sentence.
- Keep headline short and make it the immediate conclusion about what the turning point was.
- Make subheadline explain why the headline is true and which policy effect readers should examine. Do not repeat the headline.
- Keep the body to about 3-5 sentences.
- Make lead give useful feedback from the year-by-year trend and policy mechanisms, not just a first-year vs final-year comparison.
- Make policy_assessment a short evaluative phrase that links the policy package to what happened during a major event.
- Make article_body 2-4 plain sentences that explain the driver and takeaway intuitively instead of listing indicator values.
- article_body must clearly state the main driver, the policy effect, and the takeaway. Do not end with only abstract situation-setting.
- In article_body, state which policies actually helped, how they helped, and which policy effects were still insufficient in intuitive language.
- Do not put concrete numbers or change amounts in article_body. Reference the useful indicator names in parentheses instead.
- In article_body, name the charts readers should check in parentheses, such as (Crop Yield) or (Available Water).
- In article_body, connect at least one mid-period event to the policy state visible in that year.
- If there is a major damage event, do not center the report on "flat" or "stable" indicators. Lead with the damage year and evaluate where policies absorbed the shock, fell short, or remained hard to confirm.
- Do not write endpoint comparison sentences such as "crop yield improved from A to B." Tie the event-year damage to the policy state instead.
- Make expert_comment one sharp, clear sentence.
- Do not give future advice or recommendations.
- Do not contradict the simulator notes about how each policy works.
- If an effect is not yet visible, say it is hard to confirm within this 25-year period.
- Keep specific numbers to a minimum. Let the chart carry detailed values.
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
- 重大な被害イベントがある場合は、その年の政策状態との関係を優先し、「横ばい」だけで終わらせないでください。
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
- If there is a major damage event, prioritize its relationship to the policy state and do not end with a generic flat/stable summary.
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
    summaries.append("- 注意: この集計は補助情報です。評価の主軸は、別項目の主要被害イベントと政策状態です。")
    for key, label in METRIC_SPECS:
        value_rows = [
            (row, _to_float(row.get(key)))
            for row in rows
            if _to_float(row.get(key)) is not None
        ]
        if not value_rows:
            continue
        numeric_values = [value for _, value in value_rows]
        min_row, min_value = min(value_rows, key=lambda item: item[1] or 0.0)
        max_row, max_value = max(value_rows, key=lambda item: item[1] or 0.0)
        mean_value = _mean(numeric_values)
        summaries.append(
            f"- {label}: 平均={_format_number(mean_value)}, "
            f"最小={_format_number(min_value)}({_row_year(min_row)}年), "
            f"最大={_format_number(max_value)}({_row_year(max_row)}年)"
        )
    return summaries


def _row_year(row: Dict[str, Any]) -> str:
    year = _to_float(row.get("Year"))
    return str(int(year)) if year is not None else "不明年"


def _row_context(row: Dict[str, Any]) -> str:
    return (
        f"{_row_year(row)}年: "
        f"洪水被害={_format_number(_to_float(row.get('Flood Damage')))}, "
        f"収穫量={_format_number(_to_float(row.get('Crop Yield')))}, "
        f"生態系={_format_number(_to_float(row.get('Ecosystem Level')))}, "
        f"住民負担={_format_number(_to_float(row.get('Resident Burden')))}, "
        f"水量={_format_number(_to_float(row.get('available_water')))}, "
        f"猛暑日={_format_number(_to_float(row.get('Hot Days')))}, "
        f"極端降水={_format_number(_to_float(row.get('Extreme Precip Frequency')))}, "
        f"堤防={_format_number(_to_float(row.get('Levee Level')))}, "
        f"防災能力={_format_number(_to_float(row.get('Resident capacity')), digits=2)}, "
        f"高リスク住宅={_format_number(_to_float(row.get('risky_house_total')))}, "
        f"田んぼダム={_format_number(_to_float(row.get('paddy_dam_area')))}, "
        f"高温耐性={_format_number(_to_float(row.get('High Temp Tolerance Level')))}"
    )


def _signed_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{_format_number(value)}"


def _build_phase_summaries(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return []

    count = len(rows)
    first_cut = max(1, count // 3)
    second_cut = max(first_cut + 1, (count * 2) // 3)
    phases = [
        ("前半", rows[:first_cut]),
        ("中盤", rows[first_cut:second_cut]),
        ("後半", rows[second_cut:]),
    ]

    summaries: List[str] = []
    for label, phase_rows in phases:
        if not phase_rows:
            continue
        start_year = _row_year(phase_rows[0])
        end_year = _row_year(phase_rows[-1])
        summaries.append(
            f"- {label}({start_year}-{end_year}年): "
            f"平均洪水被害={_format_number(_mean(_to_float(row.get('Flood Damage')) for row in phase_rows))}, "
            f"平均収穫量={_format_number(_mean(_to_float(row.get('Crop Yield')) for row in phase_rows))}, "
            f"平均生態系={_format_number(_mean(_to_float(row.get('Ecosystem Level')) for row in phase_rows))}, "
            f"平均住民負担={_format_number(_mean(_to_float(row.get('Resident Burden')) for row in phase_rows))}, "
            f"平均水量={_format_number(_mean(_to_float(row.get('available_water')) for row in phase_rows))}, "
            f"平均極端降水={_format_number(_mean(_to_float(row.get('Extreme Precip Frequency')) for row in phase_rows))}"
        )
    return summaries


def _top_rows_by_metric(rows: List[Dict[str, Any]], key: str, count: int = 3, reverse: bool = True) -> List[Dict[str, Any]]:
    sortable_rows = [row for row in rows if _to_float(row.get(key)) is not None]
    return sorted(sortable_rows, key=lambda row: _to_float(row.get(key)) or 0.0, reverse=reverse)[:count]


def _top_middle_rows_by_metric(rows: List[Dict[str, Any]], key: str, count: int = 1, reverse: bool = True) -> List[Dict[str, Any]]:
    middle_rows = rows[1:-1] if len(rows) > 2 else rows
    return _top_rows_by_metric(middle_rows, key, count=count, reverse=reverse)


def _primary_damage_event(rows: List[Dict[str, Any]]) -> tuple[str, Dict[str, Any]] | None:
    if not rows:
        return None

    flood_row = next(iter(_top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True)), None)
    if flood_row and (_to_float(flood_row.get("Flood Damage")) or 0.0) > 0:
        return "flood", flood_row

    crop_row = next(iter(_top_middle_rows_by_metric(rows, "Crop Yield", count=1, reverse=False)), None)
    if crop_row and _to_float(crop_row.get("Crop Yield")) is not None:
        return "crop", crop_row

    burden_row = next(iter(_top_middle_rows_by_metric(rows, "Resident Burden", count=1, reverse=True)), None)
    if burden_row and (_to_float(burden_row.get("Resident Burden")) or 0.0) > 0:
        return "burden", burden_row

    return None


def _build_primary_event_focus(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    if not event:
        return "- 主要被害イベント: 特定できる大きな被害イベントは少ない。"

    event_type, row = event
    is_english = req.language.lower().startswith("en")
    if is_english:
        if event_type == "flood":
            return (
                f"- Primary damage event: {_row_year(row)} flood damage reached "
                f"{_format_number(_to_float(row.get('Flood Damage')))}. Policy state that year: levee "
                f"{_format_number(_to_float(row.get('Levee Level')))}, preparedness "
                f"{_format_number(_to_float(row.get('Resident capacity')), digits=2)}, high-risk homes "
                f"{_format_number(_to_float(row.get('risky_house_total')))}, paddy dams "
                f"{_format_number(_to_float(row.get('paddy_dam_area')))}. Evaluate how the policy package absorbed this shock; do not summarize the period as flat."
            )
        if event_type == "crop":
            return (
                f"- Primary damage event: {_row_year(row)} crop yield fell to "
                f"{_format_number(_to_float(row.get('Crop Yield')))}. Policy state that year: water "
                f"{_format_number(_to_float(row.get('available_water')))}, hot days "
                f"{_format_number(_to_float(row.get('Hot Days')))}, heat tolerance "
                f"{_format_number(_to_float(row.get('High Temp Tolerance Level')))}, paddy dams "
                f"{_format_number(_to_float(row.get('paddy_dam_area')))}. Evaluate the event and the policy state in that year."
            )
        return (
            f"- Primary burden event: {_row_year(row)} resident burden reached "
            f"{_format_number(_to_float(row.get('Resident Burden')))}. Tie the burden to observed damage and policy costs."
        )

    if event_type == "flood":
        return (
            f"- 主要被害イベント: {_row_year(row)}年に洪水被害が"
            f"{_format_number(_to_float(row.get('Flood Damage')))}まで出た。"
            f"その年の政策状態は、堤防{_format_number(_to_float(row.get('Levee Level')))}、"
            f"防災能力{_format_number(_to_float(row.get('Resident capacity')), digits=2)}、"
            f"高リスク住宅{_format_number(_to_float(row.get('risky_house_total')))}、"
            f"田んぼダム{_format_number(_to_float(row.get('paddy_dam_area')))}。"
            "評価では「期間全体は横ばい」とまとめず、この被害年に政策が衝撃をどこまで受け止めたかを中心に読む。"
        )
    if event_type == "crop":
        return (
            f"- 主要被害イベント: {_row_year(row)}年に収穫量が"
            f"{_format_number(_to_float(row.get('Crop Yield')))}まで落ちた。"
            f"その年の状態は、水量{_format_number(_to_float(row.get('available_water')))}、"
            f"猛暑日{_format_number(_to_float(row.get('Hot Days')))}、"
            f"高温耐性{_format_number(_to_float(row.get('High Temp Tolerance Level')))}、"
            f"田んぼダム{_format_number(_to_float(row.get('paddy_dam_area')))}。"
            "この年の被害と政策状態を結びつけて評価する。"
        )
    return (
        f"- 主要負担イベント: {_row_year(row)}年に住民負担が"
        f"{_format_number(_to_float(row.get('Resident Burden')))}まで重くなった。"
        "被害と政策コストが生活実感にどう出たかを評価する。"
    )


def _build_policy_event_feedback(req: IntermediateEvaluationRequest) -> List[str]:
    event = _primary_damage_event(req.simulation_rows)
    if not event:
        return ["- 主要被害イベントに結びつけて評価できる政策材料は限定的。"]

    decision_var = req.decision_var.model_dump()
    event_type, row = event
    event_year = _row_year(row)
    lines: List[str] = []

    def is_active(key: str) -> bool:
        return (_to_float(decision_var.get(key, 0)) or 0.0) > 0

    if event_type == "flood":
        lines.append(
            f"- 被害年の焦点: {event_year}年の洪水被害"
            f"{_format_number(_to_float(row.get('Flood Damage')))}を、政策がどこまで弱めたかを見る。"
        )
        if is_active("house_migration_amount"):
            lines.append(
                f"- 住宅移転: {event_year}年時点の高リスク住宅は"
                f"{_format_number(_to_float(row.get('risky_house_total')))}。"
                "移転は被害を受けやすい母数を減らす政策だが、この年に残っていた高リスク住宅が被害の受け皿になった可能性を見る。"
            )
        if is_active("dam_levee_construction_cost"):
            lines.append(
                f"- 河川堤防: {event_year}年時点の堤防レベルは"
                f"{_format_number(_to_float(row.get('Levee Level')))}。"
                "堤防投資は段階的に効くため、被害年までにレベルが上がっていたか、まだ間に合っていなかったかを評価する。"
            )
        if is_active("capacity_building_cost"):
            lines.append(
                f"- 防災訓練・啓発: {event_year}年時点の防災能力は"
                f"{_format_number(_to_float(row.get('Resident capacity')), digits=2)}。"
                "被害をゼロにする政策ではないが、避難・対応力として被害年にどこまで備えが育っていたかを見る。"
            )
        if is_active("paddy_dam_construction_cost"):
            lines.append(
                f"- 田んぼダム: {event_year}年時点の田んぼダム面積は"
                f"{_format_number(_to_float(row.get('paddy_dam_area')))}。"
                "洪水緩和に早めに効きやすい政策として、この被害年に面積が十分だったかを評価する。"
            )
        if is_active("planting_trees_amount"):
            lines.append(
                f"- 植林・森林保全: {event_year}年時点の森林面積は"
                f"{_format_number(_to_float(row.get('Forest Area')))}。"
                "新規植林の成熟は約30年遅れなので、この被害年の直接的な抑制効果は確認しにくい。"
            )
        return lines

    if event_type == "crop":
        lines.append(
            f"- 被害年の焦点: {event_year}年の収穫量"
            f"{_format_number(_to_float(row.get('Crop Yield')))}を、農業・水・暑さ対策がどこまで支えたかを見る。"
        )
        if is_active("paddy_dam_construction_cost"):
            lines.append(
                f"- 田んぼダム: {event_year}年時点の田んぼダム面積は"
                f"{_format_number(_to_float(row.get('paddy_dam_area')))}。水害緩和と農業影響の両面で、この年の支えになったかを見る。"
            )
        if is_active("agricultural_RnD_cost"):
            lines.append(
                f"- 高温耐性品種: {event_year}年時点の高温耐性レベルは"
                f"{_format_number(_to_float(row.get('High Temp Tolerance Level')))}、猛暑日は"
                f"{_format_number(_to_float(row.get('Hot Days')))}。暑さに対して技術効果が出ていたかを見る。"
            )
        if is_active("planting_trees_amount"):
            lines.append(
                f"- 植林・森林保全: {event_year}年時点の森林面積は"
                f"{_format_number(_to_float(row.get('Forest Area')))}。水循環や生態系への長期効果は、この25年では読み切りにくい。"
            )
        return lines

    lines.append(
        f"- 負担年の焦点: {event_year}年の住民負担"
        f"{_format_number(_to_float(row.get('Resident Burden')))}を、被害と政策コストの生活実感として評価する。"
    )
    return lines


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


def _build_turning_point_highlights(rows: List[Dict[str, Any]]) -> List[str]:
    highlights: List[str] = []
    specs = [
        ("Flood Damage", "洪水被害"),
        ("Crop Yield", "収穫量"),
        ("Ecosystem Level", "生態系"),
        ("Resident Burden", "住民負担"),
    ]

    for key, label in specs:
        changes: List[tuple[float, float, Dict[str, Any], Dict[str, Any]]] = []
        for previous, current in zip(rows, rows[1:]):
            before = _to_float(previous.get(key))
            after = _to_float(current.get(key))
            if before is None or after is None:
                continue
            delta = after - before
            changes.append((abs(delta), delta, previous, current))

        if not changes:
            continue

        _, delta, previous, current = max(changes, key=lambda item: item[0])
        highlights.append(
            f"- {label}の最大変化: {_row_year(previous)}年 -> {_row_year(current)}年で"
            f"{_signed_delta(delta)}。変化後の状態: {_row_context(current)}"
        )

    return highlights


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

    primary_event = _primary_damage_event(rows)
    if primary_event:
        event_type, row = primary_event
        if event_type == "flood":
            highlights.append(
                "最優先で評価する被害イベント: "
                f"{_row_year(row)}年の洪水被害={_format_number(_to_float(row.get('Flood Damage')))}。"
                f"政策状態は堤防={_format_number(_to_float(row.get('Levee Level')))}、"
                f"防災能力={_format_number(_to_float(row.get('Resident capacity')), digits=2)}、"
                f"高リスク住宅={_format_number(_to_float(row.get('risky_house_total')))}、"
                f"田んぼダム={_format_number(_to_float(row.get('paddy_dam_area')))}。"
            )
        elif event_type == "crop":
            highlights.append(
                "最優先で評価する被害イベント: "
                f"{_row_year(row)}年の収穫量低迷={_format_number(_to_float(row.get('Crop Yield')))}。"
                f"政策状態は水量={_format_number(_to_float(row.get('available_water')))}、"
                f"猛暑日={_format_number(_to_float(row.get('Hot Days')))}、"
                f"高温耐性={_format_number(_to_float(row.get('High Temp Tolerance Level')))}、"
                f"田んぼダム={_format_number(_to_float(row.get('paddy_dam_area')))}。"
            )
        else:
            highlights.append(
                "最優先で評価する負担イベント: "
                f"{_row_year(row)}年の住民負担={_format_number(_to_float(row.get('Resident Burden')))}。"
            )

    for row in _top_rows_by_metric(rows, "Flood Damage", count=3, reverse=True):
        highlights.append(
            "洪水被害が大きい年: "
            f"{_row_context(row)}。"
            "この年は降雨の強さだけでなく、堤防・防災能力・高リスク住宅の状態も合わせて読む。"
        )

    for row in _top_rows_by_metric(rows, "Crop Yield", count=2, reverse=False):
        highlights.append(
            "収穫量が低い年: "
            f"{_row_context(row)}。"
            "この年は水量・猛暑日・高温耐性・田んぼダム面積を合わせて読む。"
        )

    for row in _top_rows_by_metric(rows, "Resident Burden", count=2, reverse=True):
        highlights.append(
            "住民負担が重い年: "
            f"{_row_context(row)}。"
            "この年は政策コストと被害の両方が生活実感に出やすい。"
        )

    ecosystem_low = next(iter(_top_rows_by_metric(rows, "Ecosystem Level", count=1, reverse=False)), None)
    ecosystem_high = next(iter(_top_rows_by_metric(rows, "Ecosystem Level", count=1, reverse=True)), None)
    if ecosystem_low and ecosystem_high:
        highlights.append(
            "生態系の注目年: "
            f"最低は{_row_year(ecosystem_low)}年の{_format_number(_to_float(ecosystem_low.get('Ecosystem Level')))}、"
            f"最高は{_row_year(ecosystem_high)}年の{_format_number(_to_float(ecosystem_high.get('Ecosystem Level')))}。"
            "被害イベント年と重なるかを確認して読む。"
        )

    return highlights


def _build_yearly_timeline(rows: List[Dict[str, Any]]) -> List[str]:
    timeline: List[str] = []
    for row in rows:
        year = _row_year(row)
        context = _row_context(row)
        prefix = f"{year}年: "
        if context.startswith(prefix):
            context = context[len(prefix):]
        timeline.append(f"| {year} | {context} |")
    return timeline


def _extract_message_content(response: Any) -> str:
    if isinstance(response, dict):
        return str(response.get("message", {}).get("content", "")).strip()

    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", "")
        return str(content).strip()

    return str(response).strip()


def _chat_ollama(
    *,
    model: str,
    messages: List[Dict[str, str]],
    options: Dict[str, Any],
    timeout: float = OLLAMA_TIMEOUT_SECONDS,
    response_format: str | None = None,
) -> Any:
    client = ollama.Client(timeout=timeout)
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "options": options,
    }
    if response_format:
        kwargs["format"] = response_format
    return client.chat(**kwargs)


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
    flood_event = next(iter(_top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True)), None)
    crop_event = next(iter(_top_middle_rows_by_metric(rows, "Crop Yield", count=1, reverse=False)), None)

    fast_labels = _active_policy_labels(decision_var, FAST_RESPONSE_POLICY_KEYS, is_english)
    slow_labels = _active_policy_labels(decision_var, SLOW_RESPONSE_POLICY_KEYS, is_english)
    fast_text = _format_label_list(fast_labels[:2], is_english)
    slow_text = _format_label_list(slow_labels[:2], is_english)

    if is_english:
        if flood_event:
            return (
                f"The {_row_year(flood_event)} flood peak tested the policy package with levees at "
                f"{_format_number(_to_float(flood_event.get('Levee Level')))} and preparedness at "
                f"{_format_number(_to_float(flood_event.get('Resident capacity')), digits=2)}."
            )
        if crop_event:
            return (
                f"The {_row_year(crop_event)} harvest low exposed the combined pressure from water, heat, and farm measures."
            )
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

    if flood_event:
        return (
            f"{_row_year(flood_event)}年の洪水被害ピークでは、堤防"
            f"{_format_number(_to_float(flood_event.get('Levee Level')))}・防災能力"
            f"{_format_number(_to_float(flood_event.get('Resident capacity')), digits=2)}の状態が政策評価の山場になった。"
        )
    if crop_event:
        return (
            f"{_row_year(crop_event)}年の収穫低迷は、水量・猛暑・農業対策が同時に問われた山場だった。"
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
    event = _primary_damage_event(req.simulation_rows)

    fast_labels = _active_policy_labels(decision_var, FAST_RESPONSE_POLICY_KEYS, is_english)
    slow_labels = _active_policy_labels(decision_var, SLOW_RESPONSE_POLICY_KEYS, is_english)

    if is_english:
        if event:
            event_type, row = event
            if event_type == "flood":
                return (
                    f"The {_row_year(row)} flood damage event was the real test of how much levees, relocation, and preparedness absorbed the shock."
                )
            if event_type == "crop":
                return (
                    f"The {_row_year(row)} harvest drop is the clearest test of water, heat tolerance, and paddy-dam policy effects in this period."
                )
            return (
                f"The {_row_year(row)} resident-burden peak shows where policy costs became visible in daily life."
            )
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

    if event:
        event_type, row = event
        if event_type == "flood":
            return (
                f"{_row_year(row)}年の洪水被害は、堤防・移転・防災能力が衝撃をどこまで受け止めたかを示す山場だった。"
            )
        if event_type == "crop":
            return (
                f"{_row_year(row)}年の収穫低迷は、水量・高温耐性・田んぼダムの効き方を見る最もはっきりした試験だった。"
            )
        return f"{_row_year(row)}年の住民負担ピークは、政策コストが生活に見えた瞬間だった。"

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


def _build_policy_assessment(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    is_english = req.language.lower().startswith("en")
    label = _pick_policy_assessment(decision_var, is_english)
    primary_event = _primary_damage_event(req.simulation_rows)
    event_type, event_row = primary_event if primary_event else (None, None)
    flood_row = event_row if event_type == "flood" else next(iter(_top_rows_by_metric(req.simulation_rows, "Flood Damage", count=1, reverse=True)), None)
    crop_row = event_row if event_type == "crop" else next(iter(_top_rows_by_metric(req.simulation_rows, "Crop Yield", count=1, reverse=False)), None)

    if is_english:
        if event_type == "crop" and crop_row:
            return (
                f"{label}: the hardest harvest year was {_row_year(crop_row)}, with water at "
                f"{_format_number(_to_float(crop_row.get('available_water')))}, heat tolerance at "
                f"{_format_number(_to_float(crop_row.get('High Temp Tolerance Level')))}, and paddy dams at "
                f"{_format_number(_to_float(crop_row.get('paddy_dam_area')))}."
            )
        if flood_row:
            return (
                f"{label}: the hardest flood year was {_row_year(flood_row)}, with levees at "
                f"{_format_number(_to_float(flood_row.get('Levee Level')))} and preparedness at "
                f"{_format_number(_to_float(flood_row.get('Resident capacity')), digits=2)}."
            )
        return label

    if event_type == "crop" and crop_row:
        return (
            f"{label}: 収穫が最も落ちた{_row_year(crop_row)}年に、水量"
            f"{_format_number(_to_float(crop_row.get('available_water')))}・田んぼダム"
            f"{_format_number(_to_float(crop_row.get('paddy_dam_area')))}が問われた。"
        )
    if flood_row:
        return (
            f"{label}: 洪水被害が最大だった{_row_year(flood_row)}年に、堤防"
            f"{_format_number(_to_float(flood_row.get('Levee Level')))}・防災能力"
            f"{_format_number(_to_float(flood_row.get('Resident capacity')), digits=2)}が試された。"
        )
    return label


def _event_headline(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    if not event:
        if is_english:
            return "Policy Timing Became the Story"
        return "政策効果の時間差が焦点"

    event_type, row = event
    year = _row_year(row)
    if is_english:
        if event_type == "flood":
            return f"{year} Flood Tested Local Defenses"
        if event_type == "crop":
            return f"{year} Harvest Drop Exposed Farm Risk"
        return f"{year} Burden Peak Reached Residents"

    if event_type == "flood":
        return f"{year}年、水害対策の山場"
    if event_type == "crop":
        return f"{year}年、収穫低迷の警告"
    return f"{year}年、住民負担が表面化"


def _event_subheadline(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    if not event:
        return _build_fallback_subheadline(req)

    event_type, row = event
    decision_var = req.decision_var.model_dump()
    if is_english:
        if event_type == "flood":
            labels = _active_policy_labels(
                decision_var,
                (
                    "house_migration_amount",
                    "dam_levee_construction_cost",
                    "paddy_dam_construction_cost",
                    "capacity_building_cost",
                ),
                True,
            )
            if labels:
                return (
                    f"The key question is whether {_format_label_list(labels[:3], True)} had become enough protection before the peak."
                )
            return (
                "Remaining exposure and thin flood defenses made the rainfall shock harder to absorb."
            )
        if event_type == "crop":
            labels = _active_policy_labels(
                decision_var,
                (
                    "paddy_dam_construction_cost",
                    "agricultural_RnD_cost",
                    "planting_trees_amount",
                ),
                True,
            )
            if labels:
                return (
                    f"Water and heat stress outweighed the visible support from {_format_label_list(labels[:3], True)}."
                )
            return (
                "Water shortage and heat stress hit before farm-support measures showed enough force."
            )
        return "Damage response and policy costs surfaced as a household burden before enough relief was visible."

    if event_type == "flood":
        labels = _active_policy_labels(
            decision_var,
            (
                "house_migration_amount",
                "dam_levee_construction_cost",
                "paddy_dam_construction_cost",
                "capacity_building_cost",
            ),
            False,
        )
        if labels:
            return (
                f"{_format_label_list(labels[:3], False)}が、被害年までに十分な守りへ変わっていたかが評価の分かれ目になった。"
            )
        return (
            "危険地の住宅や防御力不足が残り、強い雨を受け止めにくい状態だった。"
        )
    if event_type == "crop":
        labels = _active_policy_labels(
            decision_var,
            (
                "paddy_dam_construction_cost",
                "agricultural_RnD_cost",
                "planting_trees_amount",
            ),
            False,
        )
        if labels:
            return (
                f"{_format_label_list(labels[:3], False)}の支えを、水不足と暑さの圧力が上回った。"
            )
        return (
            "水不足と暑さに対して、農業を支える政策効果がまだ弱かった。"
        )
    return "被害対応と政策コストが重なり、住民側に負担が先に見えた。"


def _event_lead(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    if not event:
        return _build_fallback_subheadline(req)

    event_type, row = event
    if is_english:
        if event_type == "flood":
            return (
                f"The key feedback comes from {_row_year(row)}: flood damage reached "
                f"{_format_number(_to_float(row.get('Flood Damage')))} when levees were "
                f"{_format_number(_to_float(row.get('Levee Level')))} and preparedness was "
                f"{_format_number(_to_float(row.get('Resident capacity')), digits=2)}."
            )
        if event_type == "crop":
            return (
                f"The policy feedback is clearest in {_row_year(row)}, when crop yield fell to "
                f"{_format_number(_to_float(row.get('Crop Yield')))} under water and heat stress."
            )
        return (
            f"The policy feedback is clearest in {_row_year(row)}, when resident burden reached "
            f"{_format_number(_to_float(row.get('Resident Burden')))}."
        )

    if event_type == "flood":
        return (
            f"平均だけでは見えにくい評価の中心は、{_row_year(row)}年に洪水被害"
            f"{_format_number(_to_float(row.get('Flood Damage')))}が出た局面で、堤防"
            f"{_format_number(_to_float(row.get('Levee Level')))}・防災能力"
            f"{_format_number(_to_float(row.get('Resident capacity')), digits=2)}がどこまで受け止めたかにある。"
        )
    if event_type == "crop":
        return (
            f"評価の中心は{_row_year(row)}年に収穫量が"
            f"{_format_number(_to_float(row.get('Crop Yield')))}まで落ちた局面で、水量・高温耐性・田んぼダムがどこまで支えたかにある。"
        )
    return (
        f"評価の中心は{_row_year(row)}年に住民負担が"
        f"{_format_number(_to_float(row.get('Resident Burden')))}まで重くなった局面で、政策コストが生活にどう出たかにある。"
    )


def _event_body_sentence(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    decision_var = req.decision_var.model_dump()
    if not event:
        if is_english:
            return (
                "The main driver was not one standout disaster year, but a timing gap between policies that can affect risks quickly "
                "and slower measures whose effects were still hard to see."
            )
        return (
            "主因は、1つの大きな被害年というより、早く効く対策と効果が見えるまで時間がかかる対策の差が出たことだ。"
        )

    event_type, row = event
    if is_english:
        if event_type == "flood":
            return (
                f"Main driver: the {_row_year(row)} flood damage came from heavy rainfall pressure meeting remaining exposure and insufficient protection."
            )
        if event_type == "crop":
            return (
                f"Main driver: the {_row_year(row)} harvest drop came from water and heat stress outweighing the visible farm support."
            )
        return (
            f"Main driver: the {_row_year(row)} burden peak came from damage pressure and policy costs becoming visible to residents at the same time."
        )

    if event_type == "flood":
        return (
            f"主因: {_row_year(row)}年の洪水被害は、強い雨の圧力に、危ない場所に残る住宅や防御力不足が重なって大きくなった。"
        )
    if event_type == "crop":
        return (
            f"主因: {_row_year(row)}年の収穫低迷は、水不足と暑さの圧力が、農業を支える政策効果を上回って起きた。"
        )
    return (
        f"主因: {_row_year(row)}年の負担ピークは、被害への対応と政策コストが同じ時期に暮らしの重さとして表れたことだ。"
    )


def _policy_active(decision_var: Dict[str, Any], key: str) -> bool:
    return (_to_float(decision_var.get(key, 0)) or 0.0) > 0


def _increased(start: float | None, end: float | None) -> bool:
    return start is not None and end is not None and end > start + 1e-9


def _decreased(start: float | None, end: float | None) -> bool:
    return start is not None and end is not None and end < start - 1e-9


def _policy_factor_sentence(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    decision_var = req.decision_var.model_dump()
    event_type = event[0] if event else None
    row = event[1] if event else req.simulation_rows[-1]
    first_row = req.simulation_rows[0]

    if is_english:
        if event_type == "flood":
            effects: List[str] = []
            critiques: List[str] = []
            if _policy_active(decision_var, "house_migration_amount"):
                start = _to_float(first_row.get("risky_house_total"))
                end = _to_float(row.get("risky_house_total"))
                if _decreased(start, end):
                    effects.append("relocation reduced the pool of homes exposed to flood damage (High-Risk Households)")
                else:
                    critiques.append("relocation was selected, but its protective effect was not yet clear (High-Risk Households)")
            if _policy_active(decision_var, "dam_levee_construction_cost"):
                start = _to_float(first_row.get("Levee Level"))
                end = _to_float(row.get("Levee Level"))
                if _increased(start, end):
                    effects.append("levee work increased the physical buffer against flooding (Levee Level)")
                else:
                    critiques.append("levee investment was selected, but a stronger buffer was not yet visible (Levee Level)")
            if _policy_active(decision_var, "paddy_dam_construction_cost"):
                start = _to_float(first_row.get("paddy_dam_area"))
                end = _to_float(row.get("paddy_dam_area"))
                if _increased(start, end):
                    effects.append("paddy dams created more room to hold rainfall temporarily (Paddy Dam Area)")
                else:
                    critiques.append("paddy dams were selected, but the storage effect was not yet visible (Paddy Dam Area)")
            if _policy_active(decision_var, "capacity_building_cost"):
                start = _to_float(first_row.get("Resident capacity"))
                end = _to_float(row.get("Resident capacity"))
                if _increased(start, end):
                    effects.append("preparedness training improved the local ability to respond (Resident Capacity)")
                else:
                    critiques.append("preparedness training was selected, but response capacity was not yet visible (Resident Capacity)")
            if effects:
                return "Policies that actually moved: " + "; ".join(effects[:4]) + "."
            if critiques:
                return "Policies that actually moved: no clear protective effect yet; " + "; ".join(critiques[:2]) + "."
            return "Policies that actually moved: no direct flood-risk measure showed a clear protective effect by the event year."

        if event_type == "crop":
            effects = []
            if _policy_active(decision_var, "paddy_dam_construction_cost"):
                start = _to_float(first_row.get("paddy_dam_area"))
                end = _to_float(row.get("paddy_dam_area"))
                if _increased(start, end):
                    effects.append("paddy dams helped buffer water swings around farmland (Paddy Dam Area)(Available Water)")
            if _policy_active(decision_var, "agricultural_RnD_cost"):
                start = _to_float(first_row.get("High Temp Tolerance Level"))
                end = _to_float(row.get("High Temp Tolerance Level"))
                if _increased(start, end):
                    effects.append("heat-tolerant crops worked as a cushion against heat stress (Crop Yield)(Temperature)")
            if _policy_active(decision_var, "planting_trees_amount"):
                start = _to_float(first_row.get("Forest Area"))
                end = _to_float(row.get("Forest Area"))
                if _increased(start, end):
                    effects.append("planting supported the long-term land and ecosystem base (Forest Area)(Ecosystem Level)")
                else:
                    effects.append("planting was selected, but its farm-support effect was still hard to see because the payoff is delayed (Forest Area)")
            if effects:
                return "Policies that actually moved: " + "; ".join(effects[:3]) + "."
            return "Policies that actually moved: no direct farm-stability measure showed a clear support effect by the event year."

        if event_type == "burden":
            return (
                "Policies that actually moved: the visible result was burden on residents before enough damage reduction could be felt."
            )
        return (
            "Policies that actually moved: no single policy stood out clearly, so the period is mostly a timing and visibility problem."
        )

    if event_type == "flood":
        effects: List[str] = []
        critiques: List[str] = []
        if _policy_active(decision_var, "house_migration_amount"):
            start = _to_float(first_row.get("risky_house_total"))
            end = _to_float(row.get("risky_house_total"))
            if _decreased(start, end):
                effects.append("住宅移転は危ない場所に残る世帯を減らし、洪水被害を受けやすい母数を小さくした（高リスク住宅数）")
            else:
                critiques.append("住宅移転は選ばれていたが、被害を受けやすい世帯を減らす効果はまだ見えにくい（高リスク住宅数）")
        if _policy_active(decision_var, "dam_levee_construction_cost"):
            start = _to_float(first_row.get("Levee Level"))
            end = _to_float(row.get("Levee Level"))
            if _increased(start, end):
                effects.append("堤防整備は川からの水を受け止める物理的な守りを強めた（堤防レベル）")
            else:
                critiques.append("堤防整備は選ばれていたが、被害年までに守りの強化としては見えにくい（堤防レベル）")
        if _policy_active(decision_var, "paddy_dam_construction_cost"):
            start = _to_float(first_row.get("paddy_dam_area"))
            end = _to_float(row.get("paddy_dam_area"))
            if _increased(start, end):
                effects.append("田んぼダムは雨水を一時的に受け止める余地を広げた（田んぼダム面積）")
            else:
                critiques.append("田んぼダムは選ばれていたが、雨水を受ける余地としてはまだ見えにくい（田んぼダム面積）")
        if _policy_active(decision_var, "capacity_building_cost"):
            start = _to_float(first_row.get("Resident capacity"))
            end = _to_float(row.get("Resident capacity"))
            if _increased(start, end):
                effects.append("防災訓練は住民が被害に備えて動く力を底上げした（住民防災能力）")
            else:
                critiques.append("防災訓練は選ばれていたが、住民の備えとしてはまだ見えにくい（住民防災能力）")
        if effects:
            return f"実際に効いた政策: {'。'.join(effects[:4])}。"
        if critiques:
            return f"実際に効いた政策: 明確な抑制効果は弱い。{'。'.join(critiques[:2])}。"
        return "実際に効いた政策: 水害を直接弱める政策変化は目立たず、被害を抑える力は限定的だった。"

    if event_type == "crop":
        effects = []
        critiques = []
        if _policy_active(decision_var, "paddy_dam_construction_cost"):
            start = _to_float(first_row.get("paddy_dam_area"))
            end = _to_float(row.get("paddy_dam_area"))
            if _increased(start, end):
                effects.append("田んぼダムは水の変動を受け止める余地を増やし、農業への揺れを和らげる材料になった（田んぼダム面積）（利用可能水量）")
            else:
                critiques.append("田んぼダムは選ばれていたが、水の変動を受け止める効果はまだ見えにくい（田んぼダム面積）（利用可能水量）")
        if _policy_active(decision_var, "agricultural_RnD_cost"):
            start = _to_float(first_row.get("High Temp Tolerance Level"))
            end = _to_float(row.get("High Temp Tolerance Level"))
            if _increased(start, end):
                effects.append("高温耐性品種は暑さで収穫が落ちるリスクを和らげる方向に効いた（収穫量）（気温）")
            else:
                critiques.append("高温耐性品種は選ばれていたが、暑さへの下支えとしてはまだ見えにくい（収穫量）（気温）")
        if _policy_active(decision_var, "planting_trees_amount"):
            start = _to_float(first_row.get("Forest Area"))
            end = _to_float(row.get("Forest Area"))
            if _increased(start, end):
                effects.append("植林は土地や生態系の土台づくりには効いたが、農業被害をすぐ抑える政策ではない（森林面積）（生態系レベル）")
            else:
                critiques.append("植林は成熟に時間がかかるため、この被害年の農業支援としてはまだ見えにくい（森林面積）（生態系レベル）")
        if effects:
            return f"実際に効いた政策: {'。'.join(effects[:3])}。"
        if critiques:
            return f"実際に効いた政策: 明確な下支えは弱い。{'。'.join(critiques[:2])}。"
        return "実際に効いた政策: 水不足や暑さから収穫を守る政策変化は目立たず、下支えは限定的だった。"

    if event_type == "burden":
        return (
            "実際に効いた政策: 被害を弱める実感より先に、負担の重さが住民側に見えた。"
        )
    return (
        "実際に効いた政策: 単独で目立つ政策効果は弱く、政策が結果指標を動かすまでの時間差が大きかった。"
    )


def _chart_reference_sentence(req: IntermediateEvaluationRequest) -> str:
    event = _primary_damage_event(req.simulation_rows)
    is_english = req.language.lower().startswith("en")
    event_type = event[0] if event else None

    if is_english:
        if event_type == "crop":
            return (
                "Critical read: support measures moved, but the harvest still fell, so the scale or timing was not enough. Check (Crop Yield), (Available Water), and (Paddy Dam Area)."
            )
        if event_type == "flood":
            return (
                "Critical read: intermediate protections moved, but the flood peak still arrived, so the scale or timing was not enough. Check (Flood Damage), (High-Risk Households), (Levee Level), and (Paddy Dam Area)."
            )
        return (
            "Critical read: judge the event by whether policy had become real protection by that year. Check (Resident Burden) and the related damage graphs."
        )

    if event_type == "crop":
        return (
            "批判的に見ると、支える政策は動いていても収穫低迷は起きており、政策の量かタイミングが水不足・暑さに追いつかなかった。見るべきグラフ: (収穫量)(利用可能水量)(田んぼダム面積)。"
        )
    if event_type == "flood":
        return (
            "批判的に見ると、中間指標は改善していても洪水被害の山場は残っており、政策の量かタイミングが強い雨に追いつかなかった。見るべきグラフ: (洪水被害)(高リスク住宅数)(堤防レベル)(田んぼダム面積)(住民防災能力)。"
        )
    return (
        "批判的に見ると、政策の効果より先に住民側の負担が表に出ている。見るべきグラフ: (住民負担)(洪水被害)(財政コスト)。"
    )


def _build_readable_article_body(req: IntermediateEvaluationRequest) -> str:
    return "\n\n".join(
        sentence
        for sentence in [
            _event_body_sentence(req),
            _policy_factor_sentence(req),
            _chart_reference_sentence(req),
        ]
        if sentence
    ).strip()


def _format_article_body_sections(text: str, is_english: bool) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", _clean_text(text)).strip()
    if not cleaned:
        return ""

    labels = (
        ("Main driver:", "Policies that actually moved:", "Critical read:")
        if is_english
        else ("主因:", "実際に効いた政策:", "批判的に見ると")
    )

    for label in labels[1:]:
        cleaned = re.sub(rf"\s*{re.escape(label)}", f"\n\n{label}", cleaned)

    cleaned = re.sub(r"\s*見るべきグラフ:", "\n\n見るべきグラフ:", cleaned)
    cleaned = re.sub(r"\s*Check \(", "\n\nCheck (", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _article_body_looks_too_numeric(text: str) -> bool:
    if not text:
        return False

    metric_dump_markers = (
        "洪水被害=",
        "収穫量=",
        "生態系=",
        "住民負担=",
        "水量=",
        "猛暑日=",
        "極端降水=",
        "堤防=",
        "防災能力=",
        "高リスク住宅=",
        "田んぼダム=",
        "高温耐性=",
        "Flood Damage=",
        "Crop Yield=",
        "Ecosystem Level=",
        "Resident Burden=",
        "available_water=",
    )
    marker_count = sum(1 for marker in metric_dump_markers if marker in text)
    if marker_count >= 3:
        return True

    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)

    def is_year(token: str) -> bool:
        normalized = token.replace(",", "")
        return bool(re.fullmatch(r"(19|20|21)\d{2}", normalized))

    non_year_numbers = [token for token in numbers if not is_year(token)]
    return len(non_year_numbers) > 0


def _article_body_lacks_clear_point(text: str, is_english: bool) -> bool:
    if not text:
        return True

    lowered = text.lower()
    if is_english:
        return not (
            "main driver" in lowered
            and ("policies that actually moved" in lowered or "policy effect" in lowered)
            and ("critical read" in lowered or "takeaway" in lowered or "what this shows" in lowered)
            and "check (" in lowered
        )

    return not (
        "主因" in text
        and ("実際に効いた政策" in text or "政策効果" in text)
        and ("批判的" in text or "伝えたいこと" in text or "読み取るべき" in text)
        and "見るべきグラフ" in text
    )


def _same_article_line(left: str, right: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"[\s。．.、,!！?？:：\-—]+", "", _clean_text(value).lower())

    left_normalized = normalize(left)
    right_normalized = normalize(right)
    return bool(left_normalized and left_normalized == right_normalized)


def _ensure_distinct_headline_and_subheadline(
    article: Dict[str, str],
    req: IntermediateEvaluationRequest,
) -> Dict[str, str]:
    focused = dict(article)
    is_english = req.language.lower().startswith("en")

    if not focused.get("headline") or _same_article_line(focused.get("headline", ""), focused.get("subheadline", "")):
        focused["headline"] = _event_headline(req).rstrip("." if is_english else "。")

    if not focused.get("subheadline") or _same_article_line(focused.get("headline", ""), focused.get("subheadline", "")):
        focused["subheadline"] = _event_subheadline(req) or _build_fallback_subheadline(req)

    if _same_article_line(focused.get("headline", ""), focused.get("subheadline", "")):
        focused["subheadline"] = (
            "Policy effect and timing, not just the event size, determine the evaluation."
            if is_english
            else "評価の焦点は被害の大きさだけでなく、政策が間に合っていたかにある。"
        )

    return focused


def _build_fallback_article(
    req: IntermediateEvaluationRequest,
    _event_highlights: List[str],
    fallback_subheadline: str,
    fallback_expert_comment: str,
) -> Dict[str, str]:
    is_english = req.language.lower().startswith("en")

    if is_english:
        headline = _event_headline(req).rstrip(".")
        subheadline = _event_subheadline(req) or fallback_subheadline
        lead = _event_lead(req)
        expert_comment = fallback_expert_comment
        article_body = _build_readable_article_body(req)
    else:
        headline = _event_headline(req).rstrip("。")
        subheadline = _event_subheadline(req) or fallback_subheadline
        lead = _event_lead(req)
        expert_comment = fallback_expert_comment
        article_body = _build_readable_article_body(req)

    return _ensure_distinct_headline_and_subheadline({
        "headline": headline,
        "subheadline": subheadline,
        "lead": lead,
        "expert_comment": expert_comment,
        "policy_assessment": _build_policy_assessment(req),
        "article_body": article_body.strip(),
    }, req)


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


def _has_generic_flat_summary(text: str, is_english: bool) -> bool:
    lowered = text.lower()
    if is_english:
        return any(
            phrase in lowered
            for phrase in (
                "broadly flat",
                "mostly flat",
                "stayed flat",
                "little changed",
                "largely stable",
                "first year",
                "last year",
                "final year",
                "endpoint",
                "start and end",
            )
        )
    return any(
        phrase in text
        for phrase in (
            "概ね横ばい",
            "おおむね横ばい",
            "ほぼ横ばい",
            "横ばいだった",
            "大きく変わらなかった",
            "初年",
            "最終年",
            "最初の年",
            "最後の年",
            "期首",
            "期末",
        )
    )


def _has_endpoint_comparison_summary(text: str, is_english: bool) -> bool:
    if not text:
        return False

    if is_english:
        lowered = text.lower()
        return bool(
            re.search(r"\b(?:improved|worsened|rose|fell|increased|decreased)\s+from\s+[0-9,.\-]+\s+to\s+[0-9,.\-]+", lowered)
            or re.search(r"\bfrom\s+[0-9,.\-]+\s+to\s+[0-9,.\-]+", lowered)
        )

    numeric = r"[0-9０-９][0-9０-９,，.．]*"
    return bool(
        re.search(rf"{numeric}\s*から\s*{numeric}\s*(?:へ|に)\s*(?:改善|悪化|上昇|低下|増加|減少|回復|拡大|縮小)", text)
        or re.search(rf"(?:初期|開始時|期首|最初).*?{numeric}.*?(?:最終|終了時|期末|最後).*?{numeric}", text)
    )


def _is_disallowed_summary_sentence(text: str, is_english: bool) -> bool:
    return _has_generic_flat_summary(text, is_english) or _has_endpoint_comparison_summary(text, is_english)


def _strip_generic_flat_sentences(text: str, event_year: str, is_english: bool) -> str:
    if not text:
        return ""

    if is_english:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        kept = [
            sentence
            for sentence in sentences
            if sentence.strip()
            and not (
                _has_endpoint_comparison_summary(sentence, True)
                or (_has_generic_flat_summary(sentence, True) and event_year not in sentence)
            )
        ]
        return " ".join(kept).strip()

    sentences = re.findall(r"[^。！？]+[。！？]?", text)
    kept = [
        sentence
        for sentence in sentences
        if sentence.strip()
        and not (
            _has_endpoint_comparison_summary(sentence, False)
            or (_has_generic_flat_summary(sentence, False) and event_year not in sentence)
        )
    ]
    return "".join(kept).strip()


def _ensure_event_focused_article(
    article: Dict[str, str],
    req: IntermediateEvaluationRequest,
) -> Dict[str, str]:
    event = _primary_damage_event(req.simulation_rows)
    if not event:
        focused = dict(article)
        is_english = req.language.lower().startswith("en")
        if (
            _article_body_looks_too_numeric(focused.get("article_body", ""))
            or _article_body_lacks_clear_point(focused.get("article_body", ""), is_english)
        ):
            focused["article_body"] = _build_readable_article_body(req)
        focused["article_body"] = _format_article_body_sections(focused.get("article_body", ""), is_english)
        return _ensure_distinct_headline_and_subheadline(focused, req)

    _, row = event
    event_year = _row_year(row)
    is_english = req.language.lower().startswith("en")
    focused = dict(article)
    combined = " ".join(str(value) for value in focused.values())
    has_event_year = event_year in combined
    has_disallowed_summary = _is_disallowed_summary_sentence(combined, is_english)

    if not has_event_year or has_disallowed_summary:
        focused["headline"] = _event_headline(req).rstrip("." if is_english else "。")
        focused["subheadline"] = _event_subheadline(req)
        focused["lead"] = _event_lead(req)

    focused["policy_assessment"] = _build_policy_assessment(req)
    if _is_disallowed_summary_sentence(focused.get("expert_comment", ""), is_english):
        focused["expert_comment"] = _build_fallback_expert_comment(req)

    event_sentence = _event_body_sentence(req)
    body = _strip_generic_flat_sentences(focused.get("article_body", ""), event_year, is_english)
    if _article_body_looks_too_numeric(body) or _article_body_lacks_clear_point(body, is_english):
        body = _build_readable_article_body(req)
    elif event_sentence and event_year not in body:
        body = f"{event_sentence} {body}".strip()
    focused["article_body"] = body or _build_readable_article_body(req) or focused.get("article_body", "")
    focused["article_body"] = _format_article_body_sections(focused["article_body"], is_english)

    return _ensure_distinct_headline_and_subheadline(focused, req)


def _build_expert_comment_prompt(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    mechanism_notes = _build_mechanism_notes(decision_var)
    event_highlights = _build_event_highlights(req.simulation_rows)
    primary_event_focus = _build_primary_event_focus(req)
    policy_event_feedback = _build_policy_event_feedback(req)
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    turning_points = _build_turning_point_highlights(req.simulation_rows)

    if req.language.lower().startswith("en"):
        return f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}

Policies:
{chr(10).join(policy_summary)}

How these policies work in the simulator:
{chr(10).join(mechanism_notes)}

Primary damage event to evaluate first:
{primary_event_focus}

Policy feedback at that event:
{chr(10).join(policy_event_feedback)}

Early/mid/late phase comparison:
{chr(10).join(phase_summaries)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Sharp changes:
{chr(10).join(turning_points)}

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

最優先で評価する被害イベント:
{primary_event_focus}

その被害イベントに対する政策フィードバック:
{chr(10).join(policy_event_feedback)}

前半・中盤・後半の比較:
{chr(10).join(phase_summaries)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

急変・転換点:
{chr(10).join(turning_points)}

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
        response = _chat_ollama(
            model=INTERMEDIATE_EVALUATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": EXPERT_COMMENT_SYSTEM_PROMPT_EN if is_english else EXPERT_COMMENT_SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": _build_expert_comment_prompt(req)},
            ],
            options={"temperature": 0.3, "num_predict": 120},
            response_format="json",
            timeout=12.0,
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
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    turning_points = _build_turning_point_highlights(req.simulation_rows)
    primary_event_focus = _build_primary_event_focus(req)
    policy_event_feedback = _build_policy_event_feedback(req)
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

Primary damage event to evaluate first:
{primary_event_focus}

Policy feedback at that event:
{chr(10).join(policy_event_feedback)}

Early/mid/late phase comparison:
{chr(10).join(phase_summaries)}

Auxiliary 25-year extremes and averages:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {highlight}" for highlight in event_highlights)}

Sharp changes and turning points:
{chr(10).join(turning_points)}

Yearly timeline:
| Year | Indicator summary |
| --- | --- |
{chr(10).join(yearly_timeline)}

Output requirements:
- Return only one JSON object
- policy_assessment must be a compact evaluation phrase that links the policy package to a major event or turning point
- Make headline and subheadline different. Headline is the short conclusion; subheadline explains why and what policy effect to examine.
- Do not repeat the headline wording in subheadline.
- Make lead explain what the major event year and policy state reveal for the player
- Use at least one event or sharp change from the middle of the 25-year period in subheadline, lead, or article_body
- Make article_body explain the cause-and-effect in plain language. Do not list many metric values there.
- In article_body, avoid exact numbers and change amounts; reference useful chart names in parentheses instead.
- If the primary damage event exists, make it the main frame of the report. Do not say the indicators were flat/stable as the main conclusion.
- Do not use endpoint-comparison wording such as "improved from A to B" or "worsened from A to B".
- Avoid generic phrases about short-term vs slow policies unless the yearly data directly supports them
- expert_comment must be one sharp sentence
- Keep the whole article compact and specific
- Mention concrete years where useful, but keep raw numeric values out of article_body
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

最優先で評価する被害イベント:
{primary_event_focus}

その被害イベントに対する政策フィードバック:
{chr(10).join(policy_event_feedback)}

前半・中盤・後半の比較:
{chr(10).join(phase_summaries)}

25年の補助集計（最大・最小・平均）:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {highlight}" for highlight in event_highlights)}

急変・転換点:
{chr(10).join(turning_points)}

年次データ:
| 年 | 指標の要約 |
| --- | --- |
{chr(10).join(yearly_timeline)}

出力条件:
- JSON オブジェクトのみを返す
- headline と subheadline は同じ文章にしない
- headline は短く、「何が山場だったか」が一目で分かる結論にする
- subheadline は headline を繰り返さず、「なぜそう読めるか」「どの政策効果を見るべきか」を1文で補足する
- 本文は3〜5文程度
- lead は、重大イベント年の被害と政策状態から読み手に役立つフィードバックを1文で書く
- subheadline, lead, article_body のどれかで、25年の中間で起きたイベントまたは急変年を少なくとも1つ取り上げる
- 重大イベントを取り上げる時は、その年の堤防・防災能力・高リスク住宅・田んぼダム・高温耐性など政策状態も一緒に読む
- article_body は、指標の数字を並べず、「何が要因で、何を読み取るべきか」を直感的に説明する
- article_body は、「主因は何か」「政策は効いたのか／効きにくかったのか」「結局何を伝えたいのか」が分かる2〜4文にする
- article_body では、実際に効いた政策、どう効いたか、逆にどの政策は足りなかったかを読者が直感的に分かる文章で書く
- article_body の具体的な数字や変化量は書かず、詳しい値や年ごとの動きは括弧内の指標グラフで確認できると自然に案内する
- article_body では、参照すべきグラフ名を必ず括弧で書く。例: (収穫量)(利用可能水量)
- article_body では指標名をただ羅列せず、原因・政策の効き方・批判的な読み取りの3点を中心に書く
- 最優先の被害イベントがある場合、それをレポートの主軸にする。「指標は横ばい・安定」だけを主結論にしない
- 「収穫量はAからBへ改善した」「洪水被害はAからBへ悪化した」のような期間始点・終点の比較文は禁止
- 年次データに基づかない「短期で効く」「時間差がある」だけの定型的な総括は避ける
- expert_comment は、識者がズバッと言う1文にする
- 新聞一面の語り口で書く
- 中学生にも分かるやさしい日本語にする
- 今後の助言は禁止
- 具体的な年は使ってよいが、数値は本文では増やしすぎない
- policy_assessment は、政策パッケージと重大イベントまたは転換点を結びつけた短い評価句にする
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

    is_english = req.language.lower().startswith("en")
    model_name = INTERMEDIATE_EVALUATION_MODEL

    try:
        response = _chat_ollama(
            model=INTERMEDIATE_EVALUATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.2, "num_predict": 260},
            response_format="json",
        )
    except Exception:
        response = None

    if response is None:
        article = fallback_article
        model_name = f"{INTERMEDIATE_EVALUATION_MODEL} (fallback)"
    else:
        feedback_text = _extract_message_content(response)
        article = _normalize_article_payload(_extract_json_object(feedback_text), fallback_article)
        article = _ensure_event_focused_article(article, req)
        if _is_canned_subheadline(article["subheadline"], is_english):
            article["subheadline"] = fallback_subheadline
        article["expert_comment"] = _generate_expert_comment(req, article["expert_comment"])
        if _is_disallowed_summary_sentence(article["expert_comment"], is_english):
            article["expert_comment"] = _build_fallback_expert_comment(req)

    article = _ensure_event_focused_article(article, req)
    feedback = _compose_feedback(article, is_english)

    return IntermediateEvaluationResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=model_name,
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
