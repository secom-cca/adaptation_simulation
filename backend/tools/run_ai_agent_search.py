from __future__ import annotations

import csv
import importlib
import json
import math
import random
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple


# ============================================================
# Path setup
# ============================================================

THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parents[1]
PROJECT_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


# ============================================================
# Existing model imports
# ============================================================

from config import SIMULATION_RANDOM_SEED
from src.simulation import (
    POLICY_KEYS,
    calculate_budget_components,
    simulate_year,
)


# ============================================================
# Settings
# ============================================================

TARGET_PERIODS = {
    2050: (2026, 2050),
    2075: (2051, 2075),
    2100: (2076, 2100),
}

# 最終目的は「3時点それぞれの3指標等重み平均」をさらに等重み平均する。
# つまり、2050 / 2075 / 2100 も等重み。
OBJECTIVE_WEIGHTS = {
    2050: 1 / 3,
    2075: 1 / 3,
    2100: 1 / 3,
}

# T2までは探索候補をある程度残す。
# T1は洪水被害額が小さく、序盤スコアだけで切ると遅効性政策を過小評価しやすいため。
BEAM_WIDTH_BY_TURN = {
    1: 8,
    2: 5,
    3: 1,
}

# 動作確認で重ければ 8 / 8 / 8 に下げてよい。
ACTION_CANDIDATES_PER_TURN = {
    1: 20,
    2: 20,
    3: 16,
}

# スコア基準作成用の参照パターン数。
# 重ければ 30 に下げてよい。
REFERENCE_PATH_COUNT = 60

SEED = int(SIMULATION_RANDOM_SEED)

OUTPUT_DIR = BACKEND_DIR / "data"
FRONTEND_DATA_DIR = PROJECT_DIR / "frontend-new" / "src" / "data"


# ============================================================
# Data classes
# ============================================================

@dataclass
class PeriodMetrics:
    floodDamageJpy: float
    cropYield: float
    ecosystemLevel: float


@dataclass
class PeriodScores:
    floodScore: float
    cropScore: float
    ecosystemScore: float
    totalScore: float


@dataclass
class SearchNode:
    actions: List[Dict[str, int]]
    rows: List[Dict[str, Any]]
    final_state: Dict[str, Any]
    next_budget: int
    rank: float


@dataclass
class FinalCandidate:
    actions: List[Dict[str, int]]
    rows: List[Dict[str, Any]]
    metrics: Dict[int, PeriodMetrics]
    scores: Dict[int, PeriodScores]
    objective: float


# ============================================================
# Params loader
# ============================================================

def load_default_params() -> Dict[str, Any]:
    """
    既存プロジェクト側のデフォルトparamsを読む。
    config.py 内の名前が環境によって違う可能性があるため、複数候補を見る。

    見つからない場合は、config.py内のparams名を確認して、
    candidate_names に追加してください。
    """
    cfg = importlib.import_module("config")

    function_candidates = [
        "get_default_params",
        "get_params",
        "load_default_params",
    ]

    for name in function_candidates:
        fn = getattr(cfg, name, None)
        if callable(fn):
            params = fn()
            if isinstance(params, dict):
                return deepcopy(params)

    candidate_names = [
        "DEFAULT_PARAMS",
        "default_params",
        "PARAMS",
        "params",
        "SIMULATION_PARAMS",
        "simulation_params",
        "BASE_PARAMS",
        "base_params",
    ]

    for name in candidate_names:
        value = getattr(cfg, name, None)
        if isinstance(value, dict):
            return deepcopy(value)

    available_names = [name for name in dir(cfg) if not name.startswith("_")]
    raise RuntimeError(
        "config.py からデフォルトparamsを取得できませんでした。\n"
        "config.py内にあるパラメータ辞書名を確認して、load_default_params() の candidate_names に追加してください。\n"
        f"config.pyで見えている名前: {available_names}"
    )


# ============================================================
# Utility
# ============================================================

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    if not math.isfinite(float(value)):
        return low
    return max(low, min(high, float(value)))


