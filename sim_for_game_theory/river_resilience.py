import numpy as np
import matplotlib.pyplot as plt
import csv
import json

# ===============================
# シミュレーションの基本パラメータ（日本の自治体を想定）
# ===============================
START_YEAR = 2025
END_YEAR   = 2100
YEARS = np.arange(START_YEAR, END_YEAR + 1)

# 初期状態
INITIAL_FOREST_CAPACITY    = 100.0     # Forest retention capacity（単位は任意、初期は100）
INITIAL_DAM_CAPACITY       = 20.0      # 既存ダム容量（単位は任意、20）
INITIAL_EMBANKMENT_CAPACITY = 40.0      # 河川堤防許容流量（40）
INITIAL_HOUSES             = 5000      # 被災住宅数（5000戸）
INITIAL_ECOSYSTEM          = 100.0     # エコシステム指数（初期100）

# 各対策の投資効果（1回の投資で増加する単位）
FOREST_CAPACITY_INCREMENT     = 10.0   # 森林整備で10単位増加
DAM_CAPACITY_INCREMENT        = 10.0   # ダム投資で10単位増加
EMBANKMENT_CAPACITY_INCREMENT = 10.0   # 河川堤防投資で10単位増加

# 効果発現までの遅延期間（年）
DELAY_FOREST     = 40   # 森林整備：40年後に効果発現
DELAY_DAM        = 10   # ダム投資：10年後に効果発現（±1年のばらつきあり）
DELAY_EMBANKMENT = 5    # 河川堤防投資：5年後に効果発現（±1年のばらつきあり）

# 投資コスト（実際の規模に合わせて調整）
COST_FOREST_PER_UNIT      = 200000      # 森林整備：1単位あたり200,000円
COST_DAM_PER_UNIT         = 50000000    # ダム投資：1単位あたり50,000,000円
COST_EMBANKMENT_PER_UNIT  = 100000000   # 河川堤防投資：1単位あたり100,000,000円
COST_RELOCATION_PER_HOUSE = 30000000    # 住宅移転：1戸あたり30,000,000円

# 生態系への影響パラメータ
FOREST_ECO_FACTOR     = 0.2    # 森林整備による改善効果
DAM_ECO_FACTOR        = 0.1    # ダム投資による悪影響
EMBANKMENT_ECO_FACTOR = 0.05   # 河川堤防投資による悪影響

# 洪水被害モデルのパラメータ
DAMAGE_COEFFICIENT = 10000  # しきい値超過雨量1単位あたり、1戸に与える被害：10,000円

# ===============================
# 雨量モデル（実際の降水量を想定）
# ===============================
def generate_rainfall(year):
    """
    年ごとの降水量を生成する。
    - 2025年の平均降水量を300単位とし、年ごとに1単位ずつ増加
    - 標準偏差は50
    - 極端降水イベント：2025年は10%の確率で発生し、追加で100～200単位の雨量をもたらす
    """
    base_mean = 300 + (year - START_YEAR) * 1.0
    std = 50
    R = np.random.normal(base_mean, std)
    extreme_prob = 0.10 + (year - START_YEAR) * 0.001  # 2025:10%～2100:約17.5%
    if np.random.rand() < extreme_prob:
        R += np.random.uniform(100, 200)
    return max(R, 0.0)

