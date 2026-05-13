from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import DEFAULT_PARAMS, rcp_climate_params
from simulation import simulate_year


START_YEAR = 2026
TURN_YEARS = 25
TURN_STARTS = [2026, 2051, 2076]
END_YEAR = 2100

POLICY_KEYS = [
    "planting_trees_amount",
    "house_migration_amount",
    "dam_levee_construction_cost",
    "paddy_dam_construction_cost",
    "capacity_building_cost",
    "agricultural_RnD_cost",
]

WATCH_EVENTS = {
    "extreme_rain": "extreme_rain_",
    "major_flood": "major_flood_damage_",
    "severe_flood": "severe_flood_damage_",
    "crop_low": "crop_production_low",
    "crop_critical": "crop_production_critical",
    "ecosystem_low": "ecosystem_low",
    "ecosystem_critical": "ecosystem_critical",
    "budget_low": "budget_low",
    "budget_critical": "budget_critical",
    "forest_low": "forest_area_low",
    "high_risk_houses": "high_risk_houses_unmanaged",
    "resident_capacity_low": "resident_capacity_low",
    "migration_budget_pressure": "migration_budget_pressure",
    "levee_step": "levee_20mm_step_",
    "rnd_improved": "rnd_tolerance_improved_",
    "paddy_dam_5mm": "paddy_dam_5mm",
}


