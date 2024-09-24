import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO

# シミュレーションのパラメータ
start_year = 2020
end_year = 2100
years = np.arange(start_year, end_year + 1)
num_years = len(years)

# トレンドと不確実性に関する設定をサイドバーに追加
st.sidebar.title('シミュレーション設定')
scenario_name = st.sidebar.text_input('シナリオ名を入力', value='シナリオ1')

# 不確実性のある変数の設定
temp_trend = 0.04 # st.sidebar.slider('気温トレンド（年あたりの上昇率）', 0.0, 0.1, 0.03, 0.01)
temp_uncertainty = 0.5 # st.sidebar.slider('気温不確実性幅（標準偏差）', 0.0, 1.0, 0.5, 0.1)
precip_trend = 0.1 # st.sidebar.slider('降水量トレンド（年あたりの変動率）', -1.0, 1.0, -0.02, 0.1)
precip_uncertainty = 50 # st.sidebar.slider('降水量不確実性幅（標準偏差）', 0.0, 100.0, 50.0, 10.0)
municipal_demand_trend = 0.0 # st.sidebar.slider('都市需要成長トレンド（年あたり）', 0.0, 0.1, 0.01, 0.01)
municipal_demand_uncertainty = 0.01 # st.sidebar.slider('都市需要成長不確実性幅（標準偏差）', 0.0, 0.05, 0.005, 0.001)

# 意思決定変数
irrigation_amount = st.sidebar.slider('灌漑水量', 0, 100, 50, 1)
release_amount = st.sidebar.slider('放流水量', 0, 100, 20, 1)
levee_construction_cost = st.sidebar.slider('堤防工事費', 0, 100, 50, 1)
agricultural_rnd_cost = st.sidebar.slider('農業研究開発費', 0, 100, 30, 1)

# その他パラメータ
initial_available_water = 100.0
initial_crop_yield = 100.0
initial_municipal_demand = 100.0
initial_flood_risk = 10.0
initial_levee_level = 1.0
initial_heat_resistance = 1.0
ecosystem_threshold = 200
evaporation_ratio = 0.5

# モンテカルロシミュレーションの設定
num_simulations = st.sidebar.slider('モンテカルロシミュレーションの回数', 10, 1000, 100, 10)

# セッション状態の初期化
if 'scenarios' not in st.session_state:
    st.session_state['scenarios'] = {}

# シミュレーションの実行
simulate_button = st.sidebar.button('シミュレーション開始')

if simulate_button:
    # モンテカルロシミュレーションの実行
    simulation_results = []
    
    for sim in range(num_simulations):
        # 初期値の設定
        prev_temp = 15.0
        prev_precip = 1000.0
        prev_municipal_demand = initial_municipal_demand
        prev_available_water = initial_available_water
        prev_crop_yield = initial_crop_yield
        prev_flood_risk = initial_flood_risk
        levee_level = initial_levee_level
        heat_resistance = initial_heat_resistance

        # 各シミュレーションの結果を格納
        temperatures = []
        precipitations = []
        available_water = []
        crop_yield = []
        flood_damage = []
        levee_levels = []
        heat_resistances = []
        municipal_demand_list = []
        ecosystem_levels = []

        for year in years:
            # 不確実性を伴う気温と降水量
            temp = prev_temp + temp_trend + np.random.normal(0, temp_uncertainty)
            precip = prev_precip + precip_trend + np.random.normal(0, precip_uncertainty)
            summer_days = max(0, (temp - 30) * 5)
            extreme_rain = np.random.choice([0, 1, 2], p=[0.9, 0.075, 0.025])  # ランダムに発生

            # 都市需要の成長率（トレンドと不確実性）
            municipal_demand_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
            current_municipal_demand = prev_municipal_demand * (1 + municipal_demand_growth)

            # 中間変数: 利用可能水量の計算
            current_available_water = prev_available_water + precip * (1 - evaporation_ratio) - current_municipal_demand - irrigation_amount - release_amount

            # 意思決定変数の適用 (5年ごとに適用)
            if (year - start_year) % 5 == 0:
                levee_level = min(1.0, levee_level + levee_construction_cost / 100)
                heat_resistance = min(1.0, heat_resistance + agricultural_rnd_cost / 100)

            # 作物収量の計算
            current_crop_yield = irrigation_amount - (summer_days * (1 - heat_resistance))

            # 生態系レベルの計算
            ecosystem_level = 100 if (precip + release_amount) >= ecosystem_threshold else max(0, 100 - 5)

            # 極端降水回数と洪水被害額の計算
            current_flood_damage = extreme_rain * (1 - levee_level) * 100000

            # リストに結果を追加
            temperatures.append(temp)
            precipitations.append(precip)
            available_water.append(current_available_water)
            crop_yield.append(current_crop_yield)
            flood_damage.append(current_flood_damage)
            levee_levels.append(levee_level)
            heat_resistances.append(heat_resistance)
            municipal_demand_list.append(current_municipal_demand)
            ecosystem_levels.append(ecosystem_level)

            # 前年の値を更新
            prev_temp = temp
            prev_precip = precip
            prev_municipal_demand = current_municipal_demand
            prev_available_water = current_available_water

        # シミュレーション結果をデータフレームに格納
        df_simulation = pd.DataFrame({
            'Year': years,
            'Temperature (℃)': temperatures,
            'Precipitation (mm)': precipitations,
            'Available Water': available_water,
            'Crop Yield': crop_yield,
            'Flood Damage': flood_damage,
            'Levee Level': levee_levels,
            'Heat Resistance': heat_resistances,
            'Municipal Demand': municipal_demand_list,
            'Ecosystem Level': ecosystem_levels
        })

        simulation_results.append(df_simulation)

    # モンテカルロシミュレーションの結果を統合（平均と標準偏差を計算）
    combined_df = pd.concat(simulation_results).groupby('Year').agg(['mean', 'std'])

    # シミュレーション結果を保存
    st.session_state['scenarios'][scenario_name] = combined_df

