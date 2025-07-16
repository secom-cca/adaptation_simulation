import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from itertools import product
from backend.src.simulation import simulate_simulation
from backend.config import DEFAULT_PARAMS, rcp_climate_params
from adjustText import adjust_text

# パラメータ設定
timestep_year = 25
start_year = DEFAULT_PARAMS['start_year']
end_year = DEFAULT_PARAMS['end_year']
years = np.arange(start_year, end_year + 1)

# 意思決定の対象年
decision_years = [2026, 2051, 2076]

# 意思決定の対象項目
decision_items = [
    'planting_trees_amount',
    'house_migration_amount',
    'dam_levee_construction_cost',
    'paddy_dam_construction_cost',
    'agricultural_RnD_cost',
    'capacity_building_cost'
]

# 意思決定の値（0, 1, 2 → 実際の値へ変換する）
decision_levels = [0, 1, 2]
value_map = {
    'planting_trees_amount': [0, 75, 150],
    'house_migration_amount': [0, 50, 100],
    'dam_levee_construction_cost': [0.0, 1.0, 2.0],
    'paddy_dam_construction_cost': [0.0, 5.0, 10.0],
    'agricultural_RnD_cost': [0.0, 5.0, 10.0],
    'capacity_building_cost': [0.0, 5.0, 10.0],
}

# decision_levels = [0, 1]
# value_map = {
#     'planting_trees_amount': [0, 150],
#     'house_migration_amount': [0, 100],
#     'dam_levee_construction_cost': [0.0, 2.0],
#     'capacity_building_cost': [0.0, 10.0],
# }


# RCP設定とMonte Carlo回数
rcps = {'RCP1.9': 1.9, 'RCP8.5': 8.5} # 'RCP2.6': 2.6, 'RCP4.5': 4.5, 'RCP6.0': 6.0, 
num_simulations = 5  # 本番では50や100に上げると良い

decision_combos = list(product(decision_levels, repeat=len(decision_items)))

# 結果を集めるリスト
summary_results = []

for combo_idx, decision_values in enumerate(decision_combos):
    decision_df = pd.DataFrame({'Year': decision_years})
    for i, item in enumerate(decision_items):
        mapped_values = [value_map[item][decision_values[i]]] * len(decision_years)
        decision_df[item] = mapped_values
    # decision_df['agricultural_RnD_cost'] = [0.0] * len(decision_years)
    decision_df['transportation_invest'] = [0.0] * len(decision_years)
    decision_df = decision_df.set_index('Year')

    for rcp_name, rcp_val in rcps.items():
        params = DEFAULT_PARAMS.copy()
        params.update(rcp_climate_params[rcp_val])

        sim_results = []
        for _ in range(num_simulations):
            sim_data = simulate_simulation(years, {}, decision_df, params)
            df = pd.DataFrame(sim_data)
            sim_results.append(df)

        generations = {
            'Gen1': (2026, 2050),
            'Gen2': (2051, 2075),
            'Gen3': (2076, 2100),
        }

        # indicators = ['Flood Damage', 'Ecosystem Level', 'Municipal Cost', 'Crop Yield']
        indicators = ['Flood Damage', 'Ecosystem Level', 'Municipal Cost']
        avg_data = {'Decision_ID': combo_idx, 'RCP': rcp_name}

        df_all = pd.concat(sim_results, keys=range(num_simulations), names=["Sim", "Row"])
        for gen_label, (start, end) in generations.items():
            df_gen = df_all[(df_all['Year'] >= start) & (df_all['Year'] <= end)]
            for ind in indicators:
                mean = df_gen.groupby("Sim")[ind].mean()
                avg_data[f'{ind}_{gen_label}'] = mean.mean()
                avg_data[f'{ind}_{gen_label}_std'] = mean.std()

        summary_results.append(avg_data)

# DataFrameとして整形
summary_df = pd.DataFrame(summary_results)
# 各インプット項目の実値を列として追加
for i, item in enumerate(decision_items):
    summary_df[item] = summary_df['Decision_ID'].apply(
        lambda idx: value_map[item][decision_combos[idx][i]]
    )

