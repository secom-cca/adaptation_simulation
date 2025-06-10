# utils.py

import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np

BENCHMARK = {
    '収量':     dict(best=10_000, worst=0,     invert=False),
    '洪水被害': dict(best=0,       worst=200_000_000, invert=True),
    '生態系':   dict(best=100,     worst=0,     invert=False),
    '都市利便性':dict(best=100,     worst=0,     invert=False),
    '予算':     dict(best=0, worst=1_000_000_000, invert=True),
}

BLOCKS = [
    (2026, 2050, '2026-2050'),
    (2051, 2075, '2051-2075'),
    (2076, 2100, '2076-2100')
]

def calculate_scenario_indicators(df: pd.DataFrame) -> dict:
    last_ecosystem = df.loc[df['Year'] == 2100, 'Ecosystem Level']
    ecosystem_level_end = last_ecosystem.values[0] if not last_ecosystem.empty else float('nan')
    return {
        '収量': df['Crop Yield'].sum(),
        '洪水被害': df['Flood Damage'].sum(),
        '生態系': ecosystem_level_end,
        '予算': df['Municipal Cost'].sum(),
        '都市利便性': df['Urban Level'].mean(),
    }

def aggregate_blocks(df: pd.DataFrame) -> list[dict]:
    records = []
    for s, e, label in BLOCKS:
        mask = (df['Year'] >= s) & (df['Year'] <= e)
        if df.loc[mask].empty:
            continue
        raw = _raw_values(df, s, e)
        score = {k: _scale_to_100(v, k) for k, v in raw.items()}
        total = float(np.mean(list(score.values())))
        records.append(dict(period=label, raw=raw, score=score, total_score=total))
    return records

def _scale_to_100(raw_val: float, metric: str) -> float:
    b = BENCHMARK[metric]
    v = np.clip(raw_val, b['worst'], b['best']) if b['worst'] < b['best'] else np.clip(raw_val, b['best'], b['worst'])
    if b['invert']:
        score = 100 * (b['worst'] - v) / (b['worst'] - b['best'])
    else:
        score = 100 * (v - b['worst']) / (b['best'] - b['worst'])
    return float(np.round(score, 1))

def _raw_values(df: pd.DataFrame, start: int, end: int) -> dict:
    mask = (df['Year'] >= start) & (df['Year'] <= end)
    return {
        '収量': df.loc[mask, 'Crop Yield'].sum(),
        '洪水被害': df.loc[mask, 'Flood Damage'].sum(),
        '予算': df.loc[mask, 'Municipal Cost'].sum(),
        '生態系': df.loc[mask, 'Ecosystem Level'].mean(),
        '都市利便性': df.loc[mask, 'Urban Level'].mean(),
    }


def create_line_chart(df, x_column, y_column, group_column=None, title='', x_title='', y_title=''):
    fig = go.Figure()
    if group_column:
        groups = df[group_column].unique()
        for group in groups:
            df_group = df[df[group_column] == group]
            fig.add_trace(go.Scatter(
                x=df_group[x_column],
                y=df_group[y_column],
                mode='lines',
                name=f'{group}',
                line=dict(width=1),
                opacity=0.2,
                showlegend=False
            ))
    else:
        fig.add_trace(go.Scatter(
            x=df[x_column],
            y=df[y_column],
            mode='lines',
            name=y_column
        ))
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title
    )
    st.plotly_chart(fig)

def create_scatter_plot(data, x_axis, y_axis, scenario_column='Scenario', title=''):
    fig = go.Figure()
    for scenario in data[scenario_column].unique():
        df_scenario = data[data[scenario_column] == scenario]
        fig.add_trace(go.Scatter(
            x=df_scenario[x_axis],
            y=df_scenario[y_axis],
            mode='markers',
            name=scenario,
            opacity=0.7
        ))
    fig.update_layout(
        title=title,
        xaxis_title=x_axis,
        yaxis_title=y_axis
    )
    st.plotly_chart(fig)

def compare_scenarios(scenarios_data, variables, x_axis_label='X軸', y_axis_label='Y軸'):
    st.subheader('Scenario Comparison / シナリオ比較')
    selected_scenarios = st.multiselect('Choose scenarios / 比較するシナリオを選択', list(scenarios_data.keys()))
    if selected_scenarios:
        # 軸の選択
        st.write('Choose Metrics / 散布図の軸を選択してください。')
        x_axis = st.selectbox(x_axis_label, variables, index=0)
        y_axis = st.selectbox(y_axis_label, variables, index=1)
        
        # シナリオごとのデータを結合
        combined_data = pd.DataFrame()
        for scenario in selected_scenarios:
            df_scenario = scenarios_data[scenario].copy()
            df_scenario['Scenario'] = scenario
            combined_data = pd.concat([combined_data, df_scenario], ignore_index=True)
        
        # 各シナリオの総額または平均を計算（必要に応じて）
        if 'Simulation' in combined_data.columns:
            # モンテカルロシミュレーションの場合、各シミュレーションの総和を計算
            sim_totals = combined_data.groupby(['Scenario', 'Simulation']).agg({x_axis: 'sum', y_axis: 'sum'}).reset_index()
        else:
            # 逐次意思決定シミュレーションの場合、年ごとの値をそのまま使用
            sim_totals = combined_data.groupby(['Scenario', 'Year']).agg({x_axis: 'sum', y_axis: 'sum'}).reset_index()
        
        # 散布図の作成
        create_scatter_plot(
            data=sim_totals,
            x_axis=x_axis,
            y_axis=y_axis,
            scenario_column='Scenario',
            title=f'{x_axis} vs {y_axis} Scatter Plot'
        )

def compare_scenarios_yearly(scenarios_data, variables, x_axis_label='X軸', y_axis_label='Y軸'):
    st.subheader('Scenario Comparison / シナリオ比較')
    selected_scenarios = st.multiselect('Choose scenarios / 比較するシナリオを選択してください', list(scenarios_data.keys()))
    # selected_scenarios = list(scenarios_data.keys())
    if selected_scenarios:
        # 軸の選択
        x_axis = st.selectbox(x_axis_label, variables, index=0)
        y_axis = st.selectbox(y_axis_label, variables, index=1)

        # シナリオごとの10年おきの値をプロット
        fig_scatter_seq = go.Figure()

        for scenario in selected_scenarios:
            df_scenario = scenarios_data[scenario].copy()

            # 10年ごとのデータを取得
            df_scenario_10yrs = df_scenario[df_scenario['Year'] % 10 == 0]

            # 年に基づいてマーカーサイズを変える
            marker_size = 10 + (df_scenario_10yrs['Year'] - df_scenario_10yrs['Year'].min()) / 5  # 年が進むごとにマーカーを大きく

            fig_scatter_seq.add_trace(go.Scatter(
                x=df_scenario_10yrs[x_axis],
                y=df_scenario_10yrs[y_axis],
                mode='lines+markers',
                name=scenario,
                text=df_scenario_10yrs['Year'].astype(str),  # Year情報をポイントに追加
                marker=dict(size=marker_size),  # 年に基づいてマーカーサイズを変更
                hovertemplate='<b>Year: %{text}</b><br>' +  # カーソルを合わせた際に表示される
                              f'{x_axis}: %{{x}}<br>{y_axis}: %{{y}}<extra></extra>'
            ))

        fig_scatter_seq.update_layout(
            title=f'{x_axis} vs {y_axis} Scatter Plot',
            xaxis_title=x_axis,
            yaxis_title=y_axis
        )
        st.plotly_chart(fig_scatter_seq)

