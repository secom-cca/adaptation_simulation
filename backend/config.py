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

DEFAULT_PARAMS = {
    'start_year': start_year,
    'end_year': end_year,
    'total_years': total_years,
    'years': years,

    # 地形
    'total_area': 10000,
    'paddy_field_area': 1000,
    # 'max_forest_area': 7000, 

    # 気温・降水・高温日数
    'base_temp': 15.0,
    'temp_trend': 0.04,
    'temp_uncertainty': 0.5,

    'base_precip': 1700.0,
    'precip_trend': 0,
    'base_precip_uncertainty': 50,
    'precip_uncertainty_trend': 5,

    'base_extreme_precip_freq': 0.1,
    'extreme_precip_freq_trend': 0.05,
    'extreme_precip_intensity_trend': 0.2,
    'extreme_precip_uncertainty_trend': 0.05,
    'base_mu': 180,
    'base_beta': 20,

    'initial_hot_days': 30.0,
    'temp_to_hot_days_coeff': 2.0,
    'hot_days_uncertainty': 2.0,

    # 需要（生活用水）↔︎ 住民の数とも合致
    'initial_municipal_demand': 100.0,
    'municipal_demand_trend': 0,
    'municipal_demand_uncertainty': 0.01,

    # 住宅
    'house_total': 15000,
    'cost_per_migration': 975000,

    # 水循環
    'max_available_water': 3000.0,
    'evapotranspiration_amount': 300.0,
    'ecosystem_threshold': 800.0,

    # 森林
    'cost_per_1000trees': 2310000,
    'forest_degradation_rate': 0.01,
    'tree_growup_year': 30,
    'initial_forest_area': 0.5,
    'co2_absorption_per_ha': 8.8,

    # 農業
    'temp_coefficient': 1.0,
    'max_potential_yield': 5000.0,
    'optimal_irrigation_amount': 30.0,
    'necessary_water_for_crops': 330, # [m3/ha]
    'paddy_dam_cost_per_ha': 1.5,
    'paddy_dam_yield_coef': 0.01,

    # 農業R&D
    'RnD_investment_threshold': 5.0, ############
    'RnD_investment_required_years': 5, ###########
    'temp_threshold_crop_ini': 28.0,
    'temp_crop_decrease_coef': 0.06,
    'high_temp_tolerance_increment': 0.2,

    # 水災害
    'flood_damage_coefficient': 100000,
    'levee_level_increment': 20.0,
    'levee_investment_threshold': 2.0, #########
    'levee_investment_required_years': 10, ###########
    'flood_recovery_cost_coef': 0.1,
    'runoff_coef': 0.55,

    # 交通
    'transport_level_coef': 1.0,
    'distance_urban_level_coef': 1.0,

    # 住民意識
    'capacity_building_coefficient': 0.01,
    'resident_capacity_degrade_ratio': 0.05,

    # 領域横断影響
    'forest_flood_reduction_coef': 0.4,
    'forest_ecosystem_boost_coef': 0.01,
    'forest_water_retention_coef': 0.2,
    'flood_crop_damage_coef': 0.00001,
    'levee_ecosystem_damage_coef': 0.0001,
    'flood_urban_damage_coef': 0.000001,
    'water_ecosystem_coef': 0.01,
    'paddy_dam_flood_coef': 10.0,
}

rcp_climate_params = {
    1.9: {
        'temp_trend': 0.02,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.05,
        'extreme_precip_intensity_trend': 0.2,
        'extreme_precip_uncertainty_trend': 0.05
    },
    2.6: {
        'temp_trend': 0.025,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.07,
        'extreme_precip_intensity_trend': 0.4,
        'extreme_precip_uncertainty_trend': 0.07
    },
    4.5: {
        'temp_trend': 0.035,
        'precip_uncertainty_trend': 1.5,
        'extreme_precip_freq_trend': 0.1,
        'extreme_precip_intensity_trend': 0.8,
        'extreme_precip_uncertainty_trend': 0.1
    },
    6.0: {
        'temp_trend': 0.045,
        'precip_uncertainty_trend': 2.0,
        'extreme_precip_freq_trend': 0.13,
        'extreme_precip_intensity_trend': 1.1,
        'extreme_precip_uncertainty_trend': 0.13
    },
    8.5: {
        'temp_trend': 0.06,
        'precip_uncertainty_trend': 3.0,
        'extreme_precip_freq_trend': 0.17,
        'extreme_precip_intensity_trend': 1.5,
        'extreme_precip_uncertainty_trend': 0.15
    }
}

__all__ = [
    "DATA_DIR", "RANK_FILE", "ACTION_LOG_FILE", "YOUR_NAME_FILE",
    "DEFAULT_PARAMS", "rcp_climate_params"
]