def find_best_decisions(summary_df):
    results = []
    rcps = summary_df['RCP'].unique()

    for rcp in rcps:
        df_rcp = summary_df[summary_df['RCP'] == rcp].copy()

        # 指標を正規化
        for col in ['Flood Damage_Gen3', 'Ecosystem Level_Gen3', 'Municipal Cost_Gen3']:
            if 'Ecosystem' in col:
                df_rcp[col + '_norm'] = (df_rcp[col] - df_rcp[col].min()) / (df_rcp[col].max() - df_rcp[col].min())
            else:
                df_rcp[col + '_norm'] = 1 - (df_rcp[col] - df_rcp[col].min()) / (df_rcp[col].max() - df_rcp[col].min())

        # 総合スコア（重み付き合計でもよい）
        df_rcp['total_score'] = (
            df_rcp['Flood Damage_Gen3_norm']
            + df_rcp['Ecosystem Level_Gen3_norm']
            + df_rcp['Municipal Cost_Gen3_norm']
        )

        best_row = df_rcp.loc[df_rcp['total_score'].idxmax()]
        results.append(best_row)

    return pd.DataFrame(results)

# 実行
best_decisions = find_best_decisions(summary_df)

# 結果確認
print(best_decisions[['RCP', 'Decision_ID', 'Flood Damage_Gen3', 'Ecosystem Level_Gen3', 'Municipal Cost_Gen3']])

def is_dominated(sol, others):
    """solがothersに1つでも支配されていればTrue"""
    for _, other in others.iterrows():
        if (
            other['Flood Damage_Gen3'] <= sol['Flood Damage_Gen3']
            and other['Municipal Cost_Gen3'] <= sol['Municipal Cost_Gen3']
            and other['Ecosystem Level_Gen3'] >= sol['Ecosystem Level_Gen3']
            and (
                other['Flood Damage_Gen3'] < sol['Flood Damage_Gen3']
                or other['Municipal Cost_Gen3'] < sol['Municipal Cost_Gen3']
                or other['Ecosystem Level_Gen3'] > sol['Ecosystem Level_Gen3']
            )
        ):
            return True
    return False

def extract_pareto_front(summary_df):
    pareto_results = []

    for rcp in summary_df['RCP'].unique():
        df_rcp = summary_df[summary_df['RCP'] == rcp].copy()
        pareto_set = []

        for idx, sol in df_rcp.iterrows():
            others = df_rcp.drop(idx)
            if not is_dominated(sol, others):
                pareto_set.append(sol)

        pareto_df = pd.DataFrame(pareto_set)
        pareto_df['RCP'] = rcp
        pareto_results.append(pareto_df)

    return pd.concat(pareto_results, ignore_index=True)

pareto_df = extract_pareto_front(summary_df)

# パレートフロント結果を表示
print(pareto_df[['RCP', 'Decision_ID', 'Flood Damage_Gen3', 'Ecosystem Level_Gen3', 'Municipal Cost_Gen3']])

# 指標列の定義
gen_cols = {
    'Flood Damage': ['Flood Damage_Gen1', 'Flood Damage_Gen2', 'Flood Damage_Gen3'],
    'Municipal Cost': ['Municipal Cost_Gen1', 'Municipal Cost_Gen2', 'Municipal Cost_Gen3'],
    'Ecosystem Level': ['Ecosystem Level_Gen1', 'Ecosystem Level_Gen2', 'Ecosystem Level_Gen3'],
}

short_keys = {
    'planting_trees_amount': 'F',
    'house_migration_amount': 'M',
    'dam_levee_construction_cost': 'D',
    'paddy_dam_construction_cost': 'P',
    'agricultural_RnD_cost': 'R',
    'capacity_building_cost': 'C',
}

def compact_decision_label(decision_id):
    values = decision_combos[decision_id]
    label = ''
    for i, item in enumerate(decision_items):
        key = short_keys[item]
        val = value_map[item][values[i]]
        label += f"{key}{int(val) if val == int(val) else val}"
    return label

summary_df['Decision_Label'] = summary_df['Decision_ID'].apply(compact_decision_label)
pareto_df['Decision_Label'] = pareto_df['Decision_ID'].apply(compact_decision_label)

def decision_id_to_label(decision_id):
    combo = decision_combos[decision_id]
    return ''.join(str(d) for d in combo)

summary_df['Decision_Label'] = summary_df['Decision_ID'].apply(decision_id_to_label)
pareto_df['Decision_Label'] = pareto_df['Decision_ID'].apply(decision_id_to_label)

summary_df.to_csv('output/summary_results.csv', index=False)

