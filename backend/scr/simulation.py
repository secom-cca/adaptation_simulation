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
    # # --- 初期化（ストックと履歴） ---
    prev_forest_area = prev_values.get('forest_area', 100.0)  # 初期森林面積 [ha]
    forest_area_history = prev_values.get('forest_area_history', {})  # 年次履歴
    # --- 初期化（累積投資の初期化、必要に応じて） ---
    levee_investment_total = prev_values.get('levee_investment_total', 0.0)
    RnD_investment_total = prev_values.get('RnD_investment_total', 0.0)
    resident_capacity = prev_values.get('resident_capacity', 0.0)

    # --- 意思決定変数を展開 ---
    # モンテカルロモードでは mapping された internal keys が来る前提
    planting_trees_amount        = decision_vars.get('planting_trees_amount', 0)
    house_migration_amount       = decision_vars.get('house_migration_amount', 0)
    dam_levee_construction_cost  = decision_vars.get('dam_levee_construction_cost', 0)
    paddy_dam_construction_cost  = decision_vars.get('paddy_dam_construction_cost', 0)
    capacity_building_cost       = decision_vars.get('capacity_building_cost', 0)
    agricultural_RnD_cost        = decision_vars.get('agricultural_RnD_cost', 0)
    transportation_invest        = decision_vars.get('transportation_invest', 0)
    # 従来の変数（残存していれば利用）→ 利用しない方針
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
    levee_investment_required_years = params['levee_investment_required_years']
    RnD_investment_required_years = params['RnD_investment_required_years']
    max_available_water           = params['max_available_water']
    evapotranspiration_amount     = params['evapotranspiration_amount']
    ecosystem_threshold           = params['ecosystem_threshold']
    cost_per_1000trees            = 2310000
    cost_per_migration            = 3000000
    crop_rnd_max_tolerance        = 0.5
    forest_degradation_rate       = 0.01
    necessary_water_for_crops     = 1000
    capacity_building_coefficient = 0.1

    # 0.1 気象環境 ---
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)
    precip_unc = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_unc))
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = max(hot_days, 0)
    extreme_precip_freq = max(base_extreme_precip_freq + extreme_precip_freq_trend * (year - start_year), 0)
    extreme_precip_events = np.random.poisson(extreme_precip_freq)
    extreme_precip_intensity = extreme_precip_freq/base_extreme_precip_freq # 降雨強度も年々高まるという仮定

    # 0.2 社会環境 ---
    municipal_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
    current_municipal_demand = prev_municipal_demand * (1 + municipal_growth)
 
    # 1. 森林面積（植林 - 自然減衰） 1000本 = 1ha ---
    current_forest_area = max(prev_forest_area + planting_trees_amount - prev_forest_area * forest_degradation_rate, 0)
    forest_area_history[year] = current_forest_area

    # 2. forest_area の効果（20〜40年前の森林） ---
    flood_reduction = 0
    biodiversity_boost = 0
    water_retention_boost = 0
    for delay in range(20, 41):
        past_year = year - delay
        fa = forest_area_history.get(past_year, 0)
        flood_reduction += fa * 0.001  # 洪水被害を最大 40% 程度まで軽減可（例: fa=40000 で 40%）
        biodiversity_boost += fa * 0.0002
        water_retention_boost += fa * 0.001  # 水保持量を増加

    flood_reduction = min(flood_reduction, 0.4)    # 上限を設定（効果が過剰にならないように）
    biodiversity_boost = min(biodiversity_boost, 5.0)    # 上限を設定（効果が過剰にならないように）
    water_retention_boost = min(water_retention_boost, 20.0)    # 上限を設定（効果が過剰にならないように）

    # 3. 利用可能水量（System Dynamicsには未導入）
    current_available_water = min(
        max(
            prev_available_water + precip - evapotranspiration_amount
            - current_municipal_demand - irrigation_water_amount - released_water_amount
            + water_retention_boost,  # 森林による水源涵養効果
            0
        ),
        max_available_water
    )

    # 4.1 農業生産量
    temp_impact = hot_days * temp_coefficient * (1 - prev_high_temp_tolerance_level)
    water_impact = max(current_available_water/necessary_water_for_crops, 1)
    current_crop_yield = max_potential_yield - temp_impact - water_impact

    # 農業利用水を利用可能水から引く（System Dynamicsには未導入）
    current_available_water = min(current_available_water - necessary_water_for_crops, 0)

    # 4.2 農業R&D：累積投資で耐熱性向上（確率的閾値）
    RnD_investment_total += agricultural_RnD_cost
    RnD_threshold_with_noise = np.random.normal(RnD_investment_threshold * RnD_investment_required_years, RnD_investment_threshold * 0.1)

    if RnD_investment_total >= RnD_threshold_with_noise:
        prev_high_temp_tolerance_level = min(prev_high_temp_tolerance_level + high_temp_tolerance_increment, crop_rnd_max_tolerance)
        RnD_investment_total = 0.0
        crop_rnd_max_tolerance += 0.1  # レベルが段階的に上がっていくという過程

    # 5.1 堤防：累積投資で建設（確率的閾値）
    levee_investment_total += dam_levee_construction_cost
    levee_threshold_with_noise = np.random.normal(levee_investment_threshold * levee_investment_required_years, levee_investment_threshold * 0.1)

    if levee_investment_total >= levee_threshold_with_noise:
        prev_levee_level = prev_levee_level + levee_level_increment
        levee_investment_total -= levee_threshold_with_noise # リセット（差額を残す）

    # 5.2 水害
    is_flood = min(max(extreme_precip_intensity - prev_levee_level, 0),1)
    current_flood_damage = extreme_precip_events * is_flood * flood_damage_coefficient
    current_flood_damage *= (1 - flood_reduction) * (1 - resident_capacity) # 森林の影響は要検討

    # 6. 損害・生態系の評価
    water_for_ecosystem = precip + released_water_amount
    if water_for_ecosystem < ecosystem_threshold:
        prev_ecosystem_level = max(prev_ecosystem_level - 1, 0)

    # 7. 都市の居住可能性の評価
    urban_level = prev_urban_level + 0.1 * transportation_invest - 0.2 * house_migration_amount
    urban_level = min(max(urban_level, 0), 100)

    # 8. 自然生態系の評価
    biodiversity_level = max(prev_biodiversity_level - 0.05 * dam_levee_construction_cost - 0.02 * paddy_dam_construction_cost + biodiversity_boost, 0)

    # 9. 住民の防災能力・意識
    resident_capacity += capacity_building_cost * capacity_building_coefficient - 0.01 # 自然減
    resident_capacity = max(1, resident_capacity)

    # 10. コスト算出
    planting_trees_cost = planting_trees_amount * cost_per_1000trees
    migration_cost = house_migration_amount * cost_per_migration
    municipal_cost = dam_levee_construction_cost * 1000000 + agricultural_RnD_cost * 1000000 + paddy_dam_construction_cost * 1000000 + capacity_building_cost * 100000 + planting_trees_cost + migration_cost + transportation_invest
    resident_burden = municipal_cost 

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
    # outputs['Forest Area'] = current_forest_area

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
        'biodiversity_level': biodiversity_level,
        'levee_investment_total': levee_investment_total,
        'RnD_investment_total': RnD_investment_total,
        'forest_area': current_forest_area,
        'forest_area_history': forest_area_history,
        'resident_capacity': resident_capacity,
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
        # 意思決定変数の取得
        if isinstance(decision_vars_list, list):
            # 意思決定変数の取得
            decision_vars = decision_vars_list[len(decision_vars_list)-1]
        elif isinstance(decision_vars_list, pd.DataFrame):
            decision_vars = decision_vars_list.to_dict(orient='records')[0]
        else:
            decision_year = (year - params['start_year']) // 10 * 10 + params['start_year']
            decision_vars_raw = decision_vars_list.loc[decision_year].to_dict()
            # decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }
            # if '灌漑水量 (Irrigation Water Amount)' in decision_vars_raw:
            #     decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }
            # else:
            #     decision_vars = decision_vars_raw
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