INITIAL_VALUES = {
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
    row.update(kwargs)
    return row


SCENARIOS = [
    {
        "name": "01_no_policy",
        "label": "放置",
        "turns": [mana(), mana(), mana()],
    },
    {
        "name": "02_flood_infra_early",
        "label": "初期に堤防重視",
        "turns": [
            mana(dam_levee_construction_cost=5, paddy_dam_construction_cost=1),
            mana(dam_levee_construction_cost=5),
            mana(),
        ],
    },
    {
        "name": "03_distributed_flood",
        "label": "田んぼダム中心の流域治水",
        "turns": [
            mana(paddy_dam_construction_cost=3, planting_trees_amount=1),
            mana(paddy_dam_construction_cost=3, planting_trees_amount=2),
            mana(planting_trees_amount=2),
        ],
    },
    {
        "name": "04_agri_rnd_early",
        "label": "農業R&D先行",
        "turns": [
            mana(agricultural_RnD_cost=2, planting_trees_amount=1),
            mana(agricultural_RnD_cost=2),
            mana(agricultural_RnD_cost=1),
        ],
    },
    {
        "name": "05_forest_early",
        "label": "森林保全先行",
        "turns": [
            mana(planting_trees_amount=4),
            mana(planting_trees_amount=4),
            mana(planting_trees_amount=2),
        ],
    },
    {
        "name": "06_resident_relocation",
        "label": "移転と防災訓練",
        "turns": [
            mana(house_migration_amount=1, capacity_building_cost=1),
            mana(house_migration_amount=1, capacity_building_cost=1),
            mana(capacity_building_cost=1),
        ],
    },
    {
        "name": "07_balanced",
        "label": "バランス型",
        "turns": [
            mana(dam_levee_construction_cost=5, agricultural_RnD_cost=1, capacity_building_cost=1, house_migration_amount=1, planting_trees_amount=1, paddy_dam_construction_cost=1),
            mana(agricultural_RnD_cost=1, planting_trees_amount=2, paddy_dam_construction_cost=1, capacity_building_cost=1),
            mana(planting_trees_amount=2, agricultural_RnD_cost=1),
        ],
    },
    {
        "name": "08_hard_infra_heavy",
        "label": "堤防偏重",
        "turns": [
            mana(dam_levee_construction_cost=10),
            mana(dam_levee_construction_cost=10),
            mana(dam_levee_construction_cost=5),
        ],
    },
    {
        "name": "09_late_response",
        "label": "後手対応",
        "turns": [
            mana(),
            mana(dam_levee_construction_cost=5, agricultural_RnD_cost=1, capacity_building_cost=1),
            mana(planting_trees_amount=3, house_migration_amount=1, paddy_dam_construction_cost=2),
        ],
    },
    {
        "name": "10_nature_and_agri",
        "label": "自然共生と農業",
        "turns": [
            mana(planting_trees_amount=3, agricultural_RnD_cost=2),
            mana(planting_trees_amount=3, agricultural_RnD_cost=2, paddy_dam_construction_cost=1),
            mana(planting_trees_amount=2, paddy_dam_construction_cost=2),
        ],
    },
]


def decision_for_year(scenario: dict[str, Any], year: int, rcp_value: float) -> dict[str, float]:
    turn_index = min((year - START_YEAR) // TURN_YEARS, len(scenario["turns"]) - 1)
    decision = dict(scenario["turns"][turn_index])
    decision["year"] = year
    decision["cp_climate_params"] = rcp_value
    decision["transportation_invest"] = 0.0
    return decision


def event_matches(event_id: str, pattern: str) -> bool:
    return event_id == pattern or event_id.startswith(pattern)


def summarize_policy(turns: list[dict[str, float]]) -> str:
    chunks = []
    for idx, turn in enumerate(turns, start=1):
        used = [f"{key}={value:g}" for key, value in turn.items() if value]
        chunks.append(f"T{idx}: " + (", ".join(used) if used else "none"))
    return " | ".join(chunks)


def simulate_scenario(scenario: dict[str, Any], rcp_value: float) -> dict[str, Any]:
    params = DEFAULT_PARAMS.copy()
    closest_rcp = min(rcp_climate_params.keys(), key=lambda value: abs(value - rcp_value))
    params.update(rcp_climate_params[closest_rcp])

    state = deepcopy(INITIAL_VALUES)
    rows = []
    event_years: dict[str, int | None] = {key: None for key in WATCH_EVENTS}
    event_log = []
    previous_turn_avg_flood = 0.0

    for turn_start in TURN_STARTS:
        turn_rows = []
        for year in range(turn_start, min(turn_start + TURN_YEARS, END_YEAR + 1)):
            state["last_25y_avg_flood_damage_jpy"] = previous_turn_avg_flood
            decision = decision_for_year(scenario, year, closest_rcp)
            state, output = simulate_year(year, state, decision, params, fixed_seed=True)
            rows.append(output)
            turn_rows.append(output)

            for event in output.get("events", []):
                event_id = event.get("id", "")
                event_log.append(
                    {
                        "year": year,
                        "id": event_id,
                        "category": event.get("category"),
                        "value": event.get("value"),
                        "threshold": event.get("threshold"),
                    }
                )
                for key, pattern in WATCH_EVENTS.items():
                    if event_years[key] is None and event_matches(event_id, pattern):
                        event_years[key] = year

        if turn_rows:
            previous_turn_avg_flood = sum(row.get("Flood Damage JPY", 0.0) for row in turn_rows) / len(turn_rows)

    final = rows[-1]
    return {
        "scenario": scenario["name"],
        "label": scenario["label"],
        "policy": summarize_policy(scenario["turns"]),
        **event_years,
        "extreme_rain_count": sum(
            1 for item in event_log
            if str(item["id"]).startswith(("heavy_rain_", "extreme_rain_"))
        ),
        "final_crop_yield": round(final.get("Crop Yield", 0.0), 1),
        "final_heat_only_crop_yield": round(final.get("Heat-only Crop Yield", 0.0), 1),
        "final_ecosystem_level": round(final.get("Ecosystem Level", 0.0), 2),
        "final_forest_area": round(final.get("Forest Area", 0.0), 1),
        "final_levee_level": round(final.get("Levee Level", 0.0), 1),
        "final_resident_capacity": round(final.get("Resident capacity", 0.0), 3),
        "final_risky_houses": round(final.get("risky_house_total", 0.0), 1),
        "final_available_budget_mana": round(final.get("available_budget_mana", 0.0), 2),
        "max_flood_damage_jpy": round(max(row.get("Flood Damage JPY", 0.0) for row in rows), 1),
        "event_log": json.dumps(event_log, ensure_ascii=False),
    }


def write_outputs(results: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scenario",
        "label",
        "policy",
        *WATCH_EVENTS.keys(),
        "extreme_rain_count",
        "max_flood_damage_jpy",
        "final_crop_yield",
        "final_heat_only_crop_yield",
        "final_ecosystem_level",
        "final_forest_area",
        "final_levee_level",
        "final_resident_capacity",
        "final_risky_houses",
        "final_available_budget_mana",
        "event_log",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def print_summary(results: list[dict[str, Any]]) -> None:
    columns = [
        "label",
        "major_flood",
        "crop_low",
        "ecosystem_low",
        "budget_low",
        "forest_low",
        "high_risk_houses",
        "resident_capacity_low",
        "extreme_rain_count",
    ]
    print("\t".join(columns))
    for result in results:
        print("\t".join("" if result.get(column) is None else str(result.get(column)) for column in columns))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 3-turn event sensitivity checks for adaptation policies.")
    parser.add_argument("--rcp", type=float, default=4.5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "event_sensitivity_rcp45.csv",
    )
    args = parser.parse_args()

    results = [simulate_scenario(scenario, args.rcp) for scenario in SCENARIOS]
    write_outputs(results, args.output)
    print_summary(results)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
