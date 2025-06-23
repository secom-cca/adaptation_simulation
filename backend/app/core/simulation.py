"""
Core Simulation Logic for Climate Adaptation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any

def simulate_simulation(years: np.ndarray, initial_values: Dict[str, Any], 
                       decision_vars_list: pd.DataFrame, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    核心仿真函数
    
    Args:
        years: 仿真年份数组
        initial_values: 初始值字典
        decision_vars_list: 决策变量DataFrame
        params: 参数字典
    
    Returns:
        仿真结果列表
    """
    results = []
    current_values = initial_values.copy()
    
    for year in years:
        # 获取当前年份的决策变量
        year_decisions = decision_vars_list[decision_vars_list['year'] == year] if not decision_vars_list.empty else pd.DataFrame()
        
        # 更新气候变量
        current_values = _update_climate_variables(current_values, params, year)
        
        # 应用决策变量的影响
        if not year_decisions.empty:
            current_values = _apply_decisions(current_values, year_decisions.iloc[0], params)
        
        # 计算系统响应
        current_values = _calculate_system_response(current_values, params)
        
        # 记录结果
        result = current_values.copy()
        result['Year'] = year
        results.append(result)
    
    return results

def _update_climate_variables(values: Dict[str, Any], params: Dict[str, Any], year: int) -> Dict[str, Any]:
    """更新气候变量"""
    values = values.copy()
    
    # 温度变化
    temp_increase = params.get('temp_increase_rate', 0.03) * (year - params['start_year'])
    values['temp'] = values.get('temp', 15.0) + temp_increase
    
    # 降水变化
    precip_change = params.get('precip_change_rate', 0.01) * (year - params['start_year'])
    values['precip'] = values.get('precip', 1700.0) * (1 + precip_change)
    
    # 极端降水频率
    extreme_increase = params.get('extreme_precip_increase_rate', 0.02) * (year - params['start_year'])
    values['extreme_precip_freq'] = values.get('extreme_precip_freq', 0.1) + extreme_increase
    
    # 高温天数
    hot_days_increase = params.get('hot_days_increase_rate', 0.5) * (year - params['start_year'])
    values['hot_days'] = values.get('hot_days', 30.0) + hot_days_increase
    
    return values

def _apply_decisions(values: Dict[str, Any], decisions: pd.Series, params: Dict[str, Any]) -> Dict[str, Any]:
    """应用决策变量的影响"""
    values = values.copy()
    
    # 植林・森林保全
    if 'planting_trees_amount' in decisions:
        forest_increase = decisions['planting_trees_amount'] * 0.1
        values['forest_area'] = values.get('forest_area', 0.0) + forest_increase
        values['ecosystem_level'] = min(100.0, values.get('ecosystem_level', 100.0) + forest_increase * 0.5)
    
    # 住宅移転・嵩上げ
    if 'house_migration_amount' in decisions:
        migration_amount = decisions['house_migration_amount']
        values['risky_house_total'] = max(0, values.get('risky_house_total', 10000.0) - migration_amount)
        values['non_risky_house_total'] = values.get('non_risky_house_total', 0.0) + migration_amount
    
    # ダム・堤防工事
    if 'dam_levee_construction_cost' in decisions:
        levee_investment = decisions['dam_levee_construction_cost']
        values['levee_investment_total'] = values.get('levee_investment_total', 0.0) + levee_investment
        values['levee_level'] = min(1.0, values.get('levee_level', 0.5) + levee_investment * 0.0001)
    
    # 農業研究開発
    if 'agricultural_RnD_cost' in decisions:
        rnd_investment = decisions['agricultural_RnD_cost']
        values['RnD_investment_total'] = values.get('RnD_investment_total', 0.0) + rnd_investment
        values['high_temp_tolerance_level'] = min(1.0, values.get('high_temp_tolerance_level', 0.0) + rnd_investment * 0.0001)
    
    # 交通網の拡充
    if 'transportation_invest' in decisions:
        transport_investment = decisions['transportation_invest']
        values['transportation_level'] = min(100.0, values.get('transportation_level', 0.0) + transport_investment * 0.01)
    
    # 防災訓練・普及啓発
    if 'capacity_building_cost' in decisions:
        capacity_investment = decisions['capacity_building_cost']
        values['resident_capacity'] = min(100.0, values.get('resident_capacity', 0.0) + capacity_investment * 0.01)
    
    return values

def _calculate_system_response(values: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """计算系统响应"""
    values = values.copy()
    
    # 计算作物产量
    temp_effect = max(0, 1 - (values['temp'] - 15) * 0.02)
    tolerance_effect = 1 + values.get('high_temp_tolerance_level', 0.0) * 0.5
    values['crop_yield'] = 100.0 * temp_effect * tolerance_effect
    
    # 计算水资源可用性
    precip_effect = values['precip'] / 1700.0
    demand_effect = values.get('municipal_demand', 100.0) / 100.0
    values['available_water'] = 1000.0 * precip_effect / demand_effect
    
    # 计算生态系统水平
    forest_effect = values.get('forest_area', 0.0) * 0.01
    temp_stress = (values['temp'] - 15) * 0.01
    values['ecosystem_level'] = max(0, min(100, values.get('ecosystem_level', 100.0) + forest_effect - temp_stress))
    
    # 计算生物多样性水平
    ecosystem_effect = values['ecosystem_level'] / 100.0
    values['biodiversity_level'] = max(0, min(100, 100.0 * ecosystem_effect))
    
    # 计算城市水平
    transport_effect = values.get('transportation_level', 0.0) * 0.01
    values['urban_level'] = min(100.0, values.get('urban_level', 100.0) + transport_effect)
    
    # 计算居民负担
    base_burden = 5.379e8
    investment_burden = (
        values.get('levee_investment_total', 0.0) + 
        values.get('RnD_investment_total', 0.0)
    ) * 0.1
    values['resident_burden'] = base_burden + investment_burden
    
    return values
