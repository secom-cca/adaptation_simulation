# ============================================================
# 2プレイヤー（上流/下流）ゲームの可視化ユーティリティ
#  - 完備情報NE（RCP固定 or 全RCP平均）
#  - RCP事前つきベイジアンNE（自然状態の不確実性）
#  - パレートフロンティア（U/D効用の非支配集合）
#  - 可視化（UvsD効用、Flood vs Yield、Eco vs Yield）
# 依存: pandas, numpy, matplotlib（seaborn不要）
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Tuple

# ========= ユーザ設定 =========
CSV_PATH = "../output/dmdu_summary_irrigation_251006.csv"
GEN = "Gen3"  # "Gen1" / "Gen2" / "Gen3" など

# 列名（CSVに合わせる）
COL_FLOOD = f"Flood Damage_{GEN}"
COL_ECO   = f"Ecosystem Level_{GEN}"
COL_YIELD = f"Crop Yield_{GEN}"

U_DEC = ["dam_levee_construction_cost_level", "planting_trees_amount_level"]
D_DEC = ["flow_irrigation_level_level", "house_migration_amount_level"]

U_COST_VALUE_COLS = ["dam_levee_construction_cost_value", "planting_trees_amount_value"]
D_COST_VALUE_COLS = ["flow_irrigation_level_value", "house_migration_amount_value"]

# 重み（例：ベースと代替）
W_UP_BASE = {"flood":0.4, "eco":0.4, "cost":0.2}
W_DN_BASE = {"flood":0.4, "yield":0.4, "cost":0.2}

W_UP_ALT  = {"flood":0.6, "eco":0.2, "cost":0.2}   # 洪水重視
W_DN_ALT  = {"flood":0.2, "yield":0.6, "cost":0.2} # 収量重視

