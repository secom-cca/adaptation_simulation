import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO

# シミュレーションのパラメータ
start_year = 2020
end_year = 2100
total_years = end_year - start_year + 1
years = np.arange(start_year, end_year + 1)

# セッション状態の初期化
if 'current_year_index' not in st.session_state:
    st.session_state['current_year_index'] = 0
    st.session_state['simulation_results'] = []
    st.session_state['prev_values'] = []
    st.session_state['decision_vars'] = []
    st.session_state['scenario_name'] = ''
    # 'scenarios'が存在しない場合のみ初期化
    if 'scenarios' not in st.session_state:
        st.session_state['scenarios'] = {}

# トレンドと不確実性に関する設定をサイドバーに追加
st.sidebar.title('シミュレーション設定')
if st.session_state['current_year_index'] == 0:
    scenario_name = st.sidebar.text_input('シナリオ名を入力', value='シナリオ1')
    st.session_state['scenario_name'] = scenario_name
else:
    scenario_name = st.session_state['scenario_name']

# トレンドの傾きと不確実性幅（初回のみ設定可能）
if st.session_state['current_year_index'] == 0:
    temp_trend = st.sidebar.slider('気温トレンド（年あたりの上昇率）', 0.0, 0.1, 0.03, 0.01)
    temp_uncertainty = st.sidebar.slider('気温不確実性幅（標準偏差）', 0.0, 1.0, 0.5, 0.1)
    precip_trend = st.sidebar.slider('降水量トレンド（年あたりの変動率）', -10.0, 10.0, -0.2, 0.1)
    precip_uncertainty = st.sidebar.slider('降水量不確実性幅（標準偏差）', 0.0, 100.0, 50.0, 10.0)
    extreme_precip_freq_trend = st.sidebar.slider('極端降水頻度トレンド（年あたりの増加率）', 0.0, 0.05, 0.01, 0.01)
    extreme_precip_freq_uncertainty = st.sidebar.slider('極端降水頻度不確実性幅（標準偏差）', 0.0, 0.1, 0.02, 0.01)
    municipal_demand_trend = st.sidebar.slider('都市水需要成長トレンド（年あたり）', 0.0, 0.1, 0.01, 0.01)
    municipal_demand_uncertainty = st.sidebar.slider('都市水需要成長不確実性幅（標準偏差）', 0.0, 0.05, 0.005, 0.001)

    # モンテカルロシミュレーションの設定
    num_simulations = st.sidebar.slider('モンテカルロシミュレーションの回数', 10, 500, 100, 10)

    # トレンドと不確実性をセッション状態に保存
    st.session_state['trends'] = {
        'temp_trend': temp_trend,
        'temp_uncertainty': temp_uncertainty,
        'precip_trend': precip_trend,
        'precip_uncertainty': precip_uncertainty,
        'extreme_precip_freq_trend': extreme_precip_freq_trend,
        'extreme_precip_freq_uncertainty': extreme_precip_freq_uncertainty,
        'municipal_demand_trend': municipal_demand_trend,
        'municipal_demand_uncertainty': municipal_demand_uncertainty,
        'num_simulations': num_simulations
    }
else:
    temp_trend = st.session_state['trends']['temp_trend']
    temp_uncertainty = st.session_state['trends']['temp_uncertainty']
    precip_trend = st.session_state['trends']['precip_trend']
    precip_uncertainty = st.session_state['trends']['precip_uncertainty']
    extreme_precip_freq_trend = st.session_state['trends']['extreme_precip_freq_trend']
    extreme_precip_freq_uncertainty = st.session_state['trends']['extreme_precip_freq_uncertainty']
    municipal_demand_trend = st.session_state['trends']['municipal_demand_trend']
    municipal_demand_uncertainty = st.session_state['trends']['municipal_demand_uncertainty']
    num_simulations = st.session_state['trends']['num_simulations']

# その他パラメータ
initial_hot_days = 30.0
base_temp = 15.0
temp_to_hot_days_coeff = 2.0
hot_days_uncertainty = 2.0
initial_extreme_precip_freq = 0.1
ecosystem_threshold = 800.0  # 閾値
temp_coefficient = 1.0
max_potential_yield = 100.0
optimal_irrigation_amount = 30.0
flood_damage_coefficient = 100000
levee_level_increment = 0.1
high_temp_tolerance_increment = 0.1
levee_investment_threshold = 1.0
RnD_investment_threshold = 1.0
levee_investment_required_years = 5
RnD_investment_required_years = 5

