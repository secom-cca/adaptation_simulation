# 必要ライブラリ
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from backend.src.simulation import simulate_simulation
from backend.config import DEFAULT_PARAMS, rcp_climate_params
from backend.src.utils import BENCHMARK
import os
from itertools import product

# 保存先フォルダの作成
os.makedirs("fig", exist_ok=True)
os.makedirs("output", exist_ok=True)

# 固定RCPの設定
rcp_value = 8.5

# 基本設定
TIMESTEP_YEAR = 25
DECISION_STEPS = 3
DECISION_VARS = [
    'planting_trees_amount',
    'house_migration_amount',
    'dam_levee_construction_cost',
    # 'paddy_dam_construction_cost',
    'capacity_building_cost',
]
ACTION_LEVELS = [0, 2]

# 全通りの方策生成
all_policies = list(product(ACTION_LEVELS, repeat=len(DECISION_VARS) * DECISION_STEPS))

# パラメータ更新
years = DEFAULT_PARAMS['years']
start_year = DEFAULT_PARAMS['start_year']
params = DEFAULT_PARAMS.copy()
params.update(rcp_climate_params[rcp_value])

# 方策データフレーム作成関数
def policy_to_df(policy_flat):
    policy = np.array(policy_flat).reshape((DECISION_STEPS, len(DECISION_VARS)))
    years_idx = [start_year + TIMESTEP_YEAR*i for i in range(DECISION_STEPS)]
    return pd.DataFrame(policy, columns=DECISION_VARS, index=years_idx)

# 結果記録用
records = []
all_results = []

# =======================
# シミュレーションループ
# =======================
for i, policy_flat in enumerate(all_policies):
    decision_df = policy_to_df(policy_flat)
    print(i, policy_flat)

    try:
        sim_result = simulate_simulation(years, {}, decision_df, params)
        df_sim = pd.DataFrame(sim_result)
        df_sim['Policy_ID'] = i

        indicators = {
            # 'Yield': df_sim['Crop Yield'].sum(),
            'Flood Damage': df_sim['Flood Damage'].sum(),
            'Budget': df_sim['Municipal Cost'].sum(),
            'Ecosystem': df_sim.loc[df_sim['Year'] == df_sim['Year'].max(), 'Ecosystem Level'].values[0],
            # 'Urban Convenience': df_sim.loc[df_sim['Year'] == df_sim['Year'].max(), 'Urban Level'].values[0],
            # 'Forest Area': df_sim.loc[df_sim['Year'] == df_sim['Year'].max(), 'Forest Area'].values[0],
            'Resident Burden': df_sim['Resident Burden'].mean(),
            'RCP': rcp_value,
            'Policy_ID': i,
        }
        indicators.update({f'{var}_t{t+1}': policy_flat[t*len(DECISION_VARS)+j] for t in range(DECISION_STEPS) for j, var in enumerate(DECISION_VARS)})

        records.append(indicators)
        all_results.append(df_sim)
    except Exception as e:
        print(f"[{i}] Simulation failed: {e}")

# =======================
# クラスタリング
# =======================
df_indicators = pd.DataFrame(records)
# features = ['Yield', 'Flood Damage', 'Budget', 'Ecosystem', 'Urban Convenience', 'Forest Area', 'Resident Burden']
features = ['Flood Damage', 'Ecosystem', 'Resident Burden']
X = StandardScaler().fit_transform(df_indicators[features])
kmeans = KMeans(n_clusters=5, random_state=42)
df_indicators['Cluster'] = kmeans.fit_predict(X)

# フルタイムシリーズにマージ
df_ts = pd.concat(all_results)
df_ts = df_ts.merge(df_indicators[['Policy_ID', 'Cluster']], on='Policy_ID')

# =======================
# 可視化: Pairplot
# =======================
sns.pairplot(df_indicators, vars=features, hue='Cluster')
plt.suptitle("Scenario Clusters (Fixed RCP)", y=1.02)
plt.tight_layout()
plt.savefig("fig/scenario_clusters_fixed_rcp.png")
plt.close()

# =======================
# 可視化: 時系列グラフ
# =======================
# for feature in ['Crop Yield', 'Flood Damage', 'Ecosystem Level', 'Resident Burden']:
for feature in ['Flood Damage', 'Ecosystem Level', 'Resident Burden']:
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df_ts, x='Year', y=feature, hue='Cluster', estimator='mean', ci='sd')
    plt.title(f"{feature} over Time by Cluster (RCP {rcp_value})")
    plt.ylabel(feature)
    plt.xlabel("Year")
    plt.tight_layout()
    plt.savefig(f"fig/timeseries_{feature.replace(' ', '_')}_fixed_rcp.png")
    plt.close()

# =======================
# データ保存
# =======================
df_indicators.to_csv("output/dmdu_fixed_rcp_summary.csv", index=False)
df_ts.to_csv("output/dmdu_fixed_rcp_timeseries.csv", index=False)
print("✅ Fixed-RCP simulation and clustering completed.")
