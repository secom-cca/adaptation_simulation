# simulation.py

import numpy as np
import pandas as pd

def simulate_year(year, prev_values, decision_vars, params):
    # --- 前年の値を展開 ---
    prev_municipal_demand = prev_values['municipal_demand']
    prev_available_water = prev_values['available_water']
    prev_levee_level = prev_values['levee_level']
    prev_high_temp_tolerance_level = prev_values['high_temp_tolerance_level']
    prev_ecosystem_level = prev_values['ecosystem_level']
    levee_investment_years = prev_values['levee_investment_years']
    RnD_investment_years = prev_values['RnD_investment_years']
    # 新指標の前回値
    prev_urban_level = prev_values.get('urban_level', 100.0)
    prev_resident_burden = prev_values.get('resident_burden', 0.0)
    prev_biodiversity_level = prev_values.get('biodiversity_level', prev_ecosystem_level)

    # --- 意思決定変数を展開 ---
    # モンテカルロモードでは mapping された internal keys が来る前提
    planting_trees_amount        = decision_vars.get('planting_trees_amount', 0)
    house_migration_amount       = decision_vars.get('house_migration_amount', 0)
    dam_levee_construction_cost  = decision_vars.get('dam_levee_construction_cost', 0)
    paddy_dam_construction_cost  = decision_vars.get('paddy_dam_construction_cost', 0)
    capacity_building_cost       = decision_vars.get('capacity_building_cost', 0)
    agricultural_RnD_cost        = decision_vars.get('agricultural_RnD_cost', 0)
    transportation_invest        = decision_vars.get('transportation_invest', 0)
    # 従来の変数（残存していれば利用）
    irrigation_water_amount      = decision_vars.get('irrigation_water_amount', 0)
    released_water_amount        = decision_vars.get('released_water_amount', 0)

    # --- パラメータを展開 ---
    start_year                    = params['start_year']
    base_temp                     = params['base_temp']
    temp_trend                    = params['temp_trend']
    temp_uncertainty              = params['temp_uncertainty']
    base_precip                   = params['base_precip']
    precip_trend                  = params['precip_trend']
    base_precip_uncertainty       = params['base_precip_uncertainty']
    precip_uncertainty_trend      = params['precip_uncertainty_trend']
    initial_hot_days              = params['initial_hot_days']
    temp_to_hot_days_coeff        = params['temp_to_hot_days_coeff']
    hot_days_uncertainty          = params['hot_days_uncertainty']
    base_extreme_precip_freq      = params['base_extreme_precip_freq']
    extreme_precip_freq_trend     = params['extreme_precip_freq_trend']
    municipal_demand_trend        = params['municipal_demand_trend']
    municipal_demand_uncertainty  = params['municipal_demand_uncertainty']
    temp_coefficient              = params['temp_coefficient']
    max_potential_yield           = params['max_potential_yield']
    optimal_irrigation_amount     = params['optimal_irrigation_amount']
    flood_damage_coefficient      = params['flood_damage_coefficient']
    levee_level_increment         = params['levee_level_increment']
    high_temp_tolerance_increment = params['high_temp_tolerance_increment']
    levee_investment_threshold    = params['levee_investment_threshold']
    RnD_investment_threshold      = params['RnD_investment_threshold']
    levee_investment_required_years= params['levee_investment_required_years']
    RnD_investment_required_years = params['RnD_investment_required_years']
    max_available_water           = params['max_available_water']
    evapotranspiration_amount     = params['evapotranspiration_amount']
    ecosystem_threshold           = params['ecosystem_threshold']
    crop_rnd_max_tolerance        = 0.5

    # --- 気象・水資源・収量の計算 ---
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)
    precip_unc = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_unc))
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = max(hot_days, 0)
    extreme_precip_freq = max(base_extreme_precip_freq + extreme_precip_freq_trend * (year - start_year), 0)
    extreme_precip_events = np.random.poisson(extreme_precip_freq)
    municipal_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
    current_municipal_demand = prev_municipal_demand * (1 + municipal_growth)
    current_available_water = min(max(prev_available_water + precip - evapotranspiration_amount \
                                      - current_municipal_demand - irrigation_water_amount - released_water_amount, 0),
                                  max_available_water)
    cy_irrig = max_potential_yield * (irrigation_water_amount / optimal_irrigation_amount)
    cy_irrig = min(cy_irrig, max_potential_yield)
    temp_impact = hot_days * temp_coefficient * (1 - prev_high_temp_tolerance_level)
    current_crop_yield = cy_irrig - temp_impact

    # --- レベル更新 ---
    # 堤防
    if dam_levee_construction_cost >= levee_investment_threshold:
        levee_investment_years += 1
        if levee_investment_years >= levee_investment_required_years:
            prev_levee_level = min(prev_levee_level + levee_level_increment, 1.0)
            levee_investment_years = 0
    else:
        levee_investment_years = 0
    # 耐熱性
    if agricultural_RnD_cost >= RnD_investment_threshold:
        RnD_investment_years += 1
        if RnD_investment_years >= RnD_investment_required_years:
            prev_high_temp_tolerance_level = min(prev_high_temp_tolerance_level + high_temp_tolerance_increment, crop_rnd_max_tolerance)
            RnD_investment_years = 0
            crop_rnd_max_tolerance += 0.1
    else:
        RnD_investment_years = 0

    # --- 損害・生態系 ---
    current_flood_damage = extreme_precip_events * (1 - prev_levee_level) * flood_damage_coefficient
    water_for_ecosystem = precip + released_water_amount
    if water_for_ecosystem < ecosystem_threshold:
        prev_ecosystem_level = max(prev_ecosystem_level - 1, 0)
    municipal_cost = dam_levee_construction_cost + agricultural_RnD_cost + paddy_dam_construction_cost + capacity_building_cost

    # --- 新指標 ---
    urban_level = prev_urban_level + 0.1 * transportation_invest - 0.2 * house_migration_amount
    urban_level = min(max(urban_level, 0), 100)
    resident_burden = prev_resident_burden + 0.5 * (dam_levee_construction_cost + paddy_dam_construction_cost + capacity_building_cost)
    biodiversity_level = max(prev_biodiversity_level - 0.05 * dam_levee_construction_cost - 0.02 * paddy_dam_construction_cost, 0)

    # --- 出力 ---
    outputs = {
        'Year': year,
        'Temperature (℃)': temp,
        'Precipitation (mm)': precip,
        'Available Water': current_available_water,
        'Crop Yield': current_crop_yield,
        'Municipal Demand': current_municipal_demand,
        'Flood Damage': current_flood_damage,
        'Levee Level': prev_levee_level,
        'High Temp Tolerance Level': prev_high_temp_tolerance_level,
        'Hot Days': hot_days,
        'Extreme Precip Frequency': extreme_precip_freq,
        'Extreme Precip Events': extreme_precip_events,
        'Ecosystem Level': prev_ecosystem_level,
        'Municipal Cost': municipal_cost,
        'Urban Level': urban_level,
        'Resident Burden': resident_burden,
        'Biodiversity Level': biodiversity_level
    }

    current_values = {
        'temp': temp,
        'precip': precip,
        'municipal_demand': current_municipal_demand,
        'available_water': current_available_water,
        'crop_yield': current_crop_yield,
        'levee_level': prev_levee_level,
        'high_temp_tolerance_level': prev_high_temp_tolerance_level,
        'hot_days': hot_days,
        'extreme_precip_freq': extreme_precip_freq,
        'ecosystem_level': prev_ecosystem_level,
        'levee_investment_years': levee_investment_years,
        'RnD_investment_years': RnD_investment_years,
        'urban_level': urban_level,
        'resident_burden': resident_burden,
        'biodiversity_level': biodiversity_level
    }

    return current_values, outputs

