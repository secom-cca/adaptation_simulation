import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
from src.simulation import simulate_simulation
from src.utils import create_line_chart, compare_scenarios, compare_scenarios_yearly, BENCHMARK, BLOCKS
from config import DEFAULT_PARAMS, rcp_climate_params

# RCPシナリオ選択
rcp_options = {'RCP1.9': 1.9, 'RCP2.6': 2.6, 'RCP4.5': 4.5, 'RCP6.0': 6.0, 'RCP8.5': 8.5}
selected_rcp = st.sidebar.selectbox('Select RCP Scenario / RCPシナリオを選択', list(rcp_options.keys()), index=1)
rcp_value = rcp_options[selected_rcp]

# パラメータの読み込みと上書き
params = DEFAULT_PARAMS.copy()
params.update(rcp_climate_params[rcp_value])
timestep_year = 25

start_year = params['start_year']
end_year = params['end_year']
total_years = params['total_years']
years = params['years']

image_path = "fig/mayfes_merge.png"  # 画像ファイルのパスを指定
st.image(image_path, caption='Simulator Overview', use_container_width=True)

# シミュレーションモードの選択
simulation_mode = st.sidebar.selectbox('Select Simulation Mode / シミュレーションモードを選択', ['Sequential Decision-Making Mode', 'Monte Carlo Simulation Mode'])

# シナリオ名の入力
scenario_name = st.sidebar.text_input('Input scenario name / シナリオ名を入力', value='シナリオ1')

# セッション状態の初期化
if 'scenarios' not in st.session_state:
    st.session_state['scenarios'] = {}

