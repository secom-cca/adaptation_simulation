from __future__ import annotations

import re
from typing import Any, Dict, List

from intermediate_evaluation import (
    INTERMEDIATE_EVALUATION_MODEL,
    _build_event_highlights,
    _build_metric_summary,
    _build_phase_summaries,
    _build_policy_effect_snapshots,
    _build_policy_summary,
    _build_turning_point_highlights,
    _chat_ollama,
    _extract_json_object,
    _extract_message_content,
    _format_number,
    _mean,
    _row_year,
    _top_middle_rows_by_metric,
    _to_float,
)
from models import (
    IntermediateEvaluationRequest,
    ResidentCouncilResponse,
    ResidentInterviewRequest,
    ResidentInterviewResponse,
    ResidentVoice,
)


RESIDENT_COUNCIL_MODEL = INTERMEDIATE_EVALUATION_MODEL

PERSONAS: Dict[str, Dict[str, str]] = {
    "child_future": {
        "display_name": "未来を見つめる小学生",
        "handle": "@future_child",
        "avatar": "🧒",
        "role": "小学生",
        "focus": "未来、生態系、暑さ、安心して遊べる川や森",
    },
    "entrepreneur": {
        "display_name": "若手起業家",
        "handle": "@local_founder",
        "avatar": "👩‍💼",
        "role": "若手起業家",
        "focus": "都市の利便性、事業継続、持続可能性、生活コスト",
    },
    "council_member": {
        "display_name": "市議会議員",
        "handle": "@city_council",
        "avatar": "🏛",
        "role": "市議会議員",
        "focus": "予算効率、防災インフラ、住民負担、説明責任",
    },
    "farmer": {
        "display_name": "元農家",
        "handle": "@old_farmer",
        "avatar": "🧑‍🌾",
        "role": "隠居中の元農家",
        "focus": "収穫量、水、田畑、日々の平穏、次世代の農業",
    },
}

PERSONA_KEYS = tuple(PERSONAS.keys())

SYSTEM_PROMPT_JA = """
あなたは地域のAI住民評議会です。
25年分の結果を読み、4人の固定ペルソナごとに満足度スコアと短い市民の声を生成してください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。説明、Markdown、コードフェンスは禁止です。
- JSON は {"residents": [...]} の形にしてください。
- residents の各要素は persona_key, score, short_voice だけを持ってください。
- persona_key は child_future, entrepreneur, council_member, farmer の4つを必ず1回ずつ使ってください。
- score は必ず 1 から 10 の整数にしてください。5は中立、6以上は満足寄り、4以下は不満寄りです。
- short_voice は各ペルソナの一人称の短い一言にしてください。
- short_voice は25年データの実感に結びつけ、一般論だけにしないでください。
- short_voice は、重大イベントを振り返る一言、またはこの先の暮らしへの見通しがにじむ一言にしてください。
- short_voice は「満足しています」「心配です」だけの定型文にせず、ペルソナの口から出る熱のある一文にしてください。
- 4人の short_voice は同じ文型にせず、怒り、不安、希望、納得、悔しさなどをスコアに合わせて出し分けてください。
- 可能なら具体的なイベント年、政策の手応え、被害、収穫、負担、猛暑、防災能力などを1つ入れてください。
- 対象期間外の具体年、実在しない出来事、固定されていない年齢設定は作らないでください。
- 市民の声は、満足、怒り、不安、悲痛な叫び、具体的な経験の吐露など、データとペルソナに合う自然な反応にしてください。
""".strip()

SYSTEM_PROMPT_EN = """
You are the AI residents' council.
Read the 25-year results and generate one satisfaction score and one short resident voice for each fixed persona.

Required rules:
- Output only one JSON object. No explanation, no markdown, no code fences.
- Use the shape {"residents": [...]}.
- Each resident object must include only persona_key, score, and short_voice.
- Use each persona_key exactly once: child_future, entrepreneur, council_member, farmer.
- score must be an integer from 1 to 10. 5 means neutral, 6-10 satisfied, 1-4 dissatisfied.
- short_voice must sound like that persona's immediate first-person reaction.
- Ground short_voice in the 25-year data, not generic commentary.
- Make short_voice either look back at a major event or reveal that persona's outlook for life ahead.
- Do not use bland stock phrases. Make each short_voice one vivid sentence with persona-specific emotion.
- Do not give all four residents the same sentence structure.
- Include one concrete event year, policy effect, damage, harvest, burden, heat, or preparedness detail where possible.
- Do not invent specific years outside the target period, fictional events, or exact ages not provided.
""".strip()


