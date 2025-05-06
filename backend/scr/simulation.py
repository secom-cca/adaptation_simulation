# simulation.py

import numpy as np

def simulate_year(year, prev_values, decision_vars, params):
    # 前年の値を展開
    # prev_temp = prev_values['temp']
    # prev_precip = prev_values['precip']
    prev_municipal_demand = prev_values['municipal_demand']
    prev_available_water = prev_values['available_water']
    # prev_crop_yield = prev_values['crop_yield']
    prev_levee_level = prev_values['levee_level']
    prev_high_temp_tolerance_level = prev_values['high_temp_tolerance_level']
    # prev_hot_days = prev_values['hot_days']
    # prev_extreme_precip_freq = prev_values['extreme_precip_freq']
    prev_ecosystem_level = prev_values['ecosystem_level']
    levee_investment_years = prev_values['levee_investment_years']
    RnD_investment_years = prev_values['RnD_investment_years']

    # 意思決定変数を展開
    irrigation_water_amount = decision_vars['irrigation_water_amount']
    released_water_amount = decision_vars['released_water_amount']
    levee_construction_cost = decision_vars['levee_construction_cost']
    agricultural_RnD_cost = decision_vars['agricultural_RnD_cost']

    # パラメータを展開
    start_year = params['start_year']
    base_temp = params['base_temp']
    temp_trend = params['temp_trend']
    temp_uncertainty = params['temp_uncertainty']
    base_precip = params['base_precip']
    precip_trend = params['precip_trend']
    base_precip_uncertainty = params['base_precip_uncertainty']
    precip_uncertainty_trend = params['precip_uncertainty_trend']
    initial_hot_days = params['initial_hot_days']
    temp_to_hot_days_coeff = params['temp_to_hot_days_coeff']
    hot_days_uncertainty = params['hot_days_uncertainty']
    base_extreme_precip_freq = params['base_extreme_precip_freq']
    extreme_precip_freq_trend = params['extreme_precip_freq_trend']
    municipal_demand_trend = params['municipal_demand_trend']
    municipal_demand_uncertainty = params['municipal_demand_uncertainty']
    temp_coefficient = params['temp_coefficient']
    max_potential_yield = params['max_potential_yield']
    optimal_irrigation_amount = params['optimal_irrigation_amount']
    flood_damage_coefficient = params['flood_damage_coefficient']
    levee_level_increment = params['levee_level_increment']
    high_temp_tolerance_increment = params['high_temp_tolerance_increment']
    levee_investment_threshold = params['levee_investment_threshold']
    RnD_investment_threshold = params['RnD_investment_threshold']
    levee_investment_required_years = params['levee_investment_required_years']
    RnD_investment_required_years = params['RnD_investment_required_years']
    max_available_water = params['max_available_water']
    evapotranspiration_amount = params['evapotranspiration_amount']
    ecosystem_threshold = params['ecosystem_threshold']
    crop_rnd_max_tolerance = 0.5

    # 気温の計算
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)

    # 降水量の計算
    precip_uncertainty = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_uncertainty))

    # 真夏日日数の計算
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = max(hot_days, 0) 

    # 極端降水頻度の計算
    extreme_precip_freq = base_extreme_precip_freq + extreme_precip_freq_trend * (year - start_year)
    extreme_precip_freq = max(extreme_precip_freq, 0.0)

    # 極端降水回数の計算
    extreme_precip_events = np.random.poisson(extreme_precip_freq)

    # 都市水需要の成長率（トレンドと不確実性）
    municipal_demand_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
    current_municipal_demand = prev_municipal_demand * (1 + municipal_demand_growth)

    # 利用可能水量の計算
    current_available_water = max(0, prev_available_water + precip - evapotranspiration_amount - current_municipal_demand - irrigation_water_amount - released_water_amount)
    current_available_water = min(current_available_water, max_available_water)

    # 作物収量の計算
    crop_yield_irrigation_component = max_potential_yield * (irrigation_water_amount / optimal_irrigation_amount)
    crop_yield_irrigation_component = min(crop_yield_irrigation_component, max_potential_yield)
    temp_impact = hot_days * temp_coefficient * (1 - prev_high_temp_tolerance_level)
    current_crop_yield = crop_yield_irrigation_component - temp_impact
    # current_crop_yield = max(current_crop_yield, 0)  # 作物収量は0以上

    # 堤防レベルの更新
    if levee_construction_cost >= levee_investment_threshold:
        levee_investment_years += 1
        if levee_investment_years >= levee_investment_required_years:
            prev_levee_level = min(prev_levee_level + levee_level_increment, 1.0)
            levee_investment_years = 0
    else:
        levee_investment_years = 0

    # 高温耐性レベルの更新
    if agricultural_RnD_cost >= RnD_investment_threshold:
        RnD_investment_years += 1
        if RnD_investment_years >= RnD_investment_required_years:
            prev_high_temp_tolerance_level = min(prev_high_temp_tolerance_level + high_temp_tolerance_increment, crop_rnd_max_tolerance)
            RnD_investment_years = 0
            crop_rnd_max_tolerance += 0.1
    else:
        RnD_investment_years = 0

    # 洪水被害額の計算
    current_flood_damage = extreme_precip_events * (1 - prev_levee_level) * flood_damage_coefficient

    # 生態系レベルの計算
    water_for_ecosystem = precip + released_water_amount
    if water_for_ecosystem < ecosystem_threshold:
        prev_ecosystem_level -= 1  # 閾値以下なら生態系レベルを減少
    prev_ecosystem_level = max(prev_ecosystem_level, 0)  # 生態系レベルは0以上

    # 自治体コストの計算
    municipal_cost = levee_construction_cost + agricultural_RnD_cost

    # 出力データの作成
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
        'Municipal Cost': municipal_cost
    }

    # 現在の値を更新
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
        'crop_rnd_max_tolerance' : crop_rnd_max_tolerance
    }

    return current_values, outputs

def simulate_simulation(years, initial_values, decision_vars_list, params):
    prev_values = initial_values.copy()
    results = []

    for idx, year in enumerate(years):
        # 意思決定変数を取得
        if isinstance(decision_vars_list, list):
            # 逐次意思決定モードの場合
            # decision_vars_idx = idx // 10
            decision_vars = decision_vars_list[len(decision_vars_list)-1] #[min(decision_vars_idx, len(decision_vars_list)-1)]
        else:
            # モンテカルロモードの場合
            decision_year = (year - params['start_year']) // 10 * 10 + params['start_year']
            decision_vars_raw = decision_vars_list.loc[decision_year].to_dict()
            # キーをマッピング
            if '灌漑水量 (Irrigation Water Amount)' in decision_vars_raw:
                key_mapping = {
                    '灌漑水量 (Irrigation Water Amount)': 'irrigation_water_amount',
                    '放流水量 (Released Water Amount)': 'released_water_amount',
                    '堤防工事費 (Levee Construction Cost)': 'levee_construction_cost',
                    '農業研究開発費 (Agricultural R&D Cost)': 'agricultural_RnD_cost'
                }
                decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }
            else:
                decision_vars = decision_vars_raw

        prev_values, outputs = simulate_year(year, prev_values, decision_vars, params)
        results.append(outputs)

    return results
