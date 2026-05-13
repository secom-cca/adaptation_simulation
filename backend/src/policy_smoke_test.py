from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import DEFAULT_PARAMS
from simulation import calculate_budget_components, convert_mana_decisions_to_backend_units, simulate_year


def main():
    params = DEFAULT_PARAMS.copy()
    decision_mana = {
        "planting_trees_amount": 1,
        "house_migration_amount": 1,
        "dam_levee_construction_cost": 5,
        "paddy_dam_construction_cost": 1,
        "capacity_building_cost": 1,
        "agricultural_RnD_cost": 2,
    }
    converted, policy_mana = convert_mana_decisions_to_backend_units(decision_mana, params)
    assert round(converted["agricultural_RnD_cost"], 3) == 4.0
    assert round(converted["dam_levee_construction_cost"], 3) == 1.0
    assert 20.0 < converted["house_migration_amount"] < 21.0
    assert policy_mana["dam_levee_construction_cost"] == 5

    prev_values = {
        "temp": 15.5,
        "precip": 1700.0,
        "municipal_demand": 100.0,
        "available_water": 2000.0,
        "crop_yield": 4500.0,
        "hot_days": 30.0,
        "extreme_precip_freq": 0.1,
        "ecosystem_level": 1000.0,
        "levee_level": 100.0,
        "high_temp_tolerance_level": 0.0,
        "forest_area": 5000.0,
        "planting_history": {},
        "urban_level": 100.0,
        "resident_capacity": 0.0,
        "transportation_level": 100.0,
        "levee_investment_total": 0.0,
        "RnD_investment_total": 0.0,
        "risky_house_total": 15000.0,
        "non_risky_house_total": 0.0,
        "resident_burden": 0.0,
        "biodiversity_level": 100.0,
        "paddy_dam_area": 0.0,
        "last_25y_avg_flood_damage_jpy": 100_000_000,
    }
    budget = calculate_budget_components(2050, prev_values, params)
    assert round(budget["population_decline_penalty_mana"], 2) == 1.5
    assert round(budget["flood_recovery_penalty_mana"], 2) == 5.0

    current_values, outputs = simulate_year(2026, prev_values, decision_mana, params, fixed_seed=True)
    assert outputs["policy_mana"]["house_migration_amount"] == 1
    assert outputs["paddy_dam_area"] <= params["paddy_field_area"]
    assert "events" in outputs
    assert current_values["cumulative_migrated_houses"] > 0
    print("policy_smoke_test ok")


if __name__ == "__main__":
    main()
