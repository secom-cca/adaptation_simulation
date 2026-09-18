from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any, Dict, List

from config import DEFAULT_PARAMS, POLICY_MANA_RULES, rcp_climate_params
from simulation import calculate_budget_components, simulate_year


POLICY_KEYS = (
    "planting_trees_amount",
    "house_migration_amount",
    "dam_levee_construction_cost",
    "paddy_dam_construction_cost",
    "capacity_building_cost",
    "agricultural_RnD_cost",
)

POLICY_LABELS_JA = {
    "planting_trees_amount": "植林・森林保全",
    "house_migration_amount": "住宅移転",
    "dam_levee_construction_cost": "堤防・河川改修",
    "paddy_dam_construction_cost": "田んぼダム",
    "capacity_building_cost": "防災訓練",
    "agricultural_RnD_cost": "農業R&D",
}

MODE_KEYS = {
    "upstream": {
        "planting_trees_amount",
        "dam_levee_construction_cost",
        "paddy_dam_construction_cost",
    },
    "downstream": {
        "house_migration_amount",
        "capacity_building_cost",
        "agricultural_RnD_cost",
    },
    "team": set(POLICY_KEYS),
}

# A compact, interpretable decision set. Every three-turn ordering of the
# packages available in the selected role is evaluated.
PACKAGE_TEMPLATES = (
    ("none", "投資なし", {}),
    ("nature", "自然基盤重視", {
        "planting_trees_amount": 7,
        "paddy_dam_construction_cost": 2,
        "capacity_building_cost": 1,
    }),
    ("hard_defense", "堤防・移転重視", {
        "dam_levee_construction_cost": 7,
        "house_migration_amount": 2,
        "capacity_building_cost": 1,
    }),
    ("distributed_flood", "分散型治水重視", {
        "planting_trees_amount": 2,
        "house_migration_amount": 1,
        "paddy_dam_construction_cost": 6,
        "capacity_building_cost": 1,
    }),
    ("relocation", "住宅移転重視", {
        "house_migration_amount": 8,
        "capacity_building_cost": 1,
        "agricultural_RnD_cost": 1,
    }),
    ("agriculture", "農業適応重視", {
        "planting_trees_amount": 3,
        "paddy_dam_construction_cost": 4,
        "capacity_building_cost": 1,
        "agricultural_RnD_cost": 2,
    }),
    ("forest", "森林再生重視", {
        "planting_trees_amount": 9,
        "capacity_building_cost": 1,
    }),
    ("levee", "河川防御重視", {
        "dam_levee_construction_cost": 9,
        "capacity_building_cost": 1,
    }),
    ("balanced_hard", "治水均衡型", {
        "planting_trees_amount": 2,
        "house_migration_amount": 1,
        "dam_levee_construction_cost": 5,
        "paddy_dam_construction_cost": 1,
        "capacity_building_cost": 1,
    }),
    ("balanced", "総合均衡型", {
        "planting_trees_amount": 3,
        "house_migration_amount": 2,
        "paddy_dam_construction_cost": 2,
        "capacity_building_cost": 1,
        "agricultural_RnD_cost": 2,
    }),
)


def _initial_values() -> Dict[str, Any]:
    return {
        "temp": 15.5,
        "precip": 1700.0,
        "municipal_demand": 100.0,
        "available_water": 2000.0,
        "crop_yield": 4500.0,
        "hot_days": 30.0,
        "extreme_precip_freq": 0.1,
        "ecosystem_level": 1000.0,
        "levee_level": 0.0,
        "high_temp_tolerance_level": 0.0,
        "forest_area": 5000.0,
        "planting_history": {},
        "urban_level": 0.0,
        "resident_capacity": 0.0,
        "transportation_level": 100.0,
        "levee_investment_total": 0.0,
        "RnD_investment_total": 0.0,
        "risky_house_total": 10000.0,
        "non_risky_house_total": 0.0,
        "resident_burden": 0.0,
        "biodiversity_level": 0.0,
        "paddy_dam_area": 0.0,
        "cumulative_migrated_houses": 0.0,
        "cumulative_house_migration_mana": 0.0,
        "cumulative_planting_mana": 0.0,
        "cumulative_agricultural_RnD_mana": 0.0,
        "cumulative_defense_mana": 0.0,
        "initial_risky_house_total": 10000.0,
        "initial_crop_yield": 4500.0,
        "events_state": {},
        "available_budget_mana": 10.0,
        "population_budget_multiplier": 1.0,
        "population_decline_penalty_mana": 0.0,
        "migration_infra_penalty_mana": 0.0,
        "flood_recovery_penalty_mana": 0.0,
        "last_25y_avg_flood_damage_jpy": 0.0,
    }