# パレート判定関数（Flood Damage, Cost 小 / Ecosystem 大）
def extract_gen_pareto(df, gen_idx):
    gen_df = df.copy()
    cols = [
        gen_cols['Flood Damage'][gen_idx],
        gen_cols['Municipal Cost'][gen_idx],
        gen_cols['Ecosystem Level'][gen_idx],
        # gen_cols['Crop Yield'][gen_idx],
    ]
    gen_df = gen_df[cols + ['Decision_ID']].rename(columns={
        cols[0]: 'FD', cols[1]: 'Cost', cols[2]: 'Eco', cols[3]: 'Crop'
    })
    
    pareto_mask = []
    for i, row in gen_df.iterrows():
        dominated = False
        for j, other in gen_df.iterrows():
            if (
                other['FD'] <= row['FD'] and
                other['Cost'] <= row['Cost'] and
                other['Eco'] >= row['Eco'] and
                # other['Crop'] >= row['Crop'] and
                # (other['FD'] < row['FD'] or other['Cost'] < row['Cost'] or other['Eco'] > row['Eco'] or other['Crop'] > row['Crop'])
                (other['FD'] < row['FD'] or other['Cost'] < row['Cost'] or other['Eco'] > row['Eco'])
            ):
                dominated = True
                break
        pareto_mask.append(not dominated)
    return gen_df[pareto_mask]['Decision_ID'].tolist()

# # 描画
# for rcp in summary_df['RCP'].unique():
#     df = summary_df[summary_df['RCP'] == rcp]

#     # 世代ごとのパレートフロント取得
#     pareto_ids_by_gen = {
#         f'Gen{i+1}': extract_gen_pareto(df, i)
#         for i in range(3)
#     }

#     plt.figure(figsize=(10, 8))
#     plt.title(f'Trade-off Trajectories Across Generations (All) - {rcp}')
#     plt.xlabel('Flood Damage')
#     plt.ylabel('Ecosystem Level')
#     plt.grid(True)

#     for _, row in df.iterrows():
#         x_vals = [row[col] for col in gen_cols['Flood Damage']]
#         y_vals = [row[col] for col in gen_cols['Ecosystem Level']]
#         costs_vals = [row[col] for col in gen_cols['Municipal Cost']]

#         # 各世代の点をプロット（コストを色に）
#         for i in range(3):
#             color_value = (costs_vals[i] - df[gen_cols['Municipal Cost'][i]].min()) / \
#                           (df[gen_cols['Municipal Cost'][i]].max() - df[gen_cols['Municipal Cost'][i]].min() + 1e-6)
#             color = plt.cm.viridis(color_value)
#             marker_edge = 'red' if row['Decision_ID'] in pareto_ids_by_gen[f'Gen{i+1}'] else 'none'
#             sc = plt.scatter(x_vals[i], y_vals[i], color=color, s=60, edgecolors=marker_edge, linewidths=1.2, zorder=3)

#         # 矢印で軌跡を可視化
#         for i in range(2):
#             plt.arrow(
#                 x_vals[i], y_vals[i],
#                 x_vals[i+1] - x_vals[i],
#                 y_vals[i+1] - y_vals[i],
#                 head_width=0.2, head_length=0.2, fc='gray', ec='gray', alpha=0.3
#             )

#     # カラーバー（Municipal Cost）
#         # ✅ カラーバーに scatter (sc) を明示的に渡す
#     cbar = plt.colorbar(sc, label='Municipal Cost')

#     # sm = plt.cm.ScalarMappable(cmap='viridis',
#     #                            norm=plt.Normalize(vmin=df[gen_cols['Municipal Cost'][2]].min(),
#     #                                               vmax=df[gen_cols['Municipal Cost'][2]].max()))
#     # sm.set_array([])
#     # cbar = plt.colorbar(sm, label='Municipal Cost')

#     plt.tight_layout()
#     plt.show()

# ===========================================================
# for rcp in pareto_df['RCP'].unique():
#     df = pareto_df[pareto_df['RCP'] == rcp]

#     plt.figure(figsize=(10, 8))
#     plt.title(f'Trade-off Trajectories Across Generations (Pareto) - {rcp}')
#     plt.xlabel('Flood Damage')
#     plt.ylabel('Ecosystem Level')
#     plt.grid(True)

#     for _, row in df.iterrows():
#         # 各世代のX, Y座標
#         x_vals = [row[col] for col in gen_cols['Flood Damage']]
#         y_vals= [row[col] for col in gen_cols['Ecosystem Level']]
#         costs_vals = [row[col] for col in gen_cols['Municipal Cost']]