def _scale_score(value: float | None, min_value: float, max_value: float, lower_is_better: bool = False) -> float:
    if value is None or max_value <= min_value:
        return 5.0
    ratio = (value - min_value) / (max_value - min_value)
    ratio = max(0.0, min(1.0, ratio))
    if lower_is_better:
        ratio = 1.0 - ratio
    if ratio <= 0.5:
        return 1.0 + ratio * 8.0
    return 5.0 + (ratio - 0.5) * 10.0


def _coerce_score(value: Any) -> int | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return max(1, min(10, int(round(numeric))))


def _average_metric(rows: List[Dict[str, Any]], key: str) -> float | None:
    return _mean(_to_float(row.get(key)) for row in rows)


def _build_fallback_scores(req: IntermediateEvaluationRequest) -> Dict[str, int]:
    rows = req.simulation_rows
    last_row = rows[-1]

    flood_avg = _average_metric(rows, "Flood Damage")
    crop_avg = _average_metric(rows, "Crop Yield")
    water_avg = _average_metric(rows, "available_water")
    hot_days_avg = _average_metric(rows, "Hot Days")
    cost_avg = _average_metric(rows, "Municipal Cost")
    burden_avg = _average_metric(rows, "Resident Burden")

    ecosystem_last = _to_float(last_row.get("Ecosystem Level"))
    urban_last = _to_float(last_row.get("Urban Level"))
    levee_last = _to_float(last_row.get("Levee Level"))
    capacity_last = _to_float(last_row.get("Resident capacity"))

    child_future = round(
        (
            _scale_score(ecosystem_last, 0, 100)
            + _scale_score(hot_days_avg, 20, 120, lower_is_better=True)
            + _scale_score(flood_avg, 0, 200000, lower_is_better=True)
        )
        / 3
    )
    entrepreneur = round(
        (
            _scale_score(urban_last, 0, 100)
            + _scale_score(cost_avg, 0, 4_000_000, lower_is_better=True)
            + _scale_score(burden_avg, 0, 120_000, lower_is_better=True)
        )
        / 3
    )
    council_member = round(
        (
            _scale_score(flood_avg, 0, 200000, lower_is_better=True)
            + _scale_score(levee_last, 100, 400)
            + _scale_score(capacity_last, 0, 1)
        )
        / 3
    )
    farmer = round(
        (
            _scale_score(crop_avg, 0, 6000)
            + _scale_score(water_avg, 0, 3000)
            + _scale_score(flood_avg, 0, 200000, lower_is_better=True)
        )
        / 3
    )

    return {
        "child_future": max(1, min(10, child_future)),
        "entrepreneur": max(1, min(10, entrepreneur)),
        "council_member": max(1, min(10, council_member)),
        "farmer": max(1, min(10, farmer)),
    }


def _normalize_scores(payload: Dict[str, Any] | None, fallback_scores: Dict[str, int]) -> Dict[str, int]:
    normalized = dict(fallback_scores)
    if not isinstance(payload, dict):
        return normalized

    source = payload.get("scores") if isinstance(payload.get("scores"), dict) else payload
    if isinstance(source, dict):
        for key in PERSONA_KEYS:
            coerced = _coerce_score(source.get(key))
            if coerced is not None:
                normalized[key] = coerced

    residents = payload.get("residents")
    if isinstance(residents, list):
        for item in residents:
            if not isinstance(item, dict):
                continue
            key = item.get("persona_key")
            if key not in PERSONA_KEYS:
                continue
            coerced = _coerce_score(item.get("score"))
            if coerced is not None:
                normalized[key] = coerced

    return normalized


def _average_slice(rows: List[Dict[str, Any]], key: str, *, tail: bool = False, count: int = 5) -> float | None:
    if not rows:
        return None
    target_rows = rows[-count:] if tail else rows[:count]
    return _average_metric(target_rows, key)


def _intuitive_trend_line(
    rows: List[Dict[str, Any]],
    key: str,
    label: str,
    *,
    lower_is_better: bool = False,
) -> str:
    early = _average_slice(rows, key)
    late = _average_slice(rows, key, tail=True)
    if early is None or late is None:
        return f"{label}: 変化を読む材料が不足。必要なら({label})を確認。"

    delta = late - early
    threshold = max(abs(early) * 0.08, 1.0)
    if abs(delta) <= threshold:
        return f"{label}: 終盤も大きな改善・悪化は読み取りにくい。必要なら({label})を確認。"

    improved = delta < 0 if lower_is_better else delta > 0
    if improved:
        return f"{label}: 終盤は序盤より暮らしやすい方向に動いた。必要なら({label})を確認。"
    return f"{label}: 終盤ほど不安が強まる方向に動いた。必要なら({label})を確認。"