def percentile(values: List[float], p: float) -> float:
    clean = [float(v) for v in values if math.isfinite(float(v))]
    if not clean:
        return 0.0

    xs = sorted(clean)
    if len(xs) == 1:
        return xs[0]

    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return xs[int(k)]

    return xs[f] * (c - k) + xs[c] * (k - f)


def get_year(row: Dict[str, Any]) -> int:
    return int(row.get("year", row.get("Year", 0)))


def get_flood_jpy(row: Dict[str, Any]) -> float:
    if "Flood Damage JPY" in row:
        return float(row.get("Flood Damage JPY") or 0)
    return float(row.get("Flood Damage", 0) or 0) * 150.0


def get_crop_yield(row: Dict[str, Any]) -> float:
    return float(row.get("Crop Yield", row.get("cropYield", 0)) or 0)


def get_ecosystem_level(row: Dict[str, Any]) -> float:
    return float(row.get("Ecosystem Level", row.get("ecosystemLevel", 0)) or 0)


def action_sum(action: Dict[str, int]) -> int:
    return sum(int(action.get(key, 0)) for key in POLICY_KEYS)


def sanitize_action(action: Dict[str, int]) -> Dict[str, int]:
    return {
        key: max(0, int(round(float(action.get(key, 0) or 0))))
        for key in POLICY_KEYS
    }


def normalize_action_to_budget(action: Dict[str, int], budget: int) -> Dict[str, int]:
    """
    合計マナが利用可能予算を超えたら削る。
    削る優先度は、住宅移転をやや削りやすくし、植林/R&D/田んぼダムを残しやすくする。
    """
    action = sanitize_action(action)
    budget = max(0, int(math.floor(float(budget))))

    remove_priority = [
        "house_migration_amount",
        "capacity_building_cost",
        "dam_levee_construction_cost",
        "paddy_dam_construction_cost",
        "agricultural_RnD_cost",
        "planting_trees_amount",
    ]

    while action_sum(action) > budget:
        candidates = [key for key in remove_priority if action.get(key, 0) > 0]
        if not candidates:
            break
        action[candidates[0]] -= 1

    return action


def fill_action_to_budget(action: Dict[str, int], budget: int, turn: int) -> Dict[str, int]:
    """
    予算が余っていれば、ターンごとの優先政策に足す。
    """
    action = sanitize_action(action)
    budget = max(0, int(math.floor(float(budget))))

    if turn == 1:
        priority = [
            "planting_trees_amount",
            "paddy_dam_construction_cost",
            "agricultural_RnD_cost",
            "capacity_building_cost",
            "dam_levee_construction_cost",
            "house_migration_amount",
        ]
    elif turn == 2:
        priority = [
            "paddy_dam_construction_cost",
            "agricultural_RnD_cost",
            "dam_levee_construction_cost",
            "planting_trees_amount",
            "capacity_building_cost",
            "house_migration_amount",
        ]
    else:
        priority = [
            "paddy_dam_construction_cost",
            "agricultural_RnD_cost",
            "dam_levee_construction_cost",
            "capacity_building_cost",
            "house_migration_amount",
            "planting_trees_amount",
        ]

    i = 0
    while action_sum(action) < budget:
        action[priority[i % len(priority)]] += 1
        i += 1

    return action


# ============================================================
# Initial state and decision vars
# ============================================================