# 意思決定変数の入力（現在の期間用）
st.sidebar.title('意思決定変数（次の5年間）')
irrigation_water_amount = st.sidebar.number_input('灌漑水量', min_value=0.0, value=20.0, step=1.0)
released_water_amount = st.sidebar.number_input('放流水量', min_value=0.0, value=10.0, step=1.0)
levee_construction_cost = st.sidebar.number_input('堤防工事費', min_value=0.0, value=5.0, step=1.0)
agricultural_RnD_cost = st.sidebar.number_input('農業研究開発費', min_value=0.0, value=5.0, step=1.0)

# 意思決定変数をセッション状態に保存
st.session_state['decision_vars'].append({
    'irrigation_water_amount': irrigation_water_amount,
    'released_water_amount': released_water_amount,
    'levee_construction_cost': levee_construction_cost,
    'agricultural_RnD_cost': agricultural_RnD_cost
})

# シミュレーションの実行（次の5年間）
simulate_button = st.sidebar.button('次の5年へ')

if simulate_button:
    # シミュレーションの年数を計算
    current_year_index = st.session_state['current_year_index']
    next_year_index = min(current_year_index + 5, total_years)
    sim_years = years[current_year_index:next_year_index]
    
    # 前年の値を取得または初期化
    if st.session_state['current_year_index'] == 0:
        prev_values_list = []
        for sim in range(num_simulations):
            prev_values = {
                'temp': 15.0,
                'precip': 1000.0,
                'municipal_demand': 100.0,
                'available_water': 100.0,
                'crop_yield': 100.0,
                'levee_level': 0.5,
                'high_temp_tolerance_level': 0.0,
                'hot_days': 30.0,
                'extreme_precip_freq': 0.1,
                'ecosystem_level': 100.0,
                'levee_investment_years': 0,
                'RnD_investment_years': 0
            }
            prev_values_list.append(prev_values)
        st.session_state['prev_values'] = prev_values_list
    else:
        prev_values_list = st.session_state['prev_values']
    
    # 各シミュレーションの結果を格納
    simulation_results = []

    # モンテカルロシミュレーションの実行
    for sim in range(num_simulations):
        prev_values = prev_values_list[sim]
        sim_results = []

        # 投資年数の取得
        levee_investment_years = prev_values['levee_investment_years']
        RnD_investment_years = prev_values['RnD_investment_years']

        for i, year in enumerate(sim_years):
            # 現在の意思決定変数を取得
            decision_vars = st.session_state['decision_vars'][-1]
            irrigation_water_amount = decision_vars['irrigation_water_amount']
            released_water_amount = decision_vars['released_water_amount']
            levee_construction_cost = decision_vars['levee_construction_cost']
            agricultural_RnD_cost = decision_vars['agricultural_RnD_cost']
            
            # 気温のトレンドと不確実性
            temp = prev_values['temp'] + temp_trend + np.random.normal(0, temp_uncertainty)
            precip = prev_values['precip'] + precip_trend + np.random.normal(0, precip_uncertainty)
    
            # 真夏日日数の計算
            hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
            hot_days = max(hot_days, 0)  # 真夏日日数は0以上
    
            # 極端降水頻度の計算
            extreme_precip_freq = prev_values['extreme_precip_freq'] + extreme_precip_freq_trend + np.random.normal(0, extreme_precip_freq_uncertainty)
            extreme_precip_freq = max(extreme_precip_freq, 0.0)
    
            # 極端降水回数の計算
            extreme_precip_events = np.random.poisson(extreme_precip_freq)
    
            # 都市水需要の成長率（トレンドと不確実性）
            municipal_demand_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
            current_municipal_demand = prev_values['municipal_demand'] * (1 + municipal_demand_growth)
    
            # 利用可能水量の計算
            current_available_water = prev_values['available_water'] + precip - current_municipal_demand - irrigation_water_amount - released_water_amount
    
            # 作物収量の計算
            crop_yield_irrigation_component = max_potential_yield * (irrigation_water_amount / optimal_irrigation_amount)
            crop_yield_irrigation_component = min(crop_yield_irrigation_component, max_potential_yield)
            temp_impact = hot_days * temp_coefficient * (1 - prev_values['high_temp_tolerance_level'])
            current_crop_yield = crop_yield_irrigation_component - temp_impact
            current_crop_yield = max(current_crop_yield, 0)  # 作物収量は0以上
    
            # 堤防レベルの更新
            if levee_construction_cost >= levee_investment_threshold:
                levee_investment_years += 1
                if levee_investment_years >= levee_investment_required_years:
                    prev_values['levee_level'] = min(prev_values['levee_level'] + levee_level_increment, 1.0)
                    levee_investment_years = 0
            else:
                levee_investment_years = 0
    
            # 高温耐性レベルの更新
            if agricultural_RnD_cost >= RnD_investment_threshold:
                RnD_investment_years += 1
                if RnD_investment_years >= RnD_investment_required_years:
                    prev_values['high_temp_tolerance_level'] = min(prev_values['high_temp_tolerance_level'] + high_temp_tolerance_increment, 1.0)
                    RnD_investment_years = 0
            else:
                RnD_investment_years = 0
    
            # 洪水被害額の計算
            current_flood_damage = extreme_precip_events * (1 - prev_values['levee_level']) * flood_damage_coefficient
    
            # 生態系レベルの計算
            water_for_ecosystem = precip + released_water_amount
            if water_for_ecosystem < ecosystem_threshold:
                prev_values['ecosystem_level'] -= 1  # 閾値以下なら生態系レベルを減少
            prev_values['ecosystem_level'] = max(prev_values['ecosystem_level'], 0)  # 生態系レベルは0以上
    
            # 自治体コストの計算
            municipal_cost = levee_construction_cost + agricultural_RnD_cost
    
            # 結果を格納
            sim_results.append({
                'Simulation': sim,
                'Year': year,
                'Temperature (℃)': temp,
                'Precipitation (mm)': precip,
                'Available Water': current_available_water,
                'Crop Yield': current_crop_yield,
                'Municipal Demand': current_municipal_demand,
                'Flood Damage': current_flood_damage,
                'Levee Level': prev_values['levee_level'],
                'High Temp Tolerance Level': prev_values['high_temp_tolerance_level'],
                'Hot Days': hot_days,
                'Extreme Precip Frequency': extreme_precip_freq,
                'Extreme Precip Events': extreme_precip_events,
                'Ecosystem Level': prev_values['ecosystem_level'],
                'Municipal Cost': municipal_cost
            })
    
            # 前年の値を更新
            prev_values['temp'] = temp
            prev_values['precip'] = precip
            prev_values['municipal_demand'] = current_municipal_demand
            prev_values['available_water'] = current_available_water
            prev_values['crop_yield'] = current_crop_yield
            prev_values['hot_days'] = hot_days
            prev_values['extreme_precip_freq'] = extreme_precip_freq
            # levee_level と high_temp_tolerance_level は更新済み
            # levee_investment_years と RnD_investment_years を更新
            prev_values['levee_investment_years'] = levee_investment_years
            prev_values['RnD_investment_years'] = RnD_investment_years

        # シミュレーション結果をセッション状態に保存
        if len(st.session_state['simulation_results']) <= sim:
            st.session_state['simulation_results'].append(sim_results)
        else:
            st.session_state['simulation_results'][sim].extend(sim_results)
        st.session_state['prev_values'][sim] = prev_values

    st.session_state['current_year_index'] = next_year_index