def _metric_text(row: Dict[str, Any] | None, key: str, *, digits: int | None = None) -> str | None:
    if not row:
        return None
    value = _to_float(row.get(key))
    if value is None:
        return None
    if digits is None:
        return _format_number(value)
    return _format_number(value, digits=digits)


def _focused_event_line(
    row: Dict[str, Any] | None,
    specs: List[tuple[str, str, int | None]],
    takeaway: str,
) -> str | None:
    if not row:
        return None

    parts: List[str] = []
    for key, label, digits in specs:
        value = _metric_text(row, key, digits=digits)
        if value is not None:
            parts.append(f"{label}{value}")

    detail = "、".join(parts)
    prefix = f"{_row_year(row)}年"
    if detail:
        prefix = f"{prefix}: {detail}"
    return f"{prefix}。{takeaway}"


def _metric_moved(rows: List[Dict[str, Any]], key: str, *, lower_is_better: bool = False) -> bool:
    if not rows:
        return False
    start = _to_float(rows[0].get(key))
    end = _to_float(rows[-1].get(key))
    if start is None or end is None:
        return False
    threshold = max(abs(start) * 0.05, 0.01)
    delta = end - start
    if lower_is_better:
        return delta < -threshold
    return delta > threshold


def _policy_effect_fragments(req: IntermediateEvaluationRequest, persona_key: str) -> List[str]:
    rows = req.simulation_rows
    decision_var = req.decision_var.model_dump()

    def active(key: str) -> bool:
        amount = _to_float(decision_var.get(key, 0))
        return amount is not None and amount > 0

    fragments: List[str] = []

    if active("capacity_building_cost"):
        if _metric_moved(rows, "Resident capacity"):
            fragments.append("防災訓練・啓発は、災害時に慌てず動ける手応えとして効いている")
        else:
            fragments.append("防災訓練・啓発は選ばれているが、住民の備えとして見えるまでには弱い")

    if active("dam_levee_construction_cost"):
        if _metric_moved(rows, "Levee Level"):
            fragments.append("河川堤防は、水害への守りが積み上がった政策として受け止めやすい")
        else:
            fragments.append("河川堤防は投資していても、期間内に守りの変化が見えにくい")

    if active("house_migration_amount"):
        if _metric_moved(rows, "risky_house_total", lower_is_better=True):
            fragments.append("住宅移転は、危ない場所に残る世帯を減らす形で効いている")
        else:
            fragments.append("住宅移転は、危険な場所から暮らしを逃がす効果がまだ見えにくい")

    if active("paddy_dam_construction_cost"):
        if _metric_moved(rows, "paddy_dam_area"):
            fragments.append("田んぼダムは、水害や水管理を受け止める場所が増えた政策として見える")
        else:
            fragments.append("田んぼダムは選ばれているが、田畑の安心に結びつく手応えが弱い")

    if active("agricultural_RnD_cost"):
        if _metric_moved(rows, "High Temp Tolerance Level"):
            fragments.append("高温耐性品種は、暑さに耐える農業の支えとして効き始めている")
        else:
            fragments.append("高温耐性品種は投資していても、農家が安心できるほどの変化はまだ薄い")

    if active("planting_trees_amount"):
        fragments.append("植林・森林保全は長期の約束だが、この期間だけでは暑さや生態系への効きが見えにくい")

    if persona_key == "entrepreneur" and active("transportation_invest"):
        if _metric_moved(rows, "Urban Level"):
            fragments.append("交通投資は、人と商売の動きを支える材料になっている")
        else:
            fragments.append("交通投資はあるが、商売のしやすさとしてはまだ実感が弱い")

    return fragments


def _persona_policy_read(req: IntermediateEvaluationRequest, persona_key: str) -> str:
    fragments = _policy_effect_fragments(req, persona_key)
    if not fragments:
        return "- 政策の読み取り: 目立つ政策投入が少なく、住民の評価は被害や負担の実感に左右されやすい。"

    selected = _select_persona_policy_fragments(fragments, persona_key)
    return "- 政策の読み取り: " + "。".join(selected[:3]) + "。"


def _select_persona_policy_fragments(fragments: List[str], persona_key: str) -> List[str]:
    if persona_key == "child_future":
        priority = ("植林", "防災", "田んぼ", "住宅", "堤防")
    elif persona_key == "entrepreneur":
        priority = ("交通", "住宅", "堤防", "防災")
    elif persona_key == "council_member":
        priority = ("堤防", "防災", "住宅", "田んぼ")
    else:
        priority = ("高温", "田んぼ", "植林")

    relevant = [fragment for fragment in fragments if any(word in fragment for word in priority)]
    if not relevant:
        return fragments

    def rank(fragment: str) -> int:
        for index, word in enumerate(priority):
            if word in fragment:
                return index
        return len(priority)

    return sorted(relevant, key=rank)


