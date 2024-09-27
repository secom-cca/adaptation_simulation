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

image_path = "causal_loop_diagram.png"  # 画像ファイルのパスを指定
st.image(image_path, caption='シミュレーションのイメージ', use_column_width=True)

# シミュレーションモードの選択
simulation_mode = st.sidebar.selectbox('シミュレーションモードを選択', ['モンテカルロシミュレーションモード', '逐次意思決定シミュレーションモード'])

# シナリオ名の入力
scenario_name = st.sidebar.text_input('シナリオ名を入力', value='シナリオ1')

# トレンドと不確実性に関する設定をサイドバーに追加
st.sidebar.title('シミュレーション設定')

# トレンドの傾きと不確実性幅
temp_trend = st.sidebar.slider('気温トレンド（年あたりの上昇率）', 0.0, 0.1, 0.03, 0.01)
temp_uncertainty = st.sidebar.slider('気温不確実性幅（標準偏差）', 0.0, 1.0, 0.5, 0.1)
precip_trend = st.sidebar.slider('降水量トレンド（年あたりの変動率）', -10.0, 10.0, -0.2, 0.1)
precip_uncertainty = st.sidebar.slider('降水量不確実性幅（標準偏差）', 0.0, 100.0, 50.0, 10.0)
extreme_precip_freq_trend = st.sidebar.slider('極端降水頻度トレンド（年あたりの増加率）', 0.0, 0.05, 0.01, 0.01)
extreme_precip_freq_uncertainty = st.sidebar.slider('極端降水頻度不確実性幅（標準偏差）', 0.0, 0.1, 0.02, 0.01)
municipal_demand_trend = st.sidebar.slider('都市水需要成長トレンド（年あたり）', 0.0, 0.1, 0.01, 0.01)
municipal_demand_uncertainty = st.sidebar.slider('都市水需要成長不確実性幅（標準偏差）', 0.0, 0.05, 0.005, 0.001)

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
max_available_water = 5000.0  # 例: 最大の利用可能水量 [m**3]

# セッション状態の初期化
if 'scenarios' not in st.session_state:
    st.session_state['scenarios'] = {}

