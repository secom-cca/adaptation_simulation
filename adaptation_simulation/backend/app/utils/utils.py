# utils.py

import pandas as pd
import numpy as np

BENCHMARK = {
    '収量':     dict(best=10_000, worst=0,     invert=False),
    '洪水被害': dict(best=0,       worst=200_000_000, invert=True),
    '生態系':   dict(best=100,     worst=0,     invert=False),
    '都市利便性':dict(best=100,     worst=0,     invert=False),
    '予算':     dict(best=0, worst=1_000_000_000, invert=True),
    '森林面積':dict(best=10_000,     worst=0,     invert=False),
    '住民負担':dict(best=0, worst=100_000, invert=True),
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
        '森林面積': df['Forest Area'].mean(),
        '予算': df['Municipal Cost'].sum(),
        '住民負担': df['Resident Burden'].sum(),
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
        '住民負担': df.loc[mask, 'Resident Burden'].sum(),
        '生態系': df.loc[mask, 'Ecosystem Level'].mean(),
        '森林面積': df.loc[mask, 'Forest Area'].mean(),
        '都市利便性': df.loc[mask, 'Urban Level'].mean(),
    }


# 注意：图表相关函数已移除，因为它们依赖于Streamlit
# 如需图表功能，请在前端实现或使用独立的图表服务

