# ============================================================
# 2プレイヤー（上流/下流）ゲーム分析ユーティリティ
#  - 完備情報ナッシュ均衡（RCP固定 or 全RCP平均）
#  - RCP事前分布つきベイジアンNE（自然状態の不確実性）
#  - 「重み」をタイプとするベイジアンNE（タイプ不確実性）
#  - パレートフロンティア（U/D効用の非支配集合）
# 対応CSVの前提（列名例）:
#  - 行動(level): dam_levee_construction_cost_level, planting_trees_amount_level,
#                 flow_irrigation_level_level, house_migration_amount_level
#  - コスト(value): *_value 4列
#  - アウトカム: Flood Damage_<Gen>, Ecosystem Level_<Gen>, Crop Yield_<Gen>
#  - RCP: "RCP" 列（2.6/4.5/8.5等）
#  - 世代: Gen1/Gen2/Gen3 等のサフィックスを選択
# ============================================================

import pandas as pd
import numpy as np
from itertools import product

# ========= 基本設定（必要に応じて変更） =========
GEN = "Gen3"  # "Gen1" / "Gen2" / "Gen3" など
COL_FLOOD = f"Flood Damage_{GEN}"
COL_ECO   = f"Ecosystem Level_{GEN}"
COL_YIELD = f"Crop Yield_{GEN}"

U_DEC = ["dam_levee_construction_cost_level", "planting_trees_amount_level"]
D_DEC = ["flow_irrigation_level_level", "house_migration_amount_level"]

U_COST_VALUE_COLS = ["dam_levee_construction_cost_value", "planting_trees_amount_value"]
D_COST_VALUE_COLS = ["flow_irrigation_level_value", "house_migration_amount_value"]

def norm01(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    mn, mx = float(s.min()), float(s.max())
    if mx - mn < 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mn) / (mx - mn)

def list_actions(df: pd.DataFrame):
    Ua = sorted(set(tuple(x) for x in df[U_DEC].values.tolist()))
    Da = sorted(set(tuple(x) for x in df[D_DEC].values.tolist()))
    return Ua, Da

def slice_profile(df: pd.DataFrame, U_action, D_action):
    q = (df[U_DEC[0]]==U_action[0]) & (df[U_DEC[1]]==U_action[1]) & \
        (df[D_DEC[0]]==D_action[0]) & (df[D_DEC[1]]==D_action[1])
    return df[q]

def build_payoffs(df_raw: pd.DataFrame, wU: dict, wD: dict) -> pd.DataFrame:
    """アウトカム→効用（0-1正規化後、加重和）を作る。高いほど良い定義。"""
    df = df_raw.copy()
    flood_n = norm01(df[COL_FLOOD])     # 低いほど良い → 後でマイナス
    eco_n   = norm01(df[COL_ECO])       # 高いほど良い
    yield_n = norm01(df[COL_YIELD])     # 高いほど良い
    U_cost  = norm01(df[U_COST_VALUE_COLS].sum(axis=1))  # 低いほど良い → マイナス
    D_cost  = norm01(df[D_COST_VALUE_COLS].sum(axis=1))

    # 効用（maximize基準）
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
    """同一行動プロファイルが複数行ある場合は平均で集約。"""
    grp = dfP.groupby(U_DEC + D_DEC, as_index=False).agg({
        "U_payoff":"mean","D_payoff":"mean","SW":"mean",
        COL_FLOOD:"mean", COL_ECO:"mean", COL_YIELD:"mean",
        U_COST_VALUE_COLS[0]:"mean", U_COST_VALUE_COLS[1]:"mean",
        D_COST_VALUE_COLS[0]:"mean", D_COST_VALUE_COLS[1]:"mean",
    })
    # 読みやすい形に
    grp = grp.rename(columns={
        U_COST_VALUE_COLS[0]:"U_cost_1", U_COST_VALUE_COLS[1]:"U_cost_2",
        D_COST_VALUE_COLS[0]:"D_cost_1", D_COST_VALUE_COLS[1]:"D_cost_2",
    })
    grp["U_action"] = list(zip(grp[U_DEC[0]], grp[U_DEC[1]]))
    grp["D_action"] = list(zip(grp[D_DEC[0]], grp[D_DEC[1]]))
    return grp

def best_responses_and_NE(grid: pd.DataFrame):
    """ベストレスポンスの交点をNEとして抽出（純戦略）。"""
    # DのBR：各U_actionに対し D_payoff 最大のD
    idxD = grid.groupby("U_action")["D_payoff"].idxmax()
    BR_D = grid.loc[idxD, ["U_action","D_action"]].assign(BR="D")
    # UのBR：各D_actionに対し U_payoff 最大のU
    idxU = grid.groupby("D_action")["U_payoff"].idxmax()
    BR_U = grid.loc[idxU, ["U_action","D_action"]].assign(BR="U")
    # 交点がNE
    NE = pd.merge(BR_D, BR_U, on=["U_action","D_action"], how="inner")
    NE = pd.merge(NE[["U_action","D_action"]].drop_duplicates(), grid,
                  on=["U_action","D_action"], how="left").sort_values("SW", ascending=False)
    return BR_U, BR_D, NE

