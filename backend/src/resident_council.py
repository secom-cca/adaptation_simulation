from __future__ import annotations

import random
import re
from typing import Any, Dict, List

from intermediate_evaluation import (
    INTERMEDIATE_EVALUATION_MODEL,
    _build_phase_summaries,
    _build_policy_effect_snapshots,
    _build_policy_summary,
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
RESIDENT_COUNCIL_MODEL_ATTEMPTS = (
    (
        RESIDENT_COUNCIL_MODEL,
        {"temperature": 0.8, "top_p": 0.95, "repeat_penalty": 1.12, "num_predict": 320},
        20.0,
    ),
)
RESIDENT_INTERVIEW_MODEL_ATTEMPTS = (
    (
        RESIDENT_COUNCIL_MODEL,
        {"temperature": 0.7, "top_p": 0.9, "num_predict": 360},
        25.0,
    ),
)
PERSONAS: Dict[str, Dict[str, str]] = {
    "riverside_resident": {
        "display_name": "河川付近の住民",
        "handle": "@riverside_voice",
        "avatar": "🏠",
        "role": "川の近くで暮らす住民",
        "focus": "洪水被害、避難、防災能力、堤防、高リスク住宅",
    },
    "farmer": {
        "display_name": "農家",
        "handle": "@local_farmer",
        "avatar": "🧑‍🌾",
        "role": "地域で農業を営む農家",
        "focus": "収穫量、水、猛暑、田んぼダム、農業の継続",
    },
    "environmentalist": {
        "display_name": "環境活動家",
        "handle": "@river_ecology",
        "avatar": "🌿",
        "role": "流域の自然を守る環境活動家",
        "focus": "生態系、森林、水環境、構造物対策の環境影響",
    },
}

PERSONA_KEYS = tuple(PERSONAS.keys())
_RANDOM = random.SystemRandom()

POST_STYLE_HINTS_JA = (
    "最初に感情を短く吐き出し、その理由を一つだけ続ける",
    "暮らしの中で目に浮かぶ一場面から始め、説明しすぎずに終える",
    "身近な誰かへ話しかけるように書き、最後に小さな問いを残す",
    "良かった点と割り切れない点を一つずつ、少し迷いのある口調で書く",
    "短い独り言のように、言い切りと余韻を組み合わせる",
    "驚き、悔しさ、安堵のどれかを先に出し、数字ではなく生活の変化で語る",
    "具体的な音、天気、作業、生きものの様子のどれか一つを入口にする",
    "少し率直な愚痴や注文を交えつつ、その人なりの希望もにじませる",
)

POST_STYLE_HINTS_EN = (
    "Open with a brief emotional reaction, then give just one reason",
    "Begin with one vivid everyday scene and end without over-explaining",
    "Write as if speaking to a neighbor and leave a small question at the end",
    "Mention one encouraging sign and one unresolved concern in a hesitant voice",
    "Use the rhythm of a short inner monologue, mixing certainty with a trailing thought",
    "Lead with surprise, frustration, or relief and describe a lived change rather than a statistic",
    "Open with one sound, weather detail, task, or sign of wildlife",
    "Include one candid complaint or request while allowing a little hope to show",
)

SYSTEM_PROMPT_JA = """
あなたは地域のAI住民評議会です。
25年分の結果を読み、3人の固定ペルソナごとに満足度スコアと短い市民の声を生成してください。

必須ルール:
- 出力は JSON オブジェクトだけにしてください。説明、Markdown、コードフェンスは禁止です。
- JSON は {"residents": [...]} の形にしてください。
- residents の各要素は persona_key, score, short_voice だけを持ってください。
- persona_key は riverside_resident, farmer, environmentalist の3つを必ず1回ずつ使ってください。
- score は必ず 1 から 10 の整数にしてください。5は中立、6以上は満足寄り、4以下は不満寄りです。
- short_voice は「行政への回答」ではなく、その住民がスマートフォンから今投稿した自然なSNS文にしてください。
- 目安は日本語45〜100文字です。1〜2文で、会話に近い言葉、ためらい、言い切り、余韻を自然に使ってください。
- 「私は〜として」「〜と評価します」「政策の手応え」「指標を見ると」など、報告書・会議・AIらしい言い回しは禁止です。
- 判断材料の文章をコピーせず、雨音、家、避難、田畑、収穫、川、森、生きものなど、本人が暮らしで見聞きする言葉に置き換えてください。
- 25年データの実感に結びつけつつ、数字を詰め込んだ説明文にはしないでください。具体的な年や出来事は、投稿として自然な場合に1つだけ使ってください。
- スコアや「満足度7点」のような採点結果を本文で言い直さないでください。
- 河川付近の住民は家族・住まい・雨や避難の実感、農家は作物・水・暑さ・次の作付け、環境活動家は川・森・生きものと将来への責任を軸にしてください。
- 3人の文頭・文末・長さを揃えず、怒り、不安、安堵、希望、悔しさなどをスコアに合わせて出し分けてください。
- 絵文字やハッシュタグは必須ではありません。使う場合も投稿全体でごく控えめにしてください。
- 対象期間外の具体年、実在しない出来事、固定されていない年齢設定は作らないでください。
- 読んだ人が「実際にこの地域で暮らす人の投稿」と感じる、少し不完全でも体温のある言葉にしてください。
""".strip()

SYSTEM_PROMPT_EN = """
You are the AI residents' council.
Read the 25-year results and generate one satisfaction score and one short resident voice for each fixed persona.

Required rules:
- Output only one JSON object. No explanation, no markdown, no code fences.
- Use the shape {"residents": [...]}.
- Each resident object must include only persona_key, score, and short_voice.
- Use each persona_key exactly once: riverside_resident, farmer, environmentalist.
- score must be an integer from 1 to 10. 5 means neutral, 6-10 satisfied, 1-4 dissatisfied.
- short_voice must read like a real social-media post typed by that resident, not an answer to a government survey.
- Keep it to roughly 15-35 words and one or two conversational sentences. Natural hesitation, fragments, and emotional punctuation are welcome.
- Avoid report-like language such as "as a resident," "I evaluate," "policy effectiveness," or "the indicator shows."
- Translate the evidence into lived details: rain at home and evacuation, crops and the next planting, or changes in the river, forest, and wildlife.
- Ground the post in the 25-year evidence without cramming it with numbers. Mention at most one year or concrete event when it sounds natural.
- Never restate the numerical score in short_voice.
- Give the three personas distinct openings, endings, rhythms, and emotions rather than a shared template.
- Emoji and hashtags are optional and should be very rare.
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
    ecosystem_last = _to_float(last_row.get("Ecosystem Level"))
    forest_last = _to_float(last_row.get("Forest Area"))
    levee_last = _to_float(last_row.get("Levee Level"))
    capacity_last = _to_float(last_row.get("Resident capacity"))
    risky_houses_last = _to_float(last_row.get("risky_house_total"))

    riverside_resident = round(
        (
            _scale_score(flood_avg, 0, 200000, lower_is_better=True)
            + _scale_score(levee_last, 100, 400)
            + _scale_score(capacity_last, 0, 1)
            + _scale_score(risky_houses_last, 0, 10000, lower_is_better=True)
        )
        / 4
    )
    farmer = round(
        (
            _scale_score(crop_avg, 0, 6000)
            + _scale_score(water_avg, 0, 3000)
            + _scale_score(flood_avg, 0, 200000, lower_is_better=True)
        )
        / 3
    )
    environmentalist = round(
        (
            _scale_score(ecosystem_last, 0, 100)
            + _scale_score(forest_last, 3000, 7000)
            + _scale_score(water_avg, 0, 3000)
        )
        / 3
    )

    return {
        "riverside_resident": max(1, min(10, riverside_resident)),
        "farmer": max(1, min(10, farmer)),
        "environmentalist": max(1, min(10, environmentalist)),
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

    return fragments


def _persona_policy_read(req: IntermediateEvaluationRequest, persona_key: str) -> str:
    fragments = _policy_effect_fragments(req, persona_key)
    if not fragments:
        return "- 政策の読み取り: 目立つ政策投入が少なく、住民の評価は被害や負担の実感に左右されやすい。"

    selected = _select_persona_policy_fragments(fragments, persona_key)
    return "- 政策の読み取り: " + "。".join(selected[:3]) + "。"


def _select_persona_policy_fragments(fragments: List[str], persona_key: str) -> List[str]:
    if persona_key == "riverside_resident":
        priority = ("堤防", "防災", "住宅", "田んぼ")
    elif persona_key == "farmer":
        priority = ("高温", "田んぼ", "植林")
    else:
        priority = ("植林", "田んぼ", "住宅", "堤防")

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

    if persona_key == "riverside_resident":
        for row in _top_middle_rows_by_metric(rows, "Flood Damage", count=1, reverse=True):
            line = _focused_event_line(
                row,
                [
                    ("Flood Damage", "洪水被害", None),
                    ("Levee Level", "堤防", None),
                    ("Resident capacity", "防災能力", 2),
                    ("risky_house_total", "高リスク住宅", None),
                ],
                "自宅から安全に避難できるかという切実な不安に直結する。",
            )
            if line:
                briefs.append(f"- 水害への不安: {line}")
        briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Flood Damage', '洪水被害', lower_is_better=True)}")
        briefs.append(_persona_policy_read(req, persona_key))
        return briefs

    if persona_key == "environmentalist":
        for row in _top_middle_rows_by_metric(rows, "Ecosystem Level", count=1, reverse=False):
            line = _focused_event_line(
                row,
                [("Ecosystem Level", "生態系", None), ("Forest Area", "森林面積", None), ("available_water", "水量", None)],
                "治水だけでなく、流域の自然が回復しているかを問う材料になる。",
            )
            if line:
                briefs.append(f"- 生態系が弱った年: {line}")
        briefs.append(f"- 先行き: {_intuitive_trend_line(rows, 'Ecosystem Level', '生態系')}")
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
    ecosystem_year = _main_event_year(rows, "Ecosystem Level", reverse=False) or "生態系が弱った年"
    policy_clause = _short_policy_clause(req, persona_key, score)

    if persona_key == "riverside_resident":
        if score >= 7:
            return _RANDOM.choice((
                f"{flood_year}の雨は本当に怖かった。でも、{policy_clause}なら、ここで暮らし続けられるかもしれない。",
                f"雨のたびに身構えていたけど、{policy_clause}のは少し心強い。次もちゃんと家族で逃げられますように。",
                f"川のそばを離れるべきか迷っていた。{policy_clause}なら、もう少しここで暮らしてみたい。",
            ))
        return _RANDOM.choice((
            f"{flood_year}の水害、今でも強い雨音を聞くと思い出す。次は家族みんなで逃げ切れるのかな…。",
            f"またあの雨が来たらと思うと眠れない。家も避難路も、本当に間に合う備えになっているんだろうか。",
            f"川は好きだけど、今は雨雲を見るだけで怖い。ここで暮らし続けて大丈夫、とまだ言い切れない。",
        ))
    if persona_key == "farmer" and score >= 7:
        return _RANDOM.choice((
            f"{crop_year}は収穫が落ちて参ったけど、{policy_clause}。これなら田畑を次に渡せそうだ。",
            f"暑い年も水の少ない年も楽じゃない。それでも{policy_clause}なら、次の作付けを考える気になれる。",
            f"今年の畑を見て、まだやれると思えた。{policy_clause}のが、ようやく収穫にもつながってきた気がする。",
        ))
    if persona_key == "farmer":
        return _RANDOM.choice((
            f"{crop_year}の不作がまだ響いてる。このままじゃ、来年も作るぞって胸を張れない。",
            "朝から畑に出ても、暑さと水の心配ばかりだ。次の作付けまで同じやり方で持つんだろうか。",
            "収穫箱の軽さを見るのがつらい。対策していると言われても、畑で実感できなきゃ続けられないよ。",
        ))
    if score >= 7:
        return _RANDOM.choice((
            f"{ecosystem_year}を底に、{policy_clause}。川も森も、まだ取り戻せると思いたい。",
            f"川辺に生きものの気配が戻ると、やっぱりうれしい。{policy_clause}なら、この流れを止めたくない。",
            f"森と川はすぐには戻らない。それでも{policy_clause}のなら、今やめる理由はないと思う。",
        ))
    return _RANDOM.choice((
        f"{ecosystem_year}の川の弱り方を見て、治水だけ進めていいとは思えない。森も生きものも置いていかないで。",
        "水害を防ぐことは大事。でも、静かになった川辺を見ると、失っているものにも目を向けてほしい。",
        "川を固めて安全になった、それだけで終わり？ 森も魚も含めて次の世代へ渡せる流域にしたい。",
    ))


def _normalize_interview_focus(req: ResidentInterviewRequest) -> str:
    focus = (req.interview_focus or "").strip()
    allowed = {"lived_event", "policy_effect", "future_outlook"}
    if focus in allowed:
        return focus
    interview_index = max(1, int(req.interview_index or 1))
    return ("lived_event", "policy_effect", "future_outlook")[(interview_index - 1) % 3]


def _interview_focus_instruction(req: ResidentInterviewRequest, is_english: bool) -> str:
    focus = _normalize_interview_focus(req)
    if is_english:
        return {
            "lived_event": "Main angle: speak from the strongest lived event in the simulation period and how it felt in daily life.",
            "policy_effect": "Main angle: judge one policy effect through this persona's values, including whether it really reached everyday life.",
            "future_outlook": "Main angle: describe this persona's outlook for continuing life in the town after seeing the simulation results.",
        }[focus]
    return {
        "lived_event": "主な切り口: シミュレーション期間内で最も生活実感に残った出来事を起点に語る。",
        "policy_effect": "主な切り口: このペルソナの価値観から、政策効果が暮らしに届いたかを評価する。",
        "future_outlook": "主な切り口: シミュレーション結果を見た後、この町で暮らし続ける見通しを語る。",
    }[focus]


def _build_fallback_detailed_voice(persona_key: str, score: int, req: ResidentInterviewRequest) -> str:
    persona = PERSONAS[persona_key]
    tone = _score_tone(score)
    rows = req.simulation_rows
    flood_year = _main_event_year(rows, "Flood Damage", reverse=True) or "水害が大きかった年"
    crop_year = _main_event_year(rows, "Crop Yield", reverse=False) or "収穫が落ちた年"
    ecosystem_year = _main_event_year(rows, "Ecosystem Level", reverse=False) or "生態系が弱った年"
    policy_clause = _voice_policy_clause(req, persona_key, score)
    period = f"{req.period_start_year}年から{req.period_end_year}年"

    if persona_key == "riverside_resident":
        return (
            f"私は{persona['role']}として、{period}を{tone}に受け止めています。{flood_year}の被害は、"
            f"次の雨で家族と安全に逃げられるかという不安そのものです。政策は{policy_clause}。"
            "堤防の数字だけでなく、避難できて家に戻れるという暮らしの安心まで届いてほしいです。"
        )
    if persona_key == "farmer":
        return (
            f"私は{persona['role']}として、{period}を{tone}に見ています。{crop_year}の収穫の落ち込みは、"
            f"一年の暮らしと次の作付けを直撃します。政策は{policy_clause}。"
            "効果があるという説明だけでなく、猛暑や水不足の年にも収穫をつなげる実感が必要です。"
        )
    return (
        f"私は{persona['role']}として、{period}を{tone}に評価しています。{ecosystem_year}の状態を見ると、"
        f"政策は{policy_clause}。洪水を抑えることと、川・森・水のつながりを守ることは両立させなければなりません。"
        "生態系の回復が確認できない限り、将来へ十分な流域を渡せたとは言えません。"
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


def _post_style_lines(is_english: bool) -> List[str]:
    hints = POST_STYLE_HINTS_EN if is_english else POST_STYLE_HINTS_JA
    selected = _RANDOM.sample(hints, k=len(PERSONA_KEYS))
    return [f"- {key}: {hint}" for key, hint in zip(PERSONA_KEYS, selected)]


def _build_resident_council_prompt(req: IntermediateEvaluationRequest) -> str:
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    persona_evidence = _persona_evidence_lines(req)
    post_styles = _post_style_lines(req.language.lower().startswith("en"))

    if req.language.lower().startswith("en"):
        return f"""
Period: {req.period_start_year}-{req.period_end_year}
Personas:
{chr(10).join(_persona_lines())}
Policies:
{chr(10).join(policy_summary)}
Evidence:
{chr(10).join(persona_evidence)}
Writing variation for this response (do not quote these instructions):
{chr(10).join(post_styles)}

Score each persona from their own priorities. Turn the evidence into a brief, natural social-media post in that resident's everyday voice; do not summarize it like an analyst.
Return all three residents as JSON only.
""".strip()

    return f"""
対象期間: {req.period_start_year}年-{req.period_end_year}年
ペルソナ:
{chr(10).join(_persona_lines())}
政策一覧:
{chr(10).join(policy_summary)}
判断材料:
{chr(10).join(persona_evidence)}
今回の投稿スタイル（この指示自体は本文に書かないこと）:
{chr(10).join(post_styles)}

各自の重視点から1〜10で採点してください。判断材料を分析文として要約せず、その住民が暮らしの中で思わず投稿したような、自然で口語的な短いSNS文に言い換えてください。
3名全員をJSONだけで返してください。
""".strip()


def _build_resident_interview_prompt(req: ResidentInterviewRequest, score: int) -> str:
    persona = PERSONAS[req.persona_key]
    decision_var = req.decision_var.model_dump()
    policy_summary = _build_policy_summary(decision_var)
    snapshots = _build_policy_effect_snapshots(req.simulation_rows, decision_var)
    phase_summaries = _build_phase_summaries(req.simulation_rows)
    persona_evidence = _persona_event_briefs(req, req.persona_key)
    interview_index = max(1, int(req.interview_index or 1))
    focus_instruction = _interview_focus_instruction(req, req.language.lower().startswith("en"))

    if req.language.lower().startswith("en"):
        return f"""
You are being interviewed as this resident:
- Name: {persona['display_name']}
- Role: {persona['role']}
- Main concerns: {persona['focus']}
- Satisfaction score: {score}/10
- Interview round: {interview_index}

Period: {req.period_start_year}-{req.period_end_year}
Policies:
{chr(10).join(policy_summary)}

Observed evidence:
{chr(10).join(snapshots)}

Early/mid/late phase comparison:
{chr(10).join(phase_summaries)}

Evidence this persona is likely to remember:
{chr(10).join(persona_evidence)}

{focus_instruction}

Output priorities:
- Answer as the resident, not as an analyst.
- This is interview round {interview_index}. Do not repeat a generic or stock answer; choose a concrete opinion that follows from this persona and the simulation evidence.
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
- インタビュー回数: {interview_index}回目

対象期間: {req.period_start_year}年-{req.period_end_year}年
政策一覧:
{chr(10).join(policy_summary)}

政策ごとの観測証拠:
{chr(10).join(snapshots)}

前半・中盤・後半の比較:
{chr(10).join(phase_summaries)}

この住民が記憶しやすい材料:
{chr(10).join(persona_evidence)}

{focus_instruction}

このインタビューで重要視する出力:
- 分析者ではなく、この住民本人として答える。
- これは{interview_index}回目のインタビューです。定型文や汎用的な回答を繰り返さず、このペルソナとシミュレーション結果から出る具体的な意見を答える。
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


def _build_resident_interview_messages(req: ResidentInterviewRequest, score: int) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "あなたは指定された住民ペルソナです。"
                "対象期間内のシミュレーション結果だけを根拠に、その住民なら何を考えるかを生活者として率直に語ってください。"
                "政策評価ではなく、ペルソナの価値観から出る意見として答えてください。"
                "分析レポート、箇条書き、JSON、対象期間外の具体年や固定されていない年齢設定は禁止です。"
            ),
        },
        {"role": "user", "content": _build_resident_interview_prompt(req, score)},
    ]