def _persona_event_briefs(req: IntermediateEvaluationRequest, persona_key: str) -> List[str]:
    rows = req.simulation_rows
    briefs: List[str] = []

    if persona_key == "child_future":
        for row in _top_middle_rows_by_metric(rows, "Hot Days", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [("Hot Days", "猛暑日", None), ("Ecosystem Level", "生態系", None)],
                "外で遊ぶ安心と、将来の自然への不安に直結する。",
            )
            if line:
                briefs.append(f"- 猛暑の記憶: {line}")
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [("Flood Damage", "洪水被害", None), ("Resident capacity", "防災能力", 2)],
                "子どもにとっては、数字よりも町で安全に過ごせるかの記憶になる。",
            )
            if line:
                briefs.append(f"- 水害への不安: {line}")
        briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Ecosystem Level', '生態系')}")
        briefs.append(_persona_policy_read(req, persona_key))
        return briefs

    if persona_key == "entrepreneur":
        for row in _top_middle_rows_by_metric(rows, "Resident Burden", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [("Resident Burden", "住民負担", None), ("Municipal Cost", "自治体コスト", None)],
                "生活費と事業コストが読みにくくなり、投資や雇用の判断を重くする。",
            )
            if line:
                briefs.append(f"- 生活コスト・事業コストの重い年: {line}")
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [("Flood Damage", "洪水被害", None), ("Urban Level", "都市機能", None)],
                "店や人の動きが止まる不安として受け止める。",
            )
            if line:
                briefs.append(f"- 事業継続を揺らす水害年: {line}")
        briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Resident Burden', '住民負担', lower_is_better=True)}")
        briefs.append(_persona_policy_read(req, persona_key))
        return briefs

    if persona_key == "council_member":
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [
                    ("Flood Damage", "洪水被害", None),
                    ("Levee Level", "堤防", None),
                    ("Resident capacity", "防災能力", 2),
                    ("risky_house_total", "高リスク住宅", None),
                ],
                "住民に『備えは十分だったのか』を説明しなければならない年。",
            )
            if line:
                briefs.append(f"- 説明責任が重くなる水害年: {line}")
        for row in _top_middle_rows_by_metric(rows, "Resident Burden", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [("Resident Burden", "住民負担", None), ("Municipal Cost", "自治体コスト", None)],
                "政策の痛みを住民にどう説明するかが問われる。",
            )
            if line:
                briefs.append(f"- 住民負担が問われる年: {line}")
        briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Flood Damage', '洪水被害', lower_is_better=True)}")
        briefs.append(_persona_policy_read(req, persona_key))
        return briefs

    for row in _top_middle_rows_by_metric(rows, "Crop Yield", count=1, reverse=False):
        line = _focused_event_line(
            row,
            [
                ("Crop Yield", "収穫量", None),
                ("available_water", "水量", None),
                ("Hot Days", "猛暑日", None),
                ("High Temp Tolerance Level", "高温耐性", None),
            ],
            "農家にとっては、政策評価より先に『今年食えるか、次に継げるか』の記憶になる。",
        )
        if line:
            briefs.append(f"- 収穫が落ち込んだ年: {line}")
    for row in _top_middle_rows_by_metric(rows, "available_water", count=1, reverse=False):
        line = _focused_event_line(
            row,
            [("available_water", "水量", None), ("paddy_dam_area", "田んぼダム", None)],
            "田畑を守る政策が本当に支えになったかを疑う材料になる。",
        )
        if line:
            briefs.append(f"- 水が苦しかった年: {line}")
    briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Crop Yield', '収穫量')}")
    briefs.append(_persona_policy_read(req, persona_key))
    return briefs


def _score_tone(score: int) -> str:
    if score >= 7:
        return "満足寄り"
    if score <= 4:
        return "不満寄り"
    return "複雑"


def _main_event_year(rows: List[Dict[str, Any]], metric: str, *, reverse: bool = True) -> str | None:
    row = next(iter(_top_middle_rows_by_metric(rows, metric, count=1, reverse=reverse)), None)
    if not row:
        return None
    return f"{_row_year(row)}年"