# ===============================
# シミュレーション本体（1回の試行）
# ===============================
def simulate_run(policy_actions):
    # 状態変数の初期化
    forest_capacity     = INITIAL_FOREST_CAPACITY
    dam_capacity        = INITIAL_DAM_CAPACITY
    embankment_capacity = INITIAL_EMBANKMENT_CAPACITY
    houses_at_risk      = INITIAL_HOUSES
    ecosystem           = INITIAL_ECOSYSTEM

    # 効果発現予定のリスト：各要素 (effective_year, type, amount)
    pending_actions = []

    # 累積費用（円）
    upstream_cost   = 0.0    # 森林整備＋ダム投資（上流）
    downstream_cost = 0.0    # 河川堤防投資＋住宅移転（下流）

    # 累積洪水被害（円）
    cumulative_damage = 0.0

    # 年ごとの政策実施予定を整理
    policy_by_year = {}
    for act in policy_actions:
        policy_by_year.setdefault(act["year"], []).append(act)

    # 年次ループ
    for year in YEARS:
        # (1) 保留中の投資が効果発現するかチェック
        new_pending = []
        for (eff_year, act_type, amount) in pending_actions:
            if year >= eff_year:
                if act_type == "forest":
                    forest_capacity += FOREST_CAPACITY_INCREMENT * amount
                elif act_type == "dam":
                    multiplier = np.random.uniform(0.8, 1.2)
                    dam_capacity += DAM_CAPACITY_INCREMENT * amount * multiplier
                elif act_type == "embankment":
                    multiplier = np.random.uniform(0.8, 1.2)
                    embankment_capacity += EMBANKMENT_CAPACITY_INCREMENT * amount * multiplier
            else:
                new_pending.append((eff_year, act_type, amount))
        pending_actions = new_pending

        # (2) 当年の政策実施
        if year in policy_by_year:
            for act in policy_by_year[year]:
                if act["type"] == "forest":
                    pending_actions.append((year + DELAY_FOREST, "forest", act["amount"]))
                    cost = COST_FOREST_PER_UNIT * FOREST_CAPACITY_INCREMENT * act["amount"]
                    upstream_cost += cost
                elif act["type"] == "dam":
                    delay_offset = np.random.randint(-1, 2)
                    pending_actions.append((year + DELAY_DAM + delay_offset, "dam", act["amount"]))
                    cost = COST_DAM_PER_UNIT * DAM_CAPACITY_INCREMENT * act["amount"]
                    upstream_cost += cost
                elif act["type"] == "embankment":
                    delay_offset = np.random.randint(-1, 2)
                    pending_actions.append((year + DELAY_EMBANKMENT + delay_offset, "embankment", act["amount"]))
                    cost = COST_EMBANKMENT_PER_UNIT * EMBANKMENT_CAPACITY_INCREMENT * act["amount"]
                    downstream_cost += cost
                elif act["type"] == "relocate":
                    houses = act["houses"]
                    houses_at_risk = max(0, houses_at_risk - houses)
                    cost = COST_RELOCATION_PER_HOUSE * houses
                    downstream_cost += cost

        # (3) 降水量の発生
        R = generate_rainfall(year)
        # (4) しきい値 = 森林保持能力 + ダム貯水能力 + 河川堤防許容流量
        threshold = forest_capacity + dam_capacity + embankment_capacity
        # (5) 洪水被害の算出
        if R > threshold:
            damage = (R - threshold) * DAMAGE_COEFFICIENT * houses_at_risk
        else:
            damage = 0.0
        cumulative_damage += damage

        # (6) 生態系指標の更新（決定論的効果＋ランダムノイズ）
        forest_effect     = (forest_capacity - INITIAL_FOREST_CAPACITY) * FOREST_ECO_FACTOR
        dam_effect        = dam_capacity * DAM_ECO_FACTOR
        embankment_effect = (embankment_capacity - INITIAL_EMBANKMENT_CAPACITY) * EMBANKMENT_ECO_FACTOR
        ecosystem = INITIAL_ECOSYSTEM + forest_effect - dam_effect - embankment_effect + np.random.normal(0, 2)

    results = {
        "cumulative_damage": cumulative_damage,
        "upstream_cost": upstream_cost,
        "downstream_cost": downstream_cost,
        "final_ecosystem": ecosystem
    }
    return results

# ===============================
# モンテカルロ・シミュレーション実施関数
# ===============================
def monte_carlo_simulation(n_runs, policy_actions, seed=None):
    if seed is not None:
        np.random.seed(seed)
    results_list = []
    for _ in range(n_runs):
        results_list.append(simulate_run(policy_actions))
    return results_list

# ===============================
# 各分布のパーセンタイルを計算する関数
# ===============================
def compute_percentiles(data):
    pct = np.percentile(data, [1, 5, 25, 50, 75, 95, 99])
    return {p: v for p, v in zip([1, 5, 25, 50, 75, 95, 99], pct)}

# ===============================
# 意思決定シナリオのポリシー生成関数
# ===============================
def generate_policy_actions(forest_decision, dam_decision, embankment_decision, relocation_decision):
    """
    上流自治体：森林整備、ダム投資
    下流自治体：河川堤防投資、住宅移転
    各項目は True（する）/ False（しない）で指定
    """
    actions = []
    if forest_decision:
        actions.append({"type": "forest", "year": 2025, "amount": 1})
    if dam_decision:
        actions.append({"type": "dam", "year": 2030, "amount": 1})
    if embankment_decision:
        actions.append({"type": "embankment", "year": 2035, "amount": 1})
    if relocation_decision:
        actions.append({"type": "relocate", "year": 2040, "houses": 100})
    return actions

# ===============================
# メイン処理：16通りの組み合わせでシミュレーション実施＆CSV出力
# ===============================
if __name__ == "__main__":
    n_runs = 1000  # 試行回数
    # 意思決定の「する／しない」のラベル
    label = {True: "する", False: "しない"}
    decision_map = {True: "Yes", False: "No"}
    decisions = [False, True]

    # sim_data_out: sim_data と同じ形式に整形するための辞書
    # キー: (upstream_strategy, downstream_strategy)
    # 値: { "upstream_cost": np.array(...),
    #         "downstream_cost": np.array(...),
    #         "flood_damage": np.array(...),
    #         "ecosystem": np.array(...) }
    sim_data_out = {}

    # 以下、各組み合わせごとにシミュレーション実施
    # また、散布図用やシナリオ別分析用のデータも収集
    results_matrix = {}
    scenario_data = {}
    scatter_points = []

    for forest in decisions:
        for dam in decisions:
            for embankment in decisions:
                for relocation in decisions:
                    # Upstream戦略の文字列
                    if forest and dam:
                        u_strat = "Both"
                    elif forest:
                        u_strat = "Forest"
                    elif dam:
                        u_strat = "Dam"
                    else:
                        u_strat = "No"
                    # Downstream戦略の文字列
                    if embankment and relocation:
                        d_strat = "Both"
                    elif embankment:
                        d_strat = "Embankment"
                    elif relocation:
                        d_strat = "Relocation"
                    else:
                        d_strat = "No"

                    label_text = (f"Forest: {decision_map[forest]}, Dam: {decision_map[dam]} | "
                                  f"Embankment: {decision_map[embankment]}, Relocation: {decision_map[relocation]}")

                    policy_actions = generate_policy_actions(forest, dam, embankment, relocation)
                    sim_results = monte_carlo_simulation(n_runs, policy_actions, seed=42)
                    
                    upstream_costs   = np.array([res["upstream_cost"] for res in sim_results])
                    ecosystems       = np.array([res["final_ecosystem"] for res in sim_results])
                    flood_damages    = np.array([res["cumulative_damage"] for res in sim_results])
                    downstream_costs = np.array([res["downstream_cost"] for res in sim_results])
                    
                    # 保存：sim_data_out にはキー (u_strat, d_strat) で格納
                    sim_data_out[(u_strat, d_strat)] = {
                        "upstream_cost": upstream_costs,
                        "downstream_cost": downstream_costs,
                        "flood_damage": flood_damages,
                        "ecosystem": ecosystems
                    }
                    
                    # パーセンタイル計算（表示用）
                    up_cost_pct   = compute_percentiles(upstream_costs)
                    eco_pct       = compute_percentiles(ecosystems)
                    flood_pct     = compute_percentiles(flood_damages)
                    down_cost_pct = compute_percentiles(downstream_costs)
                    
                    combo_key = (f"森林整備:{label[forest]} / ダム投資:{label[dam]} | "
                                 f"河川堤防投資:{label[embankment]} / 住宅移転:{label[relocation]}")
                    results_matrix[combo_key] = {
                        "upstream_cost": up_cost_pct,
                        "ecosystem": eco_pct,
                        "flood_damage": flood_pct,
                        "downstream_cost": down_cost_pct
                    }
                    
                    # 散布図用：各ケースの中央値を取得
                    median_flood = flood_pct[50]
                    median_eco   = eco_pct[50]
                    scatter_points.append((median_flood, median_eco, combo_key))
                    
                    # scenario_data も（必要に応じて）
                    scenario_data[label_text] = {
                        "flood": flood_damages,
                        "eco": ecosystems,
                        "median_flood": np.median(flood_damages),
                        "median_eco": np.median(ecosystems)
                    }

    # ===============================
    # CSV 出力：sim_data_out と同じ形式で出力する
    # ===============================
    # 各行の形式は:
    # Forest,Dam,Embankment,Relocation,Run,upstream_cost,downstream_cost,cumulative_damage,final_ecosystem
    csv_filename = "sim_data.csv"
    fieldnames = ["Forest", "Dam", "Embankment", "Relocation", "Run",
                  "upstream_cost", "downstream_cost", "cumulative_damage", "final_ecosystem"]
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # 各政策組合せごとに、n_runs 試行の結果を出力
        for key, outcomes in sim_data_out.items():
            u_strat, d_strat = key
            # 上流側の戦略 u_strat: "Forest"/"Dam"/"Both" → Forest: True if either "Forest" or "Both"
            # 下流側の戦略 d_strat: "Embankment"/"Relocation"/"Both" → Embankment: True if either "Embankment" or "Both"
            for i in range(n_runs):
                row = {
                    "Forest": str(u_strat in ["Forest", "Both"]),
                    "Dam": str(u_strat in ["Dam", "Both"]),
                    "Embankment": str(d_strat in ["Embankment", "Both"]),
                    "Relocation": str(d_strat in ["Relocation", "Both"]),
                    "Run": i+1,
                    "upstream_cost": outcomes["upstream_cost"][i],
                    "downstream_cost": outcomes["downstream_cost"][i],
                    "cumulative_damage": outcomes["flood_damage"][i],
                    "final_ecosystem": outcomes["ecosystem"][i]
                }
                writer.writerow(row)
    print(f"Simulation data written to {csv_filename}")

    # =====================================
    # Scatter Plot: Distribution of Flood Damage vs Ecosystem Outcome
    # =====================================
    plt.figure(figsize=(12, 8))
    colors = plt.cm.tab20(np.linspace(0, 1, len(scenario_data)))
    for i, (label_text, data) in enumerate(scenario_data.items()):
        flood_data = data["flood"]
        eco_data   = data["eco"]
        median_flood = data["median_flood"]
        median_eco   = data["median_eco"]
        plt.scatter(flood_data, eco_data, alpha=0.05, color=colors[i])
        plt.scatter(median_flood, median_eco, marker='D', s=100, edgecolor='k',
                    color=colors[i], label=label_text)
    plt.xlabel("Flood Damage (Yen)")
    plt.ylabel("Ecosystem Index")
    plt.title("Distribution of Flood Damage vs Ecosystem Outcomes for 16 Policy Combinations")
    plt.grid(True)
    plt.tight_layout()
    plt.legend(bbox_to_anchor=(0.98, 0.98), loc='upper right', fontsize='x-small')
    plt.show()
