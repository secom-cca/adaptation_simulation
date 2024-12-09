import numpy as np

def simulate_year(year, prev_values, decision_vars, params):
    # 前年の値を展開
    prev_municipal_demand = prev_values['municipal_demand']
    prev_available_water = prev_values['available_water']
    prev_levee_level = prev_values['levee_level']
    prev_high_temp_tolerance_level = prev_values['high_temp_tolerance_level']
    prev_ecosystem_level = prev_values['ecosystem_level']
    levee_investment_years = prev_values['levee_investment_years']
    RnD_investment_years = prev_values['RnD_investment_years']
    dam_investment_years = prev_values['dam_investment_years']
    paddy_dam_investment_years = prev_values['paddy_dam_investment_years']
    relocation_investment_years = prev_values['relocation_investment_years']
    flood_proofing_investment_years = prev_values['flood_proofing_investment_years']
    houses_at_risk = prev_values['houses_at_risk']
    flood_proofed_houses = prev_values['flood_proofed_houses']
    livability = prev_values['livability']
    max_available_water = prev_values['max_available_water']

    # 意思決定変数を展開（適宜変更）
    irrigation_water_amount = decision_vars['irrigation_water_amount']
    released_water_amount = decision_vars['released_water_amount']
    levee_construction_cost = decision_vars['levee_construction_cost']
    agricultural_RnD_cost = decision_vars['agricultural_RnD_cost']

    # 新規対策に対応する投資額
    dam_construction_cost = decision_vars.get('dam_construction_cost', 0.0)
    paddy_dam_construction_cost = decision_vars.get('paddy_dam_construction_cost', 0.0)
    relocation_investment = decision_vars.get('relocation_investment', 0.0)
    flood_proofing_investment = decision_vars.get('flood_proofing_investment', 0.0)

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
    evapotranspiration_amount = params['evapotranspiration_amount']
    ecosystem_threshold = params['ecosystem_threshold']
    crop_rnd_max_tolerance = prev_values['crop_rnd_max_tolerance']

    # 新規パラメータ（ダム・田んぼダム・移転・防災改修）
    dam_investment_threshold = params['dam_investment_threshold']
    dam_investment_required_years = params['dam_investment_required_years']
    dam_capacity_increment = params['dam_capacity_increment']
    ecosystem_damage_per_dam = params['ecosystem_damage_per_dam']

    paddy_dam_investment_threshold = params['paddy_dam_investment_threshold']
    paddy_dam_investment_required_years = params['paddy_dam_investment_required_years']
    paddy_dam_capacity_increment = params['paddy_dam_capacity_increment']

    relocation_investment_threshold = params['relocation_investment_threshold']
    relocation_required_years = params['relocation_required_years']
    relocation_houses_reduction_rate = params['relocation_houses_reduction_rate']
    livability_decrement_per_relocation = params['livability_decrement_per_relocation']

    flood_proofing_investment_threshold = params['flood_proofing_investment_threshold']
    flood_proofing_required_years = params['flood_proofing_required_years']
    flood_proofed_increment_rate = params['flood_proofed_increment_rate']
    flood_damage_reduction_per_flood_proofed_house = params['flood_damage_reduction_per_flood_proofed_house']

    # 気温の計算
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)

    # 降水量の計算
    precip_uncertainty = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_uncertainty))

    # 真夏日日数の計算
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = max(hot_days, 0)

    # 極端降水頻度
    extreme_precip_freq = base_extreme_precip_freq + extreme_precip_freq_trend * (year - start_year)
    extreme_precip_freq = max(extreme_precip_freq, 0.0)
    extreme_precip_events = np.random.poisson(extreme_precip_freq)

    # 都市水需要
    municipal_demand_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
    current_municipal_demand = prev_municipal_demand * (1 + municipal_demand_growth)

    # 利用可能水量
    current_available_water = max(0, prev_available_water + precip - evapotranspiration_amount - current_municipal_demand - irrigation_water_amount - released_water_amount)
    current_available_water = min(current_available_water, max_available_water)

    # 作物収量
    crop_yield_irrigation_component = max_potential_yield * (irrigation_water_amount / optimal_irrigation_amount)
    crop_yield_irrigation_component = min(crop_yield_irrigation_component, max_potential_yield)
    temp_impact = hot_days * temp_coefficient * (1 - prev_high_temp_tolerance_level)
    current_crop_yield = crop_yield_irrigation_component - temp_impact
    current_crop_yield = max(current_crop_yield, 0)

    # 堤防レベル更新
    if levee_construction_cost >= levee_investment_threshold:
        levee_investment_years += 1
        if levee_investment_years >= levee_investment_required_years:
            prev_levee_level = min(prev_levee_level + levee_level_increment, 1.0)
            levee_investment_years = 0
    else:
        levee_investment_years = 0

    # 高温耐性
    if agricultural_RnD_cost >= RnD_investment_threshold:
        RnD_investment_years += 1
        if RnD_investment_years >= RnD_investment_required_years:
            prev_high_temp_tolerance_level = min(prev_high_temp_tolerance_level + high_temp_tolerance_increment, crop_rnd_max_tolerance)
            RnD_investment_years = 0
            crop_rnd_max_tolerance += 0.1
    else:
        RnD_investment_years = 0

    # ダム建設（自治体）
    if dam_construction_cost >= dam_investment_threshold:
        dam_investment_years += 1
        if dam_investment_years >= dam_investment_required_years:
            # ダム完成
            max_available_water += dam_capacity_increment
            # 生態系に悪影響
            prev_ecosystem_level = max(prev_ecosystem_level - ecosystem_damage_per_dam, 0)
            dam_investment_years = 0
    else:
        dam_investment_years = 0

    # 田んぼダム（農家）
    if paddy_dam_construction_cost >= paddy_dam_investment_threshold:
        paddy_dam_investment_years += 1
        if paddy_dam_investment_years >= paddy_dam_investment_required_years:
            # 田んぼダム完成
            max_available_water += paddy_dam_capacity_increment
            # 生態系への影響は小さいのでここではゼロとする
            paddy_dam_investment_years = 0
    else:
        paddy_dam_investment_years = 0

    # 集団移転（住民）
    if relocation_investment >= relocation_investment_threshold:
        relocation_investment_years += 1
        if relocation_investment_years >= relocation_required_years:
            # 集団移転完了
            houses_at_risk = houses_at_risk * (1 - relocation_houses_reduction_rate)
            # 住みやすさ低下
            livability = max(livability - livability_decrement_per_relocation, 0)
            relocation_investment_years = 0
    else:
        relocation_investment_years = 0

    # 防災改修（住民）
    if flood_proofing_investment >= flood_proofing_investment_threshold:
        flood_proofing_investment_years += 1
        if flood_proofing_investment_years >= flood_proofing_required_years:
            # 防災改修が進む
            # flood_proofed_housesを割合増加（例：全住宅中の一定割合が改修済みになる）
            flood_proofed_houses = min(flood_proofed_houses + flood_proofed_increment_rate, 1.0)
            flood_proofing_investment_years = 0
    else:
        flood_proofing_investment_years = 0

    # 洪水被害額計算
    # 元々：(extreme_precip_events * (1 - prev_levee_level) * flood_damage_coefficient)
    # ここに、houses_at_riskとflood_proofed_housesの要素を組み込む
    # 被害額はリスクある住宅数に比例すると仮定し、その一部が防災改修によって軽減
    # 被害額 = ベース × リスク住宅数 × (1 - 堤防レベル) × (1 - 防災改修効果)
    # 防災改修効果はflood_proofed_housesに比例してダメージ軽減
    damage_reduction_factor = 1 - (flood_proofed_houses * flood_damage_reduction_per_flood_proofed_house)
    current_flood_damage = extreme_precip_events * (1 - prev_levee_level) * flood_damage_coefficient * houses_at_risk * damage_reduction_factor

    # 生態系レベルの計算
    # ダムによる悪影響は上で処理済み。通常は水不足で悪化することを考慮。
    water_for_ecosystem = precip + released_water_amount
    if water_for_ecosystem < ecosystem_threshold:
        prev_ecosystem_level = max(prev_ecosystem_level - 0.5, 0)  # 閾値以下なら少し低下

    # 自治体コスト計算（例）
    municipal_cost = levee_construction_cost + agricultural_RnD_cost + dam_construction_cost
    # 農家負担などを別途計上することも可能

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
        'Max Available Water': max_available_water,
        'Houses at Risk': houses_at_risk,
        'Flood Proofed Houses Rate': flood_proofed_houses,
        'Livability': livability
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
        'crop_rnd_max_tolerance': crop_rnd_max_tolerance,
        'dam_investment_years': dam_investment_years,
        'paddy_dam_investment_years': paddy_dam_investment_years,
        'relocation_investment_years': relocation_investment_years,
        'flood_proofing_investment_years': flood_proofing_investment_years,
        'houses_at_risk': houses_at_risk,
        'flood_proofed_houses': flood_proofed_houses,
        'livability': livability,
        'max_available_water': max_available_water
    }

    return current_values, outputs