def build_initial_values(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "temp": params["base_temp"],
        "precip": params["base_precip"],
        "municipal_demand": params["initial_municipal_demand"],
        "available_water": params["max_available_water"],
        "crop_yield": params["max_potential_yield"],
        "levee_level": 100.0,
        "high_temp_tolerance_level": 0.0,
        "hot_days": params["initial_hot_days"],
        "extreme_precip_freq": 0.0,
        "ecosystem_level": 100.0,
        "urban_level": 0.0,
        "levee_investment_total": 0.0,
        "RnD_investment_total": 0.0,
        "forest_area": params["total_area"] * params["initial_forest_area"],
        "paddy_dam_area": 0.0,
        "cumulative_migrated_houses": 0.0,
        "cumulative_house_migration_mana": 0.0,
        "cumulative_planting_mana": 0.0,
        "cumulative_agricultural_RnD_mana": 0.0,
        "cumulative_defense_mana": 0.0,
        "initial_risky_house_total": params["house_total"],
        "initial_crop_yield": params["max_potential_yield"],
        "events_state": {},
        "last_25y_avg_flood_damage_jpy": 0.0,
        "available_budget_mana": params.get("BASE_POLICY_BUDGET_MANA", 10.0),
        "population_budget_multiplier": 1.0,
        "population_decline_penalty_mana": 0.0,
        "migration_infra_penalty_mana": 0.0,
        "flood_recovery_penalty_mana": 0.0,
        "resident_capacity": 0.0,
        "planting_history": {},
        "risky_house_total": params["house_total"],
        "non_risky_house_total": 0.0,
        "transportation_level": 0.0,
        "resident_burden": 0.0,
        "biodiversity_level": 100.0,
    }


def build_decision_var(year: int, action: Dict[str, int]) -> Dict[str, Any]:
    """
    actionはマナ単位。
    simulate_year() 内の convert_mana_decisions_to_backend_units() が内部単位へ変換する。
    """
    decision = {
        "year": year,
        "cp_climate_params": "rcp45",
        "transportation_invest": 0,
        "flow_irrigation_level": 0,
    }

    for key in POLICY_KEYS:
        decision[key] = int(action.get(key, 0))

    return decision


# ============================================================
# Simulation runner
# ============================================================

def previous_period_average_flood(rows: List[Dict[str, Any]], start: int, end: int) -> float:
    period_rows = [row for row in rows if start <= get_year(row) <= end]
    if not period_rows:
        return 0.0
    return mean(get_flood_jpy(row) for row in period_rows)


def update_budget_for_turn_start(
    state: Dict[str, Any],
    rows: List[Dict[str, Any]],
    params: Dict[str, Any],
    turn_start: int,
    turn_index: int,
) -> Dict[str, Any]:
    """
    T2/T3開始時に、直前25年間の平均洪水被害額を予算計算用に反映する。
    スコア表示では洪水被害は25年累計だが、
    予算ペナルティ用は既存モデル仕様に合わせて25年平均を使う。
    """
    turn_years = int(params.get("TURN_YEARS", 25))

    if turn_index > 1:
        prev_start = turn_start - turn_years
        prev_end = turn_start - 1
        state["last_25y_avg_flood_damage_jpy"] = previous_period_average_flood(
            rows,
            prev_start,
            prev_end,
        )

    budget_components = calculate_budget_components(turn_start, state, params)
    state.update(budget_components)
    return state


