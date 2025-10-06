# multiple_simulation.py (base-only MC; includes climate & intermediate outputs)
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
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 期間（2025–2100）
START_YEAR = 2025
END_YEAR   = 2100
years = np.arange(START_YEAR, END_YEAR + 1)

# 意思決定の対象年
decision_years = [2026, 2051, 2076]

# 使う意思決定（3^4 = 81ケース）
decision_items = [
    'planting_trees_amount',        # F
    'house_migration_amount',       # M
    'dam_levee_construction_cost',  # D
    # 'paddy_dam_construction_cost',  # P
    'flow_irrigation_level', # I
]
short_keys = {
    'planting_trees_amount':'F',
    'house_migration_amount':'M',
    'dam_levee_construction_cost':'D',
    # 'paddy_dam_construction_cost':'P',
    'flow_irrigation_level': 'I',
}

# 0/1/2 -> 実値マッピング
value_map = {
    'planting_trees_amount': [0, 50, 100],
    'house_migration_amount': [0, 50, 100],
    'dam_levee_construction_cost': [0.0, 0.5, 1.0],
    # 'paddy_dam_construction_cost': [0.0, 10.0, 20.0],
    'flow_irrigation_level': [0.0, 150, 300],
}

# 固定（今回は 0）
FIXED_DECISIONS = {
    'agricultural_RnD_cost': 0.0,
    'capacity_building_cost': 0.0, 
    'transportation_invest': 0.0,
    'paddy_dam_construction_cost': 0.0
}

# RCP と Monte Carlo 回数（必要に応じて増減）
rcps = {'RCP1.9': 1.9, 'RCP2.6': 2.6, 'RCP4.5': 4.5, 'RCP6.0': 6.0, 'RCP8.5': 8.5}
num_simulations = 100

# 81シナリオ（3^4）
decision_levels = [0, 1, 2]
decision_combos = list(product(decision_levels, repeat=len(decision_items)))

def build_decision_df(level_tuple):
    """(0/1/2, ...) -> 年ごとの意思決定DataFrame(index=Year)"""
    df = pd.DataFrame({'Year': decision_years})
    for i, item in enumerate(decision_items):
        df[item] = [ value_map[item][ level_tuple[i] ] ] * len(decision_years)
    for k, v in FIXED_DECISIONS.items():
        df[k] = [v] * len(decision_years)
    return df.set_index('Year')

def label_from_levels(level_tuple):
    return ''.join(f"{short_keys[item]}{value_map[item][lvl]}" for item, lvl in zip(decision_items, level_tuple))

# ===== 出力カラムの指定 =====
# 主要4指標
core_cols = ['Flood Damage', 'Ecosystem Level', 'Municipal Cost', 'Crop Yield']

# 追加で出したい「気候・水・中間」指標
mid_cols = [
    'Temperature (℃)',
    'Precipitation (mm)',
    'Hot Days',
    'Extreme Precip Events',      # 年内のイベント回数
    'Extreme Precip Frequency',   # ※命名上やや冗長だが元の出力に合わせる
    'Municipal Demand',
    'available_water',
    'Levee Level',
    'Forest Area',
    'Resident capacity',
    'Urban Level',
    'paddy_dam_area',
    'Levee investment total',
    'RnD investment total',
]

# 世代区分
generations = {
    'Gen1': (2026, 2050),
    'Gen2': (2051, 2075),
    'Gen3': (2076, 2100),
}
indicators = core_cols  # 要約は主要4指標で実施

# =========================
# 実行本体
# =========================
panel_rows = []