def simulate_simulation(years, initial_values, decision_vars_list, params):
    prev_values = initial_values.copy()
    results = []

    for idx, year in enumerate(years):
        if isinstance(decision_vars_list, list):
            decision_vars = decision_vars_list[min(idx, len(decision_vars_list)-1)]
        else:
            # モンテカルロモード等に対応するならここで処理
            decision_year = (year - params['start_year']) // 10 * 10 + params['start_year']
            decision_vars_raw = decision_vars_list.loc[decision_year].to_dict()
            key_mapping = {
                '灌漑水量 (Irrigation Water Amount)': 'irrigation_water_amount',
                '放流水量 (Released Water Amount)': 'released_water_amount',
                '堤防工事費 (Levee Construction Cost)': 'levee_construction_cost',
                '農業研究開発費 (Agricultural R&D Cost)': 'agricultural_RnD_cost',
                'ダム建設費 (Dam Construction Cost)': 'dam_construction_cost',
                '田んぼダム建設費 (Paddy Dam Construction Cost)': 'paddy_dam_construction_cost',
                '移転投資 (Relocation Investment)': 'relocation_investment',
                '防災改修投資 (Flood Proofing Investment)': 'flood_proofing_investment'
            }
            decision_vars = { new_key: decision_vars_raw[old_key] for old_key, new_key in key_mapping.items() }

        prev_values, outputs = simulate_year(year, prev_values, decision_vars, params)
        results.append(outputs)

    return results