# ---------- 完備情報 NE（RCP固定 or 全平均） ----------
def NE_complete_info(df: pd.DataFrame, rcp=None, wU=None, wD=None):
    if wU is None: wU = {"flood":0.4,"eco":0.4,"cost":0.2}
    if wD is None: wD = {"flood":0.4,"yield":0.4,"cost":0.2}
    if rcp is not None:
        dfR = df[df["RCP"]==rcp].copy()
    else:
        dfR = df.copy()  # 全RCPをプールして平均
    dfP = build_payoffs(dfR, wU, wD)
    grid = grid_from_df(dfP)
    BR_U, BR_D, NE = best_responses_and_NE(grid)
    return grid, BR_U, BR_D, NE

# ---------- RCP事前つきベイジアンNE（自然状態の不確実性） ----------
def NE_with_RCP_prior(df: pd.DataFrame, rcp_prior: dict, wU=None, wD=None):
    """RCPごとの効用を作り、事前確率で加重平均した期待効用ゲームのNEを返す。"""
    if wU is None: wU = {"flood":0.4,"eco":0.4,"cost":0.2}
    if wD is None: wD = {"flood":0.4,"yield":0.4,"cost":0.2}

    frames = []
    for r, pr in rcp_prior.items():
        sub = df[df["RCP"]==r].copy()
        sub = build_payoffs(sub, wU, wD)
        sub["__w__"] = pr
        frames.append(sub)
    cat = pd.concat(frames, ignore_index=True)

    # 期待効用で集約
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
    BR_U, BR_D, NE = best_responses_and_NE(grid)
    return grid, BR_U, BR_D, NE

# ---------- パレートフロンティア（U/D効用） ----------
def pareto_front_UD(grid: pd.DataFrame):
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

# ---------- ベイジアンNE（重みをタイプとする） ----------
def BNE_weight_types(
    df: pd.DataFrame,
    U_types: dict,  # {type_name: {"flood":..., "eco":..., "cost":...}}
    D_types: dict,  # {type_name: {"flood":..., "yield":..., "cost":...}}
    prior_U: dict,  # {type_name: prob}  sum=1
    prior_D: dict,  # {type_name: prob}  sum=1
    rcp_prior: dict | None = None  # 併せてRCP不確実性も考慮するなら与える
):
    """
    戻り値: 
      strategies_NE = {"U": {type: action}, "D": {type: action}}
      payoff_tables = {"U": {type: DataFrame(grid with U_payoff)}, "D": {...}}
    アルゴリズム:
      - 各タイプの重みで効用表（行動×行動）を作る（RCP事前があれば期待効用化）
      - 戦略（タイプ -> 行動）の全組合せを総当りし、各タイプのBR条件を満たすペアをBNEとして抽出
    注意: 行動数×タイプ数が大きいと指数的に重くなります。
    """
    # まず、RCPなしの「基底」グリッドを作っておく
    def grid_for_weights(wU, wD):
        if rcp_prior is None:
            dfP = build_payoffs(df, wU, wD)
            return grid_from_df(dfP)
        else:
            g,_BRU,_BRD,_NE = NE_with_RCP_prior(df, rcp_prior, wU, wD)
            return g  # すでに期待効用済み

    # タイプ別に効用グリッドを用意
    grid_Utype = {t: grid_for_weights(wU=U_types[t], wD=list(D_types.values())[0]) for t in U_types}  # Dの重みは仮でもOK（U_payoffはU側重みで決まる）
    grid_Dtype = {t: grid_for_weights(wU=list(U_types.values())[0], wD=D_types[t]) for t in D_types}  # 同上

    Ua, Da = list_actions(df)

    # 戦略空間：タイプ毎にどの行動を選ぶか
    U_strategy_space = list(product(Ua, repeat=len(U_types)))  # 例: Uが2タイプ×9行動 → 9^2
    D_strategy_space = list(product(Da, repeat=len(D_types)))

    # 効用の取り出し用辞書（高速化）
    def payoff_lookup(grid, U_action, D_action, which):
        row = grid[(grid["U_action"]==U_action) & (grid["D_action"]==D_action)]
        if row.empty:
            return -1e9  # 存在しない組み合わせは極小
        return float(row.iloc[0][f"{which}_payoff"])

    BNEs = []
    for U_strat in U_strategy_space:
        # 各UタイプのBRチェックで使う：相手戦略に依存するのでDのループ内で評価
        for D_strat in D_strategy_space:
            # 期待効用（相手タイプ分布に対する）で各自のタイプ別BRを確認
            # U側：各Uタイプtについて、現戦略 a_U(t) がBRか？
            ok_U = True
            for ti, tname in enumerate(U_types.keys()):
                aU = U_strat[ti]
                # 相手のタイプ分布に対して期待
                EU_current = 0.0
                # 比較用に、他のU行動全てについてEU_bestを算出
                EU_best = -1e18
                for aU_cand in Ua:
                    EU_cand = 0.0
                    for sj, sname in enumerate(D_types.keys()):
                        aD = D_strat[sj]
                        # Uタイプの効用はU重みだけで決まる → grid_Utype[tname] を使用
                        gridU = grid_Utype[tname]
                        EU_cand += prior_D[sname] * payoff_lookup(gridU, aU_cand, aD, "U")
                    EU_best = max(EU_best, EU_cand)
                    if aU_cand == aU:
                        EU_current = EU_cand
                if EU_current + 1e-12 < EU_best:
                    ok_U = False
                    break

            # D側：各Dタイプsについて、現戦略 a_D(s) がBRか？
            ok_D = True
            for sj, sname in enumerate(D_types.keys()):
                aD = D_strat[sj]
                ED_current = 0.0
                ED_best = -1e18
                for aD_cand in Da:
                    ED_cand = 0.0
                    for ti, tname in enumerate(U_types.keys()):
                        aU = U_strat[ti]
                        gridD = grid_Dtype[sname]
                        ED_cand += prior_U[tname] * payoff_lookup(gridD, aU, aD_cand, "D")
                    ED_best = max(ED_best, ED_cand)
                    if aD_cand == aD:
                        ED_current = ED_cand
                if ED_current + 1e-12 < ED_best:
                    ok_D = False
                    break

            if ok_U and ok_D:
                BNEs.append({
                    "U_strategy": {t: U_strat[i] for i,t in enumerate(U_types.keys())},
                    "D_strategy": {t: D_strat[i] for i,t in enumerate(D_types.keys())},
                })

    return BNEs

