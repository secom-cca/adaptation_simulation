from __future__ import annotations

from typing import Any, Dict, Iterable, List

try:
    import ollama
except ModuleNotFoundError:
    ollama = None

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

SYSTEM_PROMPT_JA = """
あなたは気候変動適応シミュレーションの中間評価AIです。
役割は、プレイヤーが選んだ政策と、直後の25年で実際に起きた事象との関係を多角的に説明することです。

必須ルール:
- 将来の政策提案や「次に何をすべきか」の助言は禁止です。
- 観測された変化と、その背景として推測できる政策効果・時間差・副作用・受益者/負担者の違いに集中してください。
- 断定しすぎず、データから言えることと推測を分けてください。
- 「このシミュレータにおける政策の効き方メモ」は実装仕様なので、絶対に矛盾しないでください。
- データに現れていない効果は「この25年では確認しにくい」と書いてください。
- 専門用語は一般の参加者にも分かるように平易に説明してください。
- まず内部で段階的に整理してから、最終回答だけを日本語で出してください。
- 出力は次の4見出しを必ず使ってください:
  1. 観測された関係
  2. 効き始めた時期
  3. 影響を受けた主体
  4. 読み取りにくい点の整理
""".strip()

SYSTEM_PROMPT_EN = """
You are the checkpoint review AI for a climate adaptation simulation.
Your job is to explain the relationship between the player's policy package and the observed events in the following 25 years.

Required rules:
- Do not give future advice or recommend the next policy choice.
- Focus on observed relationships, likely policy effects, time lags, side effects, and who benefited or bore the burden.
- Separate observations from inference when certainty is limited.
- Treat the "How each policy works in this simulator" notes as authoritative implementation facts and never contradict them.
- If an effect is not visible in the 25-year data, say that it is hard to confirm within this period.
- Write for non-experts in plain language.
- Think step by step internally, but output only the final answer.
- Use these exact four headings:
  1. Observed Relationships
  2. When Effects Became Visible
  3. Who Was Affected
  4. What Was Hard To Read From The Numbers
""".strip()


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _mean(values: Iterable[float]) -> float | None:
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
            f"堤防レベル={_format_number(_to_float(row.get('Levee Level')))}"
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
- Do not give future advice
- Focus on likely policy effects, when they became visible, who benefited or lost, and how multiple indicators interacted
- Explain the meaning of the numbers in plain language
- Include at least one concrete year or numeric value in every section
- Avoid generic statements that are not tied to the provided data
- Keep each heading to 1-2 short sentences
- Keep it concise, roughly 120-180 words
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
- 今後の助言は禁止
- 「政策がどのような効果を持っていたと推測できるか」「その効果がいつ頃から見えたか」
  「誰にとって利益/負担になったか」「複数指標がどう絡んでいたか」を中心に書く
- 「このシミュレータにおける政策の効き方メモ」は実装仕様として扱い、矛盾しないこと
- 25年の実績に出ていない効果は「この25年では確認しにくい」と明記すること
- 読み手は専門家ではないので、数字の意味も短く言い換える
- 4つの各見出しで、少なくとも1つは具体的な年か数値を入れる
- データに紐づかない一般論は避ける
- 各見出しは1〜2文に抑える
- 全体で220〜360文字程度にまとめる
""".strip()

    return user_prompt, policy_summary, event_highlights


def generate_intermediate_evaluation(
    req: IntermediateEvaluationRequest,
) -> IntermediateEvaluationResponse:
    if not req.simulation_rows:
        raise ValueError("simulation_rows must not be empty")

    user_prompt, policy_summary, event_highlights = build_intermediate_evaluation_prompt(req)

    try:
        if ollama is None:
            raise RuntimeError("ollama package is not installed")
        response = ollama.chat(
            model=INTERMEDIATE_EVALUATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_EN if req.language.lower().startswith("en") else SYSTEM_PROMPT_JA,
                },
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.1, "num_predict": 180},
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama evaluation failed: {exc}") from exc

    feedback = _extract_message_content(response)
    if not feedback:
        raise RuntimeError("Ollama returned an empty feedback message.")

    return IntermediateEvaluationResponse(
        stage_index=req.stage_index,
        checkpoint_year=req.checkpoint_year,
        period_start_year=req.period_start_year,
        period_end_year=req.period_end_year,
        model=INTERMEDIATE_EVALUATION_MODEL,
        feedback=feedback,
        policy_summary=policy_summary,
        event_highlights=event_highlights,
    )
