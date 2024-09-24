# Python 3.x
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Streamlitの設定
st.set_page_config(page_title='気候変動適応シミュレーション', layout='wide')

# 地域データの定義（仮定のデータ）
regions = ['Region A', 'Region B', 'Region C']
region_data = {
    'Region A': {
        'initial_temperature': 15.0,
        'initial_precipitation': 1000.0,
        'initial_agri_yield': 100.0,
        'initial_water_resource': 100.0,
        'population': 500000,
        'population_growth_rate': 0.005  # 年率0.5%
    },
    'Region B': {
        'initial_temperature': 20.0,
        'initial_precipitation': 800.0,
        'initial_agri_yield': 80.0,
        'initial_water_resource': 80.0,
        'population': 300000,
        'population_growth_rate': 0.01  # 年率1%
    },
    'Region C': {
        'initial_temperature': 10.0,
        'initial_precipitation': 1200.0,
        'initial_agri_yield': 120.0,
        'initial_water_resource': 120.0,
        'population': 200000,
        'population_growth_rate': 0.002  # 年率0.2%
    }
}

# シミュレーションのパラメータ
start_year = 2020
end_year = 2100
years = np.arange(start_year, end_year + 1)
num_years = len(years)

# サイドバーでパラメータ入力
st.sidebar.title('シミュレーション設定')

# 地域選択
selected_region = st.sidebar.selectbox('地域を選択', regions)

# 適応策パラメータ入力
st.sidebar.subheader('適応策パラメータ')
irrigation_efficiency = st.sidebar.slider('灌漑効率（倍率）', 1.0, 2.0, 1.0, 0.1)
forest_area_increase = st.sidebar.slider('森林面積増加率（%）', 0.0, 100.0, 0.0, 1.0)
infrastructure_investment = st.sidebar.slider('インフラ投資（倍率）', 0.0, 1.0, 0.0, 0.1)
policy_start_year = st.sidebar.slider('政策開始年', start_year, end_year, 2025, 1)

# シミュレーション開始ボタン
simulate_button = st.sidebar.button('シミュレーション開始')

if simulate_button:
    # 選択された地域のデータを取得
    params = region_data[selected_region]

    # 初期値の設定
    initial_temperature = params['initial_temperature']
    initial_precipitation = params['initial_precipitation']
    initial_agri_yield = params['initial_agri_yield']
    initial_water_resource = params['initial_water_resource']
    population = params['population']
    population_growth_rate = params['population_growth_rate']

    # 各年の値を格納するリスト
    temperatures = []
    precipitations = []
    agri_yields = []
    water_resources = []
    flood_risks = []
    populations = []

    # シミュレーションのループ
    for i, year in enumerate(years):
        # 気温と降水量の計算（ここでは単純なモデル）
        temp = initial_temperature + 0.03 * (year - start_year)
        precip = initial_precipitation * (1 - 0.002 * (year - start_year))

        # 適応策の適用判定
        if year >= policy_start_year:
            ie = irrigation_efficiency
            fai = forest_area_increase / 100.0  # %を倍率に変換
            ii = infrastructure_investment
        else:
            ie = 1.0
            fai = 0.0
            ii = 0.0

        # 人口の計算
        pop = population * ((1 + population_growth_rate) ** (year - start_year))

        # 農業生産の計算
        agri_yield = initial_agri_yield * (
            1 - 0.02 * (temp - initial_temperature)  # 高温による減収
            + 0.01 * ie  # 灌漑効率の向上による増収
        ) * (precip / initial_precipitation)

        # 水資源の計算
        water_demand = 100.0 * (pop / population)  # 人口増加による需要増
        water_supply = initial_water_resource * (
            (precip / initial_precipitation) +
            0.05 * fai  # 森林再生による涵養
        )
        water_balance = water_supply - water_demand
        water_resource = max(water_balance, 0)

        # 洪水リスクの計算
        flood_risk = 10.0 + 0.2 * (temp - initial_temperature) - 10 * ii
        flood_risk -= 5 * fai  # 森林によるリスク低減
        flood_risk = np.clip(flood_risk, 0, 100)

        # リストへの追加
        temperatures.append(temp)
        precipitations.append(precip)
        agri_yields.append(agri_yield)
        water_resources.append(water_resource)
        flood_risks.append(flood_risk)
        populations.append(pop)

    # 結果のデータフレームを作成
    df = pd.DataFrame({
        'Year': years,
        'Temperature (℃)': temperatures,
        'Precipitation (mm)': precipitations,
        'Agricultural Yield': agri_yields,
        'Water Resources': water_resources,
        'Flood Risk': flood_risks,
        'Population': populations
    })

    # 結果の表示
    st.title('シミュレーション結果')
    st.subheader(f'地域: {selected_region}')

    # グラフの描画
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0, 0].plot(df['Year'], df['Temperature (℃)'])
    axes[0, 0].set_title('Temperature Over Years')
    axes[0, 0].set_xlabel('Year')
    axes[0, 0].set_ylabel('Temperature (℃)')

    axes[0, 1].plot(df['Year'], df['Agricultural Yield'])
    axes[0, 1].set_title('Agricultural Yield Over Years')
    axes[0, 1].set_xlabel('Year')
    axes[0, 1].set_ylabel('Yield Index')

    axes[1, 0].plot(df['Year'], df['Water Resources'])
    axes[1, 0].set_title('Water Resources Over Years')
    axes[1, 0].set_xlabel('Year')
    axes[1, 0].set_ylabel('Water Resource Index')

    axes[1, 1].plot(df['Year'], df['Flood Risk'])
    axes[1, 1].set_title('Flood Risk Over Years')
    axes[1, 1].set_xlabel('Year')
    axes[1, 1].set_ylabel('Risk Index (0-100)')

    plt.tight_layout()
    st.pyplot(fig)

    # データフレームの表示
    st.subheader('シミュレーションデータ')
    st.dataframe(df)
