from pathlib import Path, PosixPath
import numpy as np

DATA_DIR: PosixPath = Path("data")
DATA_DIR.mkdir(exist_ok=True)

RANK_FILE = DATA_DIR / "block_scores.tsv"
ACTION_LOG_FILE = DATA_DIR / "decision_log.csv"
YOUR_NAME_FILE = DATA_DIR / "your_name.csv"

start_year = 2026
end_year = 2100
years = np.arange(start_year, end_year + 1)
total_years = len(years)
SIMULATION_RANDOM_SEED = 857

MANA_JPY_PER_YEAR = 20_000_000
BASE_POLICY_BUDGET_MANA = 10.0
BASE_POLICY_BUDGET_JPY_PER_YEAR = 200_000_000
TURN_YEARS = 25
MIN_POLICY_BUDGET_MANA = 0.0

FLOOD_RECOVERY_COST_COEF = 1.00
INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR = 10_000
MIGRATION_INFRA_PENALTY_MODE = "per_house"
MIGRATION_INFRA_PENALTY_START_MANA = 1.0
MIGRATION_INFRA_PENALTY_MANA_PER_MANA = 0.5
MIGRATION_INFRA_PENALTY_CAP_MANA = BASE_POLICY_BUDGET_MANA * 0.5

POPULATION_BUDGET_MODE = "proportional_to_population"
POPULATION_BUDGET_ALLOW_INCREASE = False
population_budget_multiplier_by_year = {
    2026: 1.00,
    2050: 0.85,
    2075: 0.68,
    2100: 0.52,
}

HIGH_TEMP_TOLERANCE_CAP = 2.5
POLICY_INPUT_UNIT = "mana"

POLICY_MANA_RULES = {
    "planting_trees_amount": {
        "label": "植林・森林保全",
        "min_mana_per_use": 1,
        "max_mana_per_turn": None,
        "cumulative_mana_cap": None,
        "optional_max_forest_share": 0.70,
        "enable_max_forest_share": False,
        "description": "長期的に森林面積を増やし、保水力と生態系を改善する。累積マナ上限は設けない。",
    },
    "capacity_building_cost": {
        "label": "避難訓練・防災訓練",
        "min_mana_per_use": 1,
        "max_mana_per_turn": 1,
        "cumulative_mana_cap": None,
        "description": "住民の対応力を高める。1ターン最大1マナ。",
    },
    "house_migration_amount": {
        "label": "住宅移転",
        "min_mana_per_use": 1,
        "max_mana_per_turn": None,
        "cumulative_mana_cap": 20,
        "max_migration_share": 1.00,
        "alternative_cumulative_mana_cap": 10,
        "alternative_max_migration_share": 0.50,
        "description": "高リスク住宅を安全な地域に移す。累計1マナ超から将来インフラ費用ペナルティが発生する。",
    },
    "agricultural_RnD_cost": {
        "label": "農業R&D・高温適応技術普及",
        "min_mana_per_use": 1,
        "max_mana_per_turn": 2,
        "cumulative_mana_cap": None,
        "description": "高温耐性品種・栽培技術を導入・実証・普及する。1ターン最大2マナ。",
    },
    "dam_levee_construction_cost": {
        "label": "堤防・河川改修",
        "min_mana_per_use": 5,
        "max_mana_per_turn": None,
        "cumulative_mana_cap": None,
        "description": "最低5マナから事業化する大型洪水対策。累積上限は設けない。",
    },
    "paddy_dam_construction_cost": {
        "label": "田んぼダム",
        "min_mana_per_use": 1,
        "max_mana_per_turn": None,
        "cumulative_mana_cap": 6,
        "description": "水田の一時貯留機能を使う流域治水策。累計6マナで最大効果。",
    },
}

POLICY_EFFECT_METADATA = {
    "planting_trees_amount": {
        "meaning_per_mana": "1マナで25年間に約86.6ha相当の植林。効果発現には時間遅れがある。",
        "side_effect": "直接の予算ペナルティは小さいが、短期の洪水対策にはなりにくい。",
    },
    "capacity_building_cost": {
        "meaning_per_mana": "1マナで既存モデルの2単位分の訓練効果。",
        "side_effect": "同じターンに大量投入しても線形に効きにくいため、1ターン最大1マナ。",
    },
    "house_migration_amount": {
        "meaning_per_mana": "1マナで25年間に約513戸を移転できる。",
        "side_effect": "累計1マナ超から、移転住宅1戸あたり年1万円のインフラ維持費ペナルティ。",
    },
    "agricultural_RnD_cost": {
        "meaning_per_mana": "1マナで25年間に高温耐性が約0.4度向上する目安。",
        "side_effect": "洪水被害は直接減らさない。研究・普及の速度制約により1ターン最大2マナ。",
    },
    "dam_levee_construction_cost": {
        "meaning_per_mana": "最低5マナで事業化。20mm強化で代表的な180mm豪雨の越流水を約25%削減。",
        "side_effect": "高コストで、生態系指標には負荷がある。",
    },
    "paddy_dam_construction_cost": {
        "meaning_per_mana": "1マナで180mm豪雨の越流水を約2%削減、累計6マナで最大約13%削減。",
        "side_effect": "最大効果は堤防より小さく、収量に最大1%程度の小さな負担。",
    },
}