for combo_idx, level_tuple in enumerate(decision_combos):
    decision_df = build_decision_df(level_tuple)
    decision_label = label_from_levels(level_tuple)

    for rcp_name, rcp_val in rcps.items():
        # ベースパラメータ
        base_params = DEFAULT_PARAMS.copy()
        base_params.update(rcp_climate_params[rcp_val])
        base_params['start_year'] = START_YEAR
        base_params['end_year']   = END_YEAR

        # Monte Carlo（★パラメータは変化させない：base_paramsのまま★）
        for sim_id in range(num_simulations):
            sim_data = simulate_simulation(years, {}, decision_df, base_params)
            df = pd.DataFrame(sim_data)

            # メタ情報
            df['ScenarioID'] = combo_idx
            df['ScenarioLabel'] = decision_label
            df['RCP'] = rcp_name
            df['Sim'] = sim_id

            # 意思決定の水準・実値（ラベル付け用）
            for i, item in enumerate(decision_items):
                df[f'{item}_level'] = level_tuple[i]
                df[f'{item}_value'] = value_map[item][level_tuple[i]]
            for k, v in FIXED_DECISIONS.items():
                df[f'{k}_value'] = v

            # 1本の行集合として保持（主要＋中間）
            keep_cols = ['ScenarioID','ScenarioLabel','RCP','Sim','Year'] + core_cols + mid_cols + \
                        [f'{it}_level' for it in decision_items] + \
                        [f'{it}_value' for it in decision_items] + \
                        [f'{k}_value' for k in FIXED_DECISIONS.keys()]
            # 存在する列だけ落とす（将来の見落とし対策）
            keep_cols = [c for c in keep_cols if c in df.columns or c in ['ScenarioID','ScenarioLabel','RCP','Sim','Year'] +
                         [f'{it}_level' for it in decision_items] + [f'{it}_value' for it in decision_items] +
                         [f'{k}_value' for k in FIXED_DECISIONS.keys()]]
            panel_rows.append(df[keep_cols])

# =========================
# CSV書き出し
# =========================
panel_df = pd.concat(panel_rows, ignore_index=True)

# panel_path = OUTPUT_DIR / "dmdu_panel_paddydam_251006.csv"
panel_path = OUTPUT_DIR / "dmdu_panel_irrigation_251006.csv"
panel_df.to_csv(panel_path, index=False)

# --- 世代要約（各 Scenario×RCP×Sim の平均 → さらに Sim 平均/標準偏差） ---
def summarize_generations(gdf):
    out = {}
    for glabel, (s, e) in generations.items():
        mask = (gdf['Year'] >= s) & (gdf['Year'] <= e)
        for ind in indicators:
            vals = gdf.loc[mask, ind].mean()
            out[f'{ind}_{glabel}'] = float(vals)
    return pd.Series(out)

sim_level = (panel_df
             .groupby(['ScenarioID','ScenarioLabel','RCP','Sim'], as_index=False)
             .apply(summarize_generations))

def agg_mean_std(df, col):
    return pd.Series({f'{col}': float(df[col].mean()), f'{col}_std': float(df[col].std())})

agg_parts = []
for (sid, slabel, rcp), g in sim_level.groupby(['ScenarioID','ScenarioLabel','RCP']):
    row = {'ScenarioID': sid, 'ScenarioLabel': slabel, 'RCP': rcp}
    for ind in indicators:
        for glabel in generations.keys():
            col = f'{ind}_{glabel}'
            stats = agg_mean_std(g, col)
            row.update(stats.to_dict())
    # 代表の意思決定水準・値（そのRCPの最初の行から）
    first = panel_df[(panel_df['ScenarioID']==sid) & (panel_df['RCP']==rcp)].iloc[0]
    for it in decision_items:
        row[f'{it}_level'] = int(first[f'{it}_level'])
        row[f'{it}_value'] = float(first[f'{it}_value'])
    agg_parts.append(row)

summary_df = pd.DataFrame(agg_parts)
# summary_path = OUTPUT_DIR / "dmdu_summary_paddydam_251006.csv"
summary_path = OUTPUT_DIR / "dmdu_summary_irrigation_251006.csv"
summary_df.to_csv(summary_path, index=False)

print(f"[OK] Saved panel:   {panel_path}")
print(f"[OK] Saved summary: {summary_path}")