def _packages_for_mode(mode: str) -> List[Dict[str, Any]]:
    allowed = MODE_KEYS.get(mode, MODE_KEYS["team"])
    packages: List[Dict[str, Any]] = []
    seen = set()

    for package_id, name, template in PACKAGE_TEMPLATES:
        allocations = {key: int(template.get(key, 0)) if key in allowed else 0 for key in POLICY_KEYS}
        signature = tuple(allocations[key] for key in POLICY_KEYS)
        if signature in seen:
            continue
        seen.add(signature)
        packages.append({"id": package_id, "name": name, "allocations": allocations})

    return packages


def _fit_package(
    template: Dict[str, int],
    budget: int,
    cumulative: Dict[str, int],
) -> Dict[str, int]:
    allocations = {key: max(0, int(template.get(key, 0))) for key in POLICY_KEYS}

    paddy_remaining = max(0, 6 - cumulative.get("paddy_dam_construction_cost", 0))
    migration_remaining = max(0, 20 - cumulative.get("house_migration_amount", 0))
    allocations["paddy_dam_construction_cost"] = min(
        allocations["paddy_dam_construction_cost"], paddy_remaining, 6,
    )
    allocations["house_migration_amount"] = min(
        allocations["house_migration_amount"], migration_remaining,
    )
    allocations["capacity_building_cost"] = min(allocations["capacity_building_cost"], 1)
    allocations["agricultural_RnD_cost"] = min(allocations["agricultural_RnD_cost"], 2)

    while sum(allocations.values()) > budget:
        active = [key for key, value in allocations.items() if value > 0]
        if not active:
            break
        key = max(active, key=lambda item: (allocations[item], -POLICY_KEYS.index(item)))
        allocations[key] -= 1
        rule = POLICY_MANA_RULES.get(key, {})
        minimum = int(rule.get("min_mana_per_use") or 1)
        if 0 < allocations[key] < minimum:
            allocations[key] = 0

    return allocations


def _decision(year: int, rcp_value: float, allocations: Dict[str, int]) -> Dict[str, float]:
    return {
        "year": year,
        "cp_climate_params": rcp_value,
        "transportation_invest": 0.0,
        **{key: float(allocations.get(key, 0)) for key in POLICY_KEYS},
    }


def _advance_node(
    node: Dict[str, Any],
    package: Dict[str, Any],
    turn_index: int,
    params: Dict[str, Any],
    rcp_value: float,
) -> Dict[str, Any]:
    state = deepcopy(node["state"])
    cumulative = dict(node["cumulative"])
    start_year = 2026 + turn_index * 25
    budget_components = calculate_budget_components(start_year, state, params)
    budget = max(0, int(round(budget_components["available_budget_mana"])))
    allocations = _fit_package(package["allocations"], budget, cumulative)
    period_flood = 0.0
    crop_sum = 0.0
    ecosystem_sum = 0.0
    public_cost = 0.0

    for year in range(start_year, start_year + 25):
        state, output = simulate_year(
            year,
            state,
            _decision(year, rcp_value, allocations),
            params,
            fixed_seed=True,
        )
        period_flood += float(output.get("Flood Damage JPY", 0) or 0)
        crop_sum += float(output.get("Crop Yield", 0) or 0)
        ecosystem_sum += float(output.get("Ecosystem Level", 0) or 0)
        public_cost += float(output.get("Municipal Cost", 0) or 0)

    state["last_25y_avg_flood_damage_jpy"] = period_flood / 25
    for key in POLICY_KEYS:
        cumulative[key] += allocations[key]

    return {
        "state": state,
        "cumulative": cumulative,
        "flood_damage_jpy": node["flood_damage_jpy"] + period_flood,
        "crop_sum": node["crop_sum"] + crop_sum,
        "ecosystem_sum": node["ecosystem_sum"] + ecosystem_sum,
        "public_cost_jpy": node["public_cost_jpy"] + public_cost,
        "policies": [
            *node["policies"],
            {
                "turn": turn_index + 1,
                "year": start_year,
                "package_id": package["id"],
                "package_name": package["name"],
                "budget": budget,
                "allocations": allocations,
            },
        ],
    }


def _normalized(value: float, low: float, high: float, higher_is_better: bool = True) -> float:
    if high <= low:
        return 1.0
    ratio = (value - low) / (high - low)
    return ratio if higher_is_better else 1.0 - ratio


def _pareto_ids(results: List[Dict[str, Any]]) -> set[int]:
    pareto: set[int] = set()
    ordered = sorted(results, key=lambda row: (row["flood_damage_jpy"], -row["crop_yield"]))

    # The result set is small, and this direct test keeps all three objectives exact.
    for candidate in ordered:
        dominated = False
        for other in results:
            if other["id"] == candidate["id"]:
                continue
            no_worse = (
                other["flood_damage_jpy"] <= candidate["flood_damage_jpy"]
                and other["crop_yield"] >= candidate["crop_yield"]
                and other["ecosystem_level"] >= candidate["ecosystem_level"]
            )
            strictly_better = (
                other["flood_damage_jpy"] < candidate["flood_damage_jpy"]
                or other["crop_yield"] > candidate["crop_yield"]
                or other["ecosystem_level"] > candidate["ecosystem_level"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            pareto.add(candidate["id"])

    return pareto


@lru_cache(maxsize=12)
def explore_scenarios(mode: str, rcp_value: float) -> Dict[str, Any]:
    safe_mode = mode if mode in MODE_KEYS else "team"
    available_rcps = list(rcp_climate_params.keys())
    selected_rcp = min(available_rcps, key=lambda value: abs(float(value) - float(rcp_value)))
    params = DEFAULT_PARAMS.copy()
    params.update(rcp_climate_params[selected_rcp])
    packages = _packages_for_mode(safe_mode)

    nodes = [{
        "state": _initial_values(),
        "cumulative": {key: 0 for key in POLICY_KEYS},
        "flood_damage_jpy": 0.0,
        "crop_sum": 0.0,
        "ecosystem_sum": 0.0,
        "public_cost_jpy": 0.0,
        "policies": [],
    }]
    for turn_index in range(3):
        nodes = [
            _advance_node(node, package, turn_index, params, float(selected_rcp))
            for node in nodes
            for package in packages
        ]

    results: List[Dict[str, Any]] = []
    for scenario_id, node in enumerate(nodes, start=1):
        results.append({
            "id": scenario_id,
            "flood_damage_jpy": node["flood_damage_jpy"],
            "crop_yield": node["crop_sum"] / 75,
            "ecosystem_level": node["ecosystem_sum"] / 75,
            "public_cost_jpy": node["public_cost_jpy"],
            "policies": node["policies"],
        })

    ranges = {
        key: {
            "min": min(result[key] for result in results),
            "max": max(result[key] for result in results),
        }
        for key in ("flood_damage_jpy", "crop_yield", "ecosystem_level", "public_cost_jpy")
    }

    for result in results:
        result["balanced_score"] = 100 * sum((
            _normalized(
                result["flood_damage_jpy"],
                ranges["flood_damage_jpy"]["min"],
                ranges["flood_damage_jpy"]["max"],
                higher_is_better=False,
            ),
            _normalized(
                result["crop_yield"],
                ranges["crop_yield"]["min"],
                ranges["crop_yield"]["max"],
            ),
            _normalized(
                result["ecosystem_level"],
                ranges["ecosystem_level"]["min"],
                ranges["ecosystem_level"]["max"],
            ),
        )) / 3

    pareto_ids = _pareto_ids(results)
    for result in results:
        result["pareto"] = result["id"] in pareto_ids

    representative_specs = (
        ("balanced", "総合バランス", max(results, key=lambda row: row["balanced_score"])),
        ("flood", "洪水被害が最小", min(results, key=lambda row: row["flood_damage_jpy"])),
        ("crop", "農作物生産高が最大", max(results, key=lambda row: row["crop_yield"])),
        ("ecosystem", "生態系が最大", max(results, key=lambda row: row["ecosystem_level"])),
        ("cost", "公的出費が最小", min(results, key=lambda row: row["public_cost_jpy"])),
    )
    representatives = []
    used_ids = set()
    for kind, label, result in representative_specs:
        if result["id"] in used_ids:
            continue
        used_ids.add(result["id"])
        representatives.append({"kind": kind, "label": label, **result})

    points = [{
        "id": result["id"],
        "flood_damage_jpy": result["flood_damage_jpy"],
        "crop_yield": result["crop_yield"],
        "ecosystem_level": result["ecosystem_level"],
        "public_cost_jpy": result["public_cost_jpy"],
        "balanced_score": result["balanced_score"],
        "pareto": result["pareto"],
    } for result in results]

    return {
        "mode": safe_mode,
        "rcp_value": selected_rcp,
        "package_count": len(packages),
        "scenario_count": len(results),
        "point_level_theoretical_count": 3_228_667_352 if safe_mode == "team" else None,
        "method": "representative_package_exhaustive",
        "ranges": ranges,
        "pareto_count": len(pareto_ids),
        "points": points,
        "representatives": representatives,
        "pareto_scenarios": sorted(
            (result for result in results if result["pareto"]),
            key=lambda row: row["balanced_score"],
            reverse=True,
        ),
        "policy_labels": POLICY_LABELS_JA,
        "packages": packages,
    }