if simulation_mode == 'Sequential Decision-Making Mode':
    np.random.seed(255)
    # セッション状態の初期化
    if 'current_year_index_seq' not in st.session_state:
        st.session_state['current_year_index_seq'] = 0
        st.session_state['simulation_results_seq'] = []
        st.session_state['prev_values_seq'] = {}
        st.session_state['decision_vars_seq'] = []

    # 意思決定変数の入力（現在の期間用）
    st.sidebar.title(f'Decision Making for the next {timestep_year} yrs / 意思決定変数（次の{timestep_year}年間）')
    st.sidebar.write(f'今後{timestep_year}年間の政策を考えてみましょう')
    planting_trees_amount = st.sidebar.slider('植林・森林保全（ha/年）', min_value=0, max_value=100, value=50, step=50)
    house_migration_amount = st.sidebar.slider('住宅移転（軒/年）', min_value=0, max_value=100, value=50, step=50)
    dam_levee_construction_cost = st.sidebar.slider('ダム・堤防工事（億円/年）', min_value=0.0, max_value=2.0, value=1.0, step=1.0)
    paddy_dam_construction_cost = st.sidebar.slider('田んぼダム工事（百万円/年）', min_value=0.0, max_value=10.0, value=5.0, step=5.0)
    capacity_building_cost = st.sidebar.slider('防災訓練・普及啓発（百万円/年）', min_value=0.0, max_value=10.0, value=5.0, step=5.0)
    agricultural_RnD_cost = st.sidebar.slider('農業研究開発（千万円/年）', min_value=0.0, max_value=10.0, value=0.0, step=5.0)
    transportation_invest = st.sidebar.slider('交通網の充実（千万円/年）', min_value=0.0, max_value=10.0, value=0.0, step=5.0)
    # irrigation_water_amount = st.sidebar.slider('Irrigation Water Amount / 灌漑水量：増やすと収量が多くなります', min_value=0, max_value=200, value=100, step=10)
    # released_water_amount = st.sidebar.slider('Released Water Amount / 放流水量：増やすと洪水リスクが小さくなります', min_value=0, max_value=200, value=100, step=10)
    # levee_construction_cost = st.sidebar.slider('Levee Construction Investment / 堤防工事費：増やすと洪水リスクが小さくなります', min_value=0.0, max_value=10.0, value=2.0, step=1.0)
    # agricultural_RnD_cost = st.sidebar.slider('Agricultural R&D Investment / 農業研究開発費：増やすと高温に強い品種ができます', min_value=0.0, max_value=10.0, value=3.0, step=1.0)

    # 意思決定変数をセッション状態に保存
    if st.session_state['current_year_index_seq'] % timestep_year == 0:
        st.session_state['decision_vars_seq'].append({
            'planting_trees_amount':planting_trees_amount,
            'house_migration_amount':house_migration_amount,
            'dam_levee_construction_cost': dam_levee_construction_cost,
            'paddy_dam_construction_cost':paddy_dam_construction_cost,
            'capacity_building_cost': capacity_building_cost,
            'agricultural_RnD_cost':agricultural_RnD_cost,
            'transportation_invest':transportation_invest,
            # 'irrigation_water_amount': irrigation_water_amount,
            # 'released_water_amount': released_water_amount,
            # 'levee_construction_cost': levee_construction_cost,
        })

    # シミュレーションの実行（次の{timestep_year}年間）
    simulate_button_seq = st.sidebar.button(f'Next / 次の{timestep_year}年へ')

    if simulate_button_seq:
        current_year_index = st.session_state['current_year_index_seq']
        next_year_index = min(current_year_index + timestep_year, total_years)
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
                'urban_level': sim_results[-1]['Urban Level'],
                'levee_investment_total': sim_results[-1]['Levee investment total'],
                'RnD_investment_total': sim_results[-1]['RnD investment total'],
                'resident_capacity': sim_results[-1]['Resident capacity'],
                'forest_area': sim_results[-1]['Forest Area'],
                'planting_history': sim_results[-1]['planting_history'],
                'transportation_level' : sim_results[-1]['transportation_level'],
                'risky_house_total' : sim_results[-1]['risky_house_total'],
                'non_risky_house_total' : sim_results[-1]['non_risky_house_total'],
                'paddy_dam_area' : sim_results[-1]['paddy_dam_area'],
            }

            st.session_state['prev_values_seq'] = last_values
            st.session_state['simulation_results_seq'].extend(sim_results)
            st.session_state['current_year_index_seq'] = next_year_index

    # シミュレーション結果の表示
    if st.session_state['simulation_results_seq']:
        df_results_seq = pd.DataFrame(st.session_state['simulation_results_seq'])
        st.subheader('Simulation results / シミュレーション結果')

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

    if st.session_state['current_year_index_seq'] >= total_years:
        st.sidebar.write('Simulation done! Click Save and check the results. / シミュレーションが完了しました！「シナリオを保存」して結果を見てみましょう')

    # # シナリオの保存とリセット
    st.sidebar.title('Scenario Management / シナリオ管理')
    save_scenario_seq = st.sidebar.button('Save / シナリオを保存')
    if save_scenario_seq:
        if st.session_state['current_year_index_seq'] < total_years:
            st.sidebar.warning(f'Please run the simulation till the final year / 最終年度までシミュレーションを回してから保存してください')
        else:
            st.session_state['scenarios'][scenario_name] = df_results_seq.copy()
            st.success(f'Successfully saved scenario "{scenario_name}" / シナリオ「{scenario_name}」を保存しました。')

    st.sidebar.write('After checking the results, reset and try a different scenario / 一通り結果を確認したら，リセットして別のシナリオを作りましょう')
    reset_simulation_seq = st.sidebar.button('Reset / シミュレーションをリセット')
    if reset_simulation_seq:
        st.session_state['current_year_index_seq'] = 0
        st.session_state['simulation_results_seq'] = []
        st.session_state['prev_values_seq'] = {}
        st.session_state['decision_vars_seq'] = []
        st.rerun()

    # シナリオの比較と散布図
    compare_scenarios_yearly(
        scenarios_data=st.session_state['scenarios'],
        variables=['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Urban Level', 'Municipal Cost']
    )

