import pandas as pd

# CSVの読み込み
df = pd.read_csv("output/dmdu_clustered_summary85.csv")

# 対象のPolicy_IDを指定（例: 上位解など）
target_ids = [158,164,82,439,388]  # 必要に応じて変更

# 意思決定変数
decision_vars = ['planting_trees_amount', 'house_migration_amount', 'dam_levee_construction_cost', 'capacity_building_cost']

# 抽出と整形
for pid in target_ids:
    row = df[df['Policy_ID'] == pid].iloc[0]
    print(f"\n=== Policy_ID {pid} ===")
    for t in range(1, 4):  # t1, t2, t3
        decision = {var: int(row[f"{var}_t{t}"]) for var in decision_vars}
        print(f"Year {2026 + (t - 1) * 25}: {decision}")
