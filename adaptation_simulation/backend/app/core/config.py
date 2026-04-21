"""
Core Configuration for Climate Adaptation Simulation
"""
from pathlib import Path, PosixPath
import numpy as np
import os

# 检查是否在Railway环境中，如果是则使用Volume路径
if os.getenv("RAILWAY_ENVIRONMENT"):
    DATA_DIR: PosixPath = Path("/app/data")
else:
    DATA_DIR: PosixPath = Path("data")

DATA_DIR.mkdir(exist_ok=True)

RANK_FILE = DATA_DIR / "block_scores.tsv"
ACTION_LOG_FILE = DATA_DIR / "decision_log.csv"
YOUR_NAME_FILE = DATA_DIR / "your_name.csv"

start_year = 2026
end_year = 2100
years = np.arange(start_year, end_year + 1)
total_years = len(years)

# 默认参数配置
DEFAULT_PARAMS = {
    'start_year': start_year,
    'end_year': end_year,
    'years': years,
    'total_years': total_years,
    'temp_increase_rate': 0.03,
    'precip_change_rate': 0.01,
    'extreme_precip_increase_rate': 0.02,
    'hot_days_increase_rate': 0.5,
    'ecosystem_decline_rate': 0.005,
    'urban_growth_rate': 0.01,
    'population_growth_rate': 0.001,
    'economic_growth_rate': 0.02,
    'adaptation_effectiveness': 0.8,
    'mitigation_effectiveness': 0.6,
    'cost_effectiveness': 0.7,
    'uncertainty_factor': 0.1,
    'discount_rate': 0.03,
    'carbon_price': 50,
    'adaptation_cost_factor': 1.2,
    'mitigation_cost_factor': 1.1,
    'damage_cost_factor': 2.0,
    'benefit_cost_ratio': 3.0,
    'risk_tolerance': 0.05,
    'planning_horizon': 30,
    'decision_frequency': 5,
    'monitoring_frequency': 1,
    'evaluation_frequency': 10,
    'learning_rate': 0.1,
    'innovation_rate': 0.05,
    'technology_improvement_rate': 0.02,
    'institutional_capacity': 0.7,
    'social_acceptance': 0.8,
    'political_stability': 0.9,
    'international_cooperation': 0.6,
    'knowledge_sharing': 0.7,
    'capacity_building': 0.8,
    'stakeholder_engagement': 0.9,
    'transparency': 0.8,
    'accountability': 0.9,
    'adaptive_management': 0.8
}

# RCP气候参数
rcp_climate_params = {
    2.6: {
        'temp_increase_rate': 0.02,
        'precip_change_rate': 0.005,
        'extreme_precip_increase_rate': 0.01,
        'hot_days_increase_rate': 0.3
    },
    4.5: {
        'temp_increase_rate': 0.03,
        'precip_change_rate': 0.01,
        'extreme_precip_increase_rate': 0.02,
        'hot_days_increase_rate': 0.5
    },
    6.0: {
        'temp_increase_rate': 0.04,
        'precip_change_rate': 0.015,
        'extreme_precip_increase_rate': 0.03,
        'hot_days_increase_rate': 0.7
    },
    8.5: {
        'temp_increase_rate': 0.05,
        'precip_change_rate': 0.02,
        'extreme_precip_increase_rate': 0.04,
        'hot_days_increase_rate': 1.0
    }
}
