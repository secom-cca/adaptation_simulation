from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import DEFAULT_PARAMS, rcp_climate_params
from simulation import POLICY_KEYS, calculate_budget_components, simulate_year


START_YEAR = 2026
END_YEAR = 2100
TURN_YEARS = 25
TURN_STARTS = [2026, 2051, 2076]


INITIAL_VALUES: dict[str, Any] = {
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


def mana(**kwargs: float) -> dict[str, float]:
    row = {key: 0.0 for key in POLICY_KEYS}
    row.update({key: float(value) for key, value in kwargs.items()})
    return row


def use_budget(available: float, priorities: list[tuple[str, float | None]]) -> tuple[dict[str, float], float, list[str]]:
    remaining = max(0.0, float(available))
    decision = mana()
    violations: list[str] = []
    for key, target in priorities:
        if remaining <= 1e-9:
            break
        max_turn = DEFAULT_PARAMS["POLICY_MANA_RULES"].get(key, {}).get("max_mana_per_turn")
        min_use = DEFAULT_PARAMS["POLICY_MANA_RULES"].get(key, {}).get("min_mana_per_use")
        desired = remaining if target is None else min(float(target), remaining)
        if max_turn is not None:
            desired = min(desired, float(max_turn))
        if min_use is not None and 0 < desired < float(min_use):
            continue
        decision[key] += desired
        remaining -= desired
    if remaining > 0.05:
        violations.append(f"unused_mana={remaining:.2f}")
    return decision, remaining, violations


def scenario_priorities(name: str, turn_index: int) -> list[tuple[str, float | None]]:
    if name == "01_no_policy":
        return []
    if name == "02_hard_infra":
        return [("dam_levee_construction_cost", None), ("paddy_dam_construction_cost", None), ("capacity_building_cost", None)]
    if name == "03_nature_based":
        return [("paddy_dam_construction_cost", 6), ("planting_trees_amount", None)]
    if name == "04_agri_rnd":
        return [("agricultural_RnD_cost", 2), ("planting_trees_amount", None), ("paddy_dam_construction_cost", None)]
    if name == "05_relocation_capacity":
        return [("capacity_building_cost", 1), ("house_migration_amount", None), ("paddy_dam_construction_cost", None), ("agricultural_RnD_cost", 2)]
    if name == "06_balanced":
        if turn_index == 0:
            return [
                ("dam_levee_construction_cost", 5), ("paddy_dam_construction_cost", 1),
                ("planting_trees_amount", 1), ("house_migration_amount", 1),
                ("capacity_building_cost", 1), ("agricultural_RnD_cost", 1),
            ]
        return [("agricultural_RnD_cost", 2), ("capacity_building_cost", 1), ("paddy_dam_construction_cost", 2), ("planting_trees_amount", None), ("dam_levee_construction_cost", 5)]
    if name == "07_late_response":
        if turn_index == 0:
            return []
        return [("dam_levee_construction_cost", 5), ("capacity_building_cost", 1), ("agricultural_RnD_cost", 2), ("paddy_dam_construction_cost", None), ("planting_trees_amount", None)]
    if name == "08_ecosystem_sacrifice":
        return [("dam_levee_construction_cost", None), ("house_migration_amount", None)]
    if name == "09_flood_neglect":
        return [("agricultural_RnD_cost", 2), ("planting_trees_amount", None), ("capacity_building_cost", 1)]
    return []


SCENARIO_LABELS = {
    "01_no_policy": "放置",
    "02_hard_infra": "堤防偏重",
    "03_nature_based": "自然共生偏重",
    "04_agri_rnd": "農業R&D偏重",
    "05_relocation_capacity": "移転・防災偏重",
    "06_balanced": "バランス型",
    "07_late_response": "後手対応",
    "08_ecosystem_sacrifice": "生態系犠牲型",
    "09_flood_neglect": "洪水軽視型",
}


def make_params(rcp_value: float = 4.5, seed: int | None = None, paddy_coef: float | None = None) -> dict[str, Any]:
    params = DEFAULT_PARAMS.copy()
    closest_rcp = min(rcp_climate_params.keys(), key=lambda value: abs(value - rcp_value))
    params.update(rcp_climate_params[closest_rcp])
    if seed is not None:
        params["SIMULATION_RANDOM_SEED"] = int(seed)
    if paddy_coef is not None:
        params["paddy_dam_flood_coef"] = float(paddy_coef)
    return params


def simulate_full_mana_scenario(name: str, params: dict[str, Any]) -> dict[str, Any]:
    state = deepcopy(INITIAL_VALUES)
    rows: list[dict[str, Any]] = []
    event_log: list[dict[str, Any]] = []
    budget_log: list[dict[str, Any]] = []
    previous_turn_avg_flood = 0.0

    for turn_index, turn_start in enumerate(TURN_STARTS):
        state["last_25y_avg_flood_damage_jpy"] = previous_turn_avg_flood
        available = calculate_budget_components(turn_start, state, params)["available_budget_mana"]
        decision, remaining, violations = use_budget(available, scenario_priorities(name, turn_index))
        if name == "01_no_policy":
            remaining = available
            violations = []
        budget_log.append({
            "turn": turn_index + 1,
            "available_budget_mana": round(available, 3),
            "used_mana": round(sum(decision.values()), 3),
            "remaining_mana": round(remaining, 3),
            "violations": ";".join(violations),
            **{key: round(decision.get(key, 0.0), 3) for key in POLICY_KEYS},
        })

        turn_rows = []
        for year in range(turn_start, min(turn_start + TURN_YEARS, END_YEAR + 1)):
            state["last_25y_avg_flood_damage_jpy"] = previous_turn_avg_flood
            year_decision = dict(decision)
            year_decision.update({"year": year, "cp_climate_params": 4.5, "transportation_invest": 0.0})
            state, output = simulate_year(year, state, year_decision, params, fixed_seed=True)
            rows.append(output)
            turn_rows.append(output)
            for event in output.get("events", []):
                event_log.append({
                    "year": event.get("year", year),
                    "id": event.get("id"),
                    "category": event.get("category"),
                    "group": event.get("group"),
                    "severity": event.get("severity"),
                    "value": event.get("value"),
                    "threshold": event.get("threshold"),
                })
        if turn_rows:
            previous_turn_avg_flood = sum(row.get("Flood Damage JPY", 0.0) for row in turn_rows) / len(turn_rows)

    final = rows[-1]
    return {
        "scenario": name,
        "label": SCENARIO_LABELS[name],
        "rows": rows,
        "event_log": event_log,
        "budget_log": budget_log,
        "max_flood_damage_jpy": max(row.get("Flood Damage JPY", 0.0) for row in rows),
        "final_available_budget_mana": final.get("available_budget_mana", 0.0),
        "final_crop_yield": final.get("Crop Yield", 0.0),
        "final_ecosystem_level": final.get("Ecosystem Level", 0.0),
        "final_risky_houses": final.get("risky_house_total", 0.0),
        "final_resident_capacity": final.get("Resident capacity", 0.0),
    }


def run_all_full_mana(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [simulate_full_mana_scenario(name, params) for name in SCENARIO_LABELS]
