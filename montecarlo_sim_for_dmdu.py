# multiple_simulation.py (DMUU/PRIM-ready)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

import os
import numpy as np
import pandas as pd
from itertools import product

from backend.src.simulation import simulate_simulation
from backend.config import DEFAULT_PARAMS, rcp_climate_params

# =========================
# 設定
# =========================
np.random.seed(42)  # 再現性（必要に応じて外す）
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 期間（2025–2100）
START_YEAR = 2025
END_YEAR   = 2100
years = np.arange(START_YEAR, END_YEAR + 1)

# 意思決定の対象年（既存設計を踏襲）
decision_years = [2026, 2051, 2076]

# ★上から4つだけ使う（3^4 = 81ケース）
decision_items = [
    'planting_trees_amount',        # F
    'house_migration_amount',       # M
    'dam_levee_construction_cost',  # D
    'paddy_dam_construction_cost',  # P
    # 'agricultural_RnD_cost',        # R
    # 'capacity_building_cost',       # C
]
short_keys = {
    'planting_trees_amount':'F',
    'house_migration_amount':'M',
    'dam_levee_construction_cost':'D',
    'paddy_dam_construction_cost':'P',
    # 'agricultural_RnD_cost':'R',
    # 'capacity_building_cost':'C',
}

# 0/1/2 -> 実値マッピング（既存値を流用）
value_map = {
    'planting_trees_amount': [0, 75, 150],
    'house_migration_amount': [0, 50, 100],
    'dam_levee_construction_cost': [0.0, 1.0, 2.0],
    'paddy_dam_construction_cost': [0.0, 5.0, 10.0],
    # 'agricultural_RnD_cost': [0.0, 5.0, 10.0],
    # 'capacity_building_cost': [0.0, 5.0, 10.0],
}

# その他の投資は今回固定（0）
FIXED_DECISIONS = {
    'agricultural_RnD_cost': 0.0,
    'capacity_building_cost': 0.0, 
    'transportation_invest': 0.0,
}

# RCP設定とMonte Carlo回数
rcps = {'RCP2.6': 2.6, 'RCP6.0': 6.0}
num_simulations = 100

# 不確実性として揺らすパラメータ（各回で 0.5～2.0 を掛ける）
UNCERTAIN_PARAMS = [
    'temp_trend',
    'precip_uncertainty_trend',
    'extreme_precip_freq_trend',
    'extreme_precip_intensity_trend',
    'municipal_demand_trend',
    'flood_damage_coefficient',
    'paddy_dam_cost_per_ha',
    'forest_degradation_rate',
    'cost_per_migration',
]
LOW, HIGH = 0.5, 2.0

# 81シナリオ（3^4）
decision_levels = [0, 1, 2]
decision_combos = list(product(decision_levels, repeat=len(decision_items)))

def build_decision_df(level_tuple):
    """(0/1/2, ...) -> 年ごとの意思決定DataFrame(index=Year)"""
    df = pd.DataFrame({'Year': decision_years})
    for i, item in enumerate(decision_items):
        df[item] = [ value_map[item][ level_tuple[i] ] ] * len(decision_years)
    # 固定の意思決定を加える
    for k, v in FIXED_DECISIONS.items():
        df[k] = [v] * len(decision_years)
    return df.set_index('Year')

def label_from_levels(level_tuple):
    return ''.join(f"{short_keys[item]}{value_map[item][lvl]}" for item, lvl in zip(decision_items, level_tuple))

# 出力バッファ（年次パネル：PRIM向け）
panel_rows = []
# ついでの要約（世代平均・std）
summary_rows = []

# 世代区分
generations = {
    'Gen1': (2026, 2050),
    'Gen2': (2051, 2075),
    'Gen3': (2076, 2100),
}
indicators = ['Flood Damage', 'Ecosystem Level', 'Municipal Cost', 'Crop Yield']