# シミュレーション結果の表示
if st.session_state['simulation_results']:
    # 全シミュレーションの結果をデータフレームに格納
    all_results = []
    for sim_results in st.session_state['simulation_results']:
        all_results.extend(sim_results)
    df_results = pd.DataFrame(all_results)

    st.subheader('シミュレーション結果')

    # グラフの作成
    fig = go.Figure()
    for sim in df_results['Simulation'].unique():
        df_sim = df_results[df_results['Simulation'] == sim]
        fig.add_trace(go.Scatter(
            x=df_sim['Year'],
            y=df_sim['Temperature (℃)'],
            mode='lines',
            name=f'Sim {sim} Temperature',
            line=dict(width=1),
            opacity=0.2,
            showlegend=False
        ))
    fig.update_layout(
        title='Temperature Over Time (All Simulations)',
        xaxis_title='Year',
        yaxis_title='Temperature (℃)'
    )
    st.plotly_chart(fig)

    # 洪水被害額と作物収量の時系列プロット
    st.subheader('洪水被害額と作物収量の時系列')
    fig2 = go.Figure()
    for sim in df_results['Simulation'].unique():
        df_sim = df_results[df_results['Simulation'] == sim]
        fig2.add_trace(go.Scatter(
            x=df_sim['Year'],
            y=df_sim['Flood Damage'],
            mode='lines',
            name=f'Sim {sim} Flood Damage',
            line=dict(width=1),
            opacity=0.2,
            showlegend=False
        ))
    fig2.update_layout(
        title='Flood Damage Over Time (All Simulations)',
        xaxis_title='Year',
        yaxis_title='Flood Damage'
    )
    st.plotly_chart(fig2)

    # 生態系レベルと自治体コストの時系列プロット
    st.subheader('生態系レベルと自治体コストの時系列')
    fig3 = go.Figure()
    for sim in df_results['Simulation'].unique():
        df_sim = df_results[df_results['Simulation'] == sim]
        fig3.add_trace(go.Scatter(
            x=df_sim['Year'],
            y=df_sim['Ecosystem Level'],
            mode='lines',
            name=f'Sim {sim} Ecosystem Level',
            line=dict(width=1),
            opacity=0.2,
            showlegend=False
        ))
    fig3.update_layout(
        title='Ecosystem Level Over Time (All Simulations)',
        xaxis_title='Year',
        yaxis_title='Ecosystem Level'
    )
    st.plotly_chart(fig3)

