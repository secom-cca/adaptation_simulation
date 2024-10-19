import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
from simulation import simulate_simulation
from utils import create_line_chart, compare_scenarios, compare_scenarios_yearly

# シミュレーションのパラメータ
start_year = 2020
end_year = 2100
total_years = end_year - start_year + 1
years = np.arange(start_year, end_year + 1)

# パラメータ辞書
params = {
    'start_year': start_year,
    'end_year': end_year,
    'total_years': total_years,
    'years': years,
    'temp_trend': 0.1,
    'temp_uncertainty': 1.0,
    'precip_trend': 0,
    'base_precip_uncertainty': 50,
    'precip_uncertainty_trend': 5,
    'base_extreme_precip_freq': 0.1,
    'extreme_precip_freq_trend': 0.05,
    'extreme_precip_freq_uncertainty': 0.1,
    'municipal_demand_trend': 0,
    'municipal_demand_uncertainty': 0.05,
    'initial_hot_days': 30.0,
    'base_temp': 15.0,
    'base_precip': 1000.0,
    'temp_to_hot_days_coeff': 2.0,
    'hot_days_uncertainty': 2.0,
    'ecosystem_threshold': 800.0,
    'temp_coefficient': 1.0,
    'max_potential_yield': 100.0,
    'optimal_irrigation_amount': 30.0,
    'flood_damage_coefficient': 100000,
    'levee_level_increment': 0.1,
    'high_temp_tolerance_increment': 0.1,
    'levee_investment_threshold': 5.0,
    'RnD_investment_threshold': 5.0,
    'levee_investment_required_years': 10,
    'RnD_investment_required_years': 10,
    'max_available_water': 2000.0,
    'evapotranspiration_amount': 600.0,
}

image_path = "causal_loop_diagram.png"  # 画像ファイルのパスを指定
st.image(image_path, caption='シミュレーションのイメージ', use_column_width=True)

# シミュレーションモードの選択
simulation_mode = st.sidebar.selectbox('シミュレーションモードを選択', ['モンテカルロシミュレーションモード', '逐次意思決定シミュレーションモード'])

# シナリオ名の入力
scenario_name = st.sidebar.text_input('シナリオ名を入力', value='シナリオ1')

# セッション状態の初期化
if 'scenarios' not in st.session_state:
    st.session_state['scenarios'] = {}

if simulation_mode == 'モンテカルロシミュレーションモード':
    st.sidebar.title('意思決定変数（5年ごと）')
    decision_years = np.arange(start_year, end_year + 1, 5)
    decision_df = pd.DataFrame({
        'Year': decision_years.astype(int),
        '灌漑水量 (Irrigation Water Amount)': [100.0]*len(decision_years),
        '放流水量 (Released Water Amount)': [100.0]*len(decision_years),
        '堤防工事費 (Levee Construction Cost)': [0.0]*len(decision_years),
        '農業研究開発費 (Agricultural R&D Cost)': [3.0]*len(decision_years)
    })
    decision_df = st.sidebar.data_editor(decision_df, use_container_width=True)
    decision_df.set_index('Year', inplace=True)

    # モンテカルロシミュレーションの設定
    num_simulations = st.sidebar.slider('モンテカルロシミュレーションの回数', 10, 500, 100, 10)

    simulate_button = st.sidebar.button('シミュレーション開始')

    if simulate_button:
        simulation_results = []

        for sim in range(num_simulations):
            # 初期値
            initial_values = {
                'temp': 15.0,
                'precip': 1000.0,
                'municipal_demand': 100.0,
                'available_water': 1000.0,
                'crop_yield': 100.0,
                'levee_level': 0.5,
                'high_temp_tolerance_level': 0.0,
                'hot_days': 30.0,
                'extreme_precip_freq': 0.1,
                'ecosystem_level': 100.0,
                'levee_investment_years': 0,
                'RnD_investment_years': 0
            }

            # シミュレーションの実行
            sim_results = simulate_simulation(years, initial_values, decision_df, params)

            # 結果をデータフレームに変換
            df_simulation = pd.DataFrame(sim_results)
            df_simulation['Simulation'] = sim
            simulation_results.append(df_simulation)

        # シミュレーション結果を保存
        df_results = pd.concat(simulation_results, ignore_index=True)
        st.session_state['scenarios'][scenario_name] = df_results.copy()
        st.success(f'シナリオ「{scenario_name}」のシミュレーションが完了しました。')

    # シミュレーション結果の表示
    if scenario_name in st.session_state['scenarios']:
        df_results = st.session_state['scenarios'][scenario_name]
        st.subheader('シミュレーション結果')

        # グラフの作成 - Temperature
        create_line_chart(
            df=df_results,
            x_column='Year',
            y_column='Temperature (℃)',
            group_column='Simulation',
            title='Temperature Over Time (All Simulations)',
            x_title='Year',
            y_title='Temperature (℃)'
        )

        # グラフの作成 - Precipitation
        create_line_chart(
            df=df_results,
            x_column='Year',
            y_column='Precipitation (mm)',
            group_column='Simulation',
            title='Precipitation Over Time (All Simulations)',
            x_title='Year',
            y_title='Precipitation (mm)'
        )

        # グラフの作成 - Available Water
        create_line_chart(
            df=df_results,
            x_column='Year',
            y_column='Available Water',
            group_column='Simulation',
            title='Available Water Over Time (All Simulations)',
            x_title='Year',
            y_title='Available Water'
        )

        # グラフの作成 - Flood Damage
        create_line_chart(
            df=df_results,
            x_column='Year',
            y_column='Flood Damage',
            group_column='Simulation',
            title='Flood Damage Over Time (All Simulations)',
            x_title='Year',
            y_title='Flood Damage'
        )

        # グラフの作成 - Crop Yield
        create_line_chart(
            df=df_results,
            x_column='Year',
            y_column='Crop Yield',
            group_column='Simulation',
            title='Crop Yield Over Time (All Simulations)',
            x_title='Year',
            y_title='Crop Yield'
        )

    # シナリオの比較と散布図
    compare_scenarios(
        scenarios_data=st.session_state['scenarios'],
        variables=['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost']
    )