EVENT_THRESHOLDS = {
    "major_extreme_rain_mm": 160,
    "warning_extreme_rain_mm": 210,
    "record_extreme_rain_mm": 260,
    "extreme_rain_event_count_per_year": 1,
    "flood_damage_notice_jpy": 250_000_000,
    "major_flood_damage_jpy": 300_000_000,
    "severe_flood_damage_jpy": 350_000_000,
    "ecosystem_low_threshold": 72.0,
    "ecosystem_critical_threshold": 68.0,
    "crop_production_low_ratio": 0.86,
    "crop_production_critical_ratio": 0.72,
    "crop_temp_impact_event_threshold": 0.06,
    "crop_production_low_after_years": 25,
    "available_budget_low_mana": 5.0,
    "available_budget_critical_mana": 3.0,
    "levee_increment_event_mm": 20,
    "forest_effect_area_threshold_ha": 100,
    "forest_effect_matured_thresholds_ha": [100, 300],
    "forest_effect_share_threshold": 0.01,
    "forest_area_low_threshold_ha": 3_100,
    "forest_area_low_after_years": 25,
    "rnd_tolerance_increment_threshold": 0.2,
    "paddy_dam_level_threshold_mm": 5.0,
    "paddy_dam_full_level_mm": 10.0,
    "resident_capacity_threshold": 0.2,
    "resident_capacity_high_threshold": 0.35,
    "resident_capacity_low_threshold": 0.10,
    "resident_capacity_low_after_years": 25,
    "high_risk_houses_high_threshold": 9_000,
    "high_risk_houses_high_after_years": 25,
    "migration_low_mana_after_major_flood": 1.0,
    "migration_budget_pressure_event_threshold": 0.05,
}

EVENT_COOLDOWNS = {
    "extreme_rain": 0,
    "major_flood_damage": 999,
    "severe_flood_damage": 999,
    "ecosystem_low": 999,
    "crop_production_low": 999,
    "budget_low": 999,
}