# ================== 使い方 ==================
if __name__ == "__main__":
    # 1) CSV読み込み
    path = "../output/dmdu_summary_irrigation_251006.csv"
    df = pd.read_csv(path)

    # 2) 完備情報NE（RCP=ALL平均）
    grid_all, BR_U, BR_D, NE_all = NE_complete_info(df, rcp=None,
        wU={"flood":0.4,"eco":0.4,"cost":0.2},
        wD={"flood":0.4,"yield":0.4,"cost":0.2}
    )
    print("=== Complete-Info NE (RCP=ALL average) ===")
    print(NE_all.head(10))

    # 3) RCP固定（例：8.5）
    grid_85, _, _, NE_85 = NE_complete_info(df, rcp=8.5)
    print("\n=== Complete-Info NE (RCP=8.5) ===")
    print(NE_85.head(10))

    # 4) RCP事前（ベイジアン：自然状態の不確実性）
    rcps = sorted(df["RCP"].unique().tolist())
    prior = {r: 1/len(rcps) for r in rcps}  # 均等事前（必要に応じて編集）
    grid_rcp, _, _, NE_rcp = NE_with_RCP_prior(df, prior)
    print("\n=== Bayesian NE under RCP prior (uniform) ===")
    print(NE_rcp.head(10))

    # 5) パレートフロンティア（U/D効用）
    PF = pareto_front_UD(grid_all)
    print("\n=== Pareto Frontier (U vs D utilities, RCP=ALL) ===")
    print(PF.head(15))

    # 6) ベイジアンNE（重み=タイプ）
    #   例: 上流タイプ（エコ重視/コスト重視）、下流タイプ（収量重視/洪水重視）
    U_types = {
        "eco_pref":   {"flood":0.3,"eco":0.6,"cost":0.1},
        "cost_pref":  {"flood":0.3,"eco":0.2,"cost":0.5},
    }
    D_types = {
        "yield_pref": {"flood":0.2,"yield":0.7,"cost":0.1},
        "flood_pref": {"flood":0.6,"yield":0.3,"cost":0.1},
    }
    prior_U = {"eco_pref":0.5, "cost_pref":0.5}
    prior_D = {"yield_pref":0.5, "flood_pref":0.5}
    # （必要なら rcp_prior=prior を渡すと、RCP不確実性も効用に畳み込み可能）
    BNEs = BNE_weight_types(df, U_types, D_types, prior_U, prior_D, rcp_prior=None)
    print("\n=== Bayesian NE with weight-types (example) ===")
    if BNEs:
        for i, bne in enumerate(BNEs[:5]):
            print(f"BNE #{i+1}", bne)
    else:
        print("No BNE found for this type/prior setup (try adjusting weights or priors).")