def _voice_policy_fragment(req: IntermediateEvaluationRequest, persona_key: str, score: int) -> str:
    fragments = _policy_effect_fragments(req, persona_key)
    if not fragments:
        return "政策の手応えが薄く、暮らしの不安がそのまま評価に出ている"
    fragments = _select_persona_policy_fragments(fragments, persona_key)

    positive_markers = ("効いている", "受け止めやすい", "効き始めている", "材料になっている", "増えた")
    critical_markers = ("弱い", "見えにくい", "薄い")
    positives = [fragment for fragment in fragments if any(marker in fragment for marker in positive_markers)]
    criticals = [fragment for fragment in fragments if any(marker in fragment for marker in critical_markers)]

    if score >= 6 and positives:
        return positives[0]
    if score <= 4 and criticals:
        return criticals[0]
    return fragments[0]


def _voice_policy_clause(req: IntermediateEvaluationRequest, persona_key: str, score: int) -> str:
    fragment = _voice_policy_fragment(req, persona_key, score)
    return fragment.rstrip("。")


def _short_policy_clause(req: IntermediateEvaluationRequest, persona_key: str, score: int) -> str:
    fragment = _voice_policy_clause(req, persona_key, score)
    replacements = (
        ("防災訓練・啓発は、災害時に慌てず動ける手応えとして効いている", "防災訓練で備えが生活に根づいている"),
        ("防災訓練・啓発は選ばれているが、住民の備えとして見えるまでには弱い", "防災訓練がまだ暮らしの安心まで届いていない"),
        ("河川堤防は、水害への守りが積み上がった政策として受け止めやすい", "堤防の守りが積み上がっている"),
        ("河川堤防は投資していても、期間内に守りの変化が見えにくい", "堤防投資の守りがまだ見えにくい"),
        ("住宅移転は、危ない場所に残る世帯を減らす形で効いている", "住宅移転で危ない場所に残る世帯が減っている"),
        ("住宅移転は、危険な場所から暮らしを逃がす効果がまだ見えにくい", "住宅移転が危ない暮らしを逃がしきれていない"),
        ("田んぼダムは、水害や水管理を受け止める場所が増えた政策として見える", "田んぼダムが水害と水管理の受け皿になっている"),
        ("田んぼダムは選ばれているが、田畑の安心に結びつく手応えが弱い", "田んぼダムが田畑の安心まで届いていない"),
        ("高温耐性品種は、暑さに耐える農業の支えとして効き始めている", "高温耐性品種が暑さに耐える支えになっている"),
        ("高温耐性品種は投資していても、農家が安心できるほどの変化はまだ薄い", "高温耐性品種が農家の安心まで届いていない"),
        ("植林・森林保全は長期の約束だが、この期間だけでは暑さや生態系への効きが見えにくい", "植林は長期の約束にとどまっている"),
        ("交通投資は、人と商売の動きを支える材料になっている", "交通投資が人と商売の動きを支えている"),
        ("交通投資はあるが、商売のしやすさとしてはまだ実感が弱い", "交通投資が商売の実感まで届いていない"),
        ("政策の手応えが薄く、暮らしの不安がそのまま評価に出ている", "政策の手応えが暮らしに届いていない"),
    )
    for source, replacement in replacements:
        if fragment == source:
            return replacement
    return fragment


def _build_fallback_short_voice(persona_key: str, score: int, req: IntermediateEvaluationRequest) -> str:
    rows = req.simulation_rows
    flood_year = _main_event_year(rows, "Flood Damage", reverse=True) or "水害が大きかった年"
    crop_year = _main_event_year(rows, "Crop Yield", reverse=False) or "収穫が落ちた年"
    burden_year = _main_event_year(rows, "Resident Burden", reverse=True) or "負担が重かった年"
    hot_year = _main_event_year(rows, "Hot Days", reverse=True) or "暑さがきつかった年"
    policy_clause = _short_policy_clause(req, persona_key, score)

    if persona_key == "child_future":
        if score >= 7:
            return f"{hot_year}は怖かったけど、{policy_clause}と感じられるなら、僕はまだ川で遊べる未来を信じたい。"
        return f"{hot_year}みたいな暑さが続くなら、外で笑って遊ぶ未来まで削られている気がして悔しい。"
    if persona_key == "entrepreneur":
        if score >= 7:
            return f"{burden_year}の重さはある。それでも{policy_clause}と感じられるなら、この町で事業を伸ばす覚悟は残る。"
        return f"{burden_year}の負担と災害リスクを見たら、人を雇う計画まで冷える。夢だけでは店は守れない。"
    if persona_key == "council_member":
        if score >= 7:
            return f"{flood_year}の教訓は重いが、{policy_clause}と説明できるなら、住民に向き合う材料はある。"
        return f"{flood_year}の被害を前に、この負担で納得してくださいとは議会で言えません。"
    if score >= 7:
        return f"{crop_year}の落ち込みを越えて{policy_clause}と感じられるなら、田畑を次に渡す言葉がまだ残る。"
    return f"{crop_year}の収穫の落ち込みは忘れられん。これでは若い者に『残れ』とはよう言えん。"