# シナリオの保存とリセット
st.sidebar.title('シナリオ管理')
save_scenario = st.sidebar.button('シナリオを保存')
if save_scenario:
    st.session_state['scenarios'][scenario_name] = df_results.copy()
    st.success(f'シナリオ「{scenario_name}」を保存しました。')

reset_simulation = st.sidebar.button('シミュレーションをリセット')
if reset_simulation:
    st.session_state['current_year_index'] = 0
    st.session_state['simulation_results'] = []
    st.session_state['prev_values'] = []
    st.session_state['decision_vars'] = []
    st.session_state['scenario_name'] = ''
    # st.session_state['scenarios'] = {}  # この行を削除
    st.rerun()

# シナリオの比較
if st.session_state['scenarios']:
    st.subheader('シナリオ比較')
    selected_scenarios = st.multiselect('比較するシナリオを選択', list(st.session_state['scenarios'].keys()))
    if selected_scenarios:
        # 軸の選択
        st.write('散布図の軸を選択してください。')
        variables = ['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost']
        x_axis = st.selectbox('X軸', variables, index=0, key='x_axis')
        y_axis = st.selectbox('Y軸', variables, index=1, key='y_axis')

        # シナリオごとの総額を計算し、散布図を作成
        fig_scatter = go.Figure()
        for scenario in selected_scenarios:
            df_scenario = st.session_state['scenarios'][scenario]
            # 各シミュレーションの総額を計算
            sim_totals = df_scenario.groupby('Simulation').agg({
                x_axis: 'sum',
                y_axis: 'sum'
            }).reset_index()
            fig_scatter.add_trace(go.Scatter(
                x=sim_totals[x_axis],
                y=sim_totals[y_axis],
                mode='markers',
                name=scenario,
                opacity=0.7
            ))
        fig_scatter.update_layout(
            title=f'{x_axis} vs {y_axis} Scatter Plot',
            xaxis_title=x_axis,
            yaxis_title=y_axis
        )
        st.plotly_chart(fig_scatter)

# データのエクスポート機能
st.subheader('データのエクスポート')
export_format = st.selectbox('ファイル形式を選択', ['CSV', 'Excel'])
export_button = st.button('データをダウンロード')

if export_button:
    if st.session_state['scenarios']:
        if selected_scenarios:
            # 選択されたシナリオのデータを結合
            export_df = pd.concat([st.session_state['scenarios'][scenario] for scenario in selected_scenarios])
        else:
            # すべてのシナリオをエクスポート
            export_df = pd.concat([df for df in st.session_state['scenarios'].values()])
    else:
        export_df = df_results.copy()

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