#         # 軌跡を矢印で描画
#         for i in range(2):
#             plt.arrow(
#                 x_vals[i], y_vals[i],
#                 x_vals[i+1] - x_vals[i],
#                 y_vals[i+1] - y_vals[i],
#                 head_width=0.2, head_length=0.2, fc='gray', ec='gray', alpha=0.7
#             )

#         # 始点にDecision_IDをラベルとして付ける
#         plt.text(x_vals[0], y_vals[0], str(row['Decision_ID']), fontsize=8, ha='right', va='bottom')

#     plt.tight_layout()
#     plt.show()

# ===========================================================
# for rcp in summary_df['RCP'].unique():
#     df = summary_df[summary_df['RCP'] == rcp]
#     plt.figure()
#     plt.scatter(df['Flood Damage_Gen3'], df['Municipal Cost_Gen3'], c=df['Ecosystem Level_Gen3'], cmap='viridis')
#     plt.colorbar(label='Ecosystem Level')
#     plt.xlabel('Flood Damage')
#     plt.ylabel('Municipal Cost')
#     plt.title(f'Tradespace - {rcp}')
#     plt.grid(True)
#     plt.tight_layout()
#     plt.show()

# ===============================================================================
import os
import matplotlib.pyplot as plt

# 保存フォルダの作成
os.makedirs('figures', exist_ok=True)

for rcp in summary_df['RCP'].unique():
    texts = []
    df = summary_df[summary_df['RCP'] == rcp]
    pareto = pareto_df[pareto_df['RCP'] == rcp]

    # パレート解にだけ赤縁、それ以外は縁なし
    df = df.copy()
    df['edgecolor'] = df['Decision_ID'].apply(lambda x: 'r' if x in pareto['Decision_ID'].values else 'none')

    # プロット
    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(
        df['Flood Damage_Gen3'], 
        df['Ecosystem Level_Gen3'], 
        c=df['Municipal Cost_Gen3'], 
        cmap='gray',
        s=100,
        edgecolors=df['edgecolor']
    )

    plt.colorbar(scatter, label='Municipal Cost (2076-2100)')
    plt.xlabel('Flood Damage (2076-2100)')
    plt.ylabel('Ecosystem Level (2076-2100)')
    plt.title(f'Tradespace Analysis at 2076–2100 - {rcp}')
    plt.grid(True)

    # for _, row in df.iterrows():
    #     texts.append(
    #         plt.text(
    #             row['Flood Damage_Gen3'], 
    #             row['Ecosystem Level_Gen3'], 
    #             str(row['Decision_Label']), 
    #             fontsize=8, 
    #             ha='right', 
    #             va='bottom'
    #         )
    #     )

    plt.errorbar(
        df['Flood Damage_Gen3'],
        df['Ecosystem Level_Gen3'],
        xerr=df['Flood Damage_Gen3_std'],
        yerr=df['Ecosystem Level_Gen3_std'],
        fmt='none',
        ecolor='gray',
        alpha=0.5,
        capsize=3
    )

    plt.tight_layout()
    # adjust_text(texts, only_move={'points': 'y', 'texts': 'y'}, arrowprops=dict(arrowstyle='-', color='gray'))

    # ファイル保存
    save_path = f'figures/tradespace_{rcp.replace(".", "_")}.png'
    plt.savefig(save_path, dpi=300)
    plt.close()


# for rcp in summary_df['RCP'].unique():
#     texts = []
#     df = summary_df[summary_df['RCP'] == rcp]
#     pareto = pareto_df[pareto_df['RCP'] == rcp]

#     # パレート解にだけ赤縁、それ以外は縁なし
#     df = df.copy()
#     df['edgecolor'] = df['Decision_ID'].apply(lambda x: 'r' if x in pareto['Decision_ID'].values else 'none')

#     # プロット
#     plt.figure(figsize=(8, 6))
#     scatter = plt.scatter(
#         df['Flood Damage_Gen3'], 
#         df['Crop Yield_Gen3'], 
#         c=df['Municipal Cost_Gen3'], 
#         cmap='gray',
#         s=100,
#         edgecolors=df['edgecolor']
#     )

#     plt.colorbar(scatter, label='Municipal Cost (2076-2100)')
#     plt.xlabel('Flood Damage (2076-2100)')
#     plt.ylabel('Crop Yield (2076-2100)')
#     plt.title(f'Tradespace Analysis at 2076–2100 - {rcp}')
#     plt.grid(True)