elif simulation_mode == 'Monte Carlo Simulation Mode':
    st.sidebar.title(f'Decision-Making Variables (every {timestep_year} yrs) / 意思決定変数（{timestep_year}年ごと）')
    decision_years = np.arange(start_year, end_year + 1, timestep_year)
    decision_df = pd.DataFrame({
        'Year': decision_years.astype(int),
        'planting_trees_amount': [100.0]*len(decision_years),
        'house_migration_amount': [50.0]*len(decision_years),
        'dam_levee_construction_cost': [1.0]*len(decision_years),  # 億円
        'paddy_dam_construction_cost': [5.0]*len(decision_years),  # 百万円
        'capacity_building_cost': [5.0]*len(decision_years),
        'agricultural_RnD_cost': [5.0]*len(decision_years),
        'transportation_invest': [5.0]*len(decision_years),
    })
    decision_df = st.sidebar.data_editor(decision_df, use_container_width=True)
    decision_df.set_index('Year', inplace=True)

    # モンテカルロシミュレーションの設定
    num_simulations = st.sidebar.slider('Number of simulations / モンテカルロシミュレーションの回数', 10, 500, 100, 10)

    simulate_button = st.sidebar.button('Run / シミュレーション開始')

    if simulate_button:
        simulation_results = []

        for sim in range(num_simulations):
            # 初期値
            initial_values = {}

            # シミュレーションの実行
            sim_results = simulate_simulation(years, initial_values, decision_df, params)

            # 結果をデータフレームに変換
            df_simulation = pd.DataFrame(sim_results)
            df_simulation['Simulation'] = sim
            simulation_results.append(df_simulation)

        # シミュレーション結果を保存
        df_results = pd.concat(simulation_results, ignore_index=True)
        st.session_state['scenarios'][scenario_name] = df_results.copy()
        st.success(f'Successfully done scenario "{scenario_name}" / シナリオ「{scenario_name}」のシミュレーションが完了しました。')

    # シミュレーション結果の表示
    if scenario_name in st.session_state['scenarios']:
        df_results = st.session_state['scenarios'][scenario_name]
        st.subheader('Simulation results / シミュレーション結果')

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
        variables=['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Urban Level', 'Municipal Cost']
    )



# シナリオの指標を集計
def calculate_scenario_indicators(scenario_data):
    indicators = {
        '収量': scenario_data['Crop Yield'].sum(),
        '洪水被害': scenario_data['Flood Damage'].sum(),
        '生態系': scenario_data.loc[scenario_data['Year'] == end_year, 'Ecosystem Level'].values[0],
        '都市利便性': scenario_data.loc[scenario_data['Year'] == end_year, 'Urban Level'].values[0],
        '予算': scenario_data['Municipal Cost'].sum(),
        '住民負担': scenario_data['Resident Burden'].mean(),
        '森林面積': scenario_data.loc[scenario_data['Year'] == end_year, 'Forest Area'].values[0],
    }
    return indicators

BAL_PARAMS = dict(field_sd_max=20, period_sd_max=15)

def _balance_score(nums: list[float], sd_max: float) -> float:
    """数値リストを 0–100 のバランス点に変換"""
    sd = float(np.std(nums, ddof=0))
    return float(np.clip(100 * (1 - sd / sd_max), 0, 100))

def _scale_to_100(raw_val: float, metric: str) -> float:
    """単一値を 0-100 点に変換（ベンチマーク利用）"""
    b = BENCHMARK[metric]
    v = np.clip(raw_val, b['worst'], b['best']) if b['worst'] < b['best'] \
        else np.clip(raw_val, b['best'], b['worst'])
    if b['invert']:                               # 小さいほど良い
        score = 100 * (b['worst'] - v) / (b['worst'] - b['best'])
    else:                                         # 大きいほど良い
        score = 100 * (v - b['worst']) / (b['best'] - b['worst'])
    return float(np.round(score, 1))

