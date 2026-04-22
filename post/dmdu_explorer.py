import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "../backend"))

# 必要ライブラリ
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from src.simulation import simulate_simulation
from config import DEFAULT_PARAMS, rcp_climate_params
from src.utils import BENCHMARK

# 基本設定
NUM_SIMULATIONS = 1000
TIMESTEP_YEAR = 25
DECISION_STEPS = 3
DECISION_VARS = ['planting_trees_amount', 'house_migration_amount', 'dam_levee_construction_cost', 'capacity_building_cost','paddy_dam_construction_cost', 'agricultural_RnD_cost']
# , 'transportation_invest']
ACTION_LEVELS = [0, 1, 2]

# value_map = {
#     'planting_trees_amount': [0, 75, 150],
#     'house_migration_amount': [0, 50, 100],
#     'dam_levee_construction_cost': [0.0, 1.0, 2.0],
#     'capacity_building_cost': [0.0, 5.0, 10.0],
#     'paddy_dam_construction_cost': [0.0, 5.0, 10.0],
#     'agricultural_RnD_cost': [0.0, 5.0, 10.0],
# }

value_map = [
    [0, 75, 150],
    [0, 50, 100],
    [0.0, 1.0, 2.0],
    [0.0, 5.0, 10.0],
    [0.0, 5.0, 10.0],
    [0.0, 5.0, 10.0],
]

def random_policy():
    return np.random.choice(ACTION_LEVELS, size=(DECISION_STEPS, len(DECISION_VARS)))

def random_rcp():
    return np.random.choice(list(rcp_climate_params.keys()))

def generate_decision_df(policy, start_year=2026):
    years = [start_year + TIMESTEP_YEAR*i for i in range(DECISION_STEPS)]
    mapped_policy = np.random.choice(ACTION_LEVELS, size=(DECISION_STEPS, len(DECISION_VARS)))
    for i in range(len(policy)):
        mapped_policy[i] = [value_map[j][policy[i][j]] for j in range(len(DECISION_VARS))]
    # mapped_policy = [[value_map[i][policy[i]]] * len(TIMESTEP_YEAR)for i in range(DECISION_STEPS)]
    return pd.DataFrame(mapped_policy, columns=DECISION_VARS, index=years)

def summarize_results(df):
    return {
        'Yield': df['Crop Yield'].mean(),
        'Flood Damage': df['Flood Damage'].mean(),
        # 'Budget': df['Municipal Cost'].sum(),
        'Ecosystem': df.loc[df['Year'] == df['Year'].max(), 'Ecosystem Level'].values[0],
        # 'Urban Convenience': df.loc[df['Year'] == df['Year'].max(), 'Urban Level'].values[0],
        # 'Forest Area': df.loc[df['Year'] == df['Year'].max(), 'Forest Area'].values[0],
        'Municipal Cost': df['Municipal Cost'].mean()
    }

# ======================
# Simulation Loop
# ======================
records = []
all_results = []

for i in range(NUM_SIMULATIONS):
    # rcp = random_rcp()
    rcp = 8.5
    params = DEFAULT_PARAMS.copy()
    params.update(rcp_climate_params[rcp])
    years = params['years']
    start_year = params['start_year']

    policy = random_policy()
    decision_df = generate_decision_df(policy, start_year)

    try:
        sim_result = simulate_simulation(years, {}, decision_df, params)
        df_sim = pd.DataFrame(sim_result)
        df_sim['Policy_ID'] = i

        indicators = summarize_results(df_sim)
        indicators.update({
            'Policy_ID': i,
            'RCP': rcp,
            **{f'{var}_t{t+1}': policy[t, j] for t in range(DECISION_STEPS) for j, var in enumerate(DECISION_VARS)}
        })
        records.append(indicators)
        all_results.append(df_sim)
    except Exception as e:
        print(f"[{i}] Simulation failed: {e}")

# ======================
# Clustering
# ======================
df_indicators = pd.DataFrame(records)
# features = ['Yield', 'Flood Damage', 'Budget', 'Ecosystem', 'Urban Convenience', 'Forest Area', 'Municipal Cost']
features = ['Yield', 'Flood Damage', 'Ecosystem', 'Municipal Cost']
X = StandardScaler().fit_transform(df_indicators[features])
kmeans = KMeans(n_clusters=15, random_state=42)
df_indicators['Cluster'] = kmeans.fit_predict(X)
# df_indicators['Cluster'] = df_indicators['planting_trees_amount_t1']*10**5+df_indicators['house_migration_amount_t1']*10**4+df_indicators['dam_levee_construction_cost_t1']*10**3+df_indicators['paddy_dam_construction_cost_t1']*10**2+df_indicators['capacity_building_cost_t1']*10+df_indicators['agricultural_RnD_cost_t1']

# Merge Cluster info into full timeseries
df_ts = pd.concat(all_results)
df_ts = df_ts.merge(df_indicators[['Policy_ID', 'Cluster']], on='Policy_ID')

# Pairplot (cluster visualization)
sns.pairplot(df_indicators, vars=features, hue='Cluster')
plt.suptitle("Scenario Clusters based on DMDU Sampling", y=1.02)
plt.tight_layout()
plt.savefig("fig/scenario_clusters.png")
plt.close()


# ======================
# Plot: Time series per cluster
# ======================
plt.figure(figsize=(12, 6))
for feature in ['Crop Yield', 'Flood Damage', 'Ecosystem Level', 'Municipal Cost']:
# for feature in ['Crop Yield', 'Flood Damage', 'Ecosystem Level', 'Urban Level', 'Forest Area', 'Municipal Cost', 'Municipal Cost']:
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df_ts, x='Year', y=feature, hue='Cluster', estimator='mean', ci='sd')
    plt.title(f"{feature} over Time by Cluster")
    plt.ylabel(feature)
    plt.xlabel("Year")
    plt.tight_layout()
    plt.savefig(f"fig/timeseries_{feature.replace(' ', '_')}.png")
    plt.close()

# ======================
# Export CSV
# ======================
df_indicators.to_csv("output/dmdu_clustered_summary19.csv", index=False)
df_ts.to_csv("output/dmdu_full_timeseries19.csv", index=False)
print("✅ Simulation, clustering, and exports completed.")