#     # for _, row in df.iterrows():
#     #     texts.append(
#     #         plt.text(
#     #             row['Flood Damage_Gen3'], 
#     #             row['Crop Yield_Gen3'], 
#     #             str(row['Decision_Label']), 
#     #             fontsize=8, 
#     #             ha='right', 
#     #             va='bottom'
#     #         )
#     #     )

#     plt.errorbar(
#         df['Flood Damage_Gen3'],
#         df['Crop Yield_Gen3'],
#         xerr=df['Flood Damage_Gen3_std'],
#         yerr=df['Crop Yield_Gen3_std'],
#         fmt='none',
#         ecolor='gray',
#         alpha=0.5,
#         capsize=3
#     )

#     plt.tight_layout()
#     # adjust_text(texts, only_move={'points': 'y', 'texts': 'y'}, arrowprops=dict(arrowstyle='-', color='gray'))

#     # ファイル保存
#     save_path = f'figures/tradespace_{rcp.replace(".", "_")}_2.png'
#     plt.savefig(save_path, dpi=300)
#     plt.close()

# ===============================================================================
# 異なるRCPのものを1つの図にしたもの
# ===============================================================================
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
from adjustText import adjust_text

# マーカーの定義
rcp_marker_map = {
    'RCP1.9': 'o',
    'RCP2.6': 'v',
    'RCP4.5': '^',
    'RCP6.0': 'D',
    'RCP8.5': 's',
}
used_rcps = summary_df['RCP'].unique()
markers = {rcp: rcp_marker_map.get(rcp, 'o') for rcp in used_rcps}

# 色スケーリング
vmin = summary_df['Municipal Cost_Gen3'].min()
vmax = summary_df['Municipal Cost_Gen3'].max()
norm = colors.Normalize(vmin=vmin, vmax=vmax)
cmap = cm.gray

plt.figure(figsize=(12, 8))
texts = []

# プロット本体
for rcp in used_rcps:
    df_rcp = summary_df[summary_df['RCP'] == rcp].copy()
    pareto_rcp = pareto_df[pareto_df['RCP'] == rcp]

    # 赤縁はパレートのみ、それ以外は黒縁
    df_rcp['edgecolor'] = df_rcp['Decision_ID'].apply(
        lambda x: 'r' if x in pareto_rcp['Decision_ID'].values else 'k'
    )

    scatter = plt.scatter(
        df_rcp['Flood Damage_Gen3'],
        df_rcp['Ecosystem Level_Gen3'],
        c=df_rcp['Municipal Cost_Gen3'],
        cmap=cmap,
        norm=norm,
        marker=markers[rcp],
        s=100,
        edgecolors=df_rcp['edgecolor'],
        alpha=0.8,
        label=f'{rcp}'
    )

    # エラーバー
    plt.errorbar(
        df_rcp['Flood Damage_Gen3'],
        df_rcp['Ecosystem Level_Gen3'],
        xerr=df_rcp['Flood Damage_Gen3_std'],
        yerr=df_rcp['Ecosystem Level_Gen3_std'],
        fmt='none',
        ecolor='gray',
        elinewidth=1,
        capsize=3,
        alpha=0.6
    )

    # ラベル
    # for _, row in df_rcp.iterrows():
    #     texts.append(
    #         plt.text(
    #             row['Flood Damage_Gen3'],
    #             row['Ecosystem Level_Gen3'],
    #             row['Decision_Label'],
    #             fontsize=8,
    #             ha='right',
    #             va='bottom'
    #         )
    #     )

# ラベル調整（重なり除去）
# adjust_text(texts, only_move={'points': 'y', 'texts': 'y'}, arrowprops=dict(arrowstyle='-', color='gray'))

# カラーバー
cbar = plt.colorbar(scatter, label='Municipal Cost', ax=plt.gca())

# 凡例（RCPごとの marker + 説明用パッチ）
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker=rcp_marker_map[rcp], color='w',
           markerfacecolor='gray', markeredgecolor='k', markersize=10, label=rcp)
    for rcp in used_rcps
] + [
    Line2D([0], [0], marker='o', color='w',
           markerfacecolor='white', markeredgecolor='r', markersize=10, label='Pareto Optimal')
]
plt.legend(handles=legend_elements, title='RCP & Pareto Status', loc='best')

# 軸ラベル・タイトル
plt.xlabel('Flood Damage (2076-2100)')
plt.ylabel('Ecosystem Level (2076-2100)')
plt.title('Tradespace with RCP Markers and Pareto Highlighting')
plt.grid(True)
plt.tight_layout()

