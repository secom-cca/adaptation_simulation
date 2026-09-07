# simulation.py

import random
import numpy as np
import pandas as pd
try:
    import ollama
except ModuleNotFoundError:
    ollama = None
from scipy.stats import gumbel_r
from config import SIMULATION_RANDOM_SEED
from src.utils import estimate_rice_yield_loss

POLICY_KEYS = [
    "planting_trees_amount",
    "house_migration_amount",
    "dam_levee_construction_cost",
    "paddy_dam_construction_cost",
    "capacity_building_cost",
    "agricultural_RnD_cost",
]

def convert_mana_decisions_to_backend_units(decision_vars, params):
    """Convert annual mana allocations to the legacy yearly units used by the model."""
    if params.get("POLICY_INPUT_UNIT", "mana") != "mana":
        return dict(decision_vars), {key: float(decision_vars.get(key, 0) or 0) for key in POLICY_KEYS}

    mana_jpy = params.get("MANA_JPY_PER_YEAR", 20_000_000)
    converted = dict(decision_vars)
    rules = params.get("POLICY_MANA_RULES", {})
    policy_mana = {}
    for key in POLICY_KEYS:
        value = max(0.0, float(decision_vars.get(key, 0) or 0))
        rule = rules.get(key, {})
        if value and rule.get("min_mana_per_use") is not None and value < rule["min_mana_per_use"]:
            value = 0.0
        if rule.get("max_mana_per_turn") is not None:
            value = min(value, float(rule["max_mana_per_turn"]))
        policy_mana[key] = value
    converted["planting_trees_amount"] = policy_mana["planting_trees_amount"] * mana_jpy / params["cost_per_1000trees"]
    converted["house_migration_amount"] = policy_mana["house_migration_amount"] * mana_jpy / params["cost_per_migration"]
    converted["dam_levee_construction_cost"] = policy_mana["dam_levee_construction_cost"] * mana_jpy / 100_000_000
    converted["paddy_dam_construction_cost"] = policy_mana["paddy_dam_construction_cost"] * mana_jpy / 1_000_000
    converted["capacity_building_cost"] = policy_mana["capacity_building_cost"] * 2.0
    converted["agricultural_RnD_cost"] = policy_mana["agricultural_RnD_cost"] * mana_jpy / 10_000_000
    return converted, policy_mana

def _interpolate_by_year(year, values_by_year):
    points = sorted((int(k), float(v)) for k, v in values_by_year.items())
    if not points:
        return 1.0
    if year <= points[0][0]:
        return points[0][1]
    if year >= points[-1][0]:
        return points[-1][1]
    for (y0, v0), (y1, v1) in zip(points, points[1:]):
        if y0 <= year <= y1:
            return v0 + (v1 - v0) * ((year - y0) / (y1 - y0))
    return points[-1][1]

def calculate_budget_components(year, prev_values, params):
    base_mana = params.get("BASE_POLICY_BUDGET_MANA", 10.0)
    mana_jpy = params.get("MANA_JPY_PER_YEAR", 20_000_000)
    pop_multiplier = _interpolate_by_year(year, params.get("population_budget_multiplier_by_year", {year: 1.0}))
    if not params.get("POPULATION_BUDGET_ALLOW_INCREASE", False):
        pop_multiplier = min(1.0, pop_multiplier)
    population_penalty = base_mana * max(0.0, 1.0 - pop_multiplier)

    migration_mana = float(prev_values.get("cumulative_house_migration_mana", 0) or 0)
    migration_start_mana = float(params.get("MIGRATION_INFRA_PENALTY_START_MANA", 1.0) or 0)
    chargeable_migration_mana = max(0.0, migration_mana - migration_start_mana)
    if params.get("MIGRATION_INFRA_PENALTY_MODE") == "mana":
        migration_penalty = min(
            chargeable_migration_mana * params.get("MIGRATION_INFRA_PENALTY_MANA_PER_MANA", 0.5),
            params.get("MIGRATION_INFRA_PENALTY_CAP_MANA", base_mana * 0.5),
        )
    else:
        houses_per_mana = mana_jpy * params.get("TURN_YEARS", 25) / params.get("cost_per_migration", 975_000)
        chargeable_migrated_houses = chargeable_migration_mana * houses_per_mana
        migration_penalty = chargeable_migrated_houses * params.get("INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR", 10_000) / mana_jpy

    avg_flood_jpy = float(prev_values.get("last_25y_avg_flood_damage_jpy", 0) or 0)
    flood_penalty = avg_flood_jpy * params.get("FLOOD_RECOVERY_COST_COEF", params.get("flood_recovery_cost_coef", 0.1)) / mana_jpy
    available = max(
        params.get("MIN_POLICY_BUDGET_MANA", 0.0),
        base_mana - population_penalty - migration_penalty - flood_penalty,
    )
    return {
        "base_budget_mana": base_mana,
        "population_budget_multiplier": pop_multiplier,
        "population_decline_penalty_mana": population_penalty,
        "migration_infra_penalty_mana": migration_penalty,
        "flood_recovery_penalty_mana": flood_penalty,
        "available_budget_mana": available,
    }

def _event_group_for_category(category):
    if category == "climate":
        return "external_shock"
    if category == "policy_effect":
        return "policy_effect"
    return "damage_or_decline"


def _format_jpy_japanese(value):
    """MayFest 2026: user-facing money text uses rounded Japanese units."""
    amount = float(value or 0)
    if amount >= 100_000_000:
        return f"約{amount / 100_000_000:.1f}億円"
    if amount >= 10_000:
        return f"約{round(amount / 10_000):,}万円"
    return f"約{round(amount):,}円"


def _capacity_after_years(initial_capacity, annual_investment, years, params):
    """MayFest 2026: benchmark disaster-training progress against one full 25-year turn."""
    capacity = float(initial_capacity or 0.0)
    for _ in range(int(years)):
        capacity = min(
            0.99,
            max(
                0.0,
                capacity * (1 - params.get("resident_capacity_degrade_ratio", 0.05))
                + float(annual_investment or 0.0) * params.get("capacity_building_coefficient", 0.02),
            ),
        )
    return capacity


def _emit_event(events, state, event_id, year, turn_index, severity, category, title, message,
                related_policy=None, metric=None, value=None, threshold=None, once=False,
                cooldown_years=None, group=None, baseline_value=None, diff_from_baseline=None):
    last_year = state.get(event_id)
    if once and last_year is not None:
        return
    if cooldown_years is not None and last_year is not None and year - int(last_year) < cooldown_years:
        return
    state[event_id] = year
    if category == "flood" and metric == "annual_flood_damage_jpy":
        current_damage = float(value or 0.0)
        baseline_damage = float(baseline_value or 0.0)
        reduction = max(float(diff_from_baseline or 0.0), baseline_damage - current_damage, 0.0)

        def _format_jpy(amount):
            amount = float(amount or 0.0)
            if amount >= 100_000_000:
                return f"約{amount / 100_000_000:.1f}億円"
            if amount >= 10_000:
                return f"約{amount / 10_000:,.0f}万円"
            return f"約{amount:,.0f}円"

        title = "洪水被害が発生しました"
        message = (
            f"この年の洪水被害額は{_format_jpy(current_damage)}でした。"
            f"同じ雨が何も対策しなかった流域に降った場合の被害額"
            f"{_format_jpy(baseline_damage)}と比べると、"
            f"{_format_jpy(reduction)}の被害を抑えています。"
        )
    events.append({
        "id": event_id,
        "year": year,
        "turn_index": turn_index,
        "severity": severity,
        "category": category,
        "group": group or _event_group_for_category(category),
        "title": title,
        "message": message,
        "related_policy": related_policy,
        "metric": metric,
        "value": value,
        "threshold": threshold,
        # MayFest 2026: display components can explain policy effect versus no-policy baseline.
        "baselineValue": baseline_value,
        "diffFromBaseline": diff_from_baseline,
    })