def _build_fallback_detailed_voice(persona_key: str, score: int, req: ResidentInterviewRequest) -> str:
    persona = PERSONAS[persona_key]
    tone = _score_tone(score)
    rows = req.simulation_rows
    flood_year = _main_event_year(rows, "Flood Damage", reverse=True) or "水害が大きかった年"
    crop_year = _main_event_year(rows, "Crop Yield", reverse=False) or "収穫が落ちた年"
    burden_year = _main_event_year(rows, "Resident Burden", reverse=True) or "負担が重かった年"
    hot_year = _main_event_year(rows, "Hot Days", reverse=True) or "暑さがきつかった年"
    policy_clause = _voice_policy_clause(req, persona_key, score)
    period = f"{req.period_start_year}年から{req.period_end_year}年"

    if persona_key == "child_future":
        return (
            f"僕は{persona['role']}として、{period}を{tone}に見ています。いちばん残るのは{hot_year}の暑さで、"
            f"外で遊ぶ場所がだんだん細っていく感じがしました。政策については、{policy_clause}。"
            "それが毎日の安心まで届かないなら、未来を守ったとは言い切れません。"
        )
    if persona_key == "entrepreneur":
        return (
            f"私は{persona['role']}として、{period}の評価は{tone}です。{burden_year}のように負担が跳ねると、"
            f"採用も設備投資も一気に慎重になります。政策については、{policy_clause}。"
            "災害やコストで街が止まる不安が残る限り、起業家は強気に賭けきれません。"
        )
    if persona_key == "council_member":
        return (
            f"私は{persona['role']}として、{period}の結果を住民説明の場で考えます。{flood_year}を覚えている住民には、"
            f"{policy_clause}と正面から言えるかが重要です。一方で負担の痛みも残るので、"
            "政策を選んだ理由と、守れなかった部分の説明から逃げてはいけません。"
        )
    return (
        f"わしは{persona['role']}として、{period}を{tone}に受け止めとる。忘れられんのは{crop_year}の収穫の落ち込みじゃ。"
        f"政策については、{policy_clause}。それでも田畑は一年悪ければ暮らしが傾く。"
        "若い者に継げと言うには、政策が畑の安心として腹に落ちるところまで必要じゃ。"
    )


def _build_fallback_residents(
    req: IntermediateEvaluationRequest,
    scores: Dict[str, int],
) -> List[ResidentVoice]:
    residents: List[ResidentVoice] = []
    for key in PERSONA_KEYS:
        persona = PERSONAS[key]
        residents.append(
            ResidentVoice(
                persona_key=key,
                display_name=persona["display_name"],
                handle=persona["handle"],
                avatar=persona["avatar"],
                role=persona["role"],
                focus=persona["focus"],
                score=scores[key],
                short_voice=_build_fallback_short_voice(key, scores[key], req),
            )
        )
    return residents


def _mentions_outside_period(text: str, start_year: int, end_year: int) -> bool:
    for match in re.finditer(r"(\d{4})年", text):
        year = int(match.group(1))
        if year < start_year or year > end_year:
            return True
    return False


def _short_voice_is_weak(text: str, req: IntermediateEvaluationRequest) -> bool:
    stripped = text.strip()
    if len(stripped) < 18:
        return True
    if _mentions_outside_period(stripped, req.period_start_year, req.period_end_year):
        return True

    weak_phrases = (
        "満足しています",
        "不満です",
        "心配です",
        "安心です",
        "よかったです",
        "評価しています",
        "将来が心配",
        "I am satisfied",
        "I am worried",
    )
    if any(phrase in stripped for phrase in weak_phrases) and len(stripped) < 40:
        return True

    return False


def _normalize_residents(
    payload: Dict[str, Any] | None,
    req: IntermediateEvaluationRequest,
    scores: Dict[str, int],
) -> List[ResidentVoice]:
    residents_by_key = {resident.persona_key: resident for resident in _build_fallback_residents(req, scores)}
    if not isinstance(payload, dict) or not isinstance(payload.get("residents"), list):
        return [residents_by_key[key] for key in PERSONA_KEYS]

    for item in payload["residents"]:
        if not isinstance(item, dict):
            continue
        key = item.get("persona_key")
        if key not in residents_by_key:
            continue
        short_voice = str(item.get("short_voice") or "").strip()
        if short_voice and not _short_voice_is_weak(short_voice, req):
            residents_by_key[key].short_voice = short_voice
        residents_by_key[key].score = scores[key]

    seen: set[str] = set()
    for key in PERSONA_KEYS:
        voice = residents_by_key[key].short_voice.strip()
        if voice in seen:
            residents_by_key[key].short_voice = _build_fallback_short_voice(key, scores[key], req)
            voice = residents_by_key[key].short_voice.strip()
        seen.add(voice)

    return [residents_by_key[key] for key in PERSONA_KEYS]