def run_path(
    actions: List[Dict[str, int]],
    seed: int = SEED,
    params: Dict[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    actions:
      1個ならT1のみ実行
      2個ならT2まで実行
      3個ならT3まで実行

    途中状態から再開せず、毎回2026年からsimulate_yearを回す。
    その方が既存状態遷移とイベント/累積投資の整合が取りやすい。
    """
    params = deepcopy(params or load_default_params())
    params["SIMULATION_RANDOM_SEED"] = seed

    state = build_initial_values(params)
    rows: List[Dict[str, Any]] = []

    start_year = int(params.get("start_year", 2026))
    turn_years = int(params.get("TURN_YEARS", 25))

    for turn_index, raw_action in enumerate(actions, start=1):
        turn_start = start_year + (turn_index - 1) * turn_years
        turn_end = turn_start + turn_years - 1

        state = update_budget_for_turn_start(
            state=state,
            rows=rows,
            params=params,
            turn_start=turn_start,
            turn_index=turn_index,
        )

        current_budget = int(math.floor(float(
            state.get("available_budget_mana", params.get("BASE_POLICY_BUDGET_MANA", 10))
        )))

        action = normalize_action_to_budget(raw_action, current_budget)

        for year in range(turn_start, turn_end + 1):
            decision_var = build_decision_var(year, action)

            state, output = simulate_year(
                year=year,
                prev_values=state,
                decision_vars=decision_var,
                params=params,
                fixed_seed=True,
            )

            output = {
                "year": year,
                **output,
            }
            rows.append(output)

    return rows, state


def run_baseline(seed: int = SEED) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    zero = {key: 0 for key in POLICY_KEYS}
    return run_path([zero, zero, zero], seed=seed)


# ============================================================
# Aggregation and scoring
# ============================================================

def aggregate_period(rows: List[Dict[str, Any]], start: int, end: int) -> PeriodMetrics:
    period_rows = [row for row in rows if start <= get_year(row) <= end]

    if not period_rows:
        return PeriodMetrics(
            floodDamageJpy=0.0,
            cropYield=0.0,
            ecosystemLevel=0.0,
        )

    return PeriodMetrics(
        # 結果表示・スコア用：洪水被害は25年累計
        floodDamageJpy=sum(get_flood_jpy(row) for row in period_rows),
        # 農作物・生態系は25年平均
        cropYield=mean(get_crop_yield(row) for row in period_rows),
        ecosystemLevel=mean(get_ecosystem_level(row) for row in period_rows),
    )


def aggregate_all_periods(rows: List[Dict[str, Any]]) -> Dict[int, PeriodMetrics]:
    return {
        target_year: aggregate_period(rows, start, end)
        for target_year, (start, end) in TARGET_PERIODS.items()
    }


def build_score_bounds(all_metrics: List[Dict[int, PeriodMetrics]]) -> Dict[str, Any]:
    """
    洪水は期間ごとに基準を変える。
    農作物・生態系は全期間共通基準。
    """
    flood_bounds: Dict[str, Any] = {}

    for year in TARGET_PERIODS:
        values = [metrics[year].floodDamageJpy for metrics in all_metrics]
        good = percentile(values, 0.10)
        bad = percentile(values, 0.90)

        if abs(bad - good) < 1e-9:
            bad = good + 1.0

        flood_bounds[str(year)] = {
            "good": good,
            "bad": bad,
        }

    crop_values: List[float] = []
    ecosystem_values: List[float] = []

    for metrics in all_metrics:
        for year in TARGET_PERIODS:
            crop_values.append(metrics[year].cropYield)
            ecosystem_values.append(metrics[year].ecosystemLevel)

    crop_bad = percentile(crop_values, 0.10)
    crop_good = percentile(crop_values, 0.90)
    eco_bad = percentile(ecosystem_values, 0.10)
    eco_good = percentile(ecosystem_values, 0.90)

    if abs(crop_good - crop_bad) < 1e-9:
        crop_good = crop_bad + 1.0

    if abs(eco_good - eco_bad) < 1e-9:
        eco_good = eco_bad + 1.0

    return {
        "flood": flood_bounds,
        "crop": {
            "bad": crop_bad,
            "good": crop_good,
        },
        "ecosystem": {
            "bad": eco_bad,
            "good": eco_good,
        },
    }


def score_periods(metrics: Dict[int, PeriodMetrics], bounds: Dict[str, Any]) -> Dict[int, PeriodScores]:
    scores: Dict[int, PeriodScores] = {}

    for year, metric in metrics.items():
        flood_bound = bounds["flood"][str(year)]
        flood_good = float(flood_bound["good"])
        flood_bad = float(flood_bound["bad"])

        # 洪水被害は小さいほど良い
        flood_score = 100.0 * (flood_bad - metric.floodDamageJpy) / max(flood_bad - flood_good, 1e-9)
        flood_score = clamp(flood_score)

        crop_bad = float(bounds["crop"]["bad"])
        crop_good = float(bounds["crop"]["good"])
        crop_score = 100.0 * (metric.cropYield - crop_bad) / max(crop_good - crop_bad, 1e-9)
        crop_score = clamp(crop_score)

        eco_bad = float(bounds["ecosystem"]["bad"])
        eco_good = float(bounds["ecosystem"]["good"])
        ecosystem_score = 100.0 * (metric.ecosystemLevel - eco_bad) / max(eco_good - eco_bad, 1e-9)
        ecosystem_score = clamp(ecosystem_score)

        total_score = (flood_score + crop_score + ecosystem_score) / 3.0

        scores[year] = PeriodScores(
            floodScore=flood_score,
            cropScore=crop_score,
            ecosystemScore=ecosystem_score,
            totalScore=total_score,
        )

    return scores


def objective(scores: Dict[int, PeriodScores]) -> float:
    """
    2050/2075/2100の総合スコアを等重み平均。
    各年の総合スコアは、洪水・農作物・生態系の等重み平均。
    """
    return sum(
        OBJECTIVE_WEIGHTS[year] * scores[year].totalScore
        for year in TARGET_PERIODS
    )


# ============================================================
# Action generation
# ============================================================

def base_templates(turn: int) -> List[Dict[str, int]]:
    """
    10マナ前提の基本型。
    実際の予算が減っている場合は normalize_action_to_budget() で削る。
    """
    def a(
        forest: int = 0,
        migration: int = 0,
        levee: int = 0,
        paddy: int = 0,
        drill: int = 0,
        rnd: int = 0,
    ) -> Dict[str, int]:
        return {
            "planting_trees_amount": forest,
            "house_migration_amount": migration,
            "dam_levee_construction_cost": levee,
            "paddy_dam_construction_cost": paddy,
            "capacity_building_cost": drill,
            "agricultural_RnD_cost": rnd,
        }

    if turn == 1:
        # T1は被害がまだ小さいため、遅効性・基盤形成型を厚めにする
        return [
            a(forest=5, paddy=3, rnd=2),
            a(forest=4, paddy=3, rnd=2, drill=1),
            a(forest=4, paddy=2, rnd=3, drill=1),
            a(forest=3, paddy=4, rnd=2, drill=1),
            a(forest=6, paddy=2, rnd=1, drill=1),
            a(forest=3, paddy=3, rnd=3, drill=1),
            a(forest=5, paddy=2, rnd=2, levee=1),
            a(forest=4, paddy=4, rnd=1, drill=1),
            a(forest=5, paddy=1, rnd=3, drill=1),
            a(forest=4, paddy=3, rnd=1, levee=1, drill=1),
        ]

    if turn == 2:
        # T2は田んぼダム・R&D・堤防を中心に、植林を少し残す
        return [
            a(forest=2, paddy=3, rnd=3, levee=1, drill=1),
            a(forest=1, paddy=3, rnd=3, levee=2, drill=1),
            a(forest=2, paddy=2, rnd=2, levee=3, drill=1),
            a(forest=1, paddy=4, rnd=2, levee=2, drill=1),
            a(forest=2, paddy=3, rnd=2, levee=2, drill=1),
            a(forest=1, paddy=2, rnd=4, levee=2, drill=1),
            a(forest=2, paddy=2, rnd=3, levee=2, migration=1),
            a(forest=1, paddy=3, rnd=2, levee=2, drill=1, migration=1),
            a(forest=2, paddy=4, rnd=2, levee=1, drill=1),
            a(forest=1, paddy=3, rnd=4, levee=1, drill=1),
        ]

    # T3は最終被害抑制。住宅移転は副作用もあるため入れすぎない。
    return [
        a(forest=1, paddy=3, rnd=3, levee=2, drill=1),
        a(forest=1, paddy=2, rnd=4, levee=1, drill=1, migration=1),
        a(paddy=3, rnd=3, levee=2, drill=1, migration=1),
        a(forest=1, paddy=2, rnd=2, levee=3, drill=1, migration=1),
        a(paddy=4, rnd=3, levee=1, drill=1, migration=1),
        a(forest=1, paddy=3, rnd=2, levee=2, drill=2),
        a(paddy=2, rnd=3, levee=3, drill=1, migration=1),
        a(forest=2, paddy=2, rnd=3, levee=2, drill=1),
        a(paddy=3, rnd=4, levee=2, drill=1),
        a(forest=1, paddy=4, rnd=2, levee=2, drill=1),
    ]


def mutate_action(action: Dict[str, int], rng: random.Random) -> Dict[str, int]:
    mutated = sanitize_action(action)

    for _ in range(rng.randint(1, 3)):
        src = rng.choice(POLICY_KEYS)
        dst = rng.choice(POLICY_KEYS)

        if src == dst:
            continue

        if mutated[src] > 0:
            mutated[src] -= 1
            mutated[dst] += 1

    return mutated


def generate_actions(turn: int, budget: int, rng: random.Random) -> List[Dict[str, int]]:
    actions: List[Dict[str, int]] = []

    for template in base_templates(turn):
        action = normalize_action_to_budget(template, budget)
        action = fill_action_to_budget(action, budget, turn)
        actions.append(action)

    while len(actions) < ACTION_CANDIDATES_PER_TURN[turn]:
        template = rng.choice(base_templates(turn))
        action = mutate_action(template, rng)
        action = normalize_action_to_budget(action, budget)
        action = fill_action_to_budget(action, budget, turn)
        actions.append(action)

    # 重複除去
    unique: List[Dict[str, int]] = []
    seen = set()

    for action in actions:
        key = tuple(action[k] for k in POLICY_KEYS)

        if key in seen:
            continue

        seen.add(key)
        unique.append(action)

    return unique


# ============================================================
# Score bounds reference
# ============================================================

def make_reference_paths(seed: int = SEED, n: int = REFERENCE_PATH_COUNT) -> List[List[Dict[str, int]]]:
    rng = random.Random(seed)
    paths: List[List[Dict[str, int]]] = []

    zero = {key: 0 for key in POLICY_KEYS}
    paths.append([zero, zero, zero])

    # 代表型を優先して入れる
    for t1 in base_templates(1):
        for t2 in base_templates(2)[:3]:
            for t3 in base_templates(3)[:2]:
                paths.append([
                    normalize_action_to_budget(t1, 10),
                    normalize_action_to_budget(t2, 10),
                    normalize_action_to_budget(t3, 10),
                ])

    while len(paths) < n:
        paths.append([
            rng.choice(generate_actions(1, 10, rng)),
            rng.choice(generate_actions(2, 10, rng)),
            rng.choice(generate_actions(3, 10, rng)),
        ])

    return paths[:n]


def build_bounds(seed: int = SEED) -> Dict[str, Any]:
    all_metrics: List[Dict[int, PeriodMetrics]] = []
    reference_paths = make_reference_paths(seed=seed, n=REFERENCE_PATH_COUNT)

    print(f"Building score bounds from {len(reference_paths)} reference paths...", flush=True)

    for i, actions in enumerate(reference_paths, start=1):
        print(f"  bounds simulation {i}/{len(reference_paths)}", flush=True)
        rows, _state = run_path(actions, seed=seed)
        all_metrics.append(aggregate_all_periods(rows))

    return build_score_bounds(all_metrics)


# ============================================================
# Beam search
# ============================================================

def partial_bonus(actions: List[Dict[str, int]], turn: int) -> float:
    """
    T1/T2で将来効く政策を早期に切り捨てないための補正。
    最終objectiveには使わず、beamの途中順位だけに使う。
    """
    cumulative = {key: 0 for key in POLICY_KEYS}

    for action in actions:
        for key in POLICY_KEYS:
            cumulative[key] += int(action.get(key, 0))

    if turn == 1:
        return (
            1.4 * cumulative["planting_trees_amount"]
            + 0.9 * cumulative["paddy_dam_construction_cost"]
            + 1.0 * cumulative["agricultural_RnD_cost"]
        )

    if turn == 2:
        return (
            0.8 * cumulative["paddy_dam_construction_cost"]
            + 1.0 * cumulative["agricultural_RnD_cost"]
            + 0.6 * cumulative["dam_levee_construction_cost"]
            + 0.4 * cumulative["planting_trees_amount"]
        )

    return 0.0


def rank_partial(
    rows: List[Dict[str, Any]],
    actions: List[Dict[str, int]],
    bounds: Dict[str, Any],
    turn: int,
) -> float:
    """
    途中評価。
    完了したターンまでの総合スコアだけで評価し、T1/T2では遅効性政策ボーナスを加える。
    """
    metrics = aggregate_all_periods(rows)
    scores = score_periods(metrics, bounds)

    completed_years = []
    if turn >= 1:
        completed_years.append(2050)
    if turn >= 2:
        completed_years.append(2075)
    if turn >= 3:
        completed_years.append(2100)

    base = mean(scores[year].totalScore for year in completed_years)
    return base + partial_bonus(actions, turn)


def run_policy_search(seed: int = SEED) -> Tuple[FinalCandidate, Dict[str, Any]]:
    rng = random.Random(seed)
    params = load_default_params()
    bounds = build_bounds(seed)

    initial_budget = int(math.floor(float(params.get("BASE_POLICY_BUDGET_MANA", 10))))

    beams: List[SearchNode] = [
        SearchNode(
            actions=[],
            rows=[],
            final_state=build_initial_values(params),
            next_budget=initial_budget,
            rank=0.0,
        )
    ]

    for turn in [1, 2, 3]:
        expanded: List[SearchNode] = []

        for beam in beams:
            budget = max(0, int(beam.next_budget))
            actions = generate_actions(turn, budget, rng)

            for action in actions:
                next_actions = beam.actions + [action]

                rows, final_state = run_path(next_actions, seed=seed, params=params)

                next_budget = int(math.floor(float(final_state.get(
                    "available_budget_mana",
                    params.get("BASE_POLICY_BUDGET_MANA", 10),
                ))))

                rank = rank_partial(rows, next_actions, bounds, turn)

                expanded.append(SearchNode(
                    actions=next_actions,
                    rows=rows,
                    final_state=final_state,
                    next_budget=next_budget,
                    rank=rank,
                ))

        expanded.sort(key=lambda node: node.rank, reverse=True)
        beams = expanded[:BEAM_WIDTH_BY_TURN[turn]]

        print(f"T{turn}: kept {len(beams)} candidates", flush=True)
        for i, node in enumerate(beams[:3], start=1):
            print(
                f"  {i}. rank={node.rank:.2f}, next_budget={node.next_budget}, actions={node.actions}",
                flush=True,
            )

    final_candidates: List[FinalCandidate] = []

    for beam in beams:
        metrics = aggregate_all_periods(beam.rows)
        scores = score_periods(metrics, bounds)

        final_candidates.append(FinalCandidate(
            actions=beam.actions,
            rows=beam.rows,
            metrics=metrics,
            scores=scores,
            objective=objective(scores),
        ))

    final_candidates.sort(key=lambda candidate: candidate.objective, reverse=True)
    return final_candidates[0], bounds


# ============================================================
# Output
# ============================================================

def action_to_ja(turn: int, action: Dict[str, int]) -> str:
    names = {
        "planting_trees_amount": "植林",
        "house_migration_amount": "住宅移転",
        "dam_levee_construction_cost": "堤防",
        "paddy_dam_construction_cost": "田んぼダム",
        "capacity_building_cost": "防災訓練",
        "agricultural_RnD_cost": "農業R&D",
    }

    parts = [
        f"{names[key]}{int(action.get(key, 0))}"
        for key in POLICY_KEYS
        if int(action.get(key, 0)) > 0
    ]

    return f"T{turn}: " + (" / ".join(parts) if parts else "対策なし")


def metrics_to_json(metrics: Dict[int, PeriodMetrics]) -> Dict[str, Any]:
    return {
        str(year): {
            "floodDamageJpy": round(metrics[year].floodDamageJpy),
            "cropYield": round(metrics[year].cropYield, 1),
            "ecosystemLevel": round(metrics[year].ecosystemLevel, 2),
        }
        for year in TARGET_PERIODS
    }


def scores_to_json(scores: Dict[int, PeriodScores]) -> Dict[str, Any]:
    return {
        str(year): {
            "floodScore": round(scores[year].floodScore, 2),
            "cropScore": round(scores[year].cropScore, 2),
            "ecosystemScore": round(scores[year].ecosystemScore, 2),
            "totalScore": round(scores[year].totalScore, 2),
        }
        for year in TARGET_PERIODS
    }


def write_outputs(
    baseline_metrics: Dict[int, PeriodMetrics],
    baseline_scores: Dict[int, PeriodScores],
    best: FinalCandidate,
    bounds: Dict[str, Any],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    benchmark_series = {
        "baseline": {
            "labelJa": "ベースライン（対策なし）",
            "labelEn": "Baseline",
            "years": metrics_to_json(baseline_metrics),
        },
        "aiOptimal": {
            "labelJa": "AIエージェント最適解",
            "labelEn": "AI optimal",
            "policiesJa": [
                action_to_ja(i + 1, action)
                for i, action in enumerate(best.actions)
            ],
            "years": metrics_to_json(best.metrics),
        },
    }

    best_result = {
        "objective": round(best.objective, 4),
        "actions": best.actions,
        "policiesJa": benchmark_series["aiOptimal"]["policiesJa"],
        "years": metrics_to_json(best.metrics),
        "scores": scores_to_json(best.scores),
        "scoreBounds": bounds,
        "note": "Objective maximizes equal-weight average of flood, crop, and ecosystem scores over 2050, 2075, and 2100 periods.",
    }

    # backend出力
    (OUTPUT_DIR / "score_bounds.json").write_text(
        json.dumps(bounds, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "best_agent_result.json").write_text(
        json.dumps(best_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # frontend出力
    (FRONTEND_DATA_DIR / "benchmark_series.json").write_text(
        json.dumps(benchmark_series, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (FRONTEND_DATA_DIR / "score_bounds.json").write_text(
        json.dumps(bounds, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUTPUT_DIR / "best_agent_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "series",
            "year",
            "floodDamageJpy",
            "cropYield",
            "ecosystemLevel",
            "floodScore",
            "cropScore",
            "ecosystemScore",
            "totalScore",
        ])

        for series_name, metrics, scores in [
            ("baseline", baseline_metrics, baseline_scores),
            ("aiOptimal", best.metrics, best.scores),
        ]:
            for year in TARGET_PERIODS:
                m = metrics[year]
                s = scores[year]
                writer.writerow([
                    series_name,
                    year,
                    round(m.floodDamageJpy),
                    round(m.cropYield, 1),
                    round(m.ecosystemLevel, 2),
                    round(s.floodScore, 1),
                    round(s.cropScore, 1),
                    round(s.ecosystemScore, 1),
                    round(s.totalScore, 1),
                ])


def main() -> None:
    print("run_ai_agent_search.py started", flush=True)

    print("Running baseline...", flush=True)
    baseline_rows, _baseline_state = run_baseline(seed=SEED)

    print("Running policy search...", flush=True)
    best, bounds = run_policy_search(seed=SEED)

    baseline_metrics = aggregate_all_periods(baseline_rows)
    baseline_scores = score_periods(baseline_metrics, bounds)

    write_outputs(
        baseline_metrics=baseline_metrics,
        baseline_scores=baseline_scores,
        best=best,
        bounds=bounds,
    )

    print("\nDone.", flush=True)
    print(f"Best objective: {best.objective:.3f}", flush=True)
    print("Best policies:", flush=True)
    for i, action in enumerate(best.actions, start=1):
        print(" ", action_to_ja(i, action), flush=True)

    print("\nFiles written:", flush=True)
    print(" - backend/data/score_bounds.json", flush=True)
    print(" - backend/data/best_agent_result.json", flush=True)
    print(" - backend/data/best_agent_summary.csv", flush=True)
    print(" - frontend-new/src/data/benchmark_series.json", flush=True)
    print(" - frontend-new/src/data/score_bounds.json", flush=True)


if __name__ == "__main__":
    main()