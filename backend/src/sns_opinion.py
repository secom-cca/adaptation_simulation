from __future__ import annotations

import random
from typing import Any, Dict, List

import ollama

from intermediate_evaluation import (
    INTERMEDIATE_EVALUATION_MODEL,
    _build_event_highlights,
    _build_metric_summary,
    _build_policy_summary,
    _extract_json_object,
    _extract_message_content,
    _mean,
    _to_float,
)
from models import SnsReactionsRequest, SnsReactionsResponse


SNS_REACTIONS_MODEL = INTERMEDIATE_EVALUATION_MODEL

SYSTEM_PROMPT_JA = """
あなたは地域SNSの投稿を生成するAIです。
25年分の結果をもとに、住民が実際に短く投稿しそうな日本語のSNS文を作ってください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。説明、Markdown、コードフェンスは禁止です。
- キーは posts だけにし、値は短文文字列の配列にしてください。
- 5件の投稿を返してください。
- 1投稿は短く、口語で、生活実感がある文にしてください。
- 良い反応だけでなく、不安や不満、様子見も混ぜてください。
- 同じ論点の繰り返しは避けてください。
- 将来の助言は禁止です。
""".strip()

SYSTEM_PROMPT_EN = """
You generate local social media reactions.
Based on the 25-year results, write short posts that sound like everyday residents.

Required rules:
- Output only one JSON object. No explanation, no markdown, no code fences.
- Use only the key posts, with an array of short strings.
- Return 5 posts.
- Keep each post short, colloquial, and grounded in daily life.
- Mix positive, negative, and uncertain reactions.
- Avoid repeating the same point.
- Do not give future advice.
""".strip()


def _average_metric(rows: List[Dict[str, Any]], key: str) -> float | None:
    return _mean(_to_float(row.get(key)) for row in rows)


def _normalize_posts(payload: Dict[str, Any] | None, fallback_posts: List[str]) -> List[str]:
    if not isinstance(payload, dict):
        return fallback_posts

    raw_posts = payload.get("posts")
    if not isinstance(raw_posts, list):
        return fallback_posts

    cleaned_posts: List[str] = []
    seen = set()
    for item in raw_posts:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned_posts.append(text)
        if len(cleaned_posts) == 5:
            break

    return cleaned_posts if cleaned_posts else fallback_posts


def _build_fallback_posts(req: SnsReactionsRequest) -> List[str]:
    rows = req.simulation_rows
    last_row = rows[-1]
    seed = (req.regeneration_token or 0) + req.stage_index * 997
    generator = random.Random(seed)

    flood_avg = _average_metric(rows, "Flood Damage") or 0.0
    crop_avg = _average_metric(rows, "Crop Yield") or 0.0
    water_avg = _average_metric(rows, "available_water") or 0.0
    ecosystem_last = _to_float(last_row.get("Ecosystem Level")) or 0.0
    capacity_last = _to_float(last_row.get("Resident capacity")) or 0.0
    risky_houses_last = _to_float(last_row.get("risky_house_total")) or 0.0

    if req.language.lower().startswith("en"):
        candidates = [
            "Flood alerts feel easier to trust than they used to." if flood_avg < 50_000 else "Big rain still makes me nervous every single time.",
            "Rice harvest feels steadier lately." if crop_avg >= 3500 else "Crop numbers still look rough for people living off the fields.",
            "I think I hear more birds by the river now." if ecosystem_last >= 55 else "Nature still doesn't feel fully back around the river.",
            "The drills are annoying but at least people know where to go now." if capacity_last >= 0.35 else "We keep talking about preparedness, but I still don't feel ready.",
            "Fewer homes seem stuck in the risky zone now." if risky_houses_last < 12_000 else "Too many houses still feel one storm away from trouble.",
            "Water doesn't feel as tight in summer this year." if water_avg >= 1200 else "Every dry spell still turns into a water worry fast.",
            "It feels like some measures worked, but the bill must be huge.",
        ]
    else:
        candidates = [
            "避難の案内、前よりは信じられるようになった。" if flood_avg < 50_000 else "大雨のたびにまだ普通にこわい。",
            "ここ数年は米の出来が少し安定してきた気がする。" if crop_avg >= 3500 else "農家目線だと収穫の波がまだきつい。",
            "川沿いで鳥を見る回数が増えた気がする。" if ecosystem_last >= 55 else "自然は戻ってきたって言うほどではないかな。",
            "訓練は面倒だけど、前より動き方は分かる。" if capacity_last >= 0.35 else "防災って言われても、まだ身についてる感じはしない。",
            "危ない場所の家が少し減ったのは大きい。" if risky_houses_last < 12_000 else "危ない場所に住む人、まだかなり多いよね。",
            "夏の水の不安が少しだけ減った。" if water_avg >= 1200 else "渇水っぽい年はやっぱり不安が残る。",
            "対策は進んだんだろうけど、結局いくらかかったんだろう。",
        ]

    generator.shuffle(candidates)
    return candidates[:5]


def _build_sns_prompt(req: SnsReactionsRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    metric_summary = _build_metric_summary(req.simulation_rows)
    event_highlights = _build_event_highlights(req.simulation_rows)

    if req.language.lower().startswith("en"):
        return f"""
Checkpoint year: {req.checkpoint_year}
Period: {req.period_start_year}-{req.period_end_year}
Stage: {req.stage_index}
Regeneration token: {req.regeneration_token}

Policies:
{chr(10).join(policy_summary)}

Metric summary:
{chr(10).join(metric_summary)}

Key events:
{chr(10).join(f"- {item}" for item in event_highlights)}

Return 5 short, varied resident-style posts in JSON.
""".strip()

    return f"""
評価時点: {req.checkpoint_year}年
対象期間: {req.period_start_year}年-{req.period_end_year}年
評価対象段階: 第{req.stage_index}段階
再生成トークン: {req.regeneration_token}

政策一覧:
{chr(10).join(policy_summary)}

実績サマリー:
{chr(10).join(metric_summary)}

重要イベント:
{chr(10).join(f"- {item}" for item in event_highlights)}

生活者が書きそうな短い投稿を5件、JSONで返してください。
""".strip()


def generate_sns_reactions(req: SnsReactionsRequest) -> SnsReactionsResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    fallback_posts = _build_fallback_posts(req)

    try:
        response = ollama.chat(
            model=SNS_REACTIONS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": _build_sns_prompt(req)},
            ],
            options={"temperature": 0.8, "num_predict": 220},
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama sns reactions failed: {exc}") from exc

    response_text = _extract_message_content(response)
    posts = _normalize_posts(_extract_json_object(response_text), fallback_posts)

    return SnsReactionsResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=SNS_REACTIONS_MODEL,
        posts=posts,
    )
