#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dmdu_panel.csv 分析スクリプト

入力: frontend/public/dmdu_panel.csv
- 行: シミュレーション番号 × 年 (時系列)
- 列: オプション/結果/変数（パネル形式）

出力 JSON (2種):
1) options_yearly_means.json
   - 各オプション組み合わせ・各年ごとの結果平均値（シミュレーション100回の平均）
   - レコード形式: {
       options: { planting_trees_amount_level, house_migration_amount_level, paddy_dam_construction_cost_level },
       year: int,
       metrics: { metricName: meanValue, ... }
     }

2) options_simulation_timeseries.json
   - 各オプション組み合わせ × 各シミュレーションの時系列データ（全指標）
   - レコード形式: {
       options: {...}, simulation: int,
       years: [...],
       series: { metricName: [v1, v2, ...] }
     }

注意:
- メモリに余裕がある前提で一括読み込みします（~350MB 程度）。
- もしメモリ不足となる場合は、chunk 読み込み + 集約で 1) のみを生成するように改修してください。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Dict

import pandas as pd


CSV_PATH = Path(__file__).parent / "dmdu_panel.csv"
OUT_MEANS = Path(__file__).parent / "options_yearly_means.json"
OUT_TIMESERIES = Path(__file__).parent / "options_simulation_timeseries.json"

# 想定オプション列（要件より）
OPTION_COLS = [
    "RCP",
    "planting_trees_amount_level",
    "house_migration_amount_level",
    "paddy_dam_construction_cost_level",
    "dam_levee_construction_cost_level",
]

PARAM_COLS = [
    "unc_temp_trend",
    "unc_precip_uncertainty_trend",
    "unc_extreme_precip_freq_trend",
    "unc_extreme_precip_intensity_trend",
    "unc_municipal_demand_trend",
    "unc_flood_damage_coefficient",
    "unc_paddy_dam_cost_per_ha",
    "unc_forest_degradation_rate",
    "unc_cost_per_migration",
]

# 想定インデックス列
YEAR_CANDIDATES = ["Year", "year"]
SIM_CANDIDATES = ["Simulation", "simulation", "sim", "simulation_id", "Sim"]

# 出力対象メトリクス（固定）
TARGET_METRICS = [
    "Flood Damage",
    "Ecosystem Level",
    "Municipal Cost",
    "Crop Yield",
]


def find_column(candidates: List[str], columns: List[str]) -> str:
    """候補名から実在カラム名を見つける（大文字小文字も許容）。"""
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise ValueError(f"Required column not found. Candidates={candidates}, available={columns}")


def main(csv_path: Path, out_means: Path, out_timeseries: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # まず列一覧を取得
    cols = pd.read_csv(csv_path, nrows=0).columns.tolist()

    year_col = find_column(YEAR_CANDIDATES, cols)
    sim_col = find_column(SIM_CANDIDATES, cols)

    # オプション列の存在確認（不足はエラー）
    for oc in OPTION_COLS:
        if oc not in cols:
            raise ValueError(f"Option column missing in CSV: {oc}")

    # メトリクス列は指定の4項目のみを採用
    available = set(cols)
    metric_cols = [c for c in TARGET_METRICS if c in available]
    if not metric_cols:
        raise ValueError("None of target metrics found. Expected any of: " + ", ".join(TARGET_METRICS))

    # 一括読み込み（必要に応じて dtype 指定や category 化を検討）
    df = pd.read_csv(csv_path)

    # 型整備（年は int, シミュレーションは int を想定）
    df[year_col] = df[year_col].astype(int)
    df[sim_col] = df[sim_col].astype(int)
    # オプション列の型: RCP は文字列のまま、それ以外は整数
    numeric_option_cols = [c for c in OPTION_COLS if c != "RCP"]
    for oc in numeric_option_cols:
        df[oc] = pd.to_numeric(df[oc], errors="coerce").fillna(0).astype(int)

    # 1) 各オプション × 年 の平均値
    grp_keys = OPTION_COLS + [year_col]
    means = df.groupby(grp_keys, as_index=False)[metric_cols].mean(numeric_only=True)
    means_records: List[Dict] = []
    for _, row in means.iterrows():
        options = {}
        for oc in OPTION_COLS:
            if oc == "RCP":
                options[oc] = str(row[oc])
            else:
                options[oc] = int(row[oc])
        metrics = {m: float(row[m]) for m in metric_cols}
        means_records.append({
            "options": options,
            "year": int(row[year_col]),
            "metrics": metrics,
        })

    pd.Series(means_records).to_json(out_means, orient="values", force_ascii=False, indent=2)

    # 2) 各オプション × 各シミュレーションの時系列
    # 年でソートしてリスト化
    df_sorted = df.sort_values([*OPTION_COLS, sim_col, year_col])
    timeseries_records: List[Dict] = []
    # params 用の利用可能カラム（平均では落ちるため元 df から判定）
    available_param_cols = [pc for pc in PARAM_COLS if pc in df.columns]

    for key, sub in df_sorted.groupby(OPTION_COLS + [sim_col]):
        # key は (opt1, opt2, opt3, sim_id) のタプル想定
        if not isinstance(key, tuple):
            key = (key,)
        opt_vals = key[: len(OPTION_COLS)]
        sim_id = key[len(OPTION_COLS)]

        options = {}
        for oc, val in zip(OPTION_COLS, opt_vals):
            if oc == "RCP":
                options[oc] = str(val)
            else:
                options[oc] = int(val)
        # パラメータはグループ内で一定のはずなので代表行から取得
        brow = sub.iloc[0]
        params = {pc: float(pd.to_numeric(brow[pc], errors="coerce")) for pc in available_param_cols}
        series = {m: pd.to_numeric(sub[m], errors="coerce").astype(float).tolist() for m in metric_cols}
        timeseries_records.append({
            "options": options,
            "simulation": int(sim_id),
            "params": params,
            "series": series,
        })

    pd.Series(timeseries_records).to_json(out_timeseries, orient="values", force_ascii=False, indent=2)

    print(f"Wrote: {out_means}")
    print(f"Wrote: {out_timeseries}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze dmdu_panel.csv and output JSON summaries")
    parser.add_argument("--csv", type=str, default=str(CSV_PATH), help="Path to dmdu_panel.csv")
    parser.add_argument("--out-means", type=str, default=str(OUT_MEANS), help="Output JSON for yearly means")
    parser.add_argument("--out-timeseries", type=str, default=str(OUT_TIMESERIES), help="Output JSON for timeseries")
    args = parser.parse_args()

    main(Path(args.csv), Path(args.out_means), Path(args.out_timeseries))