# シミュレーション結果の比較
if st.session_state['scenarios']:
    st.subheader('シナリオ比較')

    # 比較するシナリオの選択
    selected_scenarios = st.multiselect('比較するシナリオを選択', list(st.session_state['scenarios'].keys()))

    if selected_scenarios:
        # 複数シナリオのTemperatureとAvailable Waterをプロット
        fig = go.Figure()

        for scenario in selected_scenarios:
            df_scenario = st.session_state['scenarios'][scenario]

            # Temperatureをプロット
            fig.add_trace(go.Scatter(
                x=df_scenario.index, 
                y=df_scenario[('Temperature (℃)', 'mean')], 
                mode='lines', 
                name=f'{scenario} Temperature'
            ))

            # Available Waterをプロット
            fig.add_trace(go.Scatter(
                x=df_scenario.index, 
                y=df_scenario[('Available Water', 'mean')], 
                mode='lines', 
                name=f'{scenario} Available Water', 
                yaxis="y2"
            ))

        # 2つのY軸を設定
        fig.update_layout(
            title="シナリオごとのTemperatureとAvailable Waterの比較",
            xaxis_title="Year",
            yaxis=dict(title="Temperature (℃)"),
            yaxis2=dict(title="Available Water", overlaying="y", side="right")
        )

        st.plotly_chart(fig)

        # 洪水被害額と作物収量の時系列プロット
        st.subheader('洪水被害額と作物収量の時系列')

        fig2 = go.Figure()

        for scenario in selected_scenarios:
            df_scenario = st.session_state['scenarios'][scenario]

            # Flood Damage をプロット
            fig2.add_trace(go.Scatter(
                x=df_scenario.index, 
                y=df_scenario[('Flood Damage', 'mean')], 
                mode='lines', 
                name=f'{scenario} Flood Damage'
            ))

            # Crop Yield をプロット
            fig2.add_trace(go.Scatter(
                x=df_scenario.index, 
                y=df_scenario[('Crop Yield', 'mean')], 
                mode='lines', 
                name=f'{scenario} Crop Yield'
            ))

        fig2.update_layout(
            title="シナリオごとの洪水被害額と作物収量の比較",
            xaxis_title="Year",
            yaxis_title="Value"
        )

        st.plotly_chart(fig2)

# データのエクスポート機能
st.subheader('データのエクスポート')
export_format = st.selectbox('ファイル形式を選択', ['CSV', 'Excel'])
export_button = st.button('データをダウンロード')

if export_button:
    # 選択されたシナリオのデータを結合
    export_df = pd.concat([st.session_state['scenarios'][scenario].reset_index() for scenario in selected_scenarios])

    if export_format == 'CSV':
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(label='CSVファイルをダウンロード', data=csv, file_name='simulation_results.csv', mime='text/csv')

    elif export_format == 'Excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Simulation Results')
            writer.save()
            processed_data = output.getvalue()

        st.download_button(label='Excelファイルをダウンロード', data=processed_data, file_name='simulation_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
