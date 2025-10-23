# ============================================================
# 2プレイヤー（上流/下流）ゲームの可視化ユーティリティ（完全版）
#  - 完備情報NE（RCP固定 or 全RCP込み）
#  - プレイヤー別RCP / RCP事前（確率）つきNE
#  - 重みスイープ（シンプレックス走査）→ NE頻度・ヒートマップ
#  - パレートフロンティア、結果空間（Flood vs Yield, Eco vs Yield）
#  - RCPの表記ゆれにロバスト（'4.5' / 'RCP4.5' / 4.5 等）
# 依存: pandas, numpy, matplotlib（seaborn不要）
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Iterable, List, Optional

# 共通フラグ：True で“プレイヤー別コスト”を有効化
USE_SEPARATE_COSTS = True

# ========= ユーザ設定 =========
CSV_PATH = "../output/dmdu_summary_irrigation_251008v2.csv"
GEN = "mean"  # "Gen1" / "Gen2" / "Gen3" / "mean"

# 意思決定（レベル）列
U_DEC = ["planting_trees_amount_level", "dam_levee_construction_cost_level"]
D_DEC = ["house_migration_amount_level", "flow_irrigation_level_level"]

# 参考値（投入量など）の列（あれば集計に残す）
U_COST_VALUE_COLS = ["planting_trees_amount_value", "dam_levee_construction_cost_value"]
D_COST_VALUE_COLS = ["house_migration_amount_value", "flow_irrigation_level_value"]

# 重み（例）
W_UP_BASE = {"flood":0.4, "eco":0.4, "cost":0.2}
W_DN_BASE = {"flood":0.4, "yield":0.4, "cost":0.2}

W_UP_ALT  = {"flood":0.2, "eco":0.6, "cost":0.2}   # 洪水重視
W_DN_ALT  = {"flood":0.2, "yield":0.6, "cost":0.2} # 収量重視

# ========= プレイヤー別コスト（係数） =========
# level 列（*_level）は “段階番号” として扱います（例：0,1,2,...）。
# 文字列のときは、数字部分を抽出します（例: "L2" -> 2）。
U_COST_COEF = {
    "planting_trees_amount_level": 115.5e6,    # 115.5M
    "dam_levee_construction_cost_level": 100e6 # 100M
}
D_COST_COEF = {
    "house_migration_amount_level": 49e6,      # 49M
    "flow_irrigation_level_level": 0.0         # 0
}

# ========= 列名ユーティリティ =========
def get_metric_cols(gen: str):
    """世代ごとの列名を返す。gen='mean' は Gen1-3 の平均を意図。"""
    if gen == "mean":
        return {
            "flood": [f"Flood Damage_Gen{i}" for i in [1, 2, 3]],
            "eco":   [f"Ecosystem Level_Gen{i}" for i in [1, 2, 3]],
            "yield": [f"Crop Yield_Gen{i}" for i in [1, 2, 3]],
            "cost":  [f"Municipal Cost_Gen{i}" for i in [1, 2, 3]],
        }
    else:
        return {
            "flood": [f"Flood Damage_{gen}"],
            "eco":   [f"Ecosystem Level_{gen}"],
            "yield": [f"Crop Yield_{gen}"],
            "cost":  [f"Municipal Cost_{gen}"],
        }

def _level_to_num(s: pd.Series) -> pd.Series:
    """
    *_level 列を数値に。数値ならそのまま、文字列なら数字部分を抽出（なければ0）。
    例: "L2" -> 2, "2" -> 2, 2 -> 2
    """
    if s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce").fillna(0).astype(float)
    s = s.astype(str).str.strip()
    # 数字を抽出。見つからなければ0
    m = s.str.extract(r'([-+]?\d*\.?\d+)')[0]
    return pd.to_numeric(m, errors="coerce").fillna(0).astype(float)