def _persona_lines() -> List[str]:
    return [
        f"- {key}: {persona['display_name']} / 重視すること: {persona['focus']}"
        for key, persona in PERSONAS.items()
    ]


def _persona_evidence_lines(req: IntermediateEvaluationRequest) -> List[str]:
    lines: List[str] = []
    for key, persona in PERSONAS.items():
        lines.append(f"- {key} ({persona['display_name']}) が反応しやすい材料:")
        lines.extend(f"  {brief}" for brief in _persona_event_briefs(req, key))
    return lines


def _build_resident_council_prompt(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    metric_summary = _build_metric_summary(req.simulation_rows)
    event_highlights = _build_event_highlights(req.simulation_rows)
    snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    turning_points = _build_turning_point_highlights(req.simulation_rows)
    persona_evidence = _persona_evidence_lines(req)

    if req.language.lower().startswith("en"):
        return f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}

Personas:
{chr(10).join(_persona_lines())}

Policies:
{chr(10).join(policy_summary)}

Observed policy evidence:
{chr(10).join(snapshots)}

Early/mid/late phase comparison:
{chr(10).join(phase_summaries)}

Metric summary:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Sharp changes and turning points:
{chr(10).join(turning_points)}

Persona-specific evidence to use:
{chr(10).join(persona_evidence)}

Output priority:
- Score from the persona's values, not from an overall average.
- short_voice must be one vivid first-person sentence, not a policy report.
- Prefer persona-specific evidence above the general metric summary.
- Mention only years inside {req.period_start_year}-{req.period_end_year}.

Each short_voice must either remember a concrete event year, name a policy effect or failure, or express an outlook based on the late-period trend.
Return JSON only:
{{"residents":[{{"persona_key":"child_future","score":1,"short_voice":"..."}}]}}
""".strip()

    return f"""
評価時点: {req.checkpoint_year}年
対象期間: {req.period_start_year}年-{req.period_end_year}年
評価対象段階: 第{req.stage_index}段階

ペルソナ:
{chr(10).join(_persona_lines())}

政策一覧:
{chr(10).join(policy_summary)}

政策ごとの観測証拠:
{chr(10).join(snapshots)}

前半・中盤・後半の比較:
{chr(10).join(phase_summaries)}

実績サマリー:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

急変・転換点:
{chr(10).join(turning_points)}

ペルソナ別に反応しやすい材料:
{chr(10).join(persona_evidence)}

この25年の結果に対して、各ペルソナがどれだけ納得するかを採点し、一言の市民の声を返してください。
重要視して出力する内容:
- スコアは全体平均ではなく、各ペルソナが重視する価値から決めてください。
- short_voice は政策レポートではなく、住民本人の口から出る熱のある一文にしてください。
- 実績サマリーよりも、ペルソナ別に反応しやすい材料を優先してください。
- {req.period_start_year}年-{req.period_end_year}年の対象期間外の具体年や、固定されていない年齢設定は作らないでください。

各 short_voice は、具体的なイベント年、政策が効いた/足りなかった点、または終盤の傾向から見た今後の暮らしへの見通しを含めてください。
JSONのみを返してください:
{{"residents":[{{"persona_key":"child_future","score":1,"short_voice":"..."}}]}}
""".strip()


def _build_resident_interview_prompt(req: ResidentInterviewRequest, score: int) -> str:
    persona = PERSONAS[req.persona_key]
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    persona_evidence = _persona_event_briefs(req, req.persona_key)

    if req.language.lower().startswith("en"):
        return f"""
You are being interviewed as this resident:
- Name: {persona['display_name']}
- Role: {persona['role']}
- Main concerns: {persona['focus']}
- Satisfaction score: {score}/10

Period: {req.period_start_year}-{req.period_end_year}
Policies:
{chr(10).join(policy_summary)}

Observed evidence:
{chr(10).join(snapshots)}

Early/mid/late phase comparison:
{chr(10).join(phase_summaries)}

Evidence this persona is likely to remember:
{chr(10).join(persona_evidence)}

Output priorities:
- Answer as the resident, not as an analyst.
- Focus on the strongest lived event or turning point, one policy that clearly helped or failed, and the emotion behind the score.
- Do not recite all metrics. Use metric names only as background.
- Do not invent exact ages, years outside {req.period_start_year}-{req.period_end_year}, or events not in the data.