DEFAULT_PARAMS = {
    "start_year": start_year,
    "end_year": end_year,
    "total_years": total_years,
    "years": years,
    "total_area": 10000,
    "paddy_field_area": 2000,
    "base_temp": 15.5,
    "temp_trend": 0.04,
    "temp_uncertainty": 0.5,
    "base_precip": 1700.0,
    "precip_trend": 0.0,
    "base_precip_uncertainty": 50,
    "precip_uncertainty_trend": 0,
    "base_extreme_precip_freq": 0.1,
    "extreme_precip_freq_trend": 0.05,
    "extreme_precip_intensity_trend": 0.2,
    "extreme_precip_uncertainty_trend": 0.05,
    "base_mu": 180,
    "base_beta": 20,
    "initial_hot_days": 30.0,
    "temp_to_hot_days_coeff": 2.0,
    "hot_days_uncertainty": 2.0,
    "initial_municipal_demand": 100.0,
    "municipal_demand_trend": 0,
    "municipal_demand_uncertainty": 0.01,
    "house_total": 15000,
    "cost_per_migration": 975000,
    "max_available_water": 3000.0,
    "evapotranspiration_amount": 300.0,
    "ecosystem_threshold": 800.0,
    "cost_per_1000trees": 2310000,
    "forest_degradation_rate": 0.01,
    "tree_growup_year": 30,
    "initial_forest_area": 0.5,
    "co2_absorption_per_ha": 8.8,
    "temp_coefficient": 1.0,
    "max_potential_yield": 5000.0,
    "optimal_irrigation_amount": 30.0,
    "necessary_water_for_crops": 330,
    "paddy_dam_cost_per_ha": 1.5,
    "paddy_dam_yield_coef": 0.01,
    "RnD_investment_threshold": 5.0,
    "RnD_investment_required_years": 5,
    "temp_threshold_crop_ini": 28.0,
    "temp_crop_decrease_coef": 0.06,
    "high_temp_tolerance_increment": 0.2,
    "flood_damage_coefficient": 1_000_000,
    "levee_level_increment": 20.0,
    "levee_investment_threshold": 2.0,
    "levee_investment_required_years": 10,
    "flood_recovery_cost_coef": FLOOD_RECOVERY_COST_COEF,
    "runoff_coef": 0.6,
    "transport_level_coef": 1.0,
    "distance_urban_level_coef": 1.0,
    "capacity_building_coefficient": 0.01,
    "resident_capacity_degrade_ratio": 0.05,
    "forest_flood_reduction_coef": 0.4,
    "forest_ecosystem_boost_coef": 0.01,
    "forest_water_retention_coef": 0.2,
    "flood_crop_damage_coef": 0.00001,
    "levee_ecosystem_damage_coef": 0.03,
    "flood_urban_damage_coef": 0.000001,
    "water_ecosystem_coef": 0.01,
    "paddy_dam_flood_coef": 10.0,
    "SIMULATION_RANDOM_SEED": SIMULATION_RANDOM_SEED,
    "MANA_JPY_PER_YEAR": MANA_JPY_PER_YEAR,
    "BASE_POLICY_BUDGET_MANA": BASE_POLICY_BUDGET_MANA,
    "BASE_POLICY_BUDGET_JPY_PER_YEAR": BASE_POLICY_BUDGET_JPY_PER_YEAR,
    "TURN_YEARS": TURN_YEARS,
    "MIN_POLICY_BUDGET_MANA": MIN_POLICY_BUDGET_MANA,
    "FLOOD_RECOVERY_COST_COEF": FLOOD_RECOVERY_COST_COEF,
    "INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR": INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR,
    "MIGRATION_INFRA_PENALTY_MODE": MIGRATION_INFRA_PENALTY_MODE,
    "MIGRATION_INFRA_PENALTY_START_MANA": MIGRATION_INFRA_PENALTY_START_MANA,
    "MIGRATION_INFRA_PENALTY_MANA_PER_MANA": MIGRATION_INFRA_PENALTY_MANA_PER_MANA,
    "MIGRATION_INFRA_PENALTY_CAP_MANA": MIGRATION_INFRA_PENALTY_CAP_MANA,
    "POPULATION_BUDGET_MODE": POPULATION_BUDGET_MODE,
    "POPULATION_BUDGET_ALLOW_INCREASE": POPULATION_BUDGET_ALLOW_INCREASE,
    "population_budget_multiplier_by_year": population_budget_multiplier_by_year,
    "HIGH_TEMP_TOLERANCE_CAP": HIGH_TEMP_TOLERANCE_CAP,
    "POLICY_INPUT_UNIT": POLICY_INPUT_UNIT,
    "POLICY_MANA_RULES": POLICY_MANA_RULES,
    "POLICY_EFFECT_METADATA": POLICY_EFFECT_METADATA,
    "EVENT_THRESHOLDS": EVENT_THRESHOLDS,
    "EVENT_COOLDOWNS": EVENT_COOLDOWNS,
}

rcp_climate_params = {
    1.9: {"temp_trend": 0.02, "precip_uncertainty_trend": 0, "extreme_precip_freq_trend": 0.01, "extreme_precip_intensity_trend": 0.02, "extreme_precip_uncertainty_trend": 0.05},
    2.6: {"temp_trend": 0.025, "precip_uncertainty_trend": 0, "extreme_precip_freq_trend": 0.015, "extreme_precip_intensity_trend": 0.025, "extreme_precip_uncertainty_trend": 0.07},
    4.5: {"temp_trend": 0.035, "precip_uncertainty_trend": 0, "extreme_precip_freq_trend": 0.02, "extreme_precip_intensity_trend": 0.035, "extreme_precip_uncertainty_trend": 0.1},
    6.0: {"temp_trend": 0.045, "precip_uncertainty_trend": 0, "extreme_precip_freq_trend": 0.03, "extreme_precip_intensity_trend": 0.045, "extreme_precip_uncertainty_trend": 0.13},
    8.5: {"temp_trend": 0.06, "precip_uncertainty_trend": 0, "extreme_precip_freq_trend": 0.04, "extreme_precip_intensity_trend": 0.06, "extreme_precip_uncertainty_trend": 0.15},
}

__all__ = [
    "DATA_DIR", "RANK_FILE", "ACTION_LOG_FILE", "YOUR_NAME_FILE",
    "DEFAULT_PARAMS", "rcp_climate_params", "SIMULATION_RANDOM_SEED",
    "MANA_JPY_PER_YEAR", "BASE_POLICY_BUDGET_MANA", "BASE_POLICY_BUDGET_JPY_PER_YEAR",
    "TURN_YEARS", "FLOOD_RECOVERY_COST_COEF", "INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR",
    "POLICY_MANA_RULES", "POLICY_EFFECT_METADATA", "EVENT_THRESHOLDS",
]
