# -*- coding: utf-8 -*-
"""
Adaptive Pathways Pipeline (Self-Contained)
------------------------------------------
What this script does (out-of-the-box):
1) Samples uncertainties (LHS) and runs a toy multi-sector simulator (3 KPIs).
2) Computes multi-objective Minimax Regret per KPI and the Pareto front.
3) Extracts interpretable rules:
   - PRIM (Patient Rule Induction Method) for high-risk "boxes"
   - Decision Tree rules (if scikit-learn available), else quantile fallback
4) Builds a DAPP plan (signals/triggers/switch actions) from PRIM & Tree rules.
5) Saves CSV outputs and an auto-filled Excel workbook.

Outputs (written to output/dapp directory):
- simulated_scenarios_mo.csv
- worst_regret_per_kpi.csv
- prim_boxes_baseline.csv
- dapp_plan.csv
- adaptive_pathways_filled.xlsx   (if openpyxl/xlsxwriter are available)
- dt_rules_baseline.txt           (if scikit-learn is available)

Usage:
    python adaptive_pathways_pipeline.py

Dependencies:
    numpy, pandas
    (optional) scikit-learn   -> for DecisionTree rules
    (optional) openpyxl, xlsxwriter -> for Excel export

You can install optional deps with:
    pip install scikit-learn openpyxl xlsxwriter
"""

import os
import sys
import math
import json
import time
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date

# Optional libraries (graceful fallback if missing)
try:
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    SKLEARN_OK = True
except Exception as e:
    SKLEARN_OK = False
    SKLEARN_ERR = str(e)

try:
    import openpyxl  # noqa: F401
    OPENPYXL_OK = True
except Exception as e:
    OPENPYXL_OK = False
    OPENPYXL_ERR = str(e)

# ------ 0) Configs ------
BASELINE_STRATEGY = "B_efficiency10"
RISK_KPI = "shortage_rate"
RISK_THRESH = 0.05
RANDOM_SEED = 2025
N_SAMPLES = 4000