elif simulation_mode == '逐次意思決定シミュレーションモード':
    # セッション状態の初期化
    if 'current_year_index_seq' not in st.session_state:
        st.session_state['current_year_index_seq'] = 0
        st.session_state['simulation_results_seq'] = []
        st.session_state['prev_values_seq'] = {
            'temp': 15.0,
            'precip': 1000.0,
            'municipal_demand': 100.0,
            'available_water': 1000.0,
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
    irrigation_water_amount = st.sidebar.number_input('灌漑水量', min_value=0.0, value=100.0, step=1.0)
    released_water_amount = st.sidebar.number_input('放流水量', min_value=0.0, value=100.0, step=1.0)
    levee_construction_cost = st.sidebar.number_input('堤防工事費', min_value=0.0, value=2.0, step=1.0)
    agricultural_RnD_cost = st.sidebar.number_input('農業研究開発費', min_value=0.0, value=3.0, step=1.0)

    # 意思決定変数をセッション状態に保存（5年ごと）
    if st.session_state['current_year_index_seq'] % 5 == 0:
        st.session_state['decision_vars_seq'].append({
            'irrigation_water_amount': irrigation_water_amount,
            'released_water_amount': released_water_amount,
            'levee_construction_cost': levee_construction_cost,
            'agricultural_RnD_cost': agricultural_RnD_cost
        })

    # シミュレーションの実行（次の5年間）
    simulate_button_seq = st.sidebar.button('次の5年へ')

    if simulate_button_seq:
        current_year_index = st.session_state['current_year_index_seq']
        next_year_index = min(current_year_index + 5, total_years)
        sim_years = years[current_year_index:next_year_index]

        prev_values = st.session_state['prev_values_seq']
        decision_vars_list = st.session_state['decision_vars_seq']

        # シミュレーションの実行
        sim_results = simulate_simulation(sim_years, prev_values, decision_vars_list, params)

        # セッション状態の更新
        if sim_results:
            # 最後の年の値を取得
            last_values = {
                'temp': sim_results[-1]['Temperature (℃)'],
                'precip': sim_results[-1]['Precipitation (mm)'],
                'municipal_demand': sim_results[-1]['Municipal Demand'],
                'available_water': sim_results[-1]['Available Water'],
                'crop_yield': sim_results[-1]['Crop Yield'],
                'levee_level': sim_results[-1]['Levee Level'],
                'high_temp_tolerance_level': sim_results[-1]['High Temp Tolerance Level'],
                'hot_days': sim_results[-1]['Hot Days'],
                'extreme_precip_freq': sim_results[-1]['Extreme Precip Frequency'],
                'ecosystem_level': sim_results[-1]['Ecosystem Level'],
                'levee_investment_years': prev_values['levee_investment_years'],
                'RnD_investment_years': prev_values['RnD_investment_years']
            }

            st.session_state['prev_values_seq'] = last_values
            st.session_state['simulation_results_seq'].extend(sim_results)
            st.session_state['current_year_index_seq'] = next_year_index

    # シミュレーション結果の表示
    if st.session_state['simulation_results_seq']:
        df_results_seq = pd.DataFrame(st.session_state['simulation_results_seq'])
        st.subheader('シミュレーション結果')

        # グラフの作成 - Temperature
        create_line_chart(
            df=df_results_seq,
            x_column='Year',
            y_column='Temperature (℃)',
            title='Temperature Over Time',
            x_title='Year',
            y_title='Temperature (℃)'
        )

        # グラフの作成 - Precipitation
        create_line_chart(
            df=df_results_seq,
            x_column='Year',
            y_column='Precipitation (mm)',
            title='Precipitation Over Time',
            x_title='Year',
            y_title='Precipitation (mm)'
        )

        # グラフの作成 - Available Water
        create_line_chart(
            df=df_results_seq,
            x_column='Year',
            y_column='Available Water',
            title='Available Water Over Time',
            x_title='Year',
            y_title='Available Water'
        )

        # グラフの作成 - Crop Yield
        create_line_chart(
            df=df_results_seq,
            x_column='Year',
            y_column='Crop Yield',
            title='Crop Yield Over Time',
            x_title='Year',
            y_title='Crop Yield'
        )

        # グラフの作成 - Flood Damage
        create_line_chart(
            df=df_results_seq,
            x_column='Year',
            y_column='Flood Damage',
            title='Flood Damage Over Time',
            x_title='Year',
            y_title='Flood Damage'
        )

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
            'available_water': 1000.0,
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

    # シナリオの比較と散布図
    compare_scenarios_yearly(
        scenarios_data=st.session_state['scenarios'],
        variables=['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost']
    )

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