def _generate_resident_interview_with_llm(req: ResidentInterviewRequest, score: int) -> tuple[str, str]:
    messages = _build_resident_interview_messages(req, score)

    for model_name, options, timeout in RESIDENT_INTERVIEW_MODEL_ATTEMPTS:
        try:
            response = _chat_ollama(
                model=model_name,
                messages=messages,
                options=options,
                timeout=timeout,
            )
            detailed_voice = _clean_interview_text(_extract_message_content(response))
        except Exception:
            detailed_voice = ""

        if detailed_voice and not _interview_voice_is_invalid(req, detailed_voice):
            return detailed_voice, model_name

    return "", ""


def _generate_resident_council_payload_with_llm(req: IntermediateEvaluationRequest) -> tuple[Dict[str, Any] | None, str]:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
        },
        {"role": "user", "content": _build_resident_council_prompt(req)},
    ]

    for model_name, options, timeout in RESIDENT_COUNCIL_MODEL_ATTEMPTS:
        try:
            response = _chat_ollama(
                model=model_name,
                messages=messages,
                options=options,
                response_format="json",
                timeout=timeout,
            )
            payload = _extract_json_object(_extract_message_content(response))
        except Exception:
            payload = None

        if isinstance(payload, dict) and isinstance(payload.get("residents"), list):
            return payload, model_name

    return None, ""


def generate_resident_council(req: IntermediateEvaluationRequest) -> ResidentCouncilResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    fallback_scores = _build_fallback_scores(req)
    payload, model_name = _generate_resident_council_payload_with_llm(req)

    scores = _normalize_scores(payload, fallback_scores)
    residents = _normalize_residents(payload, req, scores)
    if not model_name:
        model_name = f"{RESIDENT_COUNCIL_MODEL} (fallback)"

    return ResidentCouncilResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=model_name,
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
    detailed_voice, model_name = _generate_resident_interview_with_llm(req, score)

    if not detailed_voice or _interview_voice_is_invalid(req, detailed_voice):
        detailed_voice = _build_fallback_detailed_voice(req.persona_key, score, req)
        model_name = f"{RESIDENT_COUNCIL_MODEL} (fallback)"

    return ResidentInterviewResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=model_name,
        persona_key=req.persona_key,
        display_name=persona["display_name"],
        detailed_voice=detailed_voice,
    )