# ------ 1) LHS Sampling ------
def lhs(n_samples: int, n_dim: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    result = np.empty((n_samples, n_dim))
    for j in range(n_dim):
        cut = (np.arange(n_samples) + rng.random(n_samples)) / n_samples
        rng.shuffle(cut)
        result[:, j] = cut
    return result

# ------ 2) Simulator ------
def simulate_cases(n: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    bounds = {
        "rain_change": (-0.30, 0.10),
        "pop_growth": (0.00, 0.30),
        "price_shock": (-0.10, 0.20),
        "temp_increase": (0.0, 3.0),
        "tech_yield_trend": (0.0, 0.20)
    }
    X_names = list(bounds.keys())
    U = lhs(n, len(bounds), seed=seed)
    X = np.zeros_like(U)
    for j, k in enumerate(X_names):
        lo, hi = bounds[k]
        X[:, j] = lo + (hi - lo) * U[:, j]
    dfX = pd.DataFrame(X, columns=X_names)

    base_supply = 100.0
    base_demand = 100.0

    strategies = {
        "A_statusquo":   {"eff_improve": 0.00, "new_capacity": 0.00, "annual_cost": 0.5},
        "B_efficiency10":{"eff_improve": 0.10, "new_capacity": 0.05, "annual_cost": 1.0},
        "C_expand20":    {"eff_improve": 0.15, "new_capacity": 0.20, "annual_cost": 2.5},
    }

    price_elasticity = -0.3
    climate_penalty = lambda T: (1.0 - 0.02 * T)

    rows = []
    for s_name, s in strategies.items():
        S = (
            base_supply * (1.0 + dfX["rain_change"].values) *
            (1.0 + s["eff_improve"]) *
            (1.0 + dfX["tech_yield_trend"].values) *
            climate_penalty(dfX["temp_increase"].values)
            +
            base_supply * s["new_capacity"]
        )
        D = base_demand * (1.0 + dfX["pop_growth"].values) * (1.0 + price_elasticity * dfX["price_shock"].values)
        shortage = np.maximum(0.0, D - S)
        shortage_rate = shortage / np.maximum(D, 1e-9)

        # KPIs
        kpi_shortage = shortage_rate  # minimize
        kpi_cost = np.full_like(kpi_shortage, s["annual_cost"])  # minimize
        kpi_env  = np.maximum(0.0, -dfX["rain_change"].values) * (0.5 + 2.0 * s["new_capacity"])  # minimize

        for i in range(n):
            rows.append({
                "strategy": s_name,
                **{k: dfX.loc[i, k] for k in X_names},
                "shortage_rate": float(kpi_shortage[i]),
                "annual_cost": float(kpi_cost[i]),
                "env_impact": float(kpi_env[i]),
                "risk_label": int(kpi_shortage[i] >= RISK_THRESH),
            })
    return pd.DataFrame(rows)

# ------ 3) Minimax Regret per KPI ------
KPI_INFO = {
    "shortage_rate": {"sense": "min"},
    "annual_cost":   {"sense": "min"},
    "env_impact":    {"sense": "min"}
}
KEY_COLS = ["rain_change","pop_growth","price_shock","temp_increase","tech_yield_trend"]

def minimax_regret_per_kpi(df: pd.DataFrame, kpi_info: Dict[str, Dict]) -> pd.DataFrame:
    tmp = df[KEY_COLS + ["strategy"] + list(kpi_info.keys())].copy()
    for c in KEY_COLS:
        tmp[c] = tmp[c].round(6)
    rows = []
    for strat, g in tmp.groupby("strategy"):
        row = {"strategy": strat}
        for kpi, meta in kpi_info.items():
            if meta["sense"] == "min":
                best = tmp.groupby(KEY_COLS)[kpi].min().reset_index().rename(columns={kpi: f"best_{kpi}"})
                mg = g.merge(best, on=KEY_COLS, how="left")
                reg = mg[kpi] - mg[f"best_{kpi}"]
            else:
                best = tmp.groupby(KEY_COLS)[kpi].max().reset_index().rename(columns={kpi: f"best_{kpi}"})
                mg = g.merge(best, on=KEY_COLS, how="left")
                reg = mg[f"best_{kpi}"] - mg[kpi]
            row[f"worst_regret_{kpi}"] = float(reg.max())
        rows.append(row)
    return pd.DataFrame(rows)

def pareto_front(table: pd.DataFrame, cols: List[str]) -> np.ndarray:
    data = table[cols].values
    is_dom = np.zeros(len(data), dtype=bool)
    for i in range(len(data)):
        for j in range(len(data)):
            if i == j:
                continue
            if np.all(data[j] <= data[i]) and np.any(data[j] < data[i]):
                is_dom[i] = True
                break
    return ~is_dom

# ------ 4) Decision Tree Rules (with fallback) ------
def adaptive_rules_tree(df: pd.DataFrame, strategy: str,
                        target_col: str = RISK_KPI, thr: float = RISK_THRESH,
                        max_depth: int = 4, leaf_grid=(150,100,60,40,20,10)):
    features = KEY_COLS
    sub = df[df["strategy"]==strategy].copy()
    y = (sub[target_col] >= thr).astype(int).values
    X = sub[features].values
    rules = []
    used_leaf = None
    report = ""
    rules_text = ""

    if SKLEARN_OK:
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=7, stratify=y)
        for min_leaf in leaf_grid:
            clf = DecisionTreeClassifier(max_depth=max_depth, min_samples_leaf=min_leaf, random_state=7)
            clf.fit(Xtr, ytr)
            if not report:
                report = classification_report(yte, clf.predict(Xte), digits=3)
                try:
                    rules_text = export_text(clf, feature_names=features)
                except Exception:
                    rules_text = ""
            tree = clf.tree_
            tmp_rules = []
            def traverse(node_id, conditions):
                if tree.feature[node_id] == -2:  # leaf
                    counts = tree.value[node_id][0]
                    label = int(np.argmax(counts))
                    total = counts.sum()
                    risk_rate = counts[1] / total if total>0 else 0.0
                    if label == 1 and total >= min_leaf:
                        tmp_rules.append({"conditions": conditions.copy(), "n": int(total), "risk_rate": float(risk_rate)})
                    return
                feat = features[tree.feature[node_id]]
                thr_v = tree.threshold[node_id]
                traverse(tree.children_left[node_id], conditions + [f"{feat} <= {thr_v:.2f}"])
                traverse(tree.children_right[node_id], conditions + [f"{feat} > {thr_v:.2f}"])
            traverse(0, [])
            if tmp_rules:
                tmp_rules.sort(key=lambda r: (r["risk_rate"]*r["n"]), reverse=True)
                rules = tmp_rules
                used_leaf = min_leaf
                break

    # Fallback (or enhance) if no rules found
    if not rules:
        risk = sub[sub[target_col] >= thr]
        if len(risk) > 0:
            q = risk[KEY_COLS].quantile([0.2, 0.8]).round(2)
            conditions = [
                f"rain_change <= {q.loc[0.2,'rain_change']:.2f}",
                f"temp_increase >= {q.loc[0.8,'temp_increase']:.2f}",
                f"pop_growth >= {q.loc[0.8,'pop_growth']:.2f}"
            ]
            rules = [{"conditions": conditions, "n": int(len(risk)), "risk_rate": float((risk[target_col]>=thr).mean())}]
        else:
            rules = [{"conditions":["rain_change <= -0.15","pop_growth >= 0.20"], "n":0, "risk_rate":0.0}]

    return rules, used_leaf, report, rules_text

# ------ 5) PRIM ------
@dataclass
class PrimBox:
    bounds: Dict[str, Tuple[float, float]]
    mass: float
    density: float
    coverage: float
    n_in: int
    n_pos_in: int

def _in_box(dfX: pd.DataFrame, bounds: Dict[str, Tuple[float, float]]):
    mask = np.ones(len(dfX), dtype=bool)
    for f, (lo, hi) in bounds.items():
        mask &= (dfX[f] >= lo) & (dfX[f] <= hi)
    return mask

def prim_single(dfX: pd.DataFrame, y: np.ndarray, peeling_alpha=0.05, pasting_alpha=0.01,
                min_mass=0.05, min_density=0.6, max_iters=60) -> Optional[PrimBox]:
    bounds = {f: (dfX[f].min(), dfX[f].max()) for f in dfX.columns}
    n_total = len(dfX)
    y = y.astype(int)
    # Peeling
    for _ in range(max_iters):
        mask = _in_box(dfX, bounds)
        n_in = mask.sum()
        if n_in / n_total < min_mass:
            break
        dens = y[mask].mean() if n_in>0 else 0.0
        best_gain = 0.0
        best_bounds = None
        for f in dfX.columns:
            vals = dfX.loc[mask, f].values
            if len(vals) == 0:
                continue
            low, high = bounds[f]
            q_low  = np.quantile(vals, peeling_alpha)
            q_high = np.quantile(vals, 1.0 - peeling_alpha)
            # peel lower
            b1 = dict(bounds); b1[f] = (max(low, q_low), high)
            m1 = _in_box(dfX, b1)
            if m1.sum()/n_total >= min_mass:
                d1 = y[m1].mean() if m1.sum()>0 else 0.0
                if d1 - dens > best_gain + 1e-6:
                    best_gain, best_bounds = d1 - dens, b1
            # peel upper
            b2 = dict(bounds); b2[f] = (low, min(high, q_high))
            m2 = _in_box(dfX, b2)
            if m2.sum()/n_total >= min_mass:
                d2 = y[m2].mean() if m2.sum()>0 else 0.0
                if d2 - dens > best_gain + 1e-6:
                    best_gain, best_bounds = d2 - dens, b2
        if best_bounds is None:
            break
        bounds = best_bounds

    # Pasting (simple relax)
    for f in dfX.columns:
        low, high = bounds[f]
        vals = dfX[f].values
        qL = np.quantile(vals, peeling_alpha)
        qH = np.quantile(vals, 1.0 - peeling_alpha)
        b_try = dict(bounds); b_try[f] = (min(low, qL), high)
        m_try = _in_box(dfX, b_try)
        if m_try.sum()/n_total >= min_mass and y[m_try].mean() > (y[_in_box(dfX, bounds)].mean() if _in_box(dfX, bounds).sum()>0 else 0.0):
            bounds = b_try
        b_try = dict(bounds); b_try[f] = (low, max(high, qH))
        m_try = _in_box(dfX, b_try)
        if m_try.sum()/n_total >= min_mass and y[m_try].mean() > (y[_in_box(dfX, bounds)].mean() if _in_box(dfX, bounds).sum()>0 else 0.0):
            bounds = b_try

    mask = _in_box(dfX, bounds)
    n_in = int(mask.sum())
    if n_in == 0:
        return None
    dens = float(y[mask].mean())
    mass = n_in / len(dfX)
    cov = (y[mask].sum()) / (y.sum() + 1e-9)
    if dens < min_density or mass < min_mass:
        return None
    return PrimBox(bounds=bounds, mass=mass, density=dens, coverage=float(cov), n_in=n_in, n_pos_in=int(y[mask].sum()))

def prim_sequential(dfX: pd.DataFrame, y: np.ndarray, max_boxes=3, **kwargs) -> List[PrimBox]:
    boxes = []
    df_work = dfX.copy()
    y_work  = y.copy().astype(int)
    for _ in range(max_boxes):
        box = prim_single(df_work, y_work, **kwargs)
        if box is None:
            # Relax density once if needed
            if kwargs.get("min_density", 0.6) > 0.5:
                kwargs["min_density"] = kwargs.get("min_density", 0.6) - 0.05
                box = prim_single(df_work, y_work, **kwargs)
            if box is None:
                break
        boxes.append(box)
        m = _in_box(df_work, box.bounds)
        keep = ~(m & (y_work==1))    # remove covered positives
        df_work = df_work.loc[keep].reset_index(drop=True)
        y_work  = y_work[keep]
        if y_work.sum() == 0:
            break
    return boxes

def boxes_to_df(boxes: List[PrimBox]) -> pd.DataFrame:
    rows = []
    for i, b in enumerate(boxes, 1):
        conds = [f"{f} in [{lo:.2f}, {hi:.2f}]" for f,(lo,hi) in b.bounds.items()]
        rows.append({
            "BoxID": f"B{i}",
            "conditions": " & ".join(conds),
            "mass": b.mass,
            "density": b.density,
            "coverage": b.coverage,
            "n_in": b.n_in,
            "n_pos_in": b.n_pos_in
        })
    return pd.DataFrame(rows)

# ------ 6) DAPP builder ------
def build_dapp(prim_boxes_df: pd.DataFrame, rulesB: List[Dict], used_leafB, rulesA: List[Dict], used_leafA) -> pd.DataFrame:
    today = date.today().isoformat()
    rows = []
    # From PRIM boxes (B→C)
    for _, row in prim_boxes_df.head(3).iterrows():
        rows.append({
            "pathway": "B→C（PRIM箱）",
            "ATP_KPI": "不足率（%）",
            "trigger_threshold": "3年移動平均で5%超（B戦略下）",
            "signals": row["conditions"],
            "monitoring_freq": "四半期",
            "data_source": "気象（降水/気温）＋人口統計＋市場価格",
            "lead_time": "12か月",
            "switch_action": "C_expand20へ段階的切替",
            "option_traits": "可逆性中/拡張余地大/ロックイン中",
            "rough_cost_duration": "¥2.5B/年, 実装3年",
            "owner": "水資源局/農政部",
            "review_cycle": "年1回",
            "set_on": today,
            "note": f"PRIM: mass={row['mass']:.2f}, density={row['density']:.2f}, coverage={row['coverage']:.2f}"
        })
    # From Decision Tree rules (B→C)
    for r in rulesB[:3]:
        rows.append({
            "pathway": "B→C（Decision Tree）",
            "ATP_KPI": "不足率（%）",
            "trigger_threshold": "3年移動平均で5%超（B戦略下）",
            "signals": " / ".join(r["conditions"]),
            "monitoring_freq": "四半期",
            "data_source": "気象（降水/気温）＋人口統計＋市場価格",
            "lead_time": "12か月",
            "switch_action": "C_expand20へ段階的切替",
            "option_traits": "可逆性中/拡張余地大/ロックイン中",
            "rough_cost_duration": "¥2.5B/年, 実装3年",
            "owner": "水資源局/農政部",
            "review_cycle": "年1回",
            "set_on": today,
            "note": f"DT(B): n={r.get('n','-')}, risk={r.get('risk_rate','-')}, min_leaf={used_leafB}"
        })
    # From Decision Tree rules (A→B)
    for r in rulesA[:3]:
        rows.append({
            "pathway": "A→B（Decision Tree）",
            "ATP_KPI": "不足率（%）",
            "trigger_threshold": "年次で5%超（A戦略下）",
            "signals": " / ".join(r["conditions"]),
            "monitoring_freq": "四半期",
            "data_source": "気象（降水/気温）＋人口統計＋市場価格",
            "lead_time": "6か月",
            "switch_action": "B_efficiency10へ切替",
            "option_traits": "可逆性高/拡張余地中/ロックイン低",
            "rough_cost_duration": "¥1.0B/年, 実装1-2年",
            "owner": "水資源局/農政部",
            "review_cycle": "年1回",
            "set_on": today,
            "note": f"DT(A): n={r.get('n','-')}, risk={r.get('risk_rate','-')}, min_leaf={used_leafA}"
        })
    return pd.DataFrame(rows)

# ------ 7) Excel writer ------
def write_excel_filled(prim_df: pd.DataFrame, regret_df: pd.DataFrame, dapp_df: pd.DataFrame,
                       dt_rules_text: Optional[str], dst_path: str = "adaptive_pathways_filled.xlsx"):
    if not OPENPYXL_OK:
        print("[WARN] openpyxl is not installed; skipping Excel export.")
        print("       CSVs have been saved; to enable Excel, run: pip install openpyxl xlsxwriter")
        return
    # Create a basic template-like file then append sheets
    with pd.ExcelWriter(dst_path, engine="xlsxwriter") as w:
        # Minimal README
        pd.DataFrame({
            "項目":["作成日時","注意"],
            "値":[datetime.now().isoformat(timespec="seconds"), "自動生成されたブックです。必要に応じて書式を調整してください。"]
        }).to_excel(w, sheet_name="README", index=False)
        # PRIM結果
        prim_out = prim_df.rename(columns={
            "conditions":"条件（各因子の範囲/水準）",
            "mass":"質量（mass）",
            "density":"密度（density）",
            "coverage":"カバレッジ（coverage）"
        })
        prim_out.to_excel(w, sheet_name="PRIM結果", index=False)
        # ロバスト性評価（MinimaxRegret）
        regret_df.to_excel(w, sheet_name="ロバスト性評価（MinimaxRegret）", index=False)
        # DAPP
        dapp_df.to_excel(w, sheet_name="DAPPトリガー表", index=False)
        # DecisionTree rules
        if dt_rules_text:
            dt_df = pd.DataFrame({"DecisionTree rules (B)": dt_rules_text.splitlines()})
            dt_df.to_excel(w, sheet_name="決定木ルール（B）", index=False)
    print(f"[OK] Excel written: {dst_path}")

# ------ 8) Main ------
def main():
    print(">> Simulating scenarios ...")
    df = simulate_cases()

    print(">> Minimax regret per KPI ...")
    worst_regrets = minimax_regret_per_kpi(df, KPI_INFO)
    regret_cols = [c for c in worst_regrets.columns if c.startswith("worst_regret_")]
    worst_regrets["pareto"] = pareto_front(worst_regrets, regret_cols)

    # Baseline subset & PRIM
    print(">> Running PRIM on baseline strategy:", BASELINE_STRATEGY)
    subB = df[df["strategy"]==BASELINE_STRATEGY].reset_index(drop=True)
    yB = (subB[RISK_KPI] >= RISK_THRESH).astype(int).values
    boxesB = prim_sequential(subB[KEY_COLS], yB, max_boxes=3, peeling_alpha=0.05, pasting_alpha=0.01,
                             min_mass=0.05, min_density=0.6, max_iters=60)
    prim_boxes_df = boxes_to_df(boxesB)

    # Decision Tree rules (B and A) with fallback if sklearn missing
    print(">> Extracting Decision Tree rules (with fallback if sklearn unavailable) ...")
    rulesB, used_leafB, repB, tree_textB = adaptive_rules_tree(df, BASELINE_STRATEGY)
    rulesA, used_leafA, repA, tree_textA = adaptive_rules_tree(df, "A_statusquo")
    if SKLEARN_OK and tree_textB:
        with open("dt_rules_baseline.txt", "w", encoding="utf-8") as f:
            f.write(tree_textB)
        print("[OK] Saved Decision Tree rules to dt_rules_baseline.txt")
    else:
        tree_textB = ""

    # DAPP build
    print(">> Building DAPP plan ...")
    dapp_df = build_dapp(prim_boxes_df, rulesB, used_leafB, rulesA, used_leafA)

    # ---- Save CSVs ----
    print(">> Saving CSV outputs ...")
    df.to_csv("output/dapp/simulated_scenarios_mo.csv", index=False)
    worst_regrets.to_csv("output/dapp/worst_regret_per_kpi.csv", index=False)
    prim_boxes_df.to_csv("output/dapp/prim_boxes_baseline.csv", index=False)
    dapp_df.to_csv("output/dapp/dapp_plan.csv", index=False)
    print("[OK] CSVs saved in current directory.")

    # ---- Excel export ----
    print(">> Writing Excel workbook ...")
    write_excel_filled(prim_boxes_df, worst_regrets, dapp_df, tree_textB, dst_path="adaptive_pathways_filled.xlsx")

    print(">> Done.")
    print("   - simulated_scenarios_mo.csv")
    print("   - worst_regret_per_kpi.csv")
    print("   - prim_boxes_baseline.csv")
    print("   - dapp_plan.csv")
    print("   - adaptive_pathways_filled.xlsx (if openpyxl/xlsxwriter installed)")
    if SKLEARN_OK:
        print("   - dt_rules_baseline.txt")

if __name__ == "__main__":
    main()