def compute_player_costs(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    上流/下流それぞれの level 列に係数を掛けてコストを作成。
    - U_cost_raw: 上流コスト（trees*115.5M + dam*100M）
    - D_cost_raw: 下流コスト（house*49M + irrigation*0）
    """
    df = df_raw.copy()
    # 上流コスト
    U_cost = 0.0
    for col, coef in U_COST_COEF.items():
        if col not in df.columns:
            raise KeyError(f"上流コスト列が見つかりません: {col}")
        U_cost = U_cost + _level_to_num(df[col]) * float(coef)

    # 下流コスト
    D_cost = 0.0
    for col, coef in D_COST_COEF.items():
        if col not in df.columns:
            raise KeyError(f"下流コスト列が見つかりません: {col}")
        D_cost = D_cost + _level_to_num(df[col]) * float(coef)

    df["U_cost_raw"] = U_cost
    df["D_cost_raw"] = D_cost
    # 参考：合計（Municipal に近い値になるか検証用）
    df["Estimated Municipal Cost (U+D)"] = df["U_cost_raw"] + df["D_cost_raw"]
    return df


# ========= 共通処理 =========
def norm01(s: pd.Series) -> pd.Series:
    """空Series/NaNだらけでも落ちない0-1正規化。"""
    if s is None or len(s) == 0:
        return pd.Series([], dtype=float)
    s = pd.to_numeric(s, errors="coerce")
    if s.isna().all():
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    mn, mx = float(np.nanmin(s.values)), float(np.nanmax(s.values))
    if not np.isfinite(mn) or not np.isfinite(mx) or mx - mn < 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    out = (s - mn) / (mx - mn)
    return out.fillna(0.0)

def _normalize_rcp_series(s: pd.Series) -> pd.Series:
    """
    RCP列を数値化にトライ（'RCP4.5' -> 4.5, '4.5' -> 4.5）。
    失敗した要素はNaNに。
    """
    s = s.astype(str).str.strip()
    s_num = s.str.extract(r'([-+]?\d*\.?\d+)')[0]
    return pd.to_numeric(s_num, errors="coerce")

def _filter_rcp(df: pd.DataFrame, rcp_target) -> pd.DataFrame:
    """
    rcp_target が 4.5 / '4.5' / 'RCP4.5' のいずれでも頑強に一致させる。
    数値±ε一致 or 文字列完全一致のどちらかで拾う。
    見つからない場合は候補を提示して例外。
    """
    if "RCP" not in df.columns:
        raise ValueError("RCP列が見つかりません。CSVにRCP列を含めてください。")

    # 文字列そのまま一致（早期ヒット）
    direct = df[df["RCP"].astype(str).str.strip() == str(rcp_target).strip()]
    if not direct.empty:
        return direct

    # 数値正規化して ±ε で一致
    rcps_num = _normalize_rcp_series(df["RCP"])
    target_num = _normalize_rcp_series(pd.Series([rcp_target])).iloc[0]
    if pd.notna(target_num):
        eps = 1e-6
        by_num = df[rcps_num.sub(target_num).abs() <= eps]
        if not by_num.empty:
            return by_num

    # 候補提示
    avail_str = sorted(df["RCP"].astype(str).str.strip().unique().tolist())
    avail_num = sorted([x for x in rcps_num.unique().tolist() if pd.notna(x)])
    raise ValueError(
        f"指定RCPが見つかりません: {rcp_target}\n"
        f"利用可能（文字列）: {avail_str}\n"
        f"利用可能（数値解釈）: {avail_num}\n"
        "例: rcpU=4.5 もしくは rcpU='RCP4.5' 等、データに合わせて指定してください。"
    )

def build_payoffs(df_raw: pd.DataFrame, wU: Dict, wD: Dict, gen: str = "Gen3") -> pd.DataFrame:
    """
    指標（Flood, Eco, Yield）＋ コストから U/D の効用を作成。
    - USE_SEPARATE_COSTS=True: 上流/下流で別コスト（U_cost_raw / D_cost_raw）を使用
    - USE_SEPARATE_COSTS=False: 従来通り Municipal Cost（共通）を使用
    - gen='mean' は Gen1-3 の単純平均。
    """
    cols = get_metric_cols(gen)
    df = df_raw.copy()

    # --- 指標（世代平均 or 単一） ---
    flood = df[cols["flood"]].mean(axis=1)
    eco   = df[cols["eco"]].mean(axis=1)
    yld   = df[cols["yield"]].mean(axis=1)

    # --- コスト ---
    if USE_SEPARATE_COSTS:
        if ("U_cost_raw" not in df.columns) or ("D_cost_raw" not in df.columns):
            df = compute_player_costs(df)
        U_cost_raw = df["U_cost_raw"]
        D_cost_raw = df["D_cost_raw"]
        # 各コストを別々に正規化（0-1）
        U_cost_n = norm01(U_cost_raw)
        D_cost_n = norm01(D_cost_raw)
        # 参考用に Municipal（共通）も作っておく（集計やデバッグで見たい時）
        cost_common = (U_cost_raw + D_cost_raw)
    else:
        # 従来：CSVの Municipal Cost_* を使用（平均）
        cost_common = df[cols["cost"]].mean(axis=1)
        cost_n = norm01(cost_common)
        U_cost_n = cost_n
        D_cost_n = cost_n

    # --- 正規化（指標） ---
    flood_n = norm01(flood)    # 小さい方が良い（負項）
    eco_n   = norm01(eco)      # 大きい方が良い（正項）
    yield_n = norm01(yld)      # 大きい方が良い（正項）

    # --- 効用（線形加重） ---
    # 重要：U は U_cost_n、D は D_cost_n をそれぞれ参照
    df["U_payoff"] = (
        + wU.get("eco",0.0)   * eco_n
        - wU.get("flood",0.0) * flood_n
        - wU.get("cost",0.0)  * U_cost_n
    )
    df["D_payoff"] = (
        + wD.get("yield",0.0) * yield_n
        - wD.get("flood",0.0) * flood_n
        - wD.get("cost",0.0)  * D_cost_n
    )
    df["SW"] = df["U_payoff"] + df["D_payoff"]

    # --- 解析用に元値を保持（共通名） ---
    df["Flood Damage"]     = flood
    df["Ecosystem Level"]  = eco
    df["Crop Yield"]       = yld
    # 参考列
    if USE_SEPARATE_COSTS:
        df["Upstream Cost (raw)"]   = U_cost_raw
        df["Downstream Cost (raw)"] = D_cost_raw
        df["Municipal Cost (ref)"]  = cost_common   # U+D の推計（CSVの Municipal に近いはず）
    else:
        df["Municipal Cost"]        = cost_common
    return df


def grid_from_df(dfP: pd.DataFrame) -> pd.DataFrame:
    agg_cols = {
        "U_payoff":"mean","D_payoff":"mean","SW":"mean",
        "Flood Damage":"mean","Ecosystem Level":"mean",
        "Crop Yield":"mean"
    }
    # ここから追記
    if "Upstream Cost (raw)" in dfP.columns:
        agg_cols["Upstream Cost (raw)"] = "mean"
    if "Downstream Cost (raw)" in dfP.columns:
        agg_cols["Downstream Cost (raw)"] = "mean"
    if "Municipal Cost (ref)" in dfP.columns:
        agg_cols["Municipal Cost (ref)"] = "mean"
    if "Municipal Cost" in dfP.columns:
        agg_cols["Municipal Cost"] = "mean"
    # 既存の参考値列も維持
    for c in U_COST_VALUE_COLS + D_COST_VALUE_COLS:
        if c in dfP.columns:
            agg_cols[c] = "mean"

    grp = dfP.groupby(U_DEC + D_DEC, as_index=False).agg(agg_cols)
    grp["U_action"] = list(zip(grp[U_DEC[0]], grp[U_DEC[1]]))
    grp["D_action"] = list(zip(grp[D_DEC[0]], grp[D_DEC[1]]))
    return grp

def best_responses_and_NE(grid: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """互いの最良反応の交点をNEとして抽出。"""
    idxD = grid.groupby("U_action")["D_payoff"].idxmax()
    BR_D = grid.loc[idxD, ["U_action","D_action"]].assign(BR="D")

    idxU = grid.groupby("D_action")["U_payoff"].idxmax()
    BR_U = grid.loc[idxU, ["U_action","D_action"]].assign(BR="U")

    NE = pd.merge(BR_D, BR_U, on=["U_action","D_action"], how="inner")
    NE = pd.merge(NE[["U_action","D_action"]].drop_duplicates(), grid,
                  on=["U_action","D_action"], how="left").sort_values("SW", ascending=False)
    return BR_U, BR_D, NE

# ========= NE（完備情報/平均） =========
def NE_complete_info(df: pd.DataFrame, rcp: Optional[float]=None, wU=None, wD=None, gen: str="Gen3"):
    if wU is None: wU = W_UP_BASE
    if wD is None: wD = W_DN_BASE
    if rcp is None:
        dfR = df.copy()  # 全RCPを含めた上で GEN平均 or GEN指定
    else:
        dfR = _filter_rcp(df, rcp).copy()

    dfP = build_payoffs(dfR, wU, wD, gen=gen)
    grid = grid_from_df(dfP)
    return (*best_responses_and_NE(grid), grid)

# ========= NE（プレイヤー別にRCPを固定） =========
def NE_with_player_specific_RCPs(df: pd.DataFrame, rcpU, rcpD, wU=None, wD=None, gen: str="Gen3"):
    """
    上流の効用は rcpU だけから計算、下流の効用は rcpD だけから計算。
    同一プロファイルの上に、U_payoff と D_payoff を別集計して突き合わせる。
    """
    if wU is None: wU = W_UP_BASE
    if wD is None: wD = W_DN_BASE

    # U側データを安全に抽出
    dfU = _filter_rcp(df, rcpU).copy()
    if dfU.empty:
        raise ValueError(f"RCP {rcpU} に一致するデータがありません（U側）。")

    # D側データを安全に抽出
    dfD = _filter_rcp(df, rcpD).copy()
    if dfD.empty:
        raise ValueError(f"RCP {rcpD} に一致するデータがありません（D側）。")

    # 片側だけの効用を作る（もう一方はゼロ重みでダミー化）
    dfU = build_payoffs(dfU, wU, {"yield":0,"flood":0,"cost":0}, gen=gen)
    gU  = grid_from_df(dfU)[U_DEC + D_DEC + ["U_payoff"]].copy()

    dfD = build_payoffs(dfD, {"eco":0,"flood":0,"cost":0}, wD, gen=gen)
    gD  = grid_from_df(dfD)[U_DEC + D_DEC + ["D_payoff"]].copy()

    grid = pd.merge(gU, gD, on=U_DEC + D_DEC, how="inner")
    if grid.empty:
        raise ValueError("U/Dでアクションの直積が一致せず、比較可能なプロファイルがゼロです。"
                         "（意思決定レベル列の水準がRCPごとにズレていないか確認してください）")

    grid["SW"] = grid["U_payoff"] + grid["D_payoff"]
    grid["U_action"] = list(zip(grid[U_DEC[0]], grid[U_DEC[1]]))
    grid["D_action"] = list(zip(grid[D_DEC[0]], grid[D_DEC[1]]))
    return (*best_responses_and_NE(grid), grid)

# ========= NE（プレイヤー別にRCP事前（確率）） =========
def NE_with_player_specific_priors(df: pd.DataFrame, priorU: Dict[float,float], priorD: Dict[float,float],
                                   wU=None, wD=None, gen: str="Gen3"):
    """
    UとDで異なるRCP事前分布を持つ場合の期待効用を計算。
    - 各RCPのグリッドを作り、U/Dそれぞれの期待値だけ重み付き平均して合成。
    """
    if wU is None: wU = W_UP_BASE
    if wD is None: wD = W_DN_BASE

    # 事前のキー（RCP）を数値化して正規化（'RCP4.5' → 4.5 等）
    def _norm_prior_keys(pr):
        if pr is None: return {}
        out = {}
        for k,v in pr.items():
            k_num = _normalize_rcp_series(pd.Series([k])).iloc[0]
            if pd.isna(k_num):
                # 文字列そのまま一致にも備えて保持
                out[str(k).strip()] = float(v)
            else:
                out[float(k_num)] = float(v)
        return out

    priorU_n = _norm_prior_keys(priorU)
    priorD_n = _norm_prior_keys(priorD)

    # 使用するRCP集合（数値解釈＋文字列）
    keysU = set(priorU_n.keys())
    keysD = set(priorD_n.keys())
    all_keys = keysU | keysD
    if not all_keys:
        raise ValueError("priorU/priorD が空です。")

    # データ側のRCP（両方の表現を用意）
    rcps_num = _normalize_rcp_series(df["RCP"])
    rcps_str = df["RCP"].astype(str).str.strip()

    grids = {}
    for k in sorted(all_keys, key=lambda x: str(x)):
        # k が数値なら±ε一致、文字列ならそのまま一致
        if isinstance(k, (int, float)):
            eps = 1e-6
            sub = df[rcps_num.sub(float(k)).abs() <= eps].copy()
        else:
            sub = df[rcps_str == str(k)].copy()

        if sub.empty:
            # 見つからないキーはスキップ（重みが正でもデータがなければ寄与0）
            continue

        sub = build_payoffs(sub, wU, wD, gen=gen)
        g = grid_from_df(sub)
        grids[k] = g[U_DEC + D_DEC + ["U_payoff","D_payoff"]].copy()

    if not grids:
        raise ValueError("priorU/priorD に対応するRCPデータが見つかりません。"
                         "priorキーとCSVのRCP表記をご確認ください。")

    # 期待効用（UとDで別ウェイト）
    base = None
    for k, g in grids.items():
        wU_k = priorU_n.get(k, 0.0)
        wD_k = priorD_n.get(k, 0.0)

        gU = g.copy(); gU["D_payoff"] = 0.0; gU["U_payoff"] *= wU_k
        gD = g.copy(); gD["U_payoff"] = 0.0; gD["D_payoff"] *= wD_k

        comb = gU.copy(); comb["D_payoff"] = gD["D_payoff"]
        base = comb if base is None else pd.concat([base, comb], ignore_index=True)

    grid = base.groupby(U_DEC + D_DEC, as_index=False).sum(numeric_only=True)
    if grid.empty:
        raise ValueError("RCP事前に基づく合成で、比較可能なプロファイルがゼロです。"
                         "（RCPごとに意思決定水準が異ならないか確認）")
    grid["SW"] = grid["U_payoff"] + grid["D_payoff"]
    grid["U_action"] = list(zip(grid[U_DEC[0]], grid[U_DEC[1]]))
    grid["D_action"] = list(zip(grid[D_DEC[0]], grid[D_DEC[1]]))
    return (*best_responses_and_NE(grid), grid)

# ========= パレートフロンティア =========
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

# ========= 可視化（基本） =========
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

def compare_ne_across_weights(df: pd.DataFrame, wU_a: Dict, wD_a: Dict, wU_b: Dict, wD_b: Dict,
                              label_a="A", label_b="B", gen: str="Gen3"):
    _, _, NE_a, grid_a = NE_complete_info(df, rcp=None, wU=wU_a, wD=wD_a, gen=gen)
    pf_a = pareto_front_UD(grid_a)
    _, _, NE_b, grid_b = NE_complete_info(df, rcp=None, wU=wU_b, wD=wD_b, gen=gen)
    pf_b = pareto_front_UD(grid_b)

    plt.figure()
    plt.scatter(grid_a["U_payoff"], grid_a["D_payoff"], s=18, label=f"All profiles ({label_a})")
    plt.scatter(pf_a["U_payoff"], pf_a["D_payoff"], s=35, label=f"Pareto frontier ({label_a})")
    if not NE_a.empty:
        plt.scatter(NE_a["U_payoff"], NE_a["D_payoff"], s=65, marker="^", label=f"NE ({label_a})")

    plt.scatter(grid_b["U_payoff"], grid_b["D_payoff"], s=18, label=f"All profiles ({label_b})")
    plt.scatter(pf_b["U_payoff"], pf_b["D_payoff"], s=35, label=f"Pareto frontier ({label_b})")
    if not NE_b.empty:
        plt.scatter(NE_b["U_payoff"], NE_b["D_payoff"], s=65, marker="x", label=f"NE ({label_b})")

    plt.xlabel("Upstream utility (normalized)")
    plt.ylabel("Downstream utility (normalized)")
    plt.title(f"NE comparison across weights ({label_a} vs {label_b})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    return (NE_a, NE_b)

# ========= 重みスイープ（シンプレックス上の格子） =========
def simplex_weights(steps:int=5) -> List[Tuple[float,float,float]]:
    """
    a,b,c >=0, a+b+c=1 の格子点を生成。
    steps=5 なら 0,0.25,0.5,0.75,1 など。
    """
    pts = []
    grid = np.linspace(0, 1, steps)
    for a in grid:
        for b in grid:
            c = 1 - a - b
            if c < -1e-9: continue
            if c < 0: c = 0.0
            if abs(a+b+c-1) > 1e-6: continue
            pts.append((float(a), float(b), float(c)))
    uniq = list({(round(a,6),round(b,6),round(c,6)) for (a,b,c) in pts})
    return sorted(uniq)

def sweep_weights(df: pd.DataFrame, gen:str="Gen3",
                  rcpU:Optional[float]=None, rcpD:Optional[float]=None,
                  priorU:Optional[Dict[float,float]]=None,
                  priorD:Optional[Dict[float,float]]=None,
                  steps:int=5) -> pd.DataFrame:
    """
    上流: (flood, eco, cost) 、下流: (flood, yield, cost) をシンプレックス上で走査してNEを記録。
    rcpU/rcpD を与えるとプレイヤー別RCP固定、priorU/priorD を与えるとプレイヤー別事前。
    何も与えない場合は全RCP込みの完備情報（GEN指定/平均）でスイープ。
    """
    U_points = simplex_weights(steps)
    D_points = simplex_weights(steps)

    rows = []
    for (uf, ue, uc) in U_points:
        wU = {"flood":uf, "eco":ue, "cost":uc}
        for (dflood, dy, dc) in D_points:
            wD = {"flood":dflood, "yield":dy, "cost":dc}

            if priorU is not None or priorD is not None:
                priorU_use = priorU if priorU is not None else {}
                priorD_use = priorD if priorD is not None else {}
                _, _, NE, _grid = NE_with_player_specific_priors(df, priorU_use, priorD_use, wU=wU, wD=wD, gen=gen)
            elif (rcpU is not None) or (rcpD is not None):
                rU = rcpU if rcpU is not None else df["RCP"].iloc[0]
                rD = rcpD if rcpD is not None else df["RCP"].iloc[0]
                _, _, NE, _grid = NE_with_player_specific_RCPs(df, rU, rD, wU=wU, wD=wD, gen=gen)
            else:
                _, _, NE, _grid = NE_complete_info(df, rcp=None, wU=wU, wD=wD, gen=gen)

            if NE.empty:
                rows.append({
                    "wU_flood":uf, "wU_eco":ue, "wU_cost":uc,
                    "wD_flood":dflood, "wD_yield":dy, "wD_cost":dc,
                    "NE_exists": False,
                    "U_action": None, "D_action": None,
                    "U_payoff": np.nan, "D_payoff": np.nan, "SW": np.nan
                })
            else:
                ne0 = NE.iloc[0]
                rows.append({
                    "wU_flood":uf, "wU_eco":ue, "wU_cost":uc,
                    "wD_flood":dflood, "wD_yield":dy, "wD_cost":dc,
                    "NE_exists": True,
                    "U_action": ne0["U_action"], "D_action": ne0["D_action"],
                    "U_payoff": float(ne0["U_payoff"]),
                    "D_payoff": float(ne0["D_payoff"]),
                    "SW": float(ne0["SW"]),
                })

    return pd.DataFrame(rows)

# ========= 可視化（分かりやすいヒートマップ/頻度） =========
def action_code(u_act, d_act) -> str:
    """
    アクションを短縮コード化（ヒートマップに入れる用）
    例: U(2,1)|D(0,2)
    """
    return f"U{u_act}|D{d_act}" if (u_act is not None and d_act is not None) else "—"

def plot_ne_frequency_bar(sweep_df: pd.DataFrame, top_k:int=10, title:str="Top NE action profiles by frequency"):
    ok = sweep_df[sweep_df["NE_exists"]]
    if ok.empty:
        print("No NE found in sweeps.")
        return
    freq = ok.groupby(["U_action","D_action"]).size().sort_values(ascending=False).head(top_k)
    labels = [action_code(u,d) for (u,d) in freq.index]
    plt.figure()
    plt.bar(range(len(freq)), freq.values)
    plt.xticks(range(len(freq)), labels, rotation=45, ha="right")
    plt.ylabel("Count in sweeps")
    plt.title(title)
    plt.tight_layout()

def _plot_discrete_heatmap(pivot_codes: pd.DataFrame, title:str, xlabel:str, ylabel:str):
    """
    文字コードをセルに描く”読みやすい”ヒートマップ。
    値はインデックス番号（色）＋セル中央にアクション短縮コードをテキスト表示。
    """
    # カテゴリ→番号化
    cats = sorted([c for c in pd.unique(pivot_codes.values.ravel()) if pd.notna(c)])
    cat_to_id = {c:i for i,c in enumerate(cats)}
    Z = pivot_codes.applymap(lambda x: np.nan if pd.isna(x) else cat_to_id.get(x, np.nan)).values.astype(float)

    plt.figure()
    im = plt.imshow(Z, aspect="auto", origin="lower", interpolation="nearest")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.colorbar(im, ticks=range(len(cats)), label="NE action code idx")
    # 軸目盛（浮動数表記を短く）
    plt.xticks(ticks=range(pivot_codes.shape[1]), labels=[f"{v:.2f}" for v in pivot_codes.columns])
    plt.yticks(ticks=range(pivot_codes.shape[0]), labels=[f"{v:.2f}" for v in pivot_codes.index])

    # セル文字（アクションコード）
    for i in range(pivot_codes.shape[0]):
        for j in range(pivot_codes.shape[1]):
            code = pivot_codes.iloc[i,j]
            if pd.notna(code):
                plt.text(j, i, code, ha="center", va="center", fontsize=8)

    plt.tight_layout()

def plot_weight_to_NE_heatmaps(sweep_df: pd.DataFrame,
                               upstream_eco_slices: Iterable[float]=(0.0,0.33,0.67,1.0),
                               downstream_yield_slices: Iterable[float]=(0.0,0.33,0.67,1.0)):
    """
    上流：eco固定スライス → x=U_flood, y=U_cost のヒートマップ（セルに NE アクション）
    下流：yield固定スライス → x=D_flood, y=D_cost のヒートマップ
    """
    ok = sweep_df[sweep_df["NE_exists"]].copy()
    if ok.empty:
        print("No NE found in sweeps.")
        return

    # 上流側（ecoスライス）
    for eco_fixed in upstream_eco_slices:
        sub = ok[np.isclose(ok["wU_eco"], eco_fixed)]
        if sub.empty: 
            continue
        sub = sub.copy()
        sub["code"] = [action_code(u,d) for u,d in zip(sub["U_action"], sub["D_action"])]
        # ピボット: rows=U_cost, cols=U_flood（コストは 1- U_flood - U_eco）
        piv = sub.pivot_table(index="wU_cost", columns="wU_flood", values="code", aggfunc="first")
        _plot_discrete_heatmap(piv, title=f"Upstream weights → NE (eco fixed = {eco_fixed:.2f})",
                               xlabel="wU_flood", ylabel="wU_cost")

    # 下流側（yieldスライス）
    for y_fixed in downstream_yield_slices:
        sub = ok[np.isclose(ok["wD_yield"], y_fixed)]
        if sub.empty: 
            continue
        sub = sub.copy()
        sub["code"] = [action_code(u,d) for u,d in zip(sub["U_action"], sub["D_action"])]
        piv = sub.pivot_table(index="wD_cost", columns="wD_flood", values="code", aggfunc="first")
        _plot_discrete_heatmap(piv, title=f"Downstream weights → NE (yield fixed = {y_fixed:.2f})",
                               xlabel="wD_flood", ylabel="wD_cost")

# ========= Ternary（3成分）ユーティリティ =========
def _ternary_cartesian(a: float, b: float, c: float) -> tuple:
    """
    3成分 (a,b,c)、a+b+c=1 を正三角形座標に射影（横= x, 縦= y）。
    頂点: A=(1,0,0), B=(0,1,0), C=(0,0,1)
    """
    # 座標系: 辺長=1 の正三角形を横長に配置
    # 変換（古典的なバリセントリック→2D）
    x = 0.5 * (2*b + c) / (a + b + c + 1e-12)
    y = (np.sqrt(3)/2) * c / (a + b + c + 1e-12)
    return (x, y)

def _encode_ne(u_act, d_act) -> str:
    return f"U{u_act}|D{d_act}" if (u_act is not None and d_act is not None) else "—"

def _palette_for_codes(codes):
    """カテゴリごとに整数IDを振って colormap 用の値にする。"""
    cats = sorted(list({c for c in codes if pd.notna(c)}))
    cmap_index = {c:i for i,c in enumerate(cats)}
    vals = np.array([np.nan if pd.isna(c) else cmap_index[c] for c in codes], dtype=float)
    return vals, cats

# ========= 上流 ternary：下流を固定して上流だけ掃く（推奨A） =========
def ternary_U_fixed_D(df: pd.DataFrame, D_weights: dict, gen: str="Gen3",
                      rcpU=None, rcpD=None, priorU=None, priorD=None,
                      steps:int=9, title:str=None):
    """
    下流重みを D_weights に固定して、上流の (flood, eco, cost) をシンプレックス上で掃き、
    各点の NE を ternary に描く。
    - rcpU/rcpD を渡すとプレイヤー別RCP固定
    - priorU/priorD を渡すとベイジアン
    - どちらも None なら完備情報（全RCP込み）
    """
    # 上流だけスイープ
    U_points = simplex_weights(steps)
    rows = []
    for (uf, ue, uc) in U_points:
        wU = {"flood":uf, "eco":ue, "cost":uc}
        wD = D_weights

        if priorU is not None or priorD is not None:
            _, _, NE, _ = NE_with_player_specific_priors(df, priorU or {}, priorD or {}, wU=wU, wD=wD, gen=gen)
        elif (rcpU is not None) or (rcpD is not None):
            _, _, NE, _ = NE_with_player_specific_RCPs(df, rcpU, rcpD, wU=wU, wD=wD, gen=gen)
        else:
            _, _, NE, _ = NE_complete_info(df, rcp=None, wU=wU, wD=wD, gen=gen)

        if NE.empty:
            code = "—"; Ux, Uy = _ternary_cartesian(uf, ue, uc)
            rows.append((Ux, Uy, code, uf, ue, uc))
        else:
            ne0 = NE.iloc[0]
            code = _encode_ne(ne0["U_action"], ne0["D_action"])
            Ux, Uy = _ternary_cartesian(uf, ue, uc)
            rows.append((Ux, Uy, code, uf, ue, uc))

    data = pd.DataFrame(rows, columns=["x","y","code","wU_flood","wU_eco","wU_cost"])
    vals, cats = _palette_for_codes(data["code"])

    plt.figure()
    sc = plt.scatter(data["x"], data["y"], c=vals, s=35)
    cbar = plt.colorbar(sc, ticks=range(len(cats)))
    cbar.ax.set_yticklabels(cats)
    plt.title(title or "Upstream ternary (Downstream fixed)")
    plt.xlabel("→ b (eco) + c/2")
    plt.ylabel("↑ c (cost)")

    # 三角形の枠と頂点ラベル
    tri = np.array([_ternary_cartesian(1,0,0),
                    _ternary_cartesian(0,1,0),
                    _ternary_cartesian(0,0,1),
                    _ternary_cartesian(1,0,0)])
    plt.plot(tri[:,0], tri[:,1], lw=1.0, color="black")
    Ax,Ay = _ternary_cartesian(1,0,0); Bx,By = _ternary_cartesian(0,1,0); Cx,Cy = _ternary_cartesian(0,0,1)
    plt.text(Ax,Ay, "U_flood=1", ha="right", va="top", fontsize=9)
    plt.text(Bx,By, "U_eco=1", ha="left", va="top", fontsize=9)
    plt.text(Cx,Cy, "U_cost=1", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()

# ========= 下流 ternary：上流を固定して下流だけ掃く（推奨A） =========
def ternary_D_fixed_U(df: pd.DataFrame, U_weights: dict, gen: str="Gen3",
                      rcpU=None, rcpD=None, priorU=None, priorD=None,
                      steps:int=9, title:str=None):
    """
    上流重みを U_weights に固定して、下流の (flood, yield, cost) をシンプレックス上で掃き、
    各点の NE を ternary に描く。
    - rcpU/rcpD を渡すとプレイヤー別RCP固定
    - priorU/priorD を渡すとベイジアン
    - どちらも None なら完備情報（全RCP込み）
    """
    D_points = simplex_weights(steps)
    rows = []
    for (dflood, dy, dc) in D_points:
        wD = {"flood":dflood, "yield":dy, "cost":dc}
        wU = U_weights

        if priorU is not None or priorD is not None:
            _, _, NE, _ = NE_with_player_specific_priors(df, priorU or {}, priorD or {}, wU=wU, wD=wD, gen=gen)
        elif (rcpU is not None) or (rcpD is not None):
            _, _, NE, _ = NE_with_player_specific_RCPs(df, rcpU, rcpD, wU=wU, wD=wD, gen=gen)
        else:
            _, _, NE, _ = NE_complete_info(df, rcp=None, wU=wU, wD=wD, gen=gen)

        code = "—" if NE.empty else _encode_ne(NE.iloc[0]["U_action"], NE.iloc[0]["D_action"])
        Dx, Dy = _ternary_cartesian(dflood, dy, dc)  # a=flood, b=yield, c=cost
        rows.append((Dx, Dy, code, dflood, dy, dc))

    data = pd.DataFrame(rows, columns=["x","y","code","wD_flood","wD_yield","wD_cost"])
    vals, cats = _palette_for_codes(data["code"])

    plt.figure()
    sc = plt.scatter(data["x"], data["y"], c=vals, s=35)
    cbar = plt.colorbar(sc, ticks=range(len(cats)))
    cbar.ax.set_yticklabels(cats)
    plt.title(title or "Downstream ternary (Upstream fixed)")
    plt.xlabel("→ b (yield) + c/2")
    plt.ylabel("↑ c (cost)")

    # 三角形枠と頂点ラベル
    tri = np.array([_ternary_cartesian(1,0,0),
                    _ternary_cartesian(0,1,0),
                    _ternary_cartesian(0,0,1),
                    _ternary_cartesian(1,0,0)])
    plt.plot(tri[:,0], tri[:,1], lw=1.0, color="black")
    Ax,Ay = _ternary_cartesian(1,0,0); Bx,By = _ternary_cartesian(0,1,0); Cx,Cy = _ternary_cartesian(0,0,1)
    plt.text(Ax,Ay, "D_flood=1", ha="right", va="top", fontsize=9)
    plt.text(Bx,By, "D_yield=1", ha="left", va="top", fontsize=9)
    plt.text(Cx,Cy, "D_cost=1",  ha="center", va="bottom", fontsize=9)
    plt.tight_layout()

# ========= ternary：上流固定なし→“最頻NE（mode）”で集約（推奨B） =========
def _act_code_u(u_act):  # 短縮表記（例: U(2,1)）
    return f"U{u_act}" if u_act is not None else "U—"

def _act_code_d(d_act):  # 短縮表記（例: D(0,2)）
    return f"D{d_act}" if d_act is not None else "D—"

def ternary_U_mode_over_D(
    df: pd.DataFrame, gen: str="Gen3",
    rcpU=None, rcpD=None, priorU=None, priorD=None,
    stepsU:int=9, stepsD:int=5, title:str=None,
    summarize:str="marginal",   # "marginal"（推奨） or "joint"
    show_code:str="auto"        # "auto" | "U" | "D" | "UD"
):
    """
    下流を固定せず、全 D 重み格子を走査。
    各 U 点に対して、(全D重みで) 最頻の NE を集計して ternary に描く。

    summarize:
      - "marginal": U アクション単独の“最頻”を採用（上流視点に素直で混乱がない）【推奨】
      - "joint"   : (U_action, D_action) のペア頻度で“最頻”を採用（相手情報も保持）

    show_code:
      - "auto": summarize=="marginal" のとき U のみ、"joint" のとき U|D を表示
      - "U":    常に U のみ表示（推奨）
      - "D":    常に D のみ表示（上流図では通常おすすめしません）
      - "UD":   常に U|D を表示
    """
    assert summarize in ("marginal", "joint")
    if show_code == "auto":
        show_code = "U" if summarize == "marginal" else "UD"

    U_points = simplex_weights(stepsU)
    D_points = simplex_weights(stepsD)

    rows = []
    markers = []  # "unique" / "multi" / "none"

    for (uf, ue, uc) in U_points:
        wU = {"flood":uf, "eco":ue, "cost":uc}

        # 全 D 重みで NE を収集
        joint_codes = []  # list of (U_action, D_action)
        for (dflood, dy, dc) in D_points:
            wD = {"flood":dflood, "yield":dy, "cost":dc}
            if priorU is not None or priorD is not None:
                _, _, NE, _ = NE_with_player_specific_priors(df, priorU or {}, priorD or {}, wU=wU, wD=wD, gen=gen)
            elif (rcpU is not None) or (rcpD is not None):
                _, _, NE, _ = NE_with_player_specific_RCPs(df, rcpU, rcpD, wU=wU, wD=wD, gen=gen)
            else:
                _, _, NE, _ = NE_complete_info(df, rcp=None, wU=wU, wD=wD, gen=gen)
            if not NE.empty:
                # 同一 (wU,wD) で複数NEある場合も全て記録して頻度に反映
                for _, r in NE.iterrows():
                    joint_codes.append((r["U_action"], r["D_action"]))

        if len(joint_codes) == 0:
            code = "—"; mark = "none"
        else:
            if summarize == "joint":
                # (U,D) のペア頻度で最頻
                s = pd.Series([f"{_act_code_u(u)}|{_act_code_d(d)}" for (u,d) in joint_codes])
                modes = s.mode()
                code = modes.iloc[0]
                mark = "unique" if len(modes) == 1 else "multi"
            else:
                # marginal: U 単独の頻度で最頻（D のバラつきを周辺化）
                s = pd.Series([_act_code_u(u) for (u,_) in joint_codes])
                modes = s.mode()
                code = modes.iloc[0]
                mark = "unique" if len(modes) == 1 else "multi"

            # 表示コードの調整
            if show_code == "U":
                if summarize == "joint":
                    code = code.split("|")[0]  # "U(..)|D(..)" → "U(..)"
            elif show_code == "D":
                if summarize == "joint":
                    code = code.split("|")[-1] # "U(..)|D(..)" → "D(..)"
                else:
                    code = "D—"
            elif show_code == "UD":
                if summarize == "marginal":
                    code = f"{code}|D—"       # U のみ結果を UD 風に

        Ux, Uy = _ternary_cartesian(uf, ue, uc)
        rows.append((Ux, Uy, code, uf, ue, uc))
        markers.append(mark)

    data = pd.DataFrame(rows, columns=["x","y","code","wU_flood","wU_eco","wU_cost"])
    vals, cats = _palette_for_codes(data["code"])

    plt.figure()
    sc_last = None
    for mark, mstyle in [("unique","o"), ("multi","D"), ("none","x")]:
        sub_idx = [i for i,m in enumerate(markers) if m==mark]
        if not sub_idx: continue
        sub = data.iloc[sub_idx]
        sc_last = plt.scatter(sub["x"], sub["y"],
                              c=vals[sub.index], s=40, marker=mstyle)

    if sc_last is not None:
        cbar = plt.colorbar(sc_last, ticks=range(len(cats)))
        cbar.ax.set_yticklabels(cats)

    ttl = title or ("Upstream ternary (mode over all Downstream weights)"
                    if summarize=="joint" else
                    "Upstream ternary (marginal mode of U over all Downstream weights)")
    plt.title(ttl)
    plt.xlabel("→ b (eco) + c/2")
    plt.ylabel("↑ c (cost)")

    # 正三角形の枠と頂点ラベル
    tri = np.array([_ternary_cartesian(1,0,0),
                    _ternary_cartesian(0,1,0),
                    _ternary_cartesian(0,0,1),
                    _ternary_cartesian(1,0,0)])
    plt.plot(tri[:,0], tri[:,1], lw=1.0, color="black")
    Ax,Ay = _ternary_cartesian(1,0,0); Bx,By = _ternary_cartesian(0,1,0); Cx,Cy = _ternary_cartesian(0,0,1)
    plt.text(Ax,Ay, "U_flood=1", ha="right", va="top", fontsize=9)
    plt.text(Bx,By, "U_eco=1",   ha="left",  va="top", fontsize=9)
    plt.text(Cx,Cy, "U_cost=1",  ha="center",va="bottom", fontsize=9)

    # マーカー凡例（unique / tie / no pure NE）
    import matplotlib.lines as mlines
    h1 = mlines.Line2D([], [], color='black', marker='o', linestyle='None', label='unique mode')
    h2 = mlines.Line2D([], [], color='black', marker='D', linestyle='None', label='multiple modes (tie)')
    h3 = mlines.Line2D([], [], color='black', marker='x', linestyle='None', label='no pure NE')
    plt.legend(handles=[h1,h2,h3], loc="best")

    plt.tight_layout()


def ternary_D_mode_over_U(
    df: pd.DataFrame, gen: str="Gen3",
    rcpU=None, rcpD=None, priorU=None, priorD=None,
    stepsD:int=9, stepsU:int=5, title:str=None,
    summarize:str="marginal",   # "marginal"（推奨） or "joint"
    show_code:str="auto"        # "auto" | "D" | "U" | "UD"
):
    """
    上流を固定せず、全 U 重み格子を走査。
    summarize:
      - "marginal": D アクション単独の“最頻”を採用（下流視点に素直で混乱がない）【推奨】
      - "joint"   : (U_action, D_action) の組で“最頻”を採用（ペアの情報を保持）
    show_code:
      - "auto": summarize=="marginal" のとき D のみ、"joint" のとき U|D を表示
      - "D":    常に D のみ表示
      - "U":    常に U のみ表示（下流図では通常おすすめしません）
      - "UD":   常に U|D を表示
    """
    assert summarize in ("marginal", "joint")
    if show_code == "auto":
        show_code = "D" if summarize == "marginal" else "UD"

    D_points = simplex_weights(stepsD)
    U_points = simplex_weights(stepsU)

    rows = []
    # 形状：unique（一意）/ multi（同率複数）/ none（純粋NEなし）
    markers = []

    for (dflood, dy, dc) in D_points:
        wD = {"flood":dflood, "yield":dy, "cost":dc}

        # 全 U 重みで NE を収集
        joint_codes = []  # (U_action, D_action)
        for (uf, ue, uc) in U_points:
            wU = {"flood":uf, "eco":ue, "cost":uc}
            if priorU is not None or priorD is not None:
                _, _, NE, _ = NE_with_player_specific_priors(df, priorU or {}, priorD or {}, wU=wU, wD=wD, gen=gen)
            elif (rcpU is not None) or (rcpD is not None):
                _, _, NE, _ = NE_with_player_specific_RCPs(df, rcpU, rcpD, wU=wU, wD=wD, gen=gen)
            else:
                _, _, NE, _ = NE_complete_info(df, rcp=None, wU=wU, wD=wD, gen=gen)
            if not NE.empty:
                # 同一 (wU,wD) で複数NEある場合はすべて拾う（頻度に反映される）
                for _, r in NE.iterrows():
                    joint_codes.append( (r["U_action"], r["D_action"]) )

        if len(joint_codes)==0:
            code = "—"; mark = "none"
        else:
            if summarize == "joint":
                # (U,D) のペア頻度で mode
                s = pd.Series([f"{_act_code_u(u)}|{_act_code_d(d)}" for (u,d) in joint_codes])
                modes = s.mode()  # 複数同率可
                code = modes.iloc[0]
                mark = "unique" if len(modes)==1 else "multi"
            else:
                # marginal: D 単独の頻度で mode（U によるバラつきを“周辺化”）
                s = pd.Series([_act_code_d(d) for (_,d) in joint_codes])
                modes = s.mode()
                code = modes.iloc[0]
                mark = "unique" if len(modes)==1 else "multi"

            # 表示コード指定に従って整える
            if show_code == "D":
                # すでに D のみ（marginal）ならそのまま、joint の場合は D を取り出す
                if summarize == "joint":
                    # "U(..)|D(..)" → 後半に切り出し
                    code = code.split("|")[-1]
            elif show_code == "U":
                if summarize == "joint":
                    code = code.split("|")[0]
                else:
                    # marginal から U 単独表示は意味が薄いのでダッシュ表示
                    code = "U—"
            elif show_code == "UD":
                if summarize == "marginal":
                    # D のみを UD 風に見せたい場合は U をダッシュに
                    code = f"U—|{code}"
                # summarize==joint のときはそのまま

        Dx, Dy2 = _ternary_cartesian(dflood, dy, dc)
        rows.append((Dx, Dy2, code, dflood, dy, dc))
        markers.append(mark)

    data = pd.DataFrame(rows, columns=["x","y","code","wD_flood","wD_yield","wD_cost"])
    vals, cats = _palette_for_codes(data["code"])

    plt.figure()
    # 形状ごとに描く（unique=●, multi=◇, none=×）
    sc_last = None
    for mark, mstyle in [("unique","o"), ("multi","D"), ("none","x")]:
        sub_idx = [i for i,m in enumerate(markers) if m==mark]
        if not sub_idx: continue
        sub = data.iloc[sub_idx]
        sc_last = plt.scatter(sub["x"], sub["y"],
                              c=vals[sub.index], s=40, marker=mstyle)

    if sc_last is not None:
        cbar = plt.colorbar(sc_last, ticks=range(len(cats)))
        cbar.ax.set_yticklabels(cats)

    ttl = title or ("Downstream ternary (mode over all Upstream weights)"
                    if summarize=="joint" else
                    "Downstream ternary (marginal mode of D over all Upstream weights)")
    plt.title(ttl)
    plt.xlabel("→ b (yield) + c/2")
    plt.ylabel("↑ c (cost)")

    # 三角形枠と頂点ラベル
    tri = np.array([_ternary_cartesian(1,0,0),
                    _ternary_cartesian(0,1,0),
                    _ternary_cartesian(0,0,1),
                    _ternary_cartesian(1,0,0)])
    plt.plot(tri[:,0], tri[:,1], lw=1.0, color="black")
    Ax,Ay = _ternary_cartesian(1,0,0); Bx,By = _ternary_cartesian(0,1,0); Cx,Cy = _ternary_cartesian(0,0,1)
    plt.text(Ax,Ay, "D_flood=1", ha="right", va="top", fontsize=9)
    plt.text(Bx,By, "D_yield=1", ha="left", va="top", fontsize=9)
    plt.text(Cx,Cy, "D_cost=1",  ha="center", va="bottom", fontsize=9)

    # 形状凡例
    import matplotlib.lines as mlines
    h1 = mlines.Line2D([], [], color='black', marker='o', linestyle='None', label='unique mode')
    h2 = mlines.Line2D([], [], color='black', marker='D', linestyle='None', label='multiple modes (tie)')
    h3 = mlines.Line2D([], [], color='black', marker='x', linestyle='None', label='no pure NE')
    plt.legend(handles=[h1,h2,h3], loc="best")

    plt.tight_layout()


# ========= デモ =========
if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)

    # 利用可能RCPを表示（トラブルシュート用）
    try:
        print("Available RCP (raw strings):", sorted(df["RCP"].astype(str).str.strip().unique().tolist()))
        print("Available RCP (numeric):    ", sorted([x for x in _normalize_rcp_series(df["RCP"]).unique() if pd.notna(x)]))
    except Exception as e:
        print("RCP列の確認でエラー:", e)

    # --- 1) 完備情報（全RCP込み, GEN=指定）でNE & PF
    _, _, NE_all, grid_all = NE_complete_info(df, rcp=None, wU=W_UP_BASE, wD=W_DN_BASE, gen=GEN)
    plot_utilities_with_pf_ne(grid_all, NE_all, f"U vs D utilities (GEN={GEN}, complete-info baseline)")
    plot_outcome_projection(grid_all, NE_all, "Flood Damage", "Crop Yield",
                            "Outcome space: Flood vs Yield (baseline)")
    plot_outcome_projection(grid_all, NE_all, "Ecosystem Level", "Crop Yield",
                            "Outcome space: Ecosystem vs Yield (baseline)")

    # --- 2) 重み違いでNE比較（ベース vs 代替）
    compare_ne_across_weights(df, W_UP_BASE, W_DN_BASE, W_UP_ALT, W_DN_ALT,
                              label_a="baseline", label_b="alt", gen=GEN)

    # --- 3) 各プレイヤーが異なるRCPを前提（例：Uは4.5、Dは8.5）
    rcpU, rcpD = 4.5, 8.5  # CSVの表記に合わせて 'RCP4.5', 'RCP8.5' などでも可
    try:
        _, _, NE_mis, grid_mis = NE_with_player_specific_RCPs(df, rcpU, rcpD, wU=W_UP_BASE, wD=W_DN_BASE, gen=GEN)
        plot_utilities_with_pf_ne(grid_mis, NE_mis, f"NE with player-specific RCPs (U:{rcpU}, D:{rcpD})")
    except Exception as e:
        print("NE_with_player_specific_RCPs error:", e)

    # --- 4) 各プレイヤーが異なるRCP事前（確率）を持つ例
    rcps = sorted(df["RCP"].astype(str).str.strip().unique().tolist())
    # 代表例（データに 2.6/4.5/8.5 が無い場合は自動で均等事前に）
    rcps_num = [x for x in _normalize_rcp_series(df["RCP"]).unique() if pd.notna(x)]
    if set([2.6,4.5,8.5]).issubset(set(rcps_num)):
        priorU = {2.6:0.2, 4.5:0.5, 8.5:0.3}
        priorD = {2.6:0.1, 4.5:0.3, 8.5:0.6}
    else:
        # 均等事前
        uniq = rcps_num if len(rcps_num)>0 else list(range(len(rcps)))  # 最悪raw index
        priorU = {r: 1/len(uniq) for r in uniq}
        priorD = {r: 1/len(uniq) for r in uniq}

    try:
        _, _, NE_pr, grid_pr = NE_with_player_specific_priors(df, priorU, priorD, wU=W_UP_BASE, wD=W_DN_BASE, gen=GEN)
        plot_utilities_with_pf_ne(grid_pr, NE_pr, "NE with player-specific RCP priors")
    except Exception as e:
        print("NE_with_player_specific_priors error:", e)

    # --- 5) 重みスイープ（RCPミスマッチ条件で例示）
    try:
        sweep_df = sweep_weights(df, gen=GEN, rcpU=rcpU, rcpD=rcpD, steps=5)
        # 5-1) NE頻度ランキング（上位10）
        plot_ne_frequency_bar(sweep_df, top_k=10,
                              title="Top NE action profiles by frequency (weight sweeps, mismatched RCPs)")
        # 5-2) 重み→NEの対応（読みやすいヒートマップ）
        plot_weight_to_NE_heatmaps(sweep_df,
                                   upstream_eco_slices=(0.0, 0.25, 0.5, 0.75, 1.0),
                                   downstream_yield_slices=(0.0, 0.25, 0.5, 0.75, 1.0))
    except Exception as e:
        print("sweep/plots error:", e)

    # 下流をベース重みに固定して、上流 ternary
    ternary_U_fixed_D(
        df,
        D_weights=W_DN_BASE,
        gen=GEN,
        # rcpU=4.5, rcpD=8.5,              # ← RCPミスマッチ断面にしたい場合
        # priorU={2.6:0.2,4.5:0.5,8.5:0.3}, # ← ベイジアンにしたい場合
        # priorD={2.6:0.1,4.5:0.3,8.5:0.6},
        steps=9,
        title="Upstream ternary with Downstream fixed (baseline)"
    )

    ternary_U_mode_over_D(
        df, gen=GEN,
        # rcpU=4.5, rcpD=8.5,            # or priorU/priorD=...
        stepsU=9, stepsD=5,
        summarize="marginal",            # ← 重要（U のみの最頻）
        show_code="U",                   # U アクションだけ表示
        title="Upstream ternary (marginal mode of U)"
    )

    # 1) 上流をベース重みに固定し、下流 ternary を描く（推奨A）
    ternary_D_fixed_U(
        df,
        U_weights=W_UP_BASE,
        gen=GEN,
        # rcpU=4.5, rcpD=8.5,              # ← RCPミスマッチ断面にしたい場合
        # priorU={2.6:0.2,4.5:0.5,8.5:0.3}, # ← ベイジアンにしたい場合
        # priorD={2.6:0.1,4.5:0.3,8.5:0.6},
        steps=9,
        title="Downstream ternary with Upstream fixed (baseline)"
    )

    # 2) 上流を固定せず、全U重み格子で“最頻NE”を下流 ternary に表示（推奨B）
    ternary_D_mode_over_U(
        df, gen=GEN,
        # rcpU=4.5, rcpD=8.5,         # or priorU/priorD=...
        stepsD=9, stepsU=5,
        summarize="marginal",         # ← ここがキモ
        show_code="D",                # D のみ表示（"auto" でもOK）
        title="Downstream ternary (marginal mode of D)"
    )

    plt.show()