# =========================
# 実行本体
# =========================
for combo_idx, level_tuple in enumerate(decision_combos):
    decision_df = build_decision_df(level_tuple)
    decision_label = label_from_levels(level_tuple)

    for rcp_name, rcp_val in rcps.items():
        # ベースパラメータ
        base_params = DEFAULT_PARAMS.copy()
        base_params.update(rcp_climate_params[rcp_val])

        # 年度の上書き（明示）
        base_params['start_year'] = START_YEAR
        base_params['end_year']   = END_YEAR

        # Monte Carlo
        for sim_id in range(num_simulations):
            # --- 不確実性のサンプリング ---
            mult = {p: np.random.uniform(LOW, HIGH) for p in UNCERTAIN_PARAMS}
            params = base_params.copy()
            for p, m in mult.items():
                if p in params:
                    params[p] = params[p] * m

            # 1ランのシミュレーション
            sim_data = simulate_simulation(years, {}, decision_df, params)
            df = pd.DataFrame(sim_data)

            # PRIM用に、決定と乗数も列として付与
            df['ScenarioID'] = combo_idx
            df['ScenarioLabel'] = decision_label
            df['RCP'] = rcp_name
            df['Sim'] = sim_id

            # 意思決定の水準（整数 0/1/2）と実値も付与
            for i, item in enumerate(decision_items):
                df[f'{item}_level'] = level_tuple[i]
                df[f'{item}_value'] = value_map[item][level_tuple[i]]
            # 固定分
            for k, v in FIXED_DECISIONS.items():
                df[f'{k}_value'] = v

            # 不確実性乗数を付与
            for p in UNCERTAIN_PARAMS:
                df[f'unc_{p}'] = mult[p]

            # 主要4指標だけのスリムCSVが欲しければここで選択
            panel_rows.append(df[['ScenarioID','ScenarioLabel','RCP','Sim','Year',
                                  'Flood Damage','Ecosystem Level','Municipal Cost','Crop Yield'] +
                                 [f'{it}_level' for it in decision_items] +
                                 [f'{it}_value' for it in decision_items] +
                                 [f'{k}_value' for k in FIXED_DECISIONS.keys()] +
                                 [f'unc_{p}' for p in UNCERTAIN_PARAMS]
                                 ])

        # ---- 世代別の集計（各シナリオ×RCPで100回の平均・標準偏差）----
        # 直前に積んだ 100 run だけをまとめても良いが、簡潔にやるため後で panel から集計する
        # （下で一括集計するのでここではスキップ）
        pass

# =========================
# CSV書き出し
# =========================
panel_df = pd.concat(panel_rows, ignore_index=True)
panel_path = OUTPUT_DIR / "dmdu_panel_4option_1scenario.csv"
panel_df.to_csv(panel_path, index=False)

# 要約（各 Scenario×RCP×Sim の世代平均→それをさらにSim方向に平均/標準偏差）
def summarize_generations(gdf):
    out = {}
    for glabel, (s, e) in generations.items():
        mask = (gdf['Year'] >= s) & (gdf['Year'] <= e)
        for ind in indicators:
            vals = gdf.loc[mask, ind].mean()
            out[f'{ind}_{glabel}'] = vals
    return pd.Series(out)

# まず Scenario×RCP×Sim の世代平均
sim_level = (panel_df
             .groupby(['ScenarioID','ScenarioLabel','RCP','Sim'], as_index=False)
             .apply(summarize_generations))

# 次に Scenario×RCP で平均・標準偏差
def agg_mean_std(df, col):
    return pd.Series({f'{col}': df[col].mean(), f'{col}_std': df[col].std()})

agg_parts = []
for (sid, slabel, rcp), g in sim_level.groupby(['ScenarioID','ScenarioLabel','RCP']):
    row = {'ScenarioID': sid, 'ScenarioLabel': slabel, 'RCP': rcp}
    for ind in indicators:
        for glabel in generations.keys():
            col = f'{ind}_{glabel}'
            stats = agg_mean_std(g, col)
            row.update(stats.to_dict())
    # 決定の水準・値（代表として最初の行から）
    first = panel_df[(panel_df['ScenarioID']==sid) & (panel_df['RCP']==rcp)].iloc[0]
    for it in decision_items:
        row[f'{it}_level'] = int(first[f'{it}_level'])
        row[f'{it}_value'] = float(first[f'{it}_value'])
    agg_parts.append(row)

summary_df = pd.DataFrame(agg_parts)
summary_path = OUTPUT_DIR / "dmdu_summary_4option_1scinario.csv"
summary_df.to_csv(summary_path, index=False)

print(f"[OK] Saved panel:   {panel_path}")
print(f"[OK] Saved summary: {summary_path}")