def simulate_year(year, prev_values, decision_vars, params, fixed_seed=True):
    # --- 前年の値を展開（初期値を定義していない変数は追って調整） ---
    prev_levee_level = prev_values.get('levee_level', 100.0)
    high_temp_tolerance_level = prev_values.get('high_temp_tolerance_level', 0.0)
    ecosystem_level = prev_values.get('ecosystem_level', 100)
    prev_forest_area = prev_values.get('forest_area', params['total_area'] * params['initial_forest_area']) ##################
    planting_history    = prev_values.get('planting_history', {}) ##################
    resident_capacity = prev_values.get('resident_capacity', 0.0) ##################
    transportation_level = prev_values.get('transportation_level', 0.0) ##################
    prev_municipal_demand = prev_values.get('municipal_demand', params['initial_municipal_demand'])##################
    available_water = prev_values.get('available_water', params['max_available_water'])
    levee_investment_total = prev_values.get('levee_investment_total', 0.0)
    RnD_investment_total = prev_values.get('RnD_investment_total', 0.0)
    risky_house_total = prev_values.get('risky_house_total', params['house_total'])
    non_risky_house_total = prev_values.get('non_risky_house_total', 0)
    paddy_dam_area = prev_values.get('paddy_dam_area', 0)
    temp_threshold_crop = prev_values.get('temp_threshold_crop', params['temp_threshold_crop_ini'])
    cumulative_migrated_houses = prev_values.get('cumulative_migrated_houses', non_risky_house_total)
    cumulative_house_migration_mana = prev_values.get('cumulative_house_migration_mana', 0.0)
    initial_risky_house_total = prev_values.get('initial_risky_house_total') or risky_house_total
    initial_crop_yield = prev_values.get('initial_crop_yield') or prev_values.get('crop_yield') or params['max_potential_yield']
    events_state = dict(prev_values.get('events_state', {}) or {})
    events = []

    # --- 意思決定変数を展開 ---
    # モンテカルロモードでは mapping された internal keys が来る前提
    decision_vars_raw = dict(decision_vars)
    decision_vars, policy_mana = convert_mana_decisions_to_backend_units(decision_vars_raw, params)
    planting_trees_amount        = decision_vars.get('planting_trees_amount', 0)
    house_migration_amount       = decision_vars.get('house_migration_amount', 0)
    dam_levee_construction_cost  = decision_vars.get('dam_levee_construction_cost', 0)
    paddy_dam_construction_cost  = decision_vars.get('paddy_dam_construction_cost', 0)
    capacity_building_cost       = decision_vars.get('capacity_building_cost', 0)
    agricultural_RnD_cost        = decision_vars.get('agricultural_RnD_cost', 0)
    transportation_invest        = decision_vars.get('transportation_invest', 0)
    flow_irrigation_level        = decision_vars.get('flow_irrigation_level', 0)
    is_turn_start_year = year in {params.get("start_year", 2026), params.get("start_year", 2026) + 25, params.get("start_year", 2026) + 50}
    cumulative_planting_mana = prev_values.get("cumulative_planting_mana", 0.0)
    cumulative_agricultural_RnD_mana = prev_values.get("cumulative_agricultural_RnD_mana", 0.0)
    cumulative_defense_mana = prev_values.get("cumulative_defense_mana", 0.0)
    if is_turn_start_year:
        cumulative_planting_mana += policy_mana.get("planting_trees_amount", 0.0)
        cumulative_agricultural_RnD_mana += policy_mana.get("agricultural_RnD_cost", 0.0)
        cumulative_defense_mana += (
            policy_mana.get("dam_levee_construction_cost", 0.0)
            + policy_mana.get("paddy_dam_construction_cost", 0.0)
        )

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
    # extreme_precip_uncertainty_trend=params['extreme_precip_uncertainty_trend']
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
    # temp_coefficient              = params['temp_coefficient']
    max_potential_yield           = params['max_potential_yield']
    # optimal_irrigation_amount     = params['optimal_irrigation_amount']
    high_temp_tolerance_increment = params['high_temp_tolerance_increment']
    necessary_water_for_crops = params['necessary_water_for_crops']
    paddy_dam_cost_per_ha = params['paddy_dam_cost_per_ha']
    paddy_dam_yield_coef = params['paddy_dam_yield_coef']
    temp_crop_decrease_coef = params['temp_crop_decrease_coef']
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
    forest_degradation_rate_base = params['forest_degradation_rate']
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
    # forest_flood_reduction_coef = params['forest_flood_reduction_coef'] ### 0.4-2.8 [%/%]
    # forest_water_retention_coef = params['forest_water_retention_coef'] ### 2-4 [mm/%]
    forest_flood_reduction_coef = 1.6 # np.random.uniform(0.4,2.8)
    forest_water_retention_coef = 3 # np.random.uniform(2,4)
    # forest_ecosystem_boost_coef = params['forest_ecosystem_boost_coef'] 
    flood_crop_damage_coef = params['flood_crop_damage_coef']
    levee_ecosystem_damage_coef = params.get('levee_ecosystem_damage_coef', 0.0)
    flood_urban_damage_coef = params['flood_urban_damage_coef']
    # water_ecosystem_coef = params['water_ecosystem_coef']
    paddy_dam_flood_coef = params['paddy_dam_flood_coef']
    # 地形
    total_area = params['total_area']
    paddy_field_area = params['paddy_field_area']

    # The main simulation should stay reproducible, while forecast runs can
    # keep stochastic variation so the preview chart still shows uncertainty.
    if fixed_seed:
        year_seed = int(params.get("SIMULATION_RANDOM_SEED", SIMULATION_RANDOM_SEED) + (year - start_year))
        random.seed(year_seed)
        np.random.seed(year_seed)

    turn_index = int((year - start_year) // params.get("TURN_YEARS", 25)) + 1
    budget_components = calculate_budget_components(year, prev_values, params)
    
    # resident_density = 1000 # [person/km^2]
    # water_demand_per_resident = 130 # [m3/person]
    # current_municipal_demand = water_water_demand_per_resident * resident_density / 1000 = 130 [mm]

    # ---------------------------------------------------------
    # 1. 気象環境 ---
    temp = base_temp + temp_trend * (year - start_year) + np.random.normal(0, temp_uncertainty)

    precip_unc = base_precip_uncertainty + precip_uncertainty_trend * (year - start_year)
    precip = max(0, base_precip + precip_trend * (year - start_year) + np.random.normal(0, precip_unc))
    
    hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
    hot_days = int(max(hot_days, 0))
    
    # --- 極端降水の「強度」スケーリング（最重要） ---
    # 1 K あたり 6.5% の倍率で Gumbel の scale(β) を増加させる
    # simulation.py は β(t) = base_beta + extreme_precip_intensity_trend * (t - start_year)
    # なので、 dβ/dt = (dβ/dT) * (dT/dt) = (0.065 * base_beta) * temp_trend
    # cc_per_K = 0.065  # 6.5%/K  … 2℃で+13%、4℃で+26%
    # extreme_precip_intensity_trend = base_beta * cc_per_K * temp_trend
    # # --- 極端降水の「頻度」スケーリング（基本はゼロでOK） ---
    # # 50 mm/h 超の頻度倍率（2℃:×1.8, 4℃:×3.0）は β の増加だけでほぼ再現できるため 0 のままで可。
    # extreme_precip_intensity_trend = base_beta * cc_per_K * temp_trend

    extreme_precip_freq = max(base_extreme_precip_freq * (1 + extreme_precip_freq_trend * (year - start_year)), 0)
    extreme_precip_events = np.random.poisson(extreme_precip_freq)

    # mu = max(base_mu + extreme_precip_intensity_trend * (year - start_year), 0)
    mu = max(base_mu, 0)
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
    forest_degredation_coef = 0.1
    forest_degradation_rate = forest_degradation_rate_base * (1 + temp_trend * forest_degredation_coef * (year - start_year)) # assume 50% increase in 2100
    natural_loss = prev_forest_area * forest_degradation_rate
    current_forest_area = max(prev_forest_area + matured_trees - natural_loss, 0)
    if params.get("POLICY_MANA_RULES", {}).get("planting_trees_amount", {}).get("enable_max_forest_share", False):
        max_forest_share = params["POLICY_MANA_RULES"]["planting_trees_amount"].get("optional_max_forest_share", 0.70)
        current_forest_area = min(current_forest_area, total_area * max_forest_share)
    current_forest_area = min(current_forest_area, total_area)

    # #forest_area の効果発現 ---
    flood_reduction = forest_flood_reduction_coef * ((current_forest_area - total_area * params['initial_forest_area']) / total_area)
    water_retention_boost = forest_water_retention_coef * current_forest_area / total_area * 100 # 水源涵養効果
    co2_absorbed = current_forest_area * co2_absorption_per_ha  # tCO2

    # ---------------------------------------------------------
    # 4. 利用可能水量（System Dynamicsには未導入）

    et_base = evapotranspiration_amount
    et = et_base * (1 + 0.05 * max(0, (temp - base_temp)))  # ローカル

    # 森林の降水起因の保水（降水依存に変更）
    forest_retention_ratio = forest_water_retention_coef * (current_forest_area / total_area) * 0.1  # 例：0～0.1 程度を想定
    infiltration = precip * forest_retention_ratio

    # 即時流出
    runoff = runoff_coef * precip # * (1 - forest_retention_ratio)

    # 農業需要と戻り水
    ag_demand = necessary_water_for_crops
    return_flow_ratio = 0.2
    return_flow = ag_demand * return_flow_ratio

    available_water = np.clip(
        available_water + precip - et - current_municipal_demand - ag_demand - runoff + infiltration + return_flow,
        0, max_available_water
    )
    # evapotranspiration_amount = evapotranspiration_amount * (1 + (temp - base_temp) * 0.05) # クラウジウス・クラペイロン
    # available_water = min(
    #     max(
    #         available_water + precip - evapotranspiration_amount - current_municipal_demand - runoff_coef * precip + water_retention_boost,
    #         0
    #     ),
    #     max_available_water
    # )

    # ---------------------------------------------------------
    # 5. 農業生産量
    # temp_ripening = temp + 6.0 # 仮設定：登熟期の気温の計算
    # excess = max(temp_ripening - (temp_threshold_crop + high_temp_tolerance_level), 0)
    # loss = excess * temp_crop_decrease_coef

    paddy_dam_area = min(paddy_field_area, paddy_dam_area + paddy_dam_construction_cost / paddy_dam_cost_per_ha)
    paddy_dam_yield_impact = paddy_dam_yield_coef * min(paddy_dam_area / paddy_field_area, 1)

    water_impact = min(available_water/necessary_water_for_crops, 1.0)

    # temp_impact = estimate_rice_yield_loss(temp, high_temp_tolerance_level)
    temp_impact, act = estimate_rice_yield_loss(
        temp_mean_annual=temp,
        high_temp_tolerance_level=high_temp_tolerance_level,
        irrigation_mm=flow_irrigation_level,  # 掛け流しの追加取水量（mm/yr）
        I50=300.0,                # 半飽和点
        k_cool=6.0,             # 効率（0.002〜0.01で調整）
        water_supply_ratio=water_impact,  # その年に実際どれだけ水が回ったか
        cooling_cap_degC=5.0
    )

    flow_irrigation_actual = flow_irrigation_level * act * (1 - return_flow_ratio)
    available_water = max(available_water - flow_irrigation_actual, 0)

    current_crop_yield = max((max_potential_yield * (1 - temp_impact)) * water_impact * (1 - paddy_dam_yield_impact),0) # * paddy_field_area [haあたり]
    heat_adjusted_crop_yield = current_crop_yield

    # 5.2 農業R&D：累積投資で耐熱性向上（確率的閾値）
    RND_NOISE_FACTOR = 0.1
    RnD_investment_total += agricultural_RnD_cost
    RnD_threshold_with_noise = np.random.normal(RnD_investment_threshold * RnD_investment_required_years, RnD_investment_threshold * RND_NOISE_FACTOR)

    prev_high_temp_tolerance_level = high_temp_tolerance_level
    while RnD_investment_total >= RnD_threshold_with_noise:
        high_temp_tolerance_level += high_temp_tolerance_increment
        RnD_investment_total -= RnD_threshold_with_noise
        if high_temp_tolerance_level >= params.get("HIGH_TEMP_TOLERANCE_CAP", 2.5):
            high_temp_tolerance_level = params.get("HIGH_TEMP_TOLERANCE_CAP", 2.5)
            RnD_investment_total = 0.0
            break

    # ---------------------------------------------------------
    # 6. 住宅の移転
    total_house = risky_house_total + non_risky_house_total
    max_migration_share = params.get("POLICY_MANA_RULES", {}).get("house_migration_amount", {}).get("max_migration_share", 1.0)
    migration_cap_total = initial_risky_house_total * max_migration_share
    remaining_migration_cap = max(migration_cap_total - cumulative_migrated_houses, 0.0)
    actual_migration = min(house_migration_amount, risky_house_total, remaining_migration_cap)
    risky_house_total = max(risky_house_total - actual_migration + total_house * municipal_growth, 0)
    non_risky_house_total += actual_migration
    cumulative_migrated_houses += actual_migration
    cumulative_house_migration_mana += policy_mana.get("house_migration_amount", 0.0) / params.get("TURN_YEARS", 25)
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
    # for rain in rain_events:
    #     overflow_amount = max(rain - current_levee_level - paddy_dam_level, 0) * (1 - flood_reduction)
    #     flood_impact = overflow_amount * flood_damage_coefficient
    #     # 対策効果は災害規模により段階的に変化（S字カーブ）
    #     # response_factor = 1 / (1 + np.exp(-0.1 * (overflow_amount - 400)))  # 400mm超過で能力無効に近づく
    #     response_factor = 1 / (1 + np.exp(-0.02 * (overflow_amount - 200)))  # 400mm超過で能力無効に近づく
    #     effective_protection = (1 - resident_capacity * (1 - response_factor)) * (1 - migration_ratio * (1 - response_factor))
    #     flood_impact += flood_impact * effective_protection

    flood_impact_total = 0.0
    baseline_flood_impact_total = 0.0
    max_rain = 0.0
    max_overflow = 0.0
    event_thresholds_for_rain = params.get("EVENT_THRESHOLDS", {})
    major_rain_threshold = event_thresholds_for_rain.get("major_extreme_rain_mm", 160)
    major_rain_events = []
    for rain in rain_events:
        overflow = max(rain - current_levee_level - paddy_dam_level, 0) * (1 - flood_reduction)
        max_overflow = max(max_overflow, overflow)
        if rain >= major_rain_threshold:
            major_rain_events.append((rain, overflow))
        base_damage = overflow * flood_damage_coefficient
        # MayFest 2026: no-policy baseline for event copy uses the same rain with initial levee and no distributed/behavioral mitigation.
        baseline_flood_impact_total += max(rain - 100.0, 0.0) * flood_damage_coefficient
        # 小規模時=対策効く（mult<1）、大規模時=効きにくい（→mult→1）
        response = 1 / (1 + np.exp(-0.02 * (overflow - 200)))
        mitigation_mult = (1 - resident_capacity*(1 - response))*(1 - migration_ratio*(1 - response))
        flood_impact_total += base_damage * mitigation_mult
        if rain > max_rain:
            max_rain = rain
    current_flood_damage = max(flood_impact_total, 0.0)
    baseline_flood_damage_jpy = max(baseline_flood_impact_total, current_flood_damage)

    
    # # current_flood_damage = extreme_precip_events * flood_impact
    # current_flood_damage = flood_impact * (1 - resident_capacity) * (1 - migration_ratio)
    # current_flood_damage = max(flood_impact,0.0)
    current_crop_yield = max(current_crop_yield - current_flood_damage * flood_crop_damage_coef, 0)
    # MayFest 2026: approximate no-R&D crop baseline for display only; internal model values remain unrounded.
    baseline_temp_impact, _baseline_act = estimate_rice_yield_loss(
        temp_mean_annual=temp,
        high_temp_tolerance_level=0.0,
        irrigation_mm=flow_irrigation_level,
        I50=300.0,
        k_cool=6.0,
        water_supply_ratio=water_impact,
        cooling_cap_degC=5.0
    )
    baseline_crop_yield = max((max_potential_yield * (1 - baseline_temp_impact)) * water_impact * (1 - paddy_dam_yield_impact), 0)
    baseline_crop_yield = max(baseline_crop_yield - baseline_flood_damage_jpy * flood_crop_damage_coef, 0)


    # ---------------------------------------------------------
    # 8. 損害・生態系の評価
    # Natural resource base (0–1)
    ecological_base = min(current_forest_area / total_area * 0.7, 1.0) 
    water_base = min(available_water / ecosystem_threshold, 1.0)

    # # Disturbance resistance
    # temp_diff = abs(temp - base_temp)
    # extreme_factor = extreme_precip_events
    # disturbance_resistance = max(0, 1.0 - 0.05 * temp_diff - 0.03 * extreme_factor) 

    # Human pressure
    human_pressure_raw = min(0.01 * current_levee_level - 1, 1.0)
    # keep human_pressure in [0, 1] to avoid ecosystem_level exceeding 100
    human_pressure = float(np.clip(1.0 - human_pressure_raw, 0.0, 1.0))

    # Weighted ecosystem score
    # weights = np.random.dirichlet([1/4, 1/4, 1/4])
    # w1, w2, w3 = weights
    # w1, w2, w3 = w1+1/4, w2+1/4, w3+1/4
    w1, w2, w3 = 1/3, 1/3, 1/3

    # ecosystem_level = (w1 * ecological_base + w2 * disturbance_resistance + w3 * human_pressure) * 100
    ecosystem_level = (w1 * ecological_base + w2 * water_base + w3 * human_pressure) * 100
    ecosystem_level = max(0.0, ecosystem_level - current_levee_level * levee_ecosystem_damage_coef)
    # MayFest 2026: display-only no-policy baseline approximation for event copy.
    forest_policy_gain = max(0.0, cumulative_planting_mana - 5.0) * params.get("forest_ecosystem_boost_coef", 0.01) * 18.0
    baseline_ecosystem_level = max(0.0, ecosystem_level - forest_policy_gain)

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
    if params.get("POLICY_INPUT_UNIT", "mana") == "mana":
        policy_cost_jpy = sum(policy_mana.values()) * params.get("MANA_JPY_PER_YEAR", 20_000_000)
    else:
        planting_trees_cost = planting_trees_amount * cost_per_1000trees
        migration_cost = house_migration_amount * cost_per_migration
        policy_cost_jpy = (dam_levee_construction_cost * 100_000_000
                        + agricultural_RnD_cost * 10_000_000
                        + paddy_dam_construction_cost * 1_000_000
                        + capacity_building_cost * 1_000_000
                        + planting_trees_cost
                        + migration_cost)
    municipal_cost = (policy_cost_jpy + transportation_invest * 10_000_000) / 100  # [USD]
    resident_burden = municipal_cost / total_house
    resident_burden += current_flood_damage * flood_recovery_cost_coef / total_house # added
    current_flood_damage_jpy = current_flood_damage
    current_flood_damage /= 100 # [USD]

    thresholds = params.get("EVENT_THRESHOLDS", {})
    cooldowns = params.get("EVENT_COOLDOWNS", {})
    initial_overflow_180 = max(180.0 - 100.0, 0.0)
    current_overflow_180 = max(180.0 - current_levee_level - paddy_dam_level, 0.0)
    flood_reduction_pct_180 = 0.0
    if initial_overflow_180 > 0:
        flood_reduction_pct_180 = max(0.0, min(100.0, (1.0 - current_overflow_180 / initial_overflow_180) * 100.0))
    # MayFest 2026: extreme rainfall is kept in the model, but not emitted as a user-facing event.
    if False and extreme_precip_events > 0:
        if max_rain >= thresholds.get("record_extreme_rain_mm", 260):
            rain_event_id = f"extreme_rain_record_{year}"
            rain_title = "記録的豪雨が発生しました"
            rain_message = (
                f"{max_rain:.0f}mmの記録的豪雨が発生しました。"
                "通常の治水対策だけでは被害を抑えきれない可能性があり、"
                "堤防・田んぼダム・森林保全・住宅移転・防災訓練を組み合わせる必要があります。"
            )
            rain_severity = "critical"
            rain_threshold = thresholds.get("record_extreme_rain_mm", 260)
        else:
            rain_event_id = f"extreme_rain_{year}"
            rain_title = "極端豪雨が発生しました"
            rain_message = (
                f"{max_rain:.0f}mmの極端豪雨が発生しました。"
                "治水対策が不足している場合、洪水被害や農地・生態系への影響が大きくなります。"
            )
            rain_severity = "warning"
            rain_threshold = thresholds.get("warning_extreme_rain_mm", 210)

        _emit_event(
            events, events_state, rain_event_id, year, turn_index, rain_severity, "climate",
            rain_title,
            rain_message,
            metric="max_rain_mm", value=max_rain, threshold=rain_threshold,
            group="external_shock",
        )
    if False and extreme_precip_events > 0 and not major_rain_events:
        _emit_event(
            events, events_state, f"extreme_rain_{year}", year, turn_index, "warning", "climate",
            "極端降雨が発生しました",
            f"この年は極端降雨イベントが{extreme_precip_events}回発生しました。最大降雨量は約{max_rain:.0f}mmです。",
            metric="Extreme Precip Events", value=extreme_precip_events, threshold=1,
        )
    # extreme_rain_frequency_ は extreme_rain_ と意味が重複するため、
    # ワークショップ画面では使わない。
    # 極端豪雨は extreme_rain_{year} / extreme_rain_record_{year} だけ表示する。
    if False and extreme_precip_events >= thresholds.get("extreme_rain_event_count_per_year", 3):
        _emit_event(
            events, events_state, f"extreme_rain_frequency_{year}", year, turn_index, "warning", "climate",
            "極端降雨の回数が増えています",
            f"この年は極端降雨イベントが{extreme_precip_events}回発生しました。気候変動により、強い雨が複数回起こる年が増えています。",
            metric="Extreme Precip Events", value=extreme_precip_events,
            threshold=thresholds.get("extreme_rain_event_count_per_year", 3),
        )
    if False and max_rain >= thresholds.get("major_extreme_rain_mm", 220):
        initial_overflow_180 = max(180.0 - 100.0, 0.0)
        current_overflow_180 = max(180.0 - current_levee_level - paddy_dam_level, 0.0)
        flood_reduction_pct_180 = 0.0
        if initial_overflow_180 > 0:
            flood_reduction_pct_180 = max(0.0, min(100.0, (1.0 - current_overflow_180 / initial_overflow_180) * 100.0))
        _emit_event(
            events, events_state, f"extreme_rain_{year}", year, turn_index, "warning", "climate",
            "極端降雨が発生",
            f"最大降雨量が{max_rain:.0f}mmに達しました。現在の堤防・田んぼダム水準では、代表的な180mm豪雨の越流水を初期状態より約{flood_reduction_pct_180:.0f}%削減する想定です。",
            metric="max_rain_event_mm", value=max_rain, threshold=thresholds.get("major_extreme_rain_mm", 220),
        )
    flood_diff_from_baseline = max(0.0, baseline_flood_damage_jpy - current_flood_damage_jpy)

    if extreme_precip_events > 0 and current_flood_damage_jpy >= thresholds.get("severe_flood_damage_jpy", 300_000_000):
        _emit_event(
            events,
            events_state,
            f"severe_flood_damage_{year}",
            year,
            turn_index,
            "critical",
            "flood",
            "甚大な洪水被害が発生しました",
            (
                f"洪水被害額が約{current_flood_damage_jpy:,.0f}円となり、"
                f"甚大被害の目安である{thresholds.get('severe_flood_damage_jpy', 300_000_000):,.0f}円を超えました。"
            ),
            metric="annual_flood_damage_jpy",
            value=current_flood_damage_jpy,
            threshold=thresholds.get("severe_flood_damage_jpy", 300_000_000),
            diff_from_baseline=flood_diff_from_baseline,
            baseline_value=baseline_flood_damage_jpy,
        )

    elif extreme_precip_events > 0 and current_flood_damage_jpy >= thresholds.get("large_flood_damage_jpy", 250_000_000):
        _emit_event(
            events,
            events_state,
            f"large_flood_damage_{year}",
            year,
            turn_index,
            "warning",
            "flood",
            "かなり大きな洪水被害が発生しました",
            (
                f"洪水被害額が約{current_flood_damage_jpy:,.0f}円となり、"
                f"かなり大きな被害の目安である{thresholds.get('large_flood_damage_jpy', 250_000_000):,.0f}円を超えました。"
            ),
            metric="annual_flood_damage_jpy",
            value=current_flood_damage_jpy,
            threshold=thresholds.get("large_flood_damage_jpy", 250_000_000),
            diff_from_baseline=flood_diff_from_baseline,
            baseline_value=baseline_flood_damage_jpy,
        )

    elif extreme_precip_events > 0 and current_flood_damage_jpy >= thresholds.get("major_flood_damage_jpy", 200_000_000):
        _emit_event(
            events,
            events_state,
            f"major_flood_damage_{year}",
            year,
            turn_index,
            "warning",
            "flood",
            "大きな洪水被害が発生しました",
            (
                f"洪水被害額が約{current_flood_damage_jpy:,.0f}円となり、"
                f"大規模被害の目安である{thresholds.get('major_flood_damage_jpy', 200_000_000):,.0f}円を超えました。"
            ),
            metric="annual_flood_damage_jpy",
            value=current_flood_damage_jpy,
            threshold=thresholds.get("major_flood_damage_jpy", 200_000_000),
            diff_from_baseline=flood_diff_from_baseline,
            baseline_value=baseline_flood_damage_jpy,
        )

    elif extreme_precip_events > 0 and current_flood_damage_jpy >= thresholds.get("flood_damage_notice_jpy", 100_000_000):
        _emit_event(
            events,
            events_state,
            f"flood_damage_{year}",
            year,
            turn_index,
            "info",
            "flood",
            "洪水被害が発生しました",
            (
                f"洪水被害額が約{current_flood_damage_jpy:,.0f}円となり、"
                f"注意水準の{thresholds.get('flood_damage_notice_jpy', 100_000_000):,.0f}円を超えました。"
            ),
            metric="annual_flood_damage_jpy",
            value=current_flood_damage_jpy,
            threshold=thresholds.get("flood_damage_notice_jpy", 100_000_000),
            diff_from_baseline=flood_diff_from_baseline,
            baseline_value=baseline_flood_damage_jpy,
        )
    ecosystem_diff_from_baseline = max(0.0, ecosystem_level - baseline_ecosystem_level)
    if ecosystem_level <= thresholds.get("ecosystem_critical_threshold", 25.0):
        _emit_event(events, events_state, "ecosystem_critical", year, turn_index, "critical", "ecosystem",
                    "生態系への負荷が大きくなっています",
                    f"地球温暖化による気温上昇や水環境の変化などにより、地域の生態系への負荷が大きくなっています。現在の対策により、何も対策をしていなかった場合よりは{ecosystem_diff_from_baseline:.1f}ポイント高く保たれていますが、地域の自然環境や生きもののすみかは損なわれつつあります。",
                    metric="Ecosystem Level", value=ecosystem_level, threshold=thresholds.get("ecosystem_critical_threshold", 25.0),
                    baseline_value=baseline_ecosystem_level, diff_from_baseline=ecosystem_diff_from_baseline, once=True)
    elif ecosystem_level <= thresholds.get("ecosystem_low_threshold", 40.0):
        _emit_event(events, events_state, "ecosystem_low", year, turn_index, "warning", "ecosystem",
                    "生態系への負荷が高まっています",
                    f"地球温暖化による気温上昇や水環境の変化などにより、地域の生態系への負荷が高まっています。一方で、現在の対策により、何も対策をしていなかった場合と比べて生態系指標は{ecosystem_diff_from_baseline:.1f}ポイント高く保たれています。",
                    metric="Ecosystem Level", value=ecosystem_level, threshold=thresholds.get("ecosystem_low_threshold", 40.0),
                    baseline_value=baseline_ecosystem_level, diff_from_baseline=ecosystem_diff_from_baseline,
                    once=True)
    if False and ecosystem_level <= thresholds.get("ecosystem_critical_threshold", 25.0):
        _emit_event(events, events_state, "ecosystem_critical", year, turn_index, "critical", "ecosystem",
                    "生態系指標が深刻に低下", "生態系指標が低い水準まで下がっています。洪水対策と自然環境保全のバランスに注意が必要です。",
                    metric="Ecosystem Level", value=ecosystem_level, threshold=thresholds.get("ecosystem_critical_threshold", 25.0), once=True)
    elif False and ecosystem_level <= thresholds.get("ecosystem_low_threshold", 40.0):
        _emit_event(events, events_state, "ecosystem_low", year, turn_index, "warning", "ecosystem",
                    "生態系への負荷が高まっています", "堤防整備や土地利用変化の影響により、生態系指標が低下しています。",
                    metric="Ecosystem Level", value=ecosystem_level, threshold=thresholds.get("ecosystem_low_threshold", 40.0),
                    once=True)
    crop_ratio = heat_adjusted_crop_yield / max(initial_crop_yield, 1e-9)
    crop_event_age = year - start_year
    crop_event_allowed = crop_event_age >= thresholds.get("crop_production_low_after_years", 25)
    temp_driven_crop_decline = temp_impact >= thresholds.get("crop_temp_impact_event_threshold", 0.02)
    crop_diff_from_baseline = max(0.0, current_crop_yield - baseline_crop_yield)
    if crop_event_allowed and temp_driven_crop_decline and crop_ratio <= thresholds.get("crop_production_critical_ratio", 0.6):
        _emit_event(events, events_state, "crop_production_critical", year, turn_index, "critical", "agriculture",
                    "農作物生産への影響が大きくなっています",
                    f"高温の影響により、高温障害、品質低下、水稲の白濁化などが深刻化し、作物生産性が{current_crop_yield:.0f}kg/haまで下がりました。現在の対策により、何も対策をしていなかった場合よりは{crop_diff_from_baseline:.0f}kg/ha高く保たれていますが、農作物生産への影響は大きくなっています。",
                    metric="Crop Yield", value=current_crop_yield, threshold=thresholds.get("crop_production_critical_ratio", 0.6),
                    baseline_value=baseline_crop_yield, diff_from_baseline=crop_diff_from_baseline, once=True)
    elif crop_event_allowed and temp_driven_crop_decline and crop_ratio <= thresholds.get("crop_production_low_ratio", 0.8):
        _emit_event(events, events_state, "crop_production_low", year, turn_index, "warning", "agriculture",
                    "農作物生産性が低下しています",
                    f"高温の影響により、高温障害、品質低下、水稲の白濁化などが起き、作物生産性が{current_crop_yield:.0f}kg/haまで下がりました。それでも、農業R&Dなどの対策により、何も対策をしていなかった場合と比べて{crop_diff_from_baseline:.0f}kg/ha分の生産性を守ることができています。",
                    metric="Crop Yield", value=current_crop_yield, threshold=thresholds.get("crop_production_low_ratio", 0.8),
                    baseline_value=baseline_crop_yield, diff_from_baseline=crop_diff_from_baseline,
                    once=True)
    if False and crop_event_allowed and temp_driven_crop_decline and crop_ratio <= thresholds.get("crop_production_critical_ratio", 0.6):
        _emit_event(events, events_state, "crop_production_critical", year, turn_index, "critical", "agriculture",
                    "農業生産が深刻に低下", "高温や洪水被害の影響により、農作物生産高が初期水準を大きく下回っています。",
                    metric="crop_production_ratio", value=crop_ratio, threshold=thresholds.get("crop_production_critical_ratio", 0.6), once=True)
    elif False and crop_event_allowed and temp_driven_crop_decline and crop_ratio <= thresholds.get("crop_production_low_ratio", 0.8):
        _emit_event(events, events_state, "crop_production_low", year, turn_index, "warning", "agriculture",
                    "農作物生産が低下しています", "高温や洪水被害の影響により、農作物生産高が初期水準を下回っています。",
                    metric="crop_production_ratio", value=crop_ratio, threshold=thresholds.get("crop_production_low_ratio", 0.8),
                    once=True)
    if (
        crop_event_allowed
        and (temp_driven_crop_decline or year >= start_year + 49)
        and crop_ratio > thresholds.get("crop_production_low_ratio", 0.8)
        and baseline_crop_yield < current_crop_yield
        and cumulative_agricultural_RnD_mana >= 3.0
    ):
        _emit_event(
            events, events_state, "crop_production_avoided", year, turn_index, "success", "agriculture",
            "農作物生産の低下を抑えました",
            f"農業R&Dの累積投資により、何も対策をしていなかった場合より{crop_diff_from_baseline:.0f}kg/ha高い生産性を保ち、農作物生産の大きな低下を回避しました。",
            related_policy="agricultural_RnD_cost", metric="Crop Yield", value=current_crop_yield,
            threshold=thresholds.get("crop_production_low_ratio", 0.8),
            baseline_value=baseline_crop_yield, diff_from_baseline=crop_diff_from_baseline, once=True
        )
    if (
        year >= start_year + thresholds.get("forest_area_low_after_years", 25)
        and ecosystem_level > thresholds.get("ecosystem_low_threshold", 40.0)
        and baseline_ecosystem_level < ecosystem_level
        and cumulative_planting_mana >= 5.0
    ):
        _emit_event(
            events, events_state, "ecosystem_decline_avoided", year, turn_index, "success", "ecosystem",
            "生態系の低下を抑えました",
            f"植林・森林保全の累積投資により、何も対策をしていなかった場合より生態系指標を{ecosystem_diff_from_baseline:.1f}ポイント高く保ち、生態系低下を回避しました。",
            related_policy="planting_trees_amount", metric="Ecosystem Level", value=ecosystem_level,
            threshold=thresholds.get("ecosystem_low_threshold", 40.0),
            baseline_value=baseline_ecosystem_level, diff_from_baseline=ecosystem_diff_from_baseline, once=True
        )
    if budget_components["available_budget_mana"] <= thresholds.get("available_budget_critical_mana", 3.0):
        _emit_event(events, events_state, "budget_critical", year, turn_index, "critical", "budget",
                    "政策予算が大きく縮小しています", "人口減少、洪水被害、住宅移転後の公共インフラ維持費により、次ターンに使える政策予算が大きく減少しています。",
                    metric="available_budget_mana", value=budget_components["available_budget_mana"], threshold=thresholds.get("available_budget_critical_mana", 3.0), once=True)
    elif budget_components["available_budget_mana"] <= thresholds.get("available_budget_low_mana", 5.0):
        _emit_event(events, events_state, "budget_low", year, turn_index, "warning", "budget",
                    "政策予算が縮小しています", "人口減少、洪水被害、住宅移転後の公共インフラ維持費により、次ターンに使える政策予算が減少しています。",
                    metric="available_budget_mana", value=budget_components["available_budget_mana"], threshold=thresholds.get("available_budget_low_mana", 5.0), once=True)
    if budget_components.get("migration_infra_penalty_mana", 0.0) > thresholds.get("migration_budget_pressure_event_threshold", 0.05):
        _emit_event(events, events_state, "migration_budget_pressure", year, turn_index, "warning", "budget",
                    "住宅移転後のインフラ費用が発生しています",
                    "住宅移転が累計1ポイントを超えたため、公共交通・道路・上下水道などの維持費が次ターンの政策予算を圧迫し始めています。",
                    related_policy="house_migration_amount", metric="migration_infra_penalty_mana",
                    value=budget_components.get("migration_infra_penalty_mana", 0.0),
                    threshold=thresholds.get("migration_budget_pressure_event_threshold", 0.05),
                    once=True, cooldown_years=25)
    # MayFest 2026: housing relocation is immediate/linear, with visible progress every 4 points.
    if policy_mana.get("house_migration_amount", 0.0) > 0 or house_migration_amount > 0:
        _emit_event(events, events_state, "house_migration_started", year, turn_index, "success", "policy_effect",
                    "住宅移転が始まりました",
                    "洪水リスクの高い地域から住宅を移す取り組みが始まりました。洪水時に住宅被害を受けるリスクが下がっています。",
                    related_policy="house_migration_amount", metric="cumulative_house_migration_mana",
                    value=cumulative_house_migration_mana, threshold=0.0, once=True)
    for step_point in [4, 8, 12, 16, 20]:
        if cumulative_house_migration_mana >= step_point:
            _emit_event(events, events_state, f"house_migration_step_{step_point}point", year, turn_index, "success", "policy_effect",
                        "住宅移転が進んでいます",
                        f"住宅移転への累積投資が約{step_point}ポイントに達しました。洪水リスクの高い地域に残る住宅が減り、洪水時に住宅被害を受けるリスクが下がっています。",
                        related_policy="house_migration_amount", metric="cumulative_house_migration_mana",
                        value=cumulative_house_migration_mana, threshold=step_point, once=True)
    migration_progress = cumulative_migrated_houses / max(migration_cap_total, 1e-9)
    if migration_progress >= 0.8:
        _emit_event(events, events_state, "house_migration_near_cap", year, turn_index, "success", "policy_effect",
                    "住宅移転が大きく進みました",
                    "洪水リスクの高い地域からの住宅移転が大きく進みました。移転可能な住宅は少なくなっており、これ以上の追加投資では効果の伸びは小さくなっていきます。",
                    related_policy="house_migration_amount", metric="migration_progress",
                    value=migration_progress, threshold=0.8, once=True)
    if current_levee_level - prev_levee_level >= thresholds.get("levee_increment_event_mm", 20):
        levee_step = int(current_levee_level // max(thresholds.get("levee_increment_event_mm", 20), 1))
        _emit_event(events, events_state, "levee_completed", year, turn_index, "success", "policy_effect",
                    "堤防・河川改修が完成しました", "累積投資により、堤防の防御水準が20mm向上しました。代表的な180mm豪雨では越流水を20mm減らします。",
                    related_policy="dam_levee_construction_cost", metric="Levee Level", value=current_levee_level, threshold=thresholds.get("levee_increment_event_mm", 20), once=True)
        _emit_event(events, events_state, f"levee_20mm_step_{levee_step}", year, turn_index, "success", "policy_effect",
                    "堤防・河川改修が一段階進みました", "堤防の防御水準が20mm分上がりました。",
                    related_policy="dam_levee_construction_cost", metric="Levee Level", value=current_levee_level, threshold=thresholds.get("levee_increment_event_mm", 20), once=True)
    cumulative_matured_forest_area = float(events_state.get("_cumulative_matured_forest_area", 0.0) or 0.0) + max(matured_trees, 0.0)
    events_state["_cumulative_matured_forest_area"] = cumulative_matured_forest_area
    if matured_trees > 0:
        _emit_event(
            events, events_state, "forest_effect_started", year, turn_index, "success", "policy_effect",
            "植林の効果が見え始めました",
            (
                "過去に植えた木が成長し始め、森林の保水力と生態系への効果が少しずつ現れています。"
                "ただし、十分な効果には継続的な森林保全が必要です。"
            ),
            related_policy="planting_trees_amount", metric="matured_forest_area_ha", value=matured_trees,
            threshold=tree_growup_year, once=True
        )

    for forest_threshold in thresholds.get("forest_effect_matured_thresholds_ha", [100, 300]):
        if cumulative_matured_forest_area >= forest_threshold:
            if forest_threshold < 300:
                forest_title = "森林保全の効果が広がり始めました"
                forest_message = (
                    f"成長した森林面積が約{cumulative_matured_forest_area:,.0f}haに達しました。"
                    "流域全体の保水力と生態系の改善が期待できます。"
                )
            else:
                forest_title = "森林保全の効果が流域に広がっています"
                forest_message = (
                    f"成長した森林面積が約{cumulative_matured_forest_area:,.0f}haに達しました。"
                    "森林保全は洪水緩和・生態系・水循環を支える長期的な対策です。"
                )

            _emit_event(
                events, events_state, f"forest_effect_{int(forest_threshold)}ha", year, turn_index, "success", "policy_effect",
                forest_title,
                forest_message,
                related_policy="planting_trees_amount", metric="cumulative_matured_forest_area_ha",
                value=cumulative_matured_forest_area, threshold=forest_threshold, once=True
            )
    if agricultural_RnD_cost > 0:
        _emit_event(events, events_state, "rnd_started", year, turn_index, "success", "policy_effect",
                    "高温対応品種の開発を始めました", "農業R&D・高温適応技術への投資により、高温に強い品種と栽培技術の開発・普及が始まっています。",
                    related_policy="agricultural_RnD_cost", metric="agricultural_RnD_cost", value=agricultural_RnD_cost, threshold=0.0, once=True)
    # MayFest 2026: agricultural R&D display steps are 0.5C, not 0.2C.
    for step_value, suffix in [(0.5, "05"), (1.0, "10"), (1.5, "15"), (2.0, "20")]:
        if high_temp_tolerance_level >= step_value:
            _emit_event(events, events_state, f"rnd_tolerance_step_{suffix}", year, turn_index, "success", "policy_effect",
                        "農業R&Dの効果が広がっています",
                        f"農業R&Dの蓄積により、作物の高温耐性が約{step_value:.1f}℃向上しました。高温による品質低下や収量低下を抑えやすくなっています。",
                        related_policy="agricultural_RnD_cost", metric="High Temp Tolerance Level",
                        value=high_temp_tolerance_level, threshold=step_value, once=True)
    if high_temp_tolerance_level >= params.get("HIGH_TEMP_TOLERANCE_CAP", 2.5) * 0.8:
        _emit_event(events, events_state, "rnd_tolerance_near_cap", year, turn_index, "success", "policy_effect",
                    "農業R&Dの普及が上限に近づいています",
                    "高温に強い品種や栽培技術がかなり普及しました。これ以上の追加投資では、効果の伸びは小さくなっていきます。",
                    related_policy="agricultural_RnD_cost", metric="High Temp Tolerance Level",
                    value=high_temp_tolerance_level, threshold=params.get("HIGH_TEMP_TOLERANCE_CAP", 2.5) * 0.8, once=True)
    if False and high_temp_tolerance_level - prev_high_temp_tolerance_level >= thresholds.get("rnd_tolerance_increment_threshold", 0.2):
        rnd_step = int(round(high_temp_tolerance_level / max(thresholds.get("rnd_tolerance_increment_threshold", 0.2), 0.01)))
        _emit_event(events, events_state, f"rnd_tolerance_improved_{rnd_step}", year, turn_index, "success", "policy_effect",
                    "高温適応技術が普及しました", "農業R&D・高温適応技術普及への累積投資により、作物の高温耐性が0.2℃向上しました。",
                    related_policy="agricultural_RnD_cost", metric="High Temp Tolerance Level", value=high_temp_tolerance_level, threshold=thresholds.get("rnd_tolerance_increment_threshold", 0.2), once=True)
    if paddy_dam_construction_cost > 0:
        _emit_event(events, events_state, "paddy_dam_started", year, turn_index, "success", "policy_effect",
                    "田んぼダムの導入を始めました", "水田に雨水を一時的にためる取り組みが始まりました。効果は導入面積が広がるほど大きくなります。",
                    related_policy="paddy_dam_construction_cost", metric="paddy_dam_construction_cost", value=paddy_dam_construction_cost, threshold=0.0, once=True)
    if paddy_dam_level >= thresholds.get("paddy_dam_level_threshold_mm", 5.0):
        _emit_event(events, events_state, "paddy_dam_5mm", year, turn_index, "success", "policy_effect",
                    "田んぼダムの効果が見え始めました", "田んぼダムの導入面積が拡大し、越流水を約5mm削減できる水準に達しました。",
                    related_policy="paddy_dam_construction_cost", metric="paddy_dam_level", value=paddy_dam_level, threshold=thresholds.get("paddy_dam_level_threshold_mm", 5.0), once=True)
    if paddy_dam_level >= thresholds.get("paddy_dam_full_level_mm", 10.0):
        _emit_event(
            events, events_state, "paddy_dam_full", year, turn_index, "success", "policy_effect",
            "田んぼダムが最大効果に達しました",
            (
                f"田んぼダムの貯留効果が約{paddy_dam_level:.1f}mmに達しました。"
                "導入可能な水田面積に対して、最大に近い分散型治水効果が発揮されています。"
            ),
            related_policy="paddy_dam_construction_cost", metric="paddy_dam_level", value=paddy_dam_level,
            threshold=thresholds.get("paddy_dam_full_level_mm", 10.0), once=True
        )
    if capacity_building_cost > 0:
        _emit_event(events, events_state, "resident_capacity_started", year, turn_index, "success", "resident",
                    "防災訓練を始めました", "避難訓練・防災訓練への投資により、住民の災害対応力を高める取り組みが始まっています。",
                    related_policy="capacity_building_cost", metric="capacity_building_cost", value=capacity_building_cost, threshold=0.0, once=True)
    # MayFest 2026: disaster training progress is judged at turn end against max annual investment.
    turn_years = params.get("TURN_YEARS", 25)
    full_turn_capacity = _capacity_after_years(prev_values.get("resident_capacity", 0.0), 1.0, turn_years, params)
    turn_effect_threshold = full_turn_capacity * 0.85
    near_cap_threshold = 0.99 * 0.9
    if (year - start_year + 1) % turn_years == 0 and resident_capacity >= turn_effect_threshold:
        _emit_event(events, events_state, "resident_capacity_turn_effect", year, turn_index, "success", "resident",
                    "25年間の防災訓練の効果が出ています",
                    "25年間の避難訓練・防災訓練により、洪水時にどう行動すればよいかを理解している住民が増えています。洪水による被害を軽減しやすい状態になってきました。",
                    related_policy="capacity_building_cost", metric="Resident capacity",
                    value=resident_capacity, threshold=turn_effect_threshold, once=False, cooldown_years=25)
    if resident_capacity >= near_cap_threshold:
        _emit_event(events, events_state, "resident_capacity_near_cap", year, turn_index, "success", "resident",
                    "防災訓練の効果が上限に近づいています",
                    "継続的な防災訓練により、住民の災害対応力がほぼ上限に達しました。これ以上の追加投資では、効果の伸びは小さくなっていきます。",
                    related_policy="capacity_building_cost", metric="Resident capacity",
                    value=resident_capacity, threshold=near_cap_threshold, once=True)
    if False and resident_capacity >= thresholds.get("resident_capacity_high_threshold", 0.5):
        _emit_event(events, events_state, "resident_capacity_high", year, turn_index, "success", "resident",
                    "住民の防災対応力が高い水準に到達しました", "継続的な避難訓練・防災訓練により、住民の災害対応力が高まっています。",
                    related_policy="capacity_building_cost", metric="Resident capacity", value=resident_capacity, threshold=thresholds.get("resident_capacity_high_threshold", 0.5), once=True)
    elif False and resident_capacity >= thresholds.get("resident_capacity_threshold", 0.3):
        _emit_event(events, events_state, "resident_capacity_improved", year, turn_index, "success", "resident",
                    "住民の防災対応力が向上しました", "避難訓練・防災訓練により、小〜中規模洪水での被害軽減効果が期待できます。",
                    related_policy="capacity_building_cost", metric="Resident capacity", value=resident_capacity, threshold=thresholds.get("resident_capacity_threshold", 0.3), once=False, cooldown_years=25)

    has_t2_major_flood = any(
        (str(key).startswith("major_flood_damage_") or str(key).startswith("severe_flood_damage_"))
        and 2051 <= int(value) <= 2075
        for key, value in events_state.items()
        if str(value).isdigit()
    )
    if year == start_year + params.get("TURN_YEARS", 25) * 2 - 1:
        if resident_capacity < thresholds.get("resident_capacity_low_threshold", 0.10):
            _emit_event(
                events, events_state, "resident_capacity_low_turn2_summary", year, turn_index, "warning", "resident",
                "住民の防災対応力が低い状態です",
                (
                    f"大きな洪水被害が発生した一方で、住民の防災対応力は{resident_capacity:.2f}にとどまっています。"
                    "防災訓練は小〜中規模洪水での被害軽減に効くため、次の25年での投資候補になります。"
                ),
                related_policy="capacity_building_cost", metric="resident_capacity", value=resident_capacity,
                threshold=thresholds.get("resident_capacity_low_threshold", 0.10), once=True,
                group="damage_or_decline"
            )

        if risky_house_total >= thresholds.get("high_risk_houses_high_threshold", 8_500):
            _emit_event(
                events, events_state, "high_risk_houses_unmanaged_turn2_summary", year, turn_index, "warning", "resident",
                "高リスク住宅が多く残っています",
                (
                    f"大きな洪水被害が発生した一方で、高リスク住宅が約{risky_house_total:,.0f}戸残っています。"
                    "住宅移転は洪水被害を直接下げますが、将来のインフラ維持費とのトレードオフがあります。"
                ),
                related_policy="house_migration_amount", metric="risky_house_total", value=risky_house_total,
                threshold=thresholds.get("high_risk_houses_high_threshold", 8_500), once=True,
                group="damage_or_decline"
            )
    forest_low = (
        year - start_year >= thresholds.get("forest_area_low_after_years", 50)
        and current_forest_area <= thresholds.get("forest_area_low_threshold_ha", 2_900)
    )
    if forest_low:
        _emit_event(events, events_state, "forest_area_low", year, turn_index, "warning", "ecosystem",
                    "森林面積が低下しています",
                    "森林面積が低下し、保水力・流出抑制・生態系指標への長期的な支えが弱くなっています。森林保全は効果発現に時間がかかりますが、十分に続けるとこの閾値を避けやすくなります。",
                    related_policy="planting_trees_amount", metric="Forest Area", value=current_forest_area,
                    threshold=thresholds.get("forest_area_low_threshold_ha", 2_900), once=True)

    no_capacity_policy = policy_mana.get("capacity_building_cost", 0.0) <= 0
    if (
        no_capacity_policy
        and year - start_year >= thresholds.get("resident_capacity_low_after_years", 25)
        and resident_capacity <= thresholds.get("resident_capacity_low_threshold", 0.10)
    ):
        _emit_event(events, events_state, "resident_capacity_low", year, turn_index, "warning", "resident",
                    "住民の防災対応力が低い状態です",
                    "避難訓練・防災訓練が不足しているため、洪水時の初動対応力が低いままです。防災訓練への投資を検討してください。",
                    related_policy="capacity_building_cost", metric="Resident capacity", value=resident_capacity,
                    threshold=thresholds.get("resident_capacity_low_threshold", 0.10), once=True,
                    group="damage_or_decline")
    no_migration_policy = policy_mana.get("house_migration_amount", 0.0) <= 0
    if (
        no_migration_policy
        and year - start_year >= thresholds.get("high_risk_houses_high_after_years", 25)
        and risky_house_total >= thresholds.get("high_risk_houses_high_threshold", 9_000)
    ):
        _emit_event(events, events_state, "high_risk_houses_unmanaged", year, turn_index, "warning", "resident",
                    "高リスク住宅が多く残っています",
                    "浸水リスクの高い住宅が多く残っています。住宅移転は将来の維持費とのトレードオフがありますが、直接的に被害を下げます。",
                    related_policy="house_migration_amount", metric="risky_house_total", value=risky_house_total,
                    threshold=thresholds.get("high_risk_houses_high_threshold", 9_000), once=True,
                    group="damage_or_decline")
    # forest_policy_needed は forest_area_low と意味が重複するため、通常イベントとしては出さない。
    # 森林保全の必要性は forest_area_low の本文で伝える。
    if False:
        no_forest_policy = policy_mana.get("planting_trees_amount", 0.0) <= 0
        if (
            no_forest_policy
            and year - start_year >= thresholds.get("forest_area_low_after_years", 25)
            and current_forest_area <= thresholds.get("forest_area_low_threshold_ha", 3_100)
        ):
            _emit_event(events, events_state, "forest_policy_needed", year, turn_index, "warning", "ecosystem",
                        "森林保全の遅れが目立っています",
                        "森林面積が低下し、保水力と生態系指標の下支えが弱まっています。森林保全は効果に時間がかかるため、早めの継続投資が重要です。",
                        related_policy="planting_trees_amount", metric="Forest Area", value=current_forest_area,
                        threshold=thresholds.get("forest_area_low_threshold_ha", 3_100), once=True,
                        group="damage_or_decline")

    outputs = {
        'Year': year,
        'Temperature (℃)': temp,
        'Temperature (°C)': temp,
        'Precipitation (mm)': precip,
        'available_water': available_water,
        'Crop Yield': current_crop_yield,
        'Heat-only Crop Yield': heat_adjusted_crop_yield,
        'Municipal Demand': current_municipal_demand,
        'Flood Damage': current_flood_damage,
        'Flood Damage JPY': current_flood_damage_jpy,
        'Baseline Flood Damage JPY': baseline_flood_damage_jpy,
        'Flood Damage Reduced JPY': max(0.0, baseline_flood_damage_jpy - current_flood_damage_jpy),
        'Levee Level': current_levee_level,
        'High Temp Tolerance Level': high_temp_tolerance_level,
        'Hot Days': hot_days,
        'Extreme Precip Frequency': extreme_precip_events,
        'Extreme Precip Events': max_rain,
        'Max Overflow': max_overflow,
        'Ecosystem Level': ecosystem_level,
        'Baseline Crop Yield': baseline_crop_yield,
        'Baseline Ecosystem Level': baseline_ecosystem_level,
        'Municipal Cost': municipal_cost, # resident_burdenと重複
        'Urban Level': urban_level,
        'Resident Burden': resident_burden,
        'Paddy Dam Level': paddy_dam_level,
        'Levee investment total': levee_investment_total,
        'RnD investment total': RnD_investment_total,
        'Resident capacity': resident_capacity,
        'Forest Area': current_forest_area,
        'planting_history': planting_history,
        'risky_house_total': risky_house_total,
        'non_risky_house_total': non_risky_house_total,
        'transportation_level' : transportation_level,
        'paddy_dam_area' : paddy_dam_area,
        'cumulative_migrated_houses': cumulative_migrated_houses,
        'cumulative_house_migration_mana': cumulative_house_migration_mana,
        'cumulative_planting_mana': cumulative_planting_mana,
        'cumulative_agricultural_RnD_mana': cumulative_agricultural_RnD_mana,
        'cumulative_defense_mana': cumulative_defense_mana,
        'initial_risky_house_total': initial_risky_house_total,
        'initial_crop_yield': initial_crop_yield,
        'Events': events,
        'events': events,
        'events_state': events_state,
        **budget_components,
        # 'CO2 Absorbed': co2_absorbed,
        # 意思決定変数そのものをログとして保持
        'planting_trees_amount': planting_trees_amount,
        'house_migration_amount': house_migration_amount,
        'dam_levee_construction_cost': dam_levee_construction_cost,
        'paddy_dam_construction_cost': paddy_dam_construction_cost,
        'capacity_building_cost': capacity_building_cost,
        'agricultural_RnD_cost': agricultural_RnD_cost,
        'transportation_invest': transportation_invest,
        'flow_irrigation_level': flow_irrigation_level,
        'policy_mana': policy_mana,
        'planting_trees_mana': policy_mana.get('planting_trees_amount', 0.0),
        'house_migration_mana': policy_mana.get('house_migration_amount', 0.0),
        'dam_levee_mana': policy_mana.get('dam_levee_construction_cost', 0.0),
        'paddy_dam_mana': policy_mana.get('paddy_dam_construction_cost', 0.0),
        'capacity_building_mana': policy_mana.get('capacity_building_cost', 0.0),
        'agricultural_RnD_mana': policy_mana.get('agricultural_RnD_cost', 0.0),
    }

    current_values = {
        'temp': temp,
        'precip': precip,
        'municipal_demand': current_municipal_demand,
        'available_water': available_water,
        'crop_yield': current_crop_yield,
        'levee_level': current_levee_level,
        'high_temp_tolerance_level': high_temp_tolerance_level,
        'hot_days': hot_days,
        'extreme_precip_freq': extreme_precip_events,
        'ecosystem_level': ecosystem_level,
        'urban_level': urban_level,
        'levee_investment_total': levee_investment_total,
        'RnD_investment_total': RnD_investment_total,
        'forest_area': current_forest_area,
        'paddy_dam_area' : paddy_dam_area,
        'cumulative_migrated_houses': cumulative_migrated_houses,
        'cumulative_house_migration_mana': cumulative_house_migration_mana,
        'cumulative_planting_mana': cumulative_planting_mana,
        'cumulative_agricultural_RnD_mana': cumulative_agricultural_RnD_mana,
        'cumulative_defense_mana': cumulative_defense_mana,
        'initial_risky_house_total': initial_risky_house_total,
        'initial_crop_yield': initial_crop_yield,
        'events_state': events_state,
        'last_25y_avg_flood_damage_jpy': prev_values.get('last_25y_avg_flood_damage_jpy', 0.0),
        **budget_components,
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


def simulate_simulation(years, initial_values, decision_vars_list, params, fixed_seed=True):
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

        prev_values, outputs = simulate_year(
            year,
            prev_values,
            decision_vars,
            params,
            fixed_seed=fixed_seed
        )
        results.append(outputs)

    return results

def create_random_agent():
    """
    固定された年齢リストからエージェントを生成する
    """
    # 年齢のプリセット
    AGE_PRESETS = [12, 25, 45, 78]
    rng = random.SystemRandom()
    age = rng.choice(AGE_PRESETS)
    
    # 年齢に紐づいた詳細設定
    settings = {
        12: {"role": "小学生", "pronoun": "僕", "focus": "未来の地球"},
        25: {"role": "若手起業家", "pronoun": "私", "focus": "都市の利便性と持続可能性"},
        45: {"role": "市議会議員", "pronoun": "私", "focus": "予算効率と防災インフラ"},
        78: {"role": "隠居中の元農家", "pronoun": "わし", "focus": "日々の平穏と伝統的な田畑"}
    }
    
    selected = settings[age]
    return {
        "age": age,
        "role": selected["role"],
        "pronoun": selected["pronoun"],
        "focus_point": selected["focus"],
        "name": f"{selected['role']} ({age}歳)"
    }

def _number_from_row(row, keys, default=0.0):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default

def _average_value(rows, keys, default=0.0):
    if not rows:
        return default
    values = [_number_from_row(row, keys, default) for row in rows]
    return sum(values) / len(values)

def build_fallback_persona_commentary(agent, target_results, duration):
    last = target_results[-1]
    avg_flood = _average_value(target_results, ['Flood Damage'])
    avg_yield = _average_value(target_results, ['Crop Yield'])
    avg_ecosystem = _average_value(target_results, ['Ecosystem Level'])
    avg_burden = _average_value(target_results, ['Resident Burden'])
    avg_capacity = _average_value(target_results, ['Resident capacity', 'Resident Capacity'])
    last_flood = _number_from_row(last, ['Flood Damage'])
    last_yield = _number_from_row(last, ['Crop Yield'])
    last_ecosystem = _number_from_row(last, ['Ecosystem Level'])

    flood_view = (
        "洪水被害はかなり抑えられていて、生活や事業を続ける土台は残っていると感じます。"
        if avg_flood < 1_000_000 else
        "洪水被害の負担は無視できず、安心して暮らし続けるには追加の備えが必要だと感じます。"
    )
    food_view = (
        "収穫量は比較的安定していて、地域の食と仕事を支える力があります。"
        if avg_yield >= 3_500 else
        "収穫量の落ち込みが見えていて、農業や地域経済への影響が心配です。"
    )
    ecosystem_view = (
        "生態系の状態は良く、自然を活かした回復力が町の強みになっています。"
        if avg_ecosystem >= 70 else
        "生態系にはまだストレスがあり、自然の回復を待つだけでは不十分に見えます。"
    )

    return (
        f"{agent['pronoun']}は{agent['role']}として、この{duration}年分の結果をかなり現実的に受け止めました。"
        f"{flood_view}{food_view}{ecosystem_view}\n\n"
        #f"数値で見ると、期間平均の洪水被害は約{avg_flood:,.0f} USD、収穫量は約{avg_yield:,.0f}、"
        #f"生態系レベルは約{avg_ecosystem:.1f}、住民負担は約{avg_burden:,.0f} USDです。"
        #f"最後の年は洪水被害が約{last_flood:,.0f} USD、収穫量が約{last_yield:,.0f}、"
        #f"生態系レベルが{last_ecosystem:.1f}でした。\n\n"
        f"{agent['focus_point']}を重視する立場から見ると、この町は完全に安心とは言えない一方で、"
        f"政策の積み重ねによって暮らし続ける余地を残しています。特に住民の防災能力は平均{avg_capacity:.2f}で、"
        f"災害を受けた後に立て直す力をさらに育てることが次の課題です。"
        "市長への評価としては、厳しい環境の中で町を残した点は支持できますが、"
        "次の世代に渡すには、被害の抑制と生活負担の軽減をもう一段強めてほしいです。"
    )

def generate_ai_commentary(results):
    """
    指定されたペルソナが、85歳までの残り人生を全データから読み解く
    """
    agent = create_random_agent()
    age = agent['age']
    years_to_85 = 85 - age
    
    # 85歳までの期間（またはシミュレーション全期間）を抽出
    target_results = results[-years_to_85:] if len(results) > years_to_85 else results
    duration = len(target_results)

    # --- 全データの集計（outputsにある全項目を網羅） ---
    def avg(key): return sum(r[key] for r in target_results) / duration

    # AIに渡す情報の整理
    data_summary = {
        "気象・環境": {
            "気温": f"{avg('Temperature (℃)'):.1f}℃",
            "猛暑日": f"{avg('Hot Days'):.1f}日",
            "最大豪雨": f"{max(r['Extreme Precip Events'] for r in target_results):.1f}mm"
        },
        "インフラ・安全": {
            "堤防強度": f"{target_results[-1]['Levee Level']:.1f}",
            "住みやすさスコア": f"{avg('Urban Level'):.1f}/100",
            "直近の水害被害": f"{target_results[-1]['Flood Damage']:.1f} USD"
        },
        "経済・社会": {
            "住民負担": f"{avg('Resident Burden'):.1f} USD",
            "作物の収穫量": f"{avg('Crop Yield'):.1f}",
            "住民の防災意識": f"{avg('Resident capacity'):.2f}"
        },
        "自然資源": {
            "生態系スコア": f"{avg('Ecosystem Level'):.1f}/100",
            "森林面積": f"{avg('Forest Area'):.1f}ha"
        }
    }

    # --- ペルソナを徹底的に反映させたプロンプト ---
    prompt = f"""
    あなたは、この街に暮らす「{agent['role']}」として、自治体の政策によって変化した街の姿（シミュレーション結果）を厳しく、あるいは温かく講評してください。
    あなたは予算配分の内訳を知らされていません。目の前にある「数値」と「街の変化」だけが、あなたの判断材料です。

    ### 【あなたの設定：市民ペルソナ】
    - 名前・役職: {agent['role']}
    - 年齢: {age}歳（85歳まで残り{years_to_85}年）
    - 一人称: {agent['pronoun']}
    - 最優先の関心事: {agent['focus_point']}
    - 性格・口調: {age}歳にふさわしい話し方（例：小学生なら素直に、農家なら土の匂いがするような落ち着いた口調で）。

    ### 【分析対象：これからの{years_to_85}年間の平均データ】
    {data_summary}

    ### 【講評への指示】
    1. **自己紹介**: 最初の一文で「{agent['pronoun']}」を使い、自己紹介してください。
    2. **データの裏読み（重要）**: 
    - 「作物が減ったのは、暑さ対策を後回しにしたせいじゃないか？」「生態系が壊れたのは、コンクリートの壁（堤防）ばかり作ったからか？」など、**データの変化から、職員（プレイヤー）がどのような判断をしたのかを推測**して語ってください。
    3. **トレードオフへの言及**:
    - どこかが良くなってどこかが悪くなっている点（例：住みやすさは上がったが、住民負担も増えたなど）を、市民の生活実感として指摘してください。
    4. **人生の幸福度判断**: 自身の余命（85歳まで）を考えたとき、この街で暮らし続けることに希望が持てるか、総合的に判断してください。
    5. **文字数**: 180文字〜250文字程度。
    6. **市長への評価**: 最後の一文で、市長の「適応政策のセンス」をどの程度支持するか、ズバッと述べてください。

    ### 【出力イメージ】
    「{agent['pronoun']}はXXで働くXX。最近の街を見て思うんだが……（中略）……こんなに住民負担が増えてちゃ、孫の代までこの街に残れるか不安だよ。市長、あんたのやり方は少し~だね。」
    """

    try:
        response = ollama.chat(model='gemma4:e2b', messages=[
            {'role': 'system', 'content': f'あなたは{agent["role"]}です。{agent["focus_point"]}を重視して話してください。'},
            {'role': 'user', 'content': prompt},
        ])
        comment = response['message']['content']
    except Exception:
        comment = build_fallback_persona_commentary(agent, target_results, duration)

    return {
        "text": comment,
        "agent_name": agent['name'],
        "agent_role": agent['role'],
        "agent_focus": agent['focus_point'],
        "years_to_85": years_to_85
    }

