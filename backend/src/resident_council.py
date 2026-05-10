from __future__ import annotations

from typing import Any, Dict, List

from intermediate_evaluation import (
    INTERMEDIATE_EVALUATION_MODEL,
    _build_event_highlights,
    _build_metric_summary,
    _build_phase_summaries,
    _build_policy_effect_snapshots,
    _build_policy_summary,
    _build_turning_point_highlights,
    _build_yearly_timeline,
    _chat_ollama,
    _extract_json_object,
    _extract_message_content,
    _format_number,
    _mean,
    _row_context,
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
- 可能なら具体的な年、被害、収穫、負担、水量、猛暑、防災能力などを1つ入れてください。
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
- Include one concrete year, damage, harvest, burden, water, heat, or preparedness detail where possible.
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


def _metric_snapshot(req: IntermediateEvaluationRequest) -> Dict[str, float | None]:
    rows = req.simulation_rows
    last = rows[-1]
    return {
        "avg_flood": _average_metric(rows, "Flood Damage"),
        "avg_crop": _average_metric(rows, "Crop Yield"),
        "avg_burden": _average_metric(rows, "Resident Burden"),
        "avg_hot_days": _average_metric(rows, "Hot Days"),
        "avg_water": _average_metric(rows, "available_water"),
        "last_ecosystem": _to_float(last.get("Ecosystem Level")),
        "last_levee": _to_float(last.get("Levee Level")),
        "last_capacity": _to_float(last.get("Resident capacity")),
        "last_urban": _to_float(last.get("Urban Level")),
    }


def _average_slice(rows: List[Dict[str, Any]], key: str, *, tail: bool = False, count: int = 5) -> float | None:
    if not rows:
        return None
    target_rows = rows[-count:] if tail else rows[:count]
    return _average_metric(target_rows, key)


def _outlook_line(rows: List[Dict[str, Any]], key: str, label: str, lower_is_better: bool = False) -> str:
    early = _average_slice(rows, key)
    late = _average_slice(rows, key, tail=True)
    if early is None or late is None:
        return f"{label}: 見通し材料が不足"

    delta = late - early
    threshold = max(abs(early) * 0.08, 1.0)
    if abs(delta) <= threshold:
        state = "終盤も序盤と大きく変わらず、先行きは読み切りにくい"
    else:
        improved = delta < 0 if lower_is_better else delta > 0
        state = "終盤に改善の手応えがある" if improved else "終盤に不安が強まる"
    return f"{label}: 序盤平均{_format_number(early)}、終盤平均{_format_number(late)}で、{state}"


def _persona_event_briefs(req: IntermediateEvaluationRequest, persona_key: str) -> List[str]:
    rows = req.simulation_rows
    briefs: List[str] = []

    if persona_key == "child_future":
        for row in _top_middle_rows_by_metric(rows, "Hot Days", count=1, reverse=True):
            briefs.append(f"- 猛暑の記憶: {_row_context(row)}")
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            briefs.append(f"- 水害への不安: {_row_context(row)}")
        briefs.append(f"- 先行き: {_outlook_line(rows, 'Ecosystem Level', '生態系')}")
        return briefs

    if persona_key == "entrepreneur":
        for row in _top_middle_rows_by_metric(rows, "Resident Burden", count=1, reverse=True):
            briefs.append(f"- 生活コスト・事業コストの重い年: {_row_context(row)}")
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            briefs.append(f"- 事業継続を揺らす水害年: {_row_context(row)}")
        briefs.append(f"- 先行き: {_outlook_line(rows, 'Resident Burden', '住民負担', lower_is_better=True)}")
        return briefs

    if persona_key == "council_member":
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            briefs.append(f"- 説明責任が重くなる水害年: {_row_context(row)}")
        for row in _top_middle_rows_by_metric(rows, "Resident Burden", count=1, reverse=True):
            briefs.append(f"- 住民負担が問われる年: {_row_context(row)}")
        briefs.append(f"- 先行き: {_outlook_line(rows, 'Flood Damage', '洪水被害', lower_is_better=True)}")
        return briefs

    for row in _top_middle_rows_by_metric(rows, "Crop Yield", count=1, reverse=False):
        briefs.append(f"- 収穫が落ち込んだ年: {_row_context(row)}")
    for row in _top_middle_rows_by_metric(rows, "available_water", count=1, reverse=False):
        briefs.append(f"- 水が苦しかった年: {_row_context(row)}")
    briefs.append(f"- 先行き: {_outlook_line(rows, 'Crop Yield', '収穫量')}")
    return briefs


def _score_tone(score: int) -> str:
    if score >= 7:
        return "満足寄り"
    if score <= 4:
        return "不満寄り"
    return "複雑"


def _build_fallback_short_voice(persona_key: str, score: int, req: IntermediateEvaluationRequest) -> str:
    m = _metric_snapshot(req)
    flood = _format_number(m["avg_flood"])
    crop = _format_number(m["avg_crop"])
    burden = _format_number(m["avg_burden"])
    eco = _format_number(m["last_ecosystem"])
    flood_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Flood Damage", count=1, reverse=True)), None)
    crop_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Crop Yield", count=1, reverse=False)), None)
    burden_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Resident Burden", count=1, reverse=True)), None)
    hot_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Hot Days", count=1, reverse=True)), None)

    if persona_key == "child_future":
        if score >= 7:
            return f"最後の生態系が{eco}まで残ったのはうれしい。大人になる頃も、川で遊べる町であってほしい。"
        if hot_event:
            return f"{_row_year(hot_event)}年みたいに暑さがきつい年を思うと、僕たちの遊ぶ場所が減っていく気がしてこわい。"
        return "暑い日や水害の話を聞くたびに、僕たちの遊ぶ場所がなくなる気がしてこわい。"
    if persona_key == "entrepreneur":
        if score >= 7:
            return f"平均負担が{burden}で収まるなら、事業を続けながらこの町に投資する余地はある。"
        if burden_event:
            return f"{_row_year(burden_event)}年の負担の重さを見ると、店も人材も長期計画を立てにくい。正直かなり厳しい。"
        return "災害と負担が読めない町では、店も人材も計画を立てにくい。正直かなり厳しい。"
    if persona_key == "council_member":
        if score >= 7:
            return f"平均洪水被害{flood}なら、投資の説明はまだ住民に通せる水準だと思います。"
        if flood_event:
            return f"{_row_year(flood_event)}年の水害を前に、政策の効果と住民負担を胸を張って説明するのは難しいです。"
        return "この被害と住民負担を前に、議会で胸を張って説明するのは難しいです。"
    if score >= 7:
        return f"収穫量の平均が{crop}なら、田畑を次に渡す希望はまだ残っとる。"
    if crop_event:
        return f"{_row_year(crop_event)}年の収穫の落ち込みは忘れられん。水と暑さがこの先も揺れるなら若い者が残れん。"
    return "水と収穫が揺れるたび、畑で生きてきた身には胸が痛む。これでは若い者が残れん。"


def _build_fallback_detailed_voice(persona_key: str, score: int, req: ResidentInterviewRequest) -> str:
    persona = PERSONAS[persona_key]
    m = _metric_snapshot(req)
    flood = _format_number(m["avg_flood"])
    crop = _format_number(m["avg_crop"])
    burden = _format_number(m["avg_burden"])
    hot_days = _format_number(m["avg_hot_days"])
    eco = _format_number(m["last_ecosystem"])
    tone = _score_tone(score)
    flood_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Flood Damage", count=1, reverse=True)), None)
    crop_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Crop Yield", count=1, reverse=False)), None)
    burden_event = next(iter(_top_middle_rows_by_metric(req.simulation_rows, "Resident Burden", count=1, reverse=True)), None)

    if persona_key == "child_future":
        return (
            f"僕は{persona['role']}として、この25年を{tone}に感じています。平均の暑い日は{hot_days}日で、"
            f"最後の生態系は{eco}でした。{_row_year(flood_event) if flood_event else '水害が大きかった'}年のような話が出るたびに、"
            "大人になった時にこの町が本当に安心できる場所なのか不安になります。"
        )
    if persona_key == "entrepreneur":
        return (
            f"私は{persona['role']}として、数字よりも毎年の不確実さが重く見えました。平均住民負担は{burden}、"
            f"平均洪水被害は{flood}です。{_row_year(burden_event) if burden_event else '負担が重い'}年のような局面があると、"
            "事業は希望だけでは続きません。人を雇い、設備に投資するには、"
            "災害時にも生活と商売が止まりきらないという手応えが必要です。"
        )
    if persona_key == "council_member":
        return (
            f"私は{persona['role']}として、この結果を住民に説明する場面をまず想像します。平均洪水被害{flood}、"
            f"平均住民負担{burden}という数字は、政策の成果と痛みの両方を示しています。"
            f"{_row_year(flood_event) if flood_event else '大きな水害が出た'}年を住民が覚えている限り、"
            "支持されるかどうかは、被害を抑えた実感を住民が持てるかにかかっています。"
        )
    return (
        f"わしは{persona['role']}として、平均収穫量{crop}と水の具合を見てしまう。"
        f"最後の生態系は{eco}でも、畑は一年ごとの天気に振り回される。"
        f"{_row_year(crop_event) if crop_event else '収穫が落ちた'}年のような年がまた来ると思うと、"
        "若い者に胸を張って継げとは言いにくい。"
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
        if short_voice:
            residents_by_key[key].short_voice = short_voice
        residents_by_key[key].score = scores[key]

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

Each short_voice must either remember a concrete event year or express an outlook based on the late-period trend.
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
各 short_voice は、具体的なイベント年を振り返るか、終盤の傾向から見た今後の暮らしへの見通しを含めてください。
JSONのみを返してください:
{{"residents":[{{"persona_key":"child_future","score":1,"short_voice":"..."}}]}}
""".strip()


def _build_resident_interview_prompt(req: ResidentInterviewRequest, score: int) -> str:
    persona = PERSONAS[req.persona_key]
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    metric_summary = _build_metric_summary(req.simulation_rows)
    event_highlights = _build_event_highlights(req.simulation_rows)
    snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    turning_points = _build_turning_point_highlights(req.simulation_rows)
    persona_evidence = _persona_event_briefs(req, req.persona_key)
    yearly_timeline = _build_yearly_timeline(req.simulation_rows)

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

Metric summary:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Sharp changes and turning points:
{chr(10).join(turning_points)}

Evidence this persona is likely to remember:
{chr(10).join(persona_evidence)}

Yearly data:
{chr(10).join(yearly_timeline)}

Write only the interview answer. No heading, no markdown.
Sound concrete, personal, and emotionally honest. Mention one event year or turning point and give this persona's outlook for life ahead.
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

実績サマリー:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

急変・転換点:
{chr(10).join(turning_points)}

この住民が記憶しやすい材料:
{chr(10).join(persona_evidence)}

年次データ:
{chr(10).join(yearly_timeline)}

出力はインタビュー回答本文だけにしてください。見出し、Markdown、箇条書きは禁止です。
25年間のデータを、その住民が生活の中でどう受け止めたかとして、具体的で感情のある日本語で答えてください。
イベント年または転換点を1つ以上振り返り、この先の暮らしへの見通しもにじませてください。
直感的な訴え、具体的な経験、悲痛な叫び、満足している点の熱い表明のどれでも構いません。
180〜280文字程度にしてください。
""".strip()


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
                    "content": "あなたは指定された住民ペルソナです。データに基づき、生活者として率直に語ってください。",
                },
                {"role": "user", "content": _build_resident_interview_prompt(req, score)},
            ],
            options={"temperature": 0.6, "num_predict": 260},
            timeout=20.0,
        )
        detailed_voice = _extract_message_content(response)
    except Exception:
        detailed_voice = ""

    if not detailed_voice:
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