def simulate_simulation(years, initial_values, decision_vars_list, params):
    prev_values = initial_values.copy()
    results = []

    # 日本語列名を internal key にマッピング
    key_mapping = {
        '植林・森林保全': 'planting_trees_amount',
        '住宅移転・嵩上げ': 'house_migration_amount',
        'ダム・堤防工事': 'dam_levee_construction_cost',
        '田んぼダム工事': 'paddy_dam_construction_cost',
        '防災訓練・普及啓発': 'capacity_building_cost',
        '農業研究開発': 'agricultural_RnD_cost',
        '交通網の拡充': 'transportation_invest',
        '灌漑水量 (Irrigation Water Amount)': 'irrigation_water_amount',
        '放流水量 (Released Water Amount)': 'released_water_amount'
    }

    for idx, year in enumerate(years):
        # 意思決定変数を取得
        if isinstance(decision_vars_list, list):
            # 意思決定変数の取得
            decision_vars = decision_vars_list[len(decision_vars_list)-1]
        elif isinstance(decision_vars_list, pd.DataFrame):
            decision_vars = decision_vars_list.to_dict(orient='records')[0]
        else:
            # モンテカルロモードの場合
            decision_year = (year - params['start_year']) // 10 * 10 + params['start_year']
            decision_vars_raw = decision_vars_list.loc[decision_year].to_dict()
            decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }
            # if '灌漑水量 (Irrigation Water Amount)' in decision_vars_raw:
            #     decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }
            # else:
            #     decision_vars = decision_vars_raw

        prev_values, outputs = simulate_year(year, prev_values, decision_vars, params)
        results.append(outputs)

    return results
