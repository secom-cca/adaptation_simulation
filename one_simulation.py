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
    # 'planting_trees_amount': [200, 200, 200],
    # 'house_migration_amount': [100, 100, 100],
    # 'dam_levee_construction_cost': [2.0, 2.0, 2.0],
    # 'paddy_dam_construction_cost': [10.0, 10.0, 10.0],
    # 'capacity_building_cost': [10.0, 10.0, 10.0],
    # 'agricultural_RnD_cost': [10.0, 10.0, 10.0],
    # 'transportation_invest': [10.0, 10.0, 10.0],
    'planting_trees_amount': [100, 100, 100],
    'house_migration_amount': [50, 50, 50],
    'dam_levee_construction_cost': [1.0, 1.0, 1.0],
    'paddy_dam_construction_cost': [5.0, 5.0, 5.0],
    'capacity_building_cost': [5.0, 5.0, 5.0],
    'agricultural_RnD_cost': [5.0, 5.0, 5.0],
    'transportation_invest': [5.0, 5.0, 5.0],
    # 'planting_trees_amount': [0, 0, 0],
    # 'house_migration_amount': [0, 0, 0],
    # 'dam_levee_construction_cost': [0.0, 0.0, 0.0],
    # 'paddy_dam_construction_cost': [0.0, 0.0, 0.0],
    # 'capacity_building_cost': [0.0, 0.0, 0.0],
    # 'agricultural_RnD_cost': [0.0, 0.0, 0.0],
    # 'transportation_invest': [0.0, 0.0, 0.0],
}).set_index('Year')

# RCPごとにシミュレーションを実行
rcps = {'RCP1.9': 1.9, 'RCP2.6': 2.6, 'RCP4.5': 4.5, 'RCP6.0': 6.0, 'RCP8.5': 8.5}
num_simulations = 50  # モンテカルロ回数

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

def plot_indicator(df, indicator, ci=95):
    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=df,
        x='Year',
        y=indicator,
        hue='RCP',
        estimator='mean',
        errorbar='sd',  # or use ('ci', ci) for standard deviation
        n_boot=100,  # optional for bootstrapped CI
        err_style='band'
    )

    plt.title(f'{indicator} Over Time')
    plt.xlabel('Year')
    plt.ylabel(indicator)
    plt.legend(title='RCP')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

plot_indicator(df_all, 'Crop Yield')
plot_indicator(df_all, 'Flood Damage')
plot_indicator(df_all, 'Ecosystem Level')
plot_indicator(df_all, 'Resident Burden')
plot_indicator(df_all, 'Urban Level')