# ========= 基本関数 =========
def norm01(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    mn, mx = float(s.min()), float(s.max())
    return pd.Series(np.zeros(len(s)), index=s.index) if mx - mn < 1e-12 else (s - mn) / (mx - mn)

def build_payoffs(df_raw: pd.DataFrame, wU: Dict, wD: Dict) -> pd.DataFrame:
    df = df_raw.copy()
    flood_n = norm01(df[COL_FLOOD])     # 低いほど良い → 後でマイナス
    eco_n   = norm01(df[COL_ECO])       # 高いほど良い
    yield_n = norm01(df[COL_YIELD])     # 高いほど良い
    U_cost  = norm01(df[U_COST_VALUE_COLS].sum(axis=1))  # 低いほど良い → マイナス
    D_cost  = norm01(df[D_COST_VALUE_COLS].sum(axis=1))

    df["U_payoff"] = (
        + wU.get("eco",0.4)   * eco_n
        - wU.get("flood",0.4) * flood_n
        - wU.get("cost",0.2)  * U_cost
    )
    df["D_payoff"] = (
        + wD.get("yield",0.4) * yield_n
        - wD.get("flood",0.4) * flood_n
        - wD.get("cost",0.2)  * D_cost
    )
    df["SW"] = df["U_payoff"] + df["D_payoff"]
    return df

def grid_from_df(dfP: pd.DataFrame) -> pd.DataFrame:
    grp = dfP.groupby(U_DEC + D_DEC, as_index=False).agg({
        "U_payoff":"mean","D_payoff":"mean","SW":"mean",
        COL_FLOOD:"mean", COL_ECO:"mean", COL_YIELD:"mean",
        U_COST_VALUE_COLS[0]:"mean", U_COST_VALUE_COLS[1]:"mean",
        D_COST_VALUE_COLS[0]:"mean", D_COST_VALUE_COLS[1]:"mean",
    })
    grp["U_action"] = list(zip(grp[U_DEC[0]], grp[U_DEC[1]]))
    grp["D_action"] = list(zip(grp[D_DEC[0]], grp[D_DEC[1]]))
    return grp

def best_responses_and_NE(grid: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    idxD = grid.groupby("U_action")["D_payoff"].idxmax()
    BR_D = grid.loc[idxD, ["U_action","D_action"]].assign(BR="D")
    idxU = grid.groupby("D_action")["U_payoff"].idxmax()
    BR_U = grid.loc[idxU, ["U_action","D_action"]].assign(BR="U")
    NE = pd.merge(BR_D, BR_U, on=["U_action","D_action"], how="inner")
    NE = pd.merge(NE[["U_action","D_action"]].drop_duplicates(), grid,
                  on=["U_action","D_action"], how="left").sort_values("SW", ascending=False)
    return BR_U, BR_D, NE

def NE_complete_info(df: pd.DataFrame, rcp=None, wU=None, wD=None):
    if wU is None: wU = W_UP_BASE
    if wD is None: wD = W_DN_BASE
    dfR = df[df["RCP"]==rcp].copy() if rcp is not None else df.copy()
    dfP = build_payoffs(dfR, wU, wD)
    grid = grid_from_df(dfP)
    return (*best_responses_and_NE(grid), grid)

def NE_with_RCP_prior(df: pd.DataFrame, rcp_prior: Dict, wU=None, wD=None):
    if wU is None: wU = W_UP_BASE
    if wD is None: wD = W_DN_BASE
    frames = []
    for r, pr in rcp_prior.items():
        sub = df[df["RCP"]==r].copy()
        sub = build_payoffs(sub, wU, wD)
        sub["__w__"] = pr
        frames.append(sub)
    cat = pd.concat(frames, ignore_index=True)
    g = cat.groupby(U_DEC + D_DEC, as_index=False).apply(
        lambda g: pd.Series({
            "U_payoff": np.average(g["U_payoff"], weights=g["__w__"]),
            "D_payoff": np.average(g["D_payoff"], weights=g["__w__"]),
            "SW":       np.average(g["U_payoff"]+g["D_payoff"], weights=g["__w__"]),
            COL_FLOOD:  np.average(g[COL_FLOOD], weights=g["__w__"]),
            COL_ECO:    np.average(g[COL_ECO],   weights=g["__w__"]),
            COL_YIELD:  np.average(g[COL_YIELD], weights=g["__w__"]),
        })
    ).reset_index()
    grid = g.copy()
    grid["U_action"] = list(zip(grid[U_DEC[0]], grid[U_DEC[1]]))
    grid["D_action"] = list(zip(grid[D_DEC[0]], grid[D_DEC[1]]))
    return (*best_responses_and_NE(grid), grid)

def pareto_front_UD(grid: pd.DataFrame) -> pd.DataFrame:
    G = grid.copy()
    pts = G[["U_payoff","D_payoff"]].values
    dominated = np.zeros(len(G), dtype=bool)
    for i,(u_i,d_i) in enumerate(pts):
        if dominated[i]: continue
        dom = ((G["U_payoff"] >= u_i) & (G["D_payoff"] >= d_i) &
               ((G["U_payoff"] > u_i) | (G["D_payoff"] > d_i)))
        if dom.any():
            dominated[i] = True
    return G[~dominated].sort_values("SW", ascending=False)

# ========= 可視化 =========
def plot_utilities_with_pf_ne(grid: pd.DataFrame, NE: pd.DataFrame, title: str):
    pf = pareto_front_UD(grid)
    plt.figure()
    plt.scatter(grid["U_payoff"], grid["D_payoff"], s=20, label="All profiles")
    plt.scatter(pf["U_payoff"], pf["D_payoff"], s=35, label="Pareto frontier")
    if not NE.empty:
        plt.scatter(NE["U_payoff"], NE["D_payoff"], s=60, marker="x", label="Nash equilibrium(s)")
        x = float(NE.iloc[0]["U_payoff"]); y = float(NE.iloc[0]["D_payoff"])
        ua = NE.iloc[0]["U_action"]; da = NE.iloc[0]["D_action"]
        plt.annotate(f"NE U{ua} / D{da}", (x, y))
    plt.xlabel("Upstream utility (normalized)")
    plt.ylabel("Downstream utility (normalized)")
    plt.title(title)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()

def plot_outcome_projection(grid: pd.DataFrame, NE: pd.DataFrame, xcol: str, ycol: str, title: str):
    pf = pareto_front_UD(grid)
    plt.figure()
    plt.scatter(grid[xcol], grid[ycol], s=20, label="All profiles")
    plt.scatter(pf[xcol], pf[ycol], s=35, label="Pareto frontier")
    if not NE.empty:
        plt.scatter(NE[xcol], NE[ycol], s=60, marker="x", label="NE")
    plt.xlabel(xcol)
    plt.ylabel(ycol)
    plt.title(title)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()

def compare_ne_across_weights(df: pd.DataFrame, wU_a: Dict, wD_a: Dict, wU_b: Dict, wD_b: Dict, label_a="A", label_b="B"):
    # A
    BR_Ua, BR_Da, NE_a, grid_a = NE_complete_info(df, rcp=None, wU=wU_a, wD=wD_a)
    pf_a = pareto_front_UD(grid_a)
    # B
    BR_Ub, BR_Db, NE_b, grid_b = NE_complete_info(df, rcp=None, wU=wU_b, wD=wD_b)
    pf_b = pareto_front_UD(grid_b)

    plt.figure()
    plt.scatter(grid_a["U_payoff"], grid_a["D_payoff"], s=20, label=f"All profiles ({label_a})")
    plt.scatter(pf_a["U_payoff"], pf_a["D_payoff"], s=35, label=f"Pareto frontier ({label_a})")
    if not NE_a.empty:
        plt.scatter(NE_a["U_payoff"], NE_a["D_payoff"], s=60, marker="^", label=f"NE ({label_a})")

    plt.scatter(grid_b["U_payoff"], grid_b["D_payoff"], s=20, label=f"All profiles ({label_b})")
    plt.scatter(pf_b["U_payoff"], pf_b["D_payoff"], s=35, label=f"Pareto frontier ({label_b})")
    if not NE_b.empty:
        plt.scatter(NE_b["U_payoff"], NE_b["D_payoff"], s=60, marker="x", label=f"NE ({label_b})")

    plt.xlabel("Upstream utility (normalized)")
    plt.ylabel("Downstream utility (normalized)")
    plt.title(f"NE comparison across weights ({label_a} vs {label_b})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    return (NE_a, NE_b)

# ========= メイン =========
if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)

    # 1) 完備情報（RCP=ALL平均）でNE & PF
    BR_U, BR_D, NE_all, grid_all = NE_complete_info(df, rcp=None, wU=W_UP_BASE, wD=W_DN_BASE)
    plot_utilities_with_pf_ne(grid_all, NE_all, "U vs D utilities: Profiles, Pareto frontier, NE (baseline)")
    # 2D投影（必要に応じて他の組み合わせも）
    plot_outcome_projection(grid_all, NE_all, COL_FLOOD, COL_YIELD, "Outcome space: Flood vs Yield (baseline)")
    plot_outcome_projection(grid_all, NE_all, COL_ECO,   COL_YIELD, "Outcome space: Ecosystem vs Yield (baseline)")

    # 2) 重み違いでNE比較（ベース vs 代替）
    compare_ne_across_weights(df, W_UP_BASE, W_DN_BASE, W_UP_ALT, W_DN_ALT, label_a="baseline", label_b="alt")

    # 3) RCP事前つきの期待効用ゲーム（ベイジアンNE相当）
    rcps = sorted(df["RCP"].unique().tolist())
    prior = {r: 1/len(rcps) for r in rcps}  # 均等事前。必要に応じて {2.6:0.2, 4.5:0.5, 8.5:0.3} 等へ
    BR_Ur, BR_Dr, NE_rcp, grid_rcp = NE_with_RCP_prior(df, prior, wU=W_UP_BASE, wD=W_DN_BASE)
    plot_utilities_with_pf_ne(grid_rcp, NE_rcp, "Utilities with RCP prior: Profiles, Pareto, NE")

    # 表示
    plt.show()
