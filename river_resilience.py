import itertools

# --- 1. パラメータ設定 ---

# 気候シナリオの確率
scenarios = {
    "omega1": 0.3,  # 洪水規模(小)
    "omega2": 0.5,  # 洪水規模(中)
    "omega3": 0.2   # 洪水規模(大)
}

# (上流被害, 下流被害) テーブル: {(sU, sD, omega): (被害U, 被害D), ...}
# 例示用に辞書で定義
damage_table = {
    ("Dam", "Levee", "omega1"): (1, 2),
    ("Dam", "Levee", "omega2"): (2, 3),
    ("Dam", "Levee", "omega3"): (4, 5),

    ("Dam", "Relocation", "omega1"): (1, 1),
    ("Dam", "Relocation", "omega2"): (1, 1),
    ("Dam", "Relocation", "omega3"): (2, 1),

    ("Forest", "Levee", "omega1"): (2, 3),
    ("Forest", "Levee", "omega2"): (3, 4),
    ("Forest", "Levee", "omega3"): (5, 7),

    ("Forest", "Relocation", "omega1"): (2, 2),
    ("Forest", "Relocation", "omega2"): (2, 2),
    ("Forest", "Relocation", "omega3"): (3, 2),
}

# コスト設定
cost_upstream = {
    "Dam": 8,
    "Forest": 4
}
cost_downstream = {
    "Levee": 5,
    "Relocation": 7
}

# 基準被害額（便宜上、上流・下流とも 10）
BASE_DAMAGE = 10


# --- 2. 効用計算関数 ---

def utility_upstream(strategy_u, strategy_d, scenario):
    """
    上流の効用: B_U(sU, sD, omega) - C_U(sU)
    """
    # 被害額を取得
    damage_u, _ = damage_table[(strategy_u, strategy_d, scenario)]
    benefit_u = BASE_DAMAGE - damage_u
    cost_u = cost_upstream[strategy_u]
    return benefit_u - cost_u

def utility_downstream(strategy_u, strategy_d, scenario):
    """
    下流の効用: B_D(sU, sD, omega) - C_D(sD)
    """
    # 被害額を取得
    _, damage_d = damage_table[(strategy_u, strategy_d, scenario)]
    benefit_d = BASE_DAMAGE - damage_d
    cost_d = cost_downstream[strategy_d]
    return benefit_d - cost_d


def expected_utility(strategy_u, strategy_d):
    """
    上下流の期待効用 (E[u_U], E[u_D]) を返す
    """
    eu_u = 0.0
    eu_d = 0.0
    for sc, p in scenarios.items():
        eu_u += utility_upstream(strategy_u, strategy_d, sc) * p
        eu_d += utility_downstream(strategy_u, strategy_d, sc) * p
    return eu_u, eu_d


# --- 3. 全戦略の期待効用を計算して表示 ---

strategies_u = ["Dam", "Forest"]
strategies_d = ["Levee", "Relocation"]

print("=== Expected Utilities for Each Strategy Pair ===")
payoff_table = {}
for (sU, sD) in itertools.product(strategies_u, strategies_d):
    eu_u, eu_d = expected_utility(sU, sD)
    payoff_table[(sU, sD)] = (eu_u, eu_d)
    print(f"{(sU, sD)} => E[u_U]={eu_u:.2f}, E[u_D]={eu_d:.2f}")


# --- 4. 非協力ゲーム: ナッシュ均衡探索 ---

def best_response_upstream(sD):
    """
    下流の戦略 sD が与えられたとき、上流の最適戦略と最大期待効用を返す。
    """
    best_strat = None
    best_val = float("-inf")
    for sU in strategies_u:
        val_u, _ = expected_utility(sU, sD)
        if val_u > best_val:
            best_val = val_u
            best_strat = sU
    return best_strat, best_val

def best_response_downstream(sU):
    """
    上流の戦略 sU が与えられたとき、下流の最適戦略と最大期待効用を返す。
    """
    best_strat = None
    best_val = float("-inf")
    for sD in strategies_d:
        _, val_d = expected_utility(sU, sD)
        if val_d > best_val:
            best_val = val_d
            best_strat = sD
    return best_strat, best_val

nash_candidates = []
for (sU, sD) in itertools.product(strategies_u, strategies_d):
    # (sU, sD) がナッシュ均衡となるためには:
    # 1) sU は sD を所与としたときの上流のベストレスポンス
    # 2) sD は sU を所与としたときの下流のベストレスポンス
    br_u, val_u = best_response_upstream(sD)
    br_d, val_d = best_response_downstream(sU)
    if (sU == br_u) and (sD == br_d):
        nash_candidates.append((sU, sD))

print("\n=== Nash Equilibrium Candidates ===")
for c in nash_candidates:
    eu_u, eu_d = payoff_table[c]
    print(f"{c} => E[u_U]={eu_u:.2f}, E[u_D]={eu_d:.2f}")


# --- 5. 協力ゲーム: 社会的最適解 + 利得分配 ---

# 社会的効用 (E[u_U] + E[u_D]) を最大化する戦略の探索
best_social_value = float("-inf")
best_social_strat = None
for (sU, sD) in itertools.product(strategies_u, strategies_d):
    eu_u, eu_d = payoff_table[(sU, sD)]
    social_val = eu_u + eu_d
    if social_val > best_social_value:
        best_social_value = social_val
        best_social_strat = (sU, sD)

print("\n=== Cooperative Game: Socially Optimal Strategy ===")
print(f"Strategy = {best_social_strat}, "
      f"E[u_U] + E[u_D] = {best_social_value:.2f}")

# シャープレイ値等の分配方式は、ゲームの規模が大きくなると
# 連合の生成関数などに基づいてより複雑な計算を行う。
# ここでは単に (E[u_U], E[u_D]) を参考に補償スキームを考えるなど。
