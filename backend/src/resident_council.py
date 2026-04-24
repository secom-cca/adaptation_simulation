from __future__ import annotations

from typing import Any, Dict, List

import ollama

from intermediate_evaluation import (
    INTERMEDIATE_EVALUATION_MODEL,
    _build_event_highlights,
    _build_metric_summary,
    _build_policy_effect_snapshots,
    _build_policy_summary,
    _extract_json_object,
    _extract_message_content,
    _mean,
    _to_float,
)
from models import IntermediateEvaluationRequest, ResidentCouncilResponse


RESIDENT_COUNCIL_MODEL = INTERMEDIATE_EVALUATION_MODEL
PERSONA_KEYS = ("child_future", "entrepreneur", "council_member", "farmer")

SYSTEM_PROMPT_JA = """
あなたは地域のAI住民評議会です。
25年分の結果を読んで、4人の固定ペルソナがその結果にどれだけ納得したかを1から10の整数で採点してください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。説明、Markdown、コードフェンスは禁止です。
- キーは child_future, entrepreneur, council_member, farmer の4つだけにしてください。
- 値は必ず 1 から 10 の整数にしてください。
- 5を基準点とし、5は「どちらとも言えない標準的な納得」、6以上は納得寄り、4以下は不満寄りとして採点してください。
- コメント文や理由文は返さないでください。
- 小学生は未来・生態系・暑さ、若手起業家は都市利便性・持続可能性・コスト、
  市議会議員は予算効率・防災インフラ、農家は収穫量・水・田畑・平穏を重視します。
""".strip()

SYSTEM_PROMPT_EN = """
You are the AI residents' council.
Read the 25-year results and score how satisfied each fixed persona would be on a 1-10 integer scale.

Required rules:
- Output only one JSON object. No explanation, no markdown, no code fences.
- Use only these four keys: child_future, entrepreneur, council_member, farmer.
- Each value must be an integer from 1 to 10.
- Use 5 as the baseline: 5 means neutral or standard satisfaction, 6-10 means more satisfied, and 1-4 means less satisfied.
- Do not add any comments or reasons.
- The child focuses on the future, ecology, and heat.
- The entrepreneur focuses on urban convenience, sustainability, and costs.
- The council member focuses on budget efficiency and flood infrastructure.
- The farmer focuses on crop yield, water, farmland, and day-to-day stability.
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
    for key in PERSONA_KEYS:
        coerced = _coerce_score(source.get(key))
        if coerced is not None:
            normalized[key] = coerced
    return normalized


def _build_resident_council_prompt(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    metric_summary = _build_metric_summary(req.simulation_rows)
    event_highlights = _build_event_highlights(req.simulation_rows)
    snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)

    if req.language.lower().startswith("en"):
        return f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}

Policies:
{chr(10).join(policy_summary)}

Observed policy evidence:
{chr(10).join(snapshots)}

Metric summary:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Score each persona by how convinced they would feel about the 25-year outcome.
Return JSON only.
""".strip()

    return f"""
評価時点: {req.checkpoint_year}年
対象期間: {req.period_start_year}年-{req.period_end_year}年
評価対象段階: 第{req.stage_index}段階

政策一覧:
{chr(10).join(policy_summary)}

政策ごとの観測証拠:
{chr(10).join(snapshots)}

実績サマリー:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

この25年の結果に対して、各ペルソナがどれだけ納得するかを採点してください。
JSONのみを返してください。
""".strip()


def generate_resident_council(req: IntermediateEvaluationRequest) -> ResidentCouncilResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    fallback_scores = _build_fallback_scores(req)

    try:
        response = ollama.chat(
            model=RESIDENT_COUNCIL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": _build_resident_council_prompt(req)},
            ],
            options={"temperature": 0.1, "num_predict": 120},
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama resident council failed: {exc}") from exc

    response_text = _extract_message_content(response)
    scores = _normalize_scores(_extract_json_object(response_text), fallback_scores)

    return ResidentCouncilResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=RESIDENT_COUNCIL_MODEL,
        scores=scores,
    )
