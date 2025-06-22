# simulation.py

import numpy as np
import pandas as pd
from scipy.stats import gumbel_r

def simulate_year(year, prev_values, decision_vars, params):
    # --- 前年の値を展開（初期値を定義していない変数は追って調整） ---
    prev_levee_level = prev_values.get('levee_level', 0.0)
    high_temp_tolerance_level = prev_values.get('high_temp_tolerance_level', 0.0)
    ecosystem_level = prev_values.get('ecosystem_level', 100)
    prev_forest_area = prev_values.get('forest_area', params['total_area'] * params['initial_forest_area']) ##################
    planting_history    = prev_values.get('planting_history', {}) ##################
    resident_capacity = prev_values.get('resident_capacity', 0.0) ##################
    transportation_level = prev_values.get('transportation_level', 0.0) ##################
    prev_municipal_demand = prev_values.get('municipal_demand', params['initial_municipal_demand'])##################
    prev_available_water = prev_values.get('available_water', 0.0)
    levee_investment_total = prev_values.get('levee_investment_total', 0.0)
    RnD_investment_total = prev_values.get('RnD_investment_total', 0.0)
    risky_house_total = prev_values.get('risky_house_total', params['house_total'])
    non_risky_house_total = prev_values.get('non_risky_house_total', 0)
    paddy_dam_area = prev_values.get('paddy_dam_area', 0)
    temp_threshold_crop = prev_values.get('temp_threshold_crop', params['temp_threshold_crop_ini'])

    # --- 意思決定変数を展開 ---
    # モンテカルロモードでは mapping された internal keys が来る前提
    planting_trees_amount        = decision_vars.get('planting_trees_amount', 0)
    house_migration_amount       = decision_vars.get('house_migration_amount', 0)
    dam_levee_construction_cost  = decision_vars.get('dam_levee_construction_cost', 0)
    paddy_dam_construction_cost  = decision_vars.get('paddy_dam_construction_cost', 0)
    capacity_building_cost       = decision_vars.get('capacity_building_cost', 0)
    agricultural_RnD_cost        = decision_vars.get('agricultural_RnD_cost', 0)
    transportation_invest        = decision_vars.get('transportation_invest', 0)

    # --- パラメータを展開 ---
    start_year                    = params['start_year']
    # 年平均気温
    base_temp                     = params['base_temp']
    temp_trend                    = params['temp_trend']
    temp_uncertainty              = params['temp_uncertainty']
    # 年降水量
    base_precip                   = params['base_precip']
    precip_trend                  = params['precip_trend']
    base_precip_uncertainty       = params['base_precip_uncertainty']
    precip_uncertainty_trend      = params['precip_uncertainty_trend']
    # 高温
    initial_hot_days              = params['initial_hot_days'] # hot_daysは今後の利用可能性を含め残す（熱中症など）
    temp_to_hot_days_coeff        = params['temp_to_hot_days_coeff']
    hot_days_uncertainty          = params['hot_days_uncertainty']
    # 極端降水
    base_extreme_precip_freq      = params['base_extreme_precip_freq']
    extreme_precip_freq_trend     = params['extreme_precip_freq_trend']
    extreme_precip_intensity_trend= params['extreme_precip_intensity_trend']
    extreme_precip_uncertainty_trend=params['extreme_precip_uncertainty_trend']
    base_mu = params['base_mu']
    base_beta = params['base_beta']
    # 水需要
    municipal_demand_trend        = params['municipal_demand_trend']
    municipal_demand_uncertainty  = params['municipal_demand_uncertainty']
    # 水循環
    max_available_water           = params['max_available_water']
    evapotranspiration_amount     = params['evapotranspiration_amount']
    ecosystem_threshold           = params['ecosystem_threshold']
    # 農業
    temp_coefficient              = params['temp_coefficient']
    max_potential_yield           = params['max_potential_yield']
    optimal_irrigation_amount     = params['optimal_irrigation_amount']
    high_temp_tolerance_increment = params['high_temp_tolerance_increment']
    necessary_water_for_crops = params['necessary_water_for_crops']
    paddy_dam_cost_per_ha = params['paddy_dam_cost_per_ha']
    paddy_dam_yield_coef = params['paddy_dam_yield_coef']
    temp_critical_crop = params['temp_critical_crop']
    # 水災害
    flood_damage_coefficient      = params['flood_damage_coefficient']
    levee_level_increment         = params['levee_level_increment']
    levee_investment_threshold    = params['levee_investment_threshold']
    RnD_investment_threshold      = params['RnD_investment_threshold']
    levee_investment_required_years = params['levee_investment_required_years']
    RnD_investment_required_years = params['RnD_investment_required_years']
    flood_recovery_cost_coef = params['flood_recovery_cost_coef']
    runoff_coef = params['runoff_coef']
    # 森林
    cost_per_1000trees = params['cost_per_1000trees']
    forest_degradation_rate = params['forest_degradation_rate']
    tree_growup_year = params['tree_growup_year']
    co2_absorption_per_ha = params['co2_absorption_per_ha']
    # 住宅
    cost_per_migration = params['cost_per_migration']
    # 住民意識
    capacity_building_coefficient = params['capacity_building_coefficient']
    resident_capacity_degrade_ratio = params['resident_capacity_degrade_ratio']
    # 交通
    transport_level_coef = params['transport_level_coef']
    distance_urban_level_coef = params['distance_urban_level_coef']
    # 領域横断影響
    forest_flood_reduction_coef = params['forest_flood_reduction_coef'] ### 0.4-2.8 [%/%]
    forest_water_retention_coef = params['forest_water_retention_coef'] ### 2-4 [mm/%]
    forest_flood_reduction_coef = np.random.uniform(0.4,2.8)
    forest_water_retention_coef = np.random.uniform(2,4)
    # forest_ecosystem_boost_coef = params['forest_ecosystem_boost_coef'] 
    flood_crop_damage_coef = params['flood_crop_damage_coef']
    levee_ecosystem_damage_coef = params['levee_ecosystem_damage_coef']
    flood_urban_damage_coef = params['flood_urban_damage_coef']
    water_ecosystem_coef = params['water_ecosystem_coef']
    paddy_dam_flood_coef = params['paddy_dam_flood_coef']
    # 地形
    total_area = params['total_area']
    paddy_field_area = params['paddy_field_area']
    
    # resident_density = 1000 # [person/km^2]
    # water_demand_per_resident = 130 # [m3/person]
    # current_municipal_demand = water_water_demand_per_resident * resident_density / 1000 = 130 [mm]

    # ---------------------------------------------------------
    # 1. 気象環境 ---
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)

    precip_unc = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_unc))
    
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = max(hot_days, 0)
    
    extreme_precip_freq = max(base_extreme_precip_freq + extreme_precip_freq_trend * (year - start_year), 0)
    extreme_precip_events = np.random.poisson(extreme_precip_freq)
    
    mu = max(base_mu + extreme_precip_intensity_trend * (year - start_year), 0)
    beta = max(base_beta + extreme_precip_intensity_trend * (year - start_year), 0) 
    
    rain_events = gumbel_r.rvs(loc=mu, scale=beta, size=extreme_precip_events)

    # ---------------------------------------------------------
    # 2. 社会環境（水需要） ---
    municipal_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
    current_municipal_demand = prev_municipal_demand * (1 + municipal_growth)
 
     # ---------------------------------------------------------
    # 3. 森林面積（植林 - 自然減衰） ---
    planting_history[year] = planting_trees_amount # assume 1000 trees = 1ha
    matured_trees = planting_history.get(year - tree_growup_year, 0)
    natural_loss = prev_forest_area * forest_degradation_rate
    current_forest_area = max(prev_forest_area + matured_trees - natural_loss, 0)

    # #forest_area の効果発現 ---
    flood_reduction = forest_flood_reduction_coef * ((current_forest_area - total_area * params['initial_forest_area']) / total_area)
    water_retention_boost = forest_water_retention_coef * current_forest_area / total_area # 水源涵養効果
    co2_absorbed = current_forest_area * co2_absorption_per_ha  # tCO2

    # ---------------------------------------------------------
    # 4. 利用可能水量（System Dynamicsには未導入）
    evapotranspiration_amount = evapotranspiration_amount * (1 + (temp - base_temp) * 0.05) # クラウジウス・クラペイロン
    current_available_water = min(
        max(
            prev_available_water + precip - evapotranspiration_amount - current_municipal_demand - runoff_coef * precip + water_retention_boost * precip,
            0
        ),
        max_available_water
    )

    # ---------------------------------------------------------
    # 5. 農業生産量
    temp_ripening = temp + 10.0 # 仮設定：登熟期の気温の計算
    excess = max(temp_ripening - (temp_threshold_crop + high_temp_tolerance_level), 0)
    loss = (excess / (temp_critical_crop - temp_threshold_crop))
    temp_impact = min(loss, 1)
    paddy_dam_area += paddy_dam_construction_cost / paddy_dam_cost_per_ha
    paddy_dam_yield_impact = paddy_dam_yield_coef * min(paddy_dam_area / paddy_field_area, 1)

    water_impact = min(current_available_water/necessary_water_for_crops, 1.0)
    current_crop_yield = max((max_potential_yield * (1 - temp_impact)) * water_impact * (1 - paddy_dam_yield_impact),0) # * paddy_field_area [haあたり]

    # (4. 農業利用水を利用可能水から引く（System Dynamicsには未導入）)
    current_available_water = max(current_available_water - necessary_water_for_crops, 0)

    # 5.2 農業R&D：累積投資で耐熱性向上（確率的閾値）
    RnD_investment_total += agricultural_RnD_cost
    RnD_threshold_with_noise = np.random.normal(RnD_investment_threshold * RnD_investment_required_years, RnD_investment_threshold * 0.1)

    if RnD_investment_total >= RnD_threshold_with_noise:
        high_temp_tolerance_level += high_temp_tolerance_increment
        RnD_investment_total = 0.0

    # ---------------------------------------------------------
    # 6. 住宅の移転
    total_house = risky_house_total + non_risky_house_total
    risky_house_total = max(risky_house_total - house_migration_amount + total_house * municipal_growth, 0) 
    non_risky_house_total += house_migration_amount
    migration_ratio = non_risky_house_total / total_house

    # ---------------------------------------------------------
    # 7.1 堤防：累積投資で建設（確率的閾値）
    levee_investment_total += dam_levee_construction_cost
    levee_threshold_with_noise = np.random.normal(levee_investment_threshold * levee_investment_required_years, levee_investment_threshold * 0.1)

    if levee_investment_total >= levee_threshold_with_noise:
        current_levee_level = prev_levee_level + levee_level_increment
        levee_investment_total -= levee_threshold_with_noise # リセット（差額を残す）
    else:
        current_levee_level = prev_levee_level

    # 7.2 水害
    flood_impact = 0
    paddy_dam_level = paddy_dam_flood_coef * min(paddy_dam_area / paddy_field_area, 1)
    for rain in rain_events:
        overflow_amount = max(rain - current_levee_level - paddy_dam_level, 0) * (1 - flood_reduction)
        flood_impact = overflow_amount * flood_damage_coefficient
        # 対策効果は災害規模により段階的に変化（S字カーブ）
        response_factor = 1 / (1 + np.exp(-0.1 * (overflow_amount - 400)))  # 400mm超過で能力無効に近づく
        effective_protection = (1 - resident_capacity * (1 - response_factor)) * (1 - migration_ratio * (1 - response_factor))
        flood_impact += flood_impact * effective_protection
    
    # # current_flood_damage = extreme_precip_events * flood_impact
    # current_flood_damage = flood_impact * (1 - resident_capacity) * (1 - migration_ratio)
    current_flood_damage = max(flood_impact,0.0)
    current_crop_yield -= current_flood_damage * flood_crop_damage_coef


    # ---------------------------------------------------------
    # 8. 損害・生態系の評価
    # Natural resource base (0–1)
    ecological_base = 0.5 * min(current_forest_area / total_area, 1.0) + 0.5 * min(current_available_water / ecosystem_threshold, 1.0)

    # Disturbance resistance
    temp_diff = abs(temp - base_temp)
    extreme_factor = extreme_precip_events
    disturbance_resistance = max(0, 1.0 - 0.05 * temp_diff - 0.03 * extreme_factor) 

    # Human pressure
    human_pressure_raw = min(0.01 * current_levee_level, 1.0)
    human_pressure = 1.0 - human_pressure_raw

    # Weighted ecosystem score
    # w1, w2, w3 = 1/3, 1/3, 1/3
    weights = np.random.dirichlet([1, 1, 1])
    w1, w2, w3 = weights

    ecosystem_level = (w1 * ecological_base + w2 * disturbance_resistance + w3 * human_pressure) * 100

    # ---------------------------------------------------------
    # 9. 都市の居住可能性の評価（交通面のみ）→ 一旦，土地のすみやすさ，ばらつきを表現
    transportation_level = transportation_level * 0.95 + transport_level_coef * transportation_invest - 0.01 #ここが非常に怪しい！
    urban_level = distance_urban_level_coef * (1 - migration_ratio) * transportation_level #平均移動距離が長くなることの効果を算出
    urban_level -= current_flood_damage * flood_urban_damage_coef
    urban_level = min(max(urban_level, 0), 100)
    # urban_level = (1 - migration_ratio) * 100

    # ---------------------------------------------------------
    # 10. 住民の防災能力・意識
    # resident_capacity = resident_capacity * (1 - resident_capacity_degrade_ratio) + capacity_building_cost * capacity_building_coefficient # 自然減
    # resident_capacity = min(0.95, resident_capacity)
    resident_capacity = min(0.99, max(0.0, resident_capacity * (1 - resident_capacity_degrade_ratio) + capacity_building_cost * capacity_building_coefficient))

    # ---------------------------------------------------------
    # 11. コスト・住民負担算出
    planting_trees_cost = planting_trees_amount * cost_per_1000trees
    migration_cost = house_migration_amount * cost_per_migration
    municipal_cost = dam_levee_construction_cost * 100_000_000 \
                   + agricultural_RnD_cost * 10_000_000 \
                   + paddy_dam_construction_cost * 1_000_000 \
                   + capacity_building_cost * 1_000_000 \
                   + planting_trees_cost \
                   + migration_cost \
                   + transportation_invest * 10_000_000
    resident_burden = municipal_cost / total_house
    resident_burden += current_flood_damage * flood_recovery_cost_coef / total_house # added

    # --- 出力 ---
    outputs = {
        'Year': year,
        'Temperature (℃)': temp,
        'Precipitation (mm)': precip,
        'Available Water': current_available_water,
        'Crop Yield': current_crop_yield,
        'Municipal Demand': current_municipal_demand,
        'Flood Damage': current_flood_damage,
        'Levee Level': current_levee_level,
        'High Temp Tolerance Level': high_temp_tolerance_level,
        'Hot Days': hot_days,
        'Extreme Precip Frequency': extreme_precip_freq,
        'Extreme Precip Events': extreme_precip_events,
        'Ecosystem Level': ecosystem_level,
        'Municipal Cost': municipal_cost, # resident_burdenと重複
        'Urban Level': urban_level,
        'Resident Burden': resident_burden,
        'Levee investment total': levee_investment_total,
        'RnD investment total': RnD_investment_total,
        'Resident capacity': resident_capacity,
        'Forest Area': current_forest_area,
        'planting_history': planting_history,
        'risky_house_total': risky_house_total,
        'non_risky_house_total': non_risky_house_total,
        'transportation_level' : transportation_level,
        'paddy_dam_area' : paddy_dam_area,
        # 'CO2 Absorbed': co2_absorbed,
        # 意思決定変数そのものをログとして保持
        'planting_trees_amount': planting_trees_amount,
        'house_migration_amount': house_migration_amount,
        'dam_levee_construction_cost': dam_levee_construction_cost,
        'paddy_dam_construction_cost': paddy_dam_construction_cost,
        'capacity_building_cost': capacity_building_cost,
        'agricultural_RnD_cost': agricultural_RnD_cost,
        'transportation_invest': transportation_invest,
    }

    current_values = {
        'temp': temp,
        'precip': precip,
        'municipal_demand': current_municipal_demand,
        'available_water': current_available_water,
        'crop_yield': current_crop_yield,
        'levee_level': current_levee_level,
        'high_temp_tolerance_level': high_temp_tolerance_level,
        'hot_days': hot_days,
        'extreme_precip_freq': extreme_precip_freq,
        'ecosystem_level': ecosystem_level,
        'urban_level': urban_level,
        'levee_investment_total': levee_investment_total,
        'RnD_investment_total': RnD_investment_total,
        'forest_area': current_forest_area,
        'paddy_dam_area' : paddy_dam_area,
        'resident_capacity': resident_capacity,
        'planting_history': planting_history,
        'risky_house_total': risky_house_total,
        'non_risky_house_total': non_risky_house_total,
        'transportation_level' : transportation_level,
        'resident_burden': resident_burden,
        'biodiversity_level': ecosystem_level,
    }

    # 辞書の中のNumPy型をすべてPython標準型に変換する関数を追加
    def convert_numpy(obj):
        if isinstance(obj, dict):
            return {convert_numpy(k): convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(i) for i in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        else:
            return obj

    outputs = convert_numpy(outputs)
    current_values = convert_numpy(current_values)

    return current_values, outputs


def simulate_simulation(years, initial_values, decision_vars_list, params):
    prev_values = initial_values.copy()
    results = []

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
            decision_vars = decision_vars_raw

        prev_values, outputs = simulate_year(year, prev_values, decision_vars, params)
        results.append(outputs)

    return results