def _raw_values(df: pd.DataFrame, start: int, end: int) -> dict:
    """2050・2075・2100 年時点の raw 指標を取り出す"""
    mask = (df['Year'] >= start) & (df['Year'] <= end)
    return {
        '収量':       df.loc[mask, 'Crop Yield'].sum(),
        '洪水被害':   df.loc[mask, 'Flood Damage'].sum(),
        '予算':       df.loc[mask, 'Municipal Cost'].sum(),
        '生態系':     df.loc[mask, 'Ecosystem Level'].mean(),
        '都市利便性': df.loc[mask, 'Urban Level'].mean(),
        '森林面積':     df.loc[mask, 'Forest Area'].mean(),
        '住民負担': df.loc[mask, 'Resident Burden'].mean(),
    }

# シナリオごとに集計
if st.session_state['scenarios']:
    scenario_indicators = {name: calculate_scenario_indicators(data) for name, data in st.session_state['scenarios'].items()}

    # DataFrameに変換し、指標を基に順位づけ
    df_indicators = pd.DataFrame(scenario_indicators).T
    df_indicators['収量順位'] = df_indicators['収量'].rank(ascending=False)
    df_indicators['洪水被害順位'] = df_indicators['洪水被害'].rank(ascending=True)
    df_indicators['生態系順位'] = df_indicators['生態系'].rank(ascending=False)
    df_indicators['都市利便性順位'] = df_indicators['都市利便性'].rank(ascending=False)
    df_indicators['予算順位'] = df_indicators['予算'].rank(ascending=True)
    df_indicators['森林面積順位'] = df_indicators['森林面積'].rank(ascending=False)
    df_indicators['住民負担順位'] = df_indicators['住民負担'].rank(ascending=True)

    # 結果の表示
    st.subheader('Metrics and Rankings / シナリオごとの指標と順位')
    st.write(df_indicators)

    records = []
    for sc_name, df in st.session_state['scenarios'].items():
        for s, e, label in BLOCKS:
            raw = _raw_values(df, s, e)
            scores = {k: _scale_to_100(v, k) for k, v in raw.items()}  # 既存の _scale_to_100 を利用
            scores.update({'Scenario': sc_name, 'Period': label})
            records.append(scores)

    score_df = (
        pd.DataFrame(records)
          .set_index(['Scenario', 'Period'])            # MultiIndex
          .sort_index(level='Period')                   # 表示順をブロック順に
    )

    st.subheader('Period Scores (0–100 点)')
    st.write(score_df.style.format('{:.1f}'))

    field_balance = (
        score_df.groupby(['Scenario', 'Period'])
                .apply(lambda sub: _balance_score(sub.values, BAL_PARAMS['field_sd_max']))
                .groupby('Scenario').mean()        # 3 ブロック平均
                .rename('分野間バランス')
    )

    # ブロック間バランス：指標ごとに 3 ブロックの SD（5 指標平均）
    block_balance = (
        score_df.stack()              # → Scenario, Period, Metric
                .unstack('Period')    # 列=Period
                .groupby(level=0)     # Scenario ごと
                .apply(lambda df:
                    np.mean([_balance_score(row.values, BAL_PARAMS['period_sd_max'])
                                for _, row in df.iterrows()]))
                .rename('年代間バランス')
)

    balance_df = pd.concat([field_balance, block_balance], axis=1)
    st.subheader('Balance Scores (0–100)')
    st.write(balance_df.style.format('{:.1f}'))

# データのエクスポート機能
st.subheader('Export / データのエクスポート')
# export_format = st.selectbox('ファイル形式を選択', ['CSV', 'Excel'])
export_button = st.button('Download / データをダウンロード')

if export_button:
    if st.session_state['scenarios']:
        # すべてのシナリオをエクスポート
        export_df = pd.concat([df for df in st.session_state['scenarios'].values()])
    else:
        export_df = pd.DataFrame()
        st.warning('No data to export')

    if not export_df.empty:
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(label='Download CSV', data=csv, file_name='simulation_results.csv', mime='text/csv')