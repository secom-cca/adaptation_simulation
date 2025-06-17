import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from backend.src.simulation import simulate_simulation
from backend.config import DEFAULT_PARAMS, rcp_climate_params
import seaborn as sns
import matplotlib.pyplot as plt

# 設定
timestep_year = 25
start_year = DEFAULT_PARAMS['start_year']
end_year = DEFAULT_PARAMS['end_year']
years = np.arange(start_year, end_year + 1)

# 意思決定例（手動で1つ指定）
decision_df = pd.DataFrame({
    'Year': [2026, 2051, 2076],
    # 'planting_trees_amount': [100, 100, 100],
    # 'house_migration_amount': [100, 100, 100],
    # 'dam_levee_construction_cost': [2.0, 2.0, 2.0],
    # 'paddy_dam_construction_cost': [10.0, 10.0, 10.0],
    # 'capacity_building_cost': [10.0, 10.0, 10.0],
    # 'agricultural_RnD_cost': [10.0, 10.0, 10.0],
    # 'transportation_invest': [10.0, 10.0, 10.0],
    'planting_trees_amount': [50, 50, 50],
    # 'house_migration_amount': [50, 50, 50],
    # 'dam_levee_construction_cost': [1.0, 1.0, 1.0],
    # 'paddy_dam_construction_cost': [5.0, 5.0, 5.0],
    # 'capacity_building_cost': [5.0, 5.0, 5.0],
    # 'agricultural_RnD_cost': [5.0, 5.0, 5.0],
    # 'transportation_invest': [5.0, 5.0, 5.0],
    # 'planting_trees_amount': [0, 0, 0],
    'house_migration_amount': [0, 0, 0],
    'dam_levee_construction_cost': [0.0, 0.0, 0.0],
    'paddy_dam_construction_cost': [0.0, 0.0, 0.0],
    'capacity_building_cost': [0.0, 0.0, 0.0],
    'agricultural_RnD_cost': [0.0, 0.0, 0.0],
    'transportation_invest': [0.0, 0.0, 0.0],
}).set_index('Year')

# RCPごとにシミュレーションを実行
rcps = {'RCP1.9': 1.9, 'RCP2.6': 2.6, 'RCP4.5': 4.5, 'RCP6.0': 6.0, 'RCP8.5': 8.5}
num_simulations = 100  # モンテカルロ回数

results = []

for rcp_name, rcp_val in rcps.items():
    params = DEFAULT_PARAMS.copy()
    params.update(rcp_climate_params[rcp_val])

    for sim in range(num_simulations):
        initial_values = {}
        sim_data = simulate_simulation(years, initial_values, decision_df, params)
        df = pd.DataFrame(sim_data)
        df['Simulation'] = sim
        df['RCP'] = rcp_name
        results.append(df)

df_all = pd.concat(results)

# def plot_indicator(df, indicator): #, ci=95):
#     plt.figure(figsize=(10, 6))
#     sns.lineplot(
#         data=df,
#         x='Year',
#         y=indicator,
#         hue='RCP',
#         estimator='mean',
#         errorbar='sd',  # or use ('ci', ci) for standard deviation
#         n_boot=100,  # optional for bootstrapped CI
#         err_style='band'
#     )

#     plt.title(f'{indicator} Over Time')
#     plt.xlabel('Year')
#     plt.ylabel(indicator)
#     plt.legend(title='RCP')
#     plt.grid(True)
#     plt.tight_layout()
#     plt.show()

# plot_indicator(df_all, 'Crop Yield')
# plot_indicator(df_all, 'Flood Damage')
# plot_indicator(df_all, 'Ecosystem Level')
# plot_indicator(df_all, 'Resident Burden')
# # plot_indicator(df_all, 'Forest Area')

# # --- 2x2サブプロットで図を描画・保存 ---
# indicators = ['Flood Damage', 'Ecosystem Level']
# fig, axes = plt.subplots(1, 2, figsize=(16, 4))

# for idx, indicator in enumerate(indicators):
#     sns.lineplot(
#         data=df_all,
#         x='Year',
#         y=indicator,
#         hue='RCP',
#         estimator='mean',
#         errorbar='sd',
#         n_boot=100,
#         ax=axes[idx]
#     )
#     axes[idx].set_title(f'{indicator} Over Time')
#     axes[idx].set_xlabel('Year')
#     axes[idx].set_ylabel(indicator)
#     axes[idx].grid(True)

# handles, labels = axes[0].get_legend_handles_labels()
# plt.savefig('flood_ecosystem_rcp_results_0.png', bbox_inches='tight')
# plt.show()

# # --- 実データ範囲で誤差帯を描画する関数 ---
# def plot_with_min_max(ax, df, indicator):
#     grouped = df.groupby(['RCP', 'Year'])[indicator]
#     summary = grouped.agg(['mean', 'min', 'max']).reset_index()

#     for rcp in summary['RCP'].unique():
#         df_rcp = summary[summary['RCP'] == rcp]
#         ax.plot(df_rcp['Year'], df_rcp['mean'], label=rcp)
#         ax.fill_between(df_rcp['Year'], df_rcp['min'], df_rcp['max'], alpha=0.2)

#     ax.set_title(f'{indicator} Over Time')
#     ax.set_xlabel('Year')
#     ax.set_ylabel(indicator)
#     ax.grid(True)

# # --- 描画・保存（1×2, 凡例は右） ---
# indicators = ['Flood Damage', 'Ecosystem Level']
# fig, axes = plt.subplots(1, 2, figsize=(16, 4), sharex=True)

# for i, indicator in enumerate(indicators):
#     plot_with_min_max(axes[i], df_all, indicator)

# # 凡例を右に
# handles, labels = axes[0].get_legend_handles_labels()
# fig.legend(handles, labels, loc='center left', bbox_to_anchor=(1.01, 0.5), title='RCP')

# plt.savefig('flood_ecosystem_minmax.png', bbox_inches='tight')
# plt.show()

# --- IQRで可視化する関数 ---
def plot_with_iqr(ax, df, indicator):
    grouped = df.groupby(['RCP', 'Year'])[indicator]
    summary = grouped.agg([
        ('median', 'median'),
        ('q1', lambda x: np.percentile(x, 10)),
        ('q3', lambda x: np.percentile(x, 90))
    ]).reset_index()

    for rcp in summary['RCP'].unique():
        df_rcp = summary[summary['RCP'] == rcp]
        ax.plot(df_rcp['Year'], df_rcp['median'], label=rcp)
        ax.fill_between(df_rcp['Year'], df_rcp['q1'], df_rcp['q3'], alpha=0.2)

    ax.set_title(f'{indicator} (Median with 10-90 percentile)')
    ax.set_xlabel('Year')
    ax.set_ylabel(indicator)
    ax.grid(True)
    if indicator == 'Flood Damage':
        ax.set_ylim(0, 2e8)
        ax.legend(loc='upper left')
    elif indicator == 'Ecosystem Level':
        ax.set_ylim(0, 100)
        ax.legend(loc='lower left')

# --- 描画・保存（1×2, 凡例右） ---
indicators = ['Flood Damage', 'Ecosystem Level']
fig, axes = plt.subplots(1, 2, figsize=(16, 4.5), sharex=True)

for i, indicator in enumerate(indicators):
    plot_with_iqr(axes[i], df_all, indicator)

plt.savefig('flood_ecosystem_F.png', bbox_inches='tight')
plt.show()