Write only the interview answer. No heading, no markdown.
Sound concrete, personal, and emotionally honest. Mention one event year or turning point, explain one policy effect or criticism, and give this persona's outlook for life ahead.
Keep it around 90-140 words.
""".strip()

    return f"""
あなたは次の住民としてインタビューに答えています。
- 名前: {persona['display_name']}
- 立場: {persona['role']}
- 重視すること: {persona['focus']}
- 満足度: {score}/10

対象期間: {req.period_start_year}年-{req.period_end_year}年
政策一覧:
{chr(10).join(policy_summary)}

政策ごとの観測証拠:
{chr(10).join(snapshots)}

前半・中盤・後半の比較:
{chr(10).join(phase_summaries)}

この住民が記憶しやすい材料:
{chr(10).join(persona_evidence)}

このインタビューで重要視する出力:
- 分析者ではなく、この住民本人として答える。
- 一番記憶に残った出来事または転換点を1つ選び、生活実感として語る。
- 実際に効いた政策、または足りなかった政策批評を1つ以上入れる。
- 満足度 {score}/10 と矛盾しない、納得・怒り・不安・希望の温度を出す。
- 全指標を読み上げない。必要なら指標名は背景として触れるだけにする。
- {req.period_start_year}年-{req.period_end_year}年の対象期間外の具体年、実在しない出来事、固定されていない年齢設定は作らない。

出力はインタビュー回答本文だけにしてください。見出し、Markdown、箇条書きは禁止です。
25年間のデータを、その住民が生活の中でどう受け止めたかとして、具体的で感情のある日本語で答えてください。
イベント年または転換点を1つ以上振り返り、政策が効いた/足りなかった理由と、この先の暮らしへの見通しをにじませてください。
直感的な訴え、具体的な経験、悲痛な叫び、満足している点の熱い表明のどれでも構いません。
180〜280文字程度にしてください。
""".strip()


def _clean_interview_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip().strip('"').strip()


def _interview_voice_is_invalid(req: ResidentInterviewRequest, text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 40:
        return True
    if stripped.startswith("{") or stripped.startswith("[") or "persona_key" in stripped or "detailed_voice" in stripped:
        return True

    if _mentions_outside_period(stripped, req.period_start_year, req.period_end_year):
        return True

    return False


def generate_resident_council(req: IntermediateEvaluationRequest) -> ResidentCouncilResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    fallback_scores = _build_fallback_scores(req)
    payload: Dict[str, Any] | None = None

    try:
        response = _chat_ollama(
            model=RESIDENT_COUNCIL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": _build_resident_council_prompt(req)},
            ],
            options={"temperature": 0.35, "num_predict": 320},
            response_format="json",
            timeout=12.0,
        )
        payload = _extract_json_object(_extract_message_content(response))
    except Exception:
        payload = None

    scores = _normalize_scores(payload, fallback_scores)
    residents = _normalize_residents(payload, req, scores)

    return ResidentCouncilResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=RESIDENT_COUNCIL_MODEL,
        scores=scores,
        residents=residents,
    )


def generate_resident_interview(req: ResidentInterviewRequest) -> ResidentInterviewResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")
    if req.persona_key not in PERSONAS:
        raise ValueError(f"Unknown persona_key: {req.persona_key}")

    fallback_scores = _build_fallback_scores(req)
    score = req.score if req.score is not None else fallback_scores[req.persona_key]
    score = max(1, min(10, int(score)))
    persona = PERSONAS[req.persona_key]
    detailed_voice = ""

    try:
        response = _chat_ollama(
            model=RESIDENT_COUNCIL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは指定された住民ペルソナです。"
                        "対象期間内のデータだけを根拠に、生活者として率直に語ってください。"
                        "分析レポート、箇条書き、JSON、対象期間外の具体年や固定されていない年齢設定は禁止です。"
                    ),
                },
                {"role": "user", "content": _build_resident_interview_prompt(req, score)},
            ],
            options={"temperature": 0.6, "num_predict": 260},
            timeout=20.0,
        )
        detailed_voice = _clean_interview_text(_extract_message_content(response))
    except Exception:
        detailed_voice = ""

    if not detailed_voice or _interview_voice_is_invalid(req, detailed_voice):
        detailed_voice = _build_fallback_detailed_voice(req.persona_key, score, req)

    return ResidentInterviewResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=RESIDENT_COUNCIL_MODEL,
        persona_key=req.persona_key,
        display_name=persona["display_name"],
        detailed_voice=detailed_voice,
    )
