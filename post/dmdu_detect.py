import pandas as pd

# 読み込み（事前にファイルを保存しておくこと）
df = pd.read_csv("output/dmdu_full_timeseries85.csv")

# 指標と世代定義
features = ['Flood Damage', 'Ecosystem Level', 'Resident Burden']
generations = {
    'Gen1': (2026, 2050),
    'Gen2': (2051, 2075),
    'Gen3': (2076, 2100)
}

# 各世代の平均指標値を Policy_ID ごとに集計
records = []
for policy_id, group in df.groupby('Policy_ID'):
    result = {'Policy_ID': policy_id}
    for gen_label, (start, end) in generations.items():
        df_gen = group[(group['Year'] >= start) & (group['Year'] <= end)]
        for feat in features:
            avg_val = df_gen[feat].mean()
            result[f"{feat}_{gen_label}"] = avg_val
    records.append(result)

summary_df = pd.DataFrame(records)

# 各世代において非劣解（パレート解）を抽出する関数
def extract_pareto_ids(df, gen):
    df_gen = df[[f"Flood Damage_{gen}", f"Ecosystem Level_{gen}", f"Resident Burden_{gen}", 'Policy_ID']].copy()
    df_gen.columns = ['FD', 'Eco', 'RB', 'Policy_ID']

    pareto_ids = []
    for i, row in df_gen.iterrows():
        dominated = False
        for j, other in df_gen.iterrows():
            if (
                other['FD'] <= row['FD'] and
                other['RB'] <= row['RB'] and
                other['Eco'] >= row['Eco'] and
                (other['FD'] < row['FD'] or other['RB'] < row['RB'] or other['Eco'] > row['Eco'])
            ):
                dominated = True
                break
        if not dominated:
            pareto_ids.append(row['Policy_ID'])
    return set(pareto_ids)

# 各世代のパレート解 Policy_ID を取得
pareto_ids_gen = {
    gen: extract_pareto_ids(summary_df, gen)
    for gen in generations.keys()
}

# 全ての世代で非劣な政策の共通集合
dominant_all_gens = pareto_ids_gen['Gen1'] & pareto_ids_gen['Gen2'] & pareto_ids_gen['Gen3']

# 結果出力
print(f"✅ 3期間すべてで非劣解となったPolicy_IDの数: {len(dominant_all_gens)}")
print(dominant_all_gens)

# 詳細情報を表示（必要に応じて）
result_df = summary_df[summary_df['Policy_ID'].isin(dominant_all_gens)]
print(result_df.sort_values(by='Policy_ID').head())

# CSVで出力したい場合：
# result_df.to_csv("output/best_policies_all_gens.csv", index=False)

# ========= 重み付き評価指標（Flood Damage + 15000 × Burden - 10^6 × Ecosystem） =========
# 重み定義
FD_weight = 1
Eco_weight = -1_000_000
RB_weight = 15_000

# 各世代のスコアを計算
for gen in ['Gen1', 'Gen2', 'Gen3']:
    summary_df[f'Score_{gen}'] = (
        summary_df[f'Flood Damage_{gen}'] * FD_weight +
        summary_df[f'Ecosystem Level_{gen}'] * Eco_weight +
        summary_df[f'Resident Burden_{gen}'] * RB_weight
    )

# 合計スコア列を作成（小さい方が良い）
summary_df['Total_Score'] = summary_df[[f'Score_{gen}' for gen in ['Gen1', 'Gen2', 'Gen3']]].sum(axis=1)

# ソートして上位10件表示
ranked_df = summary_df.sort_values(by='Total_Score').reset_index(drop=True)
print(ranked_df[['Policy_ID', 'Total_Score'] + [f'Score_{gen}' for gen in ['Gen1', 'Gen2', 'Gen3']]].head(10))

# 必要に応じて保存
ranked_df.to_csv("output/policy_ranked_by_weighted_score.csv", index=False)