# モンテカルロシミュレーションモードの場合
if simulation_mode == 'モンテカルロシミュレーションモード':
    # 意思決定変数（5年おきに意思決定）
    # 本来はその決め方をシミュレーションしたい
    st.sidebar.title('意思決定変数（5年ごと）')
    decision_years = np.arange(start_year, end_year + 1, 5)
    decision_df = pd.DataFrame({
        'Year': decision_years,
        '灌漑水量 (Irrigation Water Amount)': [100.0]*len(decision_years),
        '放流水量 (Released Water Amount)': [100.0]*len(decision_years),
        '堤防工事費 (Levee Construction Cost)': [5.0]*len(decision_years),
        '農業研究開発費 (Agricultural R&D Cost)': [5.0]*len(decision_years)
    })
    decision_df = st.sidebar.data_editor(decision_df, use_container_width=True)
    
    # モンテカルロシミュレーションの設定
    num_simulations = st.sidebar.slider('モンテカルロシミュレーションの回数', 10, 500, 100, 10)
    
    simulate_button = st.sidebar.button('シミュレーション開始')
    
    if simulate_button:
        # モンテカルロシミュレーションの実行
        simulation_results = []
    
        for sim in range(num_simulations):
            # 前年の値を初期化
            prev_temp = 15.0
            prev_precip = 1000.0
            prev_municipal_demand = 100.0
            prev_available_water = 1000.0 # [m**3]
            prev_crop_yield = 100.0
            prev_levee_level = 0.5
            prev_high_temp_tolerance_level = 0.0
            prev_hot_days = 30.0
            prev_extreme_precip_freq = 0.1
            prev_ecosystem_level = 100.0
    
            # 投資年数の初期化
            levee_investment_years = 0
            RnD_investment_years = 0
    
            # 各シミュレーションの結果を格納
            temperatures = []
            precipitations = []
            available_water = []
            crop_yield = []
            municipal_demand = []
            flood_damage = []
            levee_levels = []
            high_temp_tolerance_levels = []
            hot_days_list = []
            extreme_precip_freqs = []
            extreme_precip_events_list = []
            ecosystem_levels = []
            municipal_costs = []
    
            for year in years:
                # 現在の意思決定変数を取得
                decision_period = (year - start_year) // 5 * 5 + start_year
                decision_vars = decision_df[decision_df['Year'] == decision_period]
                if not decision_vars.empty:
                    irrigation_water_amount = decision_vars['灌漑水量 (Irrigation Water Amount)'].values[0]
                    released_water_amount = decision_vars['放流水量 (Released Water Amount)'].values[0]
                    levee_construction_cost = decision_vars['堤防工事費 (Levee Construction Cost)'].values[0]
                    agricultural_RnD_cost = decision_vars['農業研究開発費 (Agricultural R&D Cost)'].values[0]
                else:
                    # デフォルト値を使用
                    irrigation_water_amount = 200.0
                    released_water_amount = 100.0
                    levee_construction_cost = 5.0
                    agricultural_RnD_cost = 5.0
    
                # 気温のトレンドと不確実性
                temp = prev_temp + temp_trend + np.random.normal(0, temp_uncertainty)
                precip = prev_precip + precip_trend + np.random.normal(0, precip_uncertainty)
    
                # 真夏日日数の計算
                hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + np.random.normal(0, hot_days_uncertainty)
                hot_days = max(hot_days, 0)  # 真夏日日数は0以上
    
                # 極端降水頻度の計算
                extreme_precip_freq = prev_extreme_precip_freq + extreme_precip_freq_trend + np.random.normal(0, extreme_precip_freq_uncertainty)
                extreme_precip_freq = max(extreme_precip_freq, 0.0)
    
                # 極端降水回数の計算
                extreme_precip_events = np.random.poisson(extreme_precip_freq)
    
                # 都市水需要の成長率（トレンドと不確実性）
                municipal_demand_growth = municipal_demand_trend + np.random.normal(0, municipal_demand_uncertainty)
                current_municipal_demand = prev_municipal_demand * (1 + municipal_demand_growth)
    
                # 利用可能水量の計算
                current_available_water = prev_available_water + precip - current_municipal_demand - irrigation_water_amount - released_water_amount
                current_available_water = min(current_available_water, max_available_water)

                # 作物収量の計算
                crop_yield_irrigation_component = max_potential_yield * (irrigation_water_amount / optimal_irrigation_amount)
                crop_yield_irrigation_component = min(crop_yield_irrigation_component, max_potential_yield)
                temp_impact = hot_days * temp_coefficient * (1 - prev_high_temp_tolerance_level)
                current_crop_yield = crop_yield_irrigation_component - temp_impact
                current_crop_yield = max(current_crop_yield, 0)  # 作物収量は0以上
    
                # 堤防レベルの更新
                if levee_construction_cost >= levee_investment_threshold:
                    levee_investment_years += 1
                    if levee_investment_years >= levee_investment_required_years:
                        prev_levee_level = min(prev_levee_level + levee_level_increment, 1.0)
                        levee_investment_years = 0
                else:
                    levee_investment_years = 0
    
                # 高温耐性レベルの更新
                if agricultural_RnD_cost >= RnD_investment_threshold:
                    RnD_investment_years += 1
                    if RnD_investment_years >= RnD_investment_required_years:
                        prev_high_temp_tolerance_level = min(prev_high_temp_tolerance_level + high_temp_tolerance_increment, 1.0)
                        RnD_investment_years = 0
                else:
                    RnD_investment_years = 0
    
                # 洪水被害額の計算
                current_flood_damage = extreme_precip_events * (1 - prev_levee_level) * flood_damage_coefficient
    
                # 生態系レベルの計算
                water_for_ecosystem = precip + released_water_amount
                if water_for_ecosystem < ecosystem_threshold:
                    prev_ecosystem_level -= 1  # 閾値以下なら生態系レベルを減少
                prev_ecosystem_level = max(prev_ecosystem_level, 0)  # 生態系レベルは0以上
    
                # 自治体コストの計算
                municipal_cost = levee_construction_cost + agricultural_RnD_cost
    
                # リストに結果を追加
                temperatures.append(temp)
                precipitations.append(precip)
                available_water.append(current_available_water)
                crop_yield.append(current_crop_yield)
                municipal_demand.append(current_municipal_demand)
                flood_damage.append(current_flood_damage)
                levee_levels.append(prev_levee_level)
                high_temp_tolerance_levels.append(prev_high_temp_tolerance_level)
                hot_days_list.append(hot_days)
                extreme_precip_freqs.append(extreme_precip_freq)
                extreme_precip_events_list.append(extreme_precip_events)
                ecosystem_levels.append(prev_ecosystem_level)
                municipal_costs.append(municipal_cost)
    
                # 前年の値を更新
                prev_temp = temp
                prev_precip = precip
                prev_municipal_demand = current_municipal_demand
                prev_available_water = current_available_water
                prev_crop_yield = current_crop_yield
                # 堤防レベルと高温耐性レベルは更新済み
    
                prev_hot_days = hot_days
                prev_extreme_precip_freq = extreme_precip_freq
                prev_ecosystem_level = prev_ecosystem_level
    
            # シミュレーション結果をデータフレームに格納
            df_simulation = pd.DataFrame({
                'Simulation': sim,
                'Year': years,
                'Temperature (℃)': temperatures,
                'Precipitation (mm)': precipitations,
                'Available Water': available_water,
                'Crop Yield': crop_yield,
                'Municipal Demand': municipal_demand,
                'Flood Damage': flood_damage,
                'Levee Level': levee_levels,
                'High Temp Tolerance Level': high_temp_tolerance_levels,
                'Hot Days': hot_days_list,
                'Extreme Precip Frequency': extreme_precip_freqs,
                'Extreme Precip Events': extreme_precip_events_list,
                'Ecosystem Level': ecosystem_levels,
                'Municipal Cost': municipal_costs
            })
    
            simulation_results.append(df_simulation)
    
        # シミュレーション結果を保存
        df_results = pd.concat(simulation_results)
        st.session_state['scenarios'][scenario_name] = df_results.copy()
        st.success(f'シナリオ「{scenario_name}」のシミュレーションが完了しました。')

    # シミュレーション結果の表示
    if scenario_name in st.session_state['scenarios']:
        df_results = st.session_state['scenarios'][scenario_name]
        st.subheader('シミュレーション結果')

        # グラフの作成 - Temperature
        fig_temp = go.Figure()
        for sim in df_results['Simulation'].unique():
            df_sim = df_results[df_results['Simulation'] == sim]
            fig_temp.add_trace(go.Scatter(
                x=df_sim['Year'],
                y=df_sim['Temperature (℃)'],
                mode='lines',
                name=f'Sim {sim} Temperature',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
        fig_temp.update_layout(
            title='Temperature Over Time (All Simulations)',
            xaxis_title='Year',
            yaxis_title='Temperature (℃)'
        )
        st.plotly_chart(fig_temp)

        # グラフの作成 - Precipitation
        fig_precip = go.Figure()
        for sim in df_results['Simulation'].unique():
            df_sim = df_results[df_results['Simulation'] == sim]
            fig_precip.add_trace(go.Scatter(
                x=df_sim['Year'],
                y=df_sim['Precipitation (mm)'],
                mode='lines',
                name=f'Sim {sim} Precipitation',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
        fig_precip.update_layout(
            title='Precipitation Over Time (All Simulations)',
            xaxis_title='Year',
            yaxis_title='Precipitation (mm)'
        )
        st.plotly_chart(fig_precip)

        # グラフの作成 - Available Water
        fig_water = go.Figure()
        for sim in df_results['Simulation'].unique():
            df_sim = df_results[df_results['Simulation'] == sim]
            fig_water.add_trace(go.Scatter(
                x=df_sim['Year'],
                y=df_sim['Available Water'],
                mode='lines',
                name=f'Sim {sim} Available Water',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
        fig_water.update_layout(
            title='Available Water Over Time (All Simulations)',
            xaxis_title='Year',
            yaxis_title='Available Water'
        )
        st.plotly_chart(fig_water)

        # グラフの作成 - Flood Damage
        fig_flood = go.Figure()
        for sim in df_results['Simulation'].unique():
            df_sim = df_results[df_results['Simulation'] == sim]
            fig_flood.add_trace(go.Scatter(
                x=df_sim['Year'],
                y=df_sim['Flood Damage'],
                mode='lines',
                name=f'Sim {sim} Flood Damage',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
        fig_flood.update_layout(
            title='Flood Damage Over Time (All Simulations)',
            xaxis_title='Year',
            yaxis_title='Flood Damage'
        )
        st.plotly_chart(fig_flood)

        # グラフの作成 - Crop Yield
        fig_crop = go.Figure()
        for sim in df_results['Simulation'].unique():
            df_sim = df_results[df_results['Simulation'] == sim]
            fig_crop.add_trace(go.Scatter(
                x=df_sim['Year'],
                y=df_sim['Crop Yield'],
                mode='lines',
                name=f'Sim {sim} Crop Yield',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
        fig_crop.update_layout(
            title='Crop Yield Over Time (All Simulations)',
            xaxis_title='Year',
            yaxis_title='Crop Yield'
        )
        st.plotly_chart(fig_crop)

    # シナリオの比較と散布図
    if st.session_state['scenarios']:
        st.subheader('シナリオ比較')
        selected_scenarios = st.multiselect('比較するシナリオを選択', list(st.session_state['scenarios'].keys()))
        if selected_scenarios:
            # 軸の選択
            st.write('散布図の軸を選択してください。')
            variables = ['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost']
            x_axis = st.selectbox('X軸', variables, index=0, key='x_axis_mc')
            y_axis = st.selectbox('Y軸', variables, index=1, key='y_axis_mc')
    
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

# 逐次意思決定シミュレーションモードの場合
elif simulation_mode == '逐次意思決定シミュレーションモード':
    # セッション状態の初期化
    if 'current_year_index_seq' not in st.session_state:
        st.session_state['current_year_index_seq'] = 0
        st.session_state['simulation_results_seq'] = []
        st.session_state['prev_values_seq'] = {
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
        st.session_state['decision_vars_seq'] = []
    
    # 意思決定変数の入力（現在の期間用）
    st.sidebar.title('意思決定変数（次の5年間）')
    irrigation_water_amount = st.sidebar.number_input('灌漑水量', min_value=0.0, value=20.0, step=1.0)
    released_water_amount = st.sidebar.number_input('放流水量', min_value=0.0, value=10.0, step=1.0)
    levee_construction_cost = st.sidebar.number_input('堤防工事費', min_value=0.0, value=5.0, step=1.0)
    agricultural_RnD_cost = st.sidebar.number_input('農業研究開発費', min_value=0.0, value=5.0, step=1.0)
    
    # 意思決定変数をセッション状態に保存
    st.session_state['decision_vars_seq'].append({
        'irrigation_water_amount': irrigation_water_amount,
        'released_water_amount': released_water_amount,
        'levee_construction_cost': levee_construction_cost,
        'agricultural_RnD_cost': agricultural_RnD_cost
    })
    
    # シミュレーションの実行（次の5年間）
    simulate_button_seq = st.sidebar.button('次の5年へ')
    
    if simulate_button_seq:
        # シミュレーションの年数を計算
        current_year_index = st.session_state['current_year_index_seq']
        next_year_index = min(current_year_index + 5, total_years)
        sim_years = years[current_year_index:next_year_index]
        
        # 前年の値を取得
        prev_values = st.session_state['prev_values_seq']
        
        # 投資年数の取得
        levee_investment_years = prev_values['levee_investment_years']
        RnD_investment_years = prev_values['RnD_investment_years']
        
        # 各年の結果を格納
        simulation_results = []
        
        for i, year in enumerate(sim_years):
            # 現在の意思決定変数を取得
            decision_vars = st.session_state['decision_vars_seq'][-1]
            irrigation_water_amount = decision_vars['irrigation_water_amount']
            released_water_amount = decision_vars['released_water_amount']
            levee_construction_cost = decision_vars['levee_construction_cost']
            agricultural_RnD_cost = decision_vars['agricultural_RnD_cost']
            
            # 不確実性パラメータを固定値に設定（毎年同じ）
            temp_random = 0
            precip_random = 0
            hot_days_random = 0
            extreme_precip_freq_random = 0
            municipal_demand_random = 0
    
            # 気温のトレンドと不確実性
            temp = prev_values['temp'] + temp_trend + temp_random
            precip = prev_values['precip'] + precip_trend + precip_random
    
            # 真夏日日数の計算
            hot_days = initial_hot_days + (temp - base_temp) * temp_to_hot_days_coeff + hot_days_random
            hot_days = max(hot_days, 0)  # 真夏日日数は0以上
    
            # 極端降水頻度の計算
            extreme_precip_freq = prev_values['extreme_precip_freq'] + extreme_precip_freq_trend + extreme_precip_freq_random
            extreme_precip_freq = max(extreme_precip_freq, 0.0)
    
            # 極端降水回数の計算
            extreme_precip_events = int(extreme_precip_freq)
    
            # 都市水需要の成長率（トレンドと不確実性）
            municipal_demand_growth = municipal_demand_trend + municipal_demand_random
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
            simulation_results.append({
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
    
        # セッション状態に結果を追加
        st.session_state['simulation_results_seq'].extend(simulation_results)
        st.session_state['prev_values_seq'] = prev_values
        st.session_state['current_year_index_seq'] = next_year_index
    
    # シミュレーション結果の表示
    if st.session_state['simulation_results_seq']:
        df_results_seq = pd.DataFrame(st.session_state['simulation_results_seq'])
        st.subheader('シミュレーション結果')
    
        # グラフの作成 - Temperature
        fig_seq_temp = go.Figure()
        fig_seq_temp.add_trace(go.Scatter(
            x=df_results_seq['Year'],
            y=df_results_seq['Temperature (℃)'],
            mode='lines',
            name='Temperature (℃)'
        ))
        fig_seq_temp.update_layout(
            title='Temperature Over Time',
            xaxis_title='Year',
            yaxis_title='Temperature (℃)'
        )
        st.plotly_chart(fig_seq_temp)

        # グラフの作成 - Precipitation
        fig_seq_precip = go.Figure()
        fig_seq_precip.add_trace(go.Scatter(
            x=df_results_seq['Year'],
            y=df_results_seq['Precipitation (mm)'],
            mode='lines',
            name='Precipitation (mm)'
        ))
        fig_seq_precip.update_layout(
            title='Precipitation Over Time',
            xaxis_title='Year',
            yaxis_title='Precipitation (mm)'
        )
        st.plotly_chart(fig_seq_precip)

        # グラフの作成 - Available Water
        fig_seq_water = go.Figure()
        fig_seq_water.add_trace(go.Scatter(
            x=df_results_seq['Year'],
            y=df_results_seq['Available Water'],
            mode='lines',
            name='Available Water'
        ))
        fig_seq_water.update_layout(
            title='Available Water Over Time',
            xaxis_title='Year',
            yaxis_title='Available Water'
        )
        st.plotly_chart(fig_seq_water)

        # グラフの作成 - Crop Yield
        fig_seq_crop = go.Figure()
        fig_seq_crop.add_trace(go.Scatter(
            x=df_results_seq['Year'],
            y=df_results_seq['Crop Yield'],
            mode='lines',
            name='Crop Yield'
        ))
        fig_seq_crop.update_layout(
            title='Crop Yield Over Time',
            xaxis_title='Year',
            yaxis_title='Crop Yield'
        )
        st.plotly_chart(fig_seq_crop)

        # グラフの作成 - Flood Damage
        fig_seq_flood = go.Figure()
        fig_seq_flood.add_trace(go.Scatter(
            x=df_results_seq['Year'],
            y=df_results_seq['Flood Damage'],
            mode='lines',
            name='Flood Damage'
        ))
        fig_seq_flood.update_layout(
            title='Flood Damage Over Time',
            xaxis_title='Year',
            yaxis_title='Flood Damage'
        )
        st.plotly_chart(fig_seq_flood)
    
    # シナリオの保存とリセット
    st.sidebar.title('シナリオ管理')
    save_scenario_seq = st.sidebar.button('シナリオを保存')
    if save_scenario_seq:
        st.session_state['scenarios'][scenario_name] = df_results_seq.copy()
        st.success(f'シナリオ「{scenario_name}」を保存しました。')
    
    reset_simulation_seq = st.sidebar.button('シミュレーションをリセット')
    if reset_simulation_seq:
        st.session_state['current_year_index_seq'] = 0
        st.session_state['simulation_results_seq'] = []
        st.session_state['prev_values_seq'] = {
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
        st.session_state['decision_vars_seq'] = []
        st.rerun()
    
    # シナリオの比較
    if st.session_state['scenarios']:
        st.subheader('シナリオ比較')
        selected_scenarios_seq = st.multiselect('比較するシナリオを選択', list(st.session_state['scenarios'].keys()))
        if selected_scenarios_seq:
            # 軸の選択
            st.write('散布図の軸を選択してください。')
            variables = ['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost']
            x_axis_seq = st.selectbox('X軸', variables, index=0, key='x_axis_seq')
            y_axis_seq = st.selectbox('Y軸', variables, index=1, key='y_axis_seq')
    
            # シナリオごとの5年おきの値をプロット
            fig_scatter_seq = go.Figure()
            for scenario in selected_scenarios_seq:
                df_scenario = st.session_state['scenarios'][scenario]
                # 5年ごとのデータを取得
                df_scenario_5yrs = df_scenario[df_scenario['Year'] % 5 == 0]
                fig_scatter_seq.add_trace(go.Scatter(
                    x=df_scenario_5yrs[x_axis_seq],
                    y=df_scenario_5yrs[y_axis_seq],
                    mode='lines+markers',
                    name=scenario
                ))
            fig_scatter_seq.update_layout(
                title=f'{x_axis_seq} vs {y_axis_seq} Scatter Plot',
                xaxis_title=x_axis_seq,
                yaxis_title=y_axis_seq
            )
            st.plotly_chart(fig_scatter_seq)

# データのエクスポート機能
st.subheader('データのエクスポート')
export_format = st.selectbox('ファイル形式を選択', ['CSV', 'Excel'])
export_button = st.button('データをダウンロード')

if export_button:
    if st.session_state['scenarios']:
        # すべてのシナリオをエクスポート
        export_df = pd.concat([df for df in st.session_state['scenarios'].values()])
    else:
        export_df = pd.DataFrame()
        st.warning('エクスポートするデータがありません。')

    if not export_df.empty:
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