# 保存
plt.savefig('figures/tradespace_allRCP_Gen3_pareto_edgecolor.png', dpi=300)
plt.close()



# ===============================================================================
import matplotlib.pyplot as plt

for rcp in summary_df['RCP'].unique():
    df_rcp = summary_df[summary_df['RCP'] == rcp]

    plt.figure(figsize=(10, 7))

    for _, row in df_rcp.iterrows():
        # 各Genの値を時系列順に並べる
        flood = [row['Flood Damage_Gen1'], row['Flood Damage_Gen2'], row['Flood Damage_Gen3']]
        eco = [row['Ecosystem Level_Gen1'], row['Ecosystem Level_Gen2'], row['Ecosystem Level_Gen3']]
        cost = row['Municipal Cost_Gen3']  # Gen3のコストで色付け
        label = row['Decision_Label']

        # 色は Gen3 の Municipal Cost を使用（正規化して colormap に渡す）
        norm = plt.Normalize(df_rcp['Municipal Cost_Gen3'].min(), df_rcp['Municipal Cost_Gen3'].max())
        color = plt.cm.viridis(norm(cost))

        # 線と点を描画
        plt.plot(flood, eco, color=color, alpha=0.6, marker='o', linewidth=1)
        plt.text(flood[-1], eco[-1], label, fontsize=8, ha='left', va='center')

    # 軸ラベル・色凡例など
    plt.xlabel('Flood Damage')
    plt.ylabel('Ecosystem Level')
    plt.title(f'Tradespace Evolution over Generations ({rcp})')

    sm = plt.cm.ScalarMappable(cmap='gray', norm=norm)
    sm.set_array([])
    plt.colorbar(sm, label='Municipal Cost', ax=plt.gca())

    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f'figures/tradespace_evolution_FEcolor_{rcp.replace(".", "_")}.png', dpi=300)
    plt.close()

# ===============================================================================


# from mpl_toolkits.mplot3d import Axes3D
# import matplotlib.pyplot as plt

# fig = plt.figure(figsize=(10, 8))
# ax = fig.add_subplot(111, projection='3d')

# ax.set_title('Policy Impact Trajectories Across Generations (Pareto Front)')
# ax.set_xlabel('Flood Damage')
# ax.set_ylabel('Municipal Cost')
# ax.set_zlabel('Ecosystem Level')

# for _, row in pareto_df.iterrows():
#     # 各世代の3軸データを取得
#     x_vals = [row['Flood Damage_Gen1'], row['Flood Damage_Gen2'], row['Flood Damage_Gen3']]
#     y_vals = [row['Municipal Cost_Gen1'], row['Municipal Cost_Gen2'], row['Municipal Cost_Gen3']]
#     z_vals = [row['Ecosystem Level_Gen1'], row['Ecosystem Level_Gen2'], row['Ecosystem Level_Gen3']]

#     # ラインプロットで各世代の推移を描画
#     ax.plot(x_vals, y_vals, z_vals, color='gray', alpha=0.7)
    
#     # 始点にラベル（Decision_ID）
#     ax.text(x_vals[0], y_vals[0], z_vals[0], str(row['Decision_ID']), fontsize=7)

# plt.tight_layout()
# plt.show()


# # ---------------------------------------------

# import seaborn as sns
# import matplotlib.pyplot as plt

# # 指標だけ抽出
# metrics_cols = [col for col in summary_df.columns if col not in ['Decision_ID', 'RCP']]
# df_pivot = summary_df[summary_df['RCP'] == 'RCP1.9']  # RCPを1つ選ぶ
# df_metrics = df_pivot.set_index('Decision_ID')[metrics_cols]

# # 正規化（各列を0-1に）
# df_normalized = (df_metrics - df_metrics.min()) / (df_metrics.max() - df_metrics.min())

# plt.figure(figsize=(12, 8))
# sns.heatmap(df_normalized, cmap="viridis")
# plt.title("Normalized Metrics by Decision ID (RCP4.5)")
# plt.xlabel("Indicator")
# plt.ylabel("Decision ID")
# plt.tight_layout()
# plt.show()

# # ---------------------------------------------
# df_tradeoff = df_normalized.copy()
# df_tradeoff['Decision_ID'] = df_metrics.index

# sns.pairplot(df_tradeoff, corner=True)
# plt.suptitle("Trade-offs between Metrics", y=1.02)
# plt.show()
