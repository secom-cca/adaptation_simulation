import sys
sys.path.insert(0, '/Users/sayumi/5月祭/adaptation_simulation/backend')

from src.simulation import generate_ai_commentary

# サンプルのシミュレーション結果を生成（75年分）
sample_results = []
for year in range(2026, 2101):
    sample_results.append({
        'Temperature (℃)': 15.5 + (year - 2026) * 0.02,  # 徐々に上昇
        'Hot Days': 30 + (year - 2026) * 0.1,
        'Extreme Precip Events': 150 + (year - 2026) * 0.5,
        'Levee Level': 50 + (year - 2026) * 0.3,
        'Urban Level': 75 - (year - 2026) * 0.1,
        'Flood Damage': 500000 - (year - 2026) * 1000,
        'Resident Burden': 5000 + (year - 2026) * 10,
        'Crop Yield': 4000 - (year - 2026) * 5,
        'Resident capacity': 0.3 + (year - 2026) * 0.002,
        'Ecosystem Level': 70 - (year - 2026) * 0.05,
        'Forest Area': 5000 + (year - 2026) * 5,
    })

# テスト実行
print("🧪 Testing generate_ai_commentary...")
result = generate_ai_commentary(sample_results)

print("\n✅ Agent Profile:")
print(f"  Name: {result['agent_name']}")
print(f"  Role: {result['agent_role']}")
print(f"  Focus: {result['agent_focus']}")
print(f"  Years to 85: {result['years_to_85']}")

print("\n💬 Generated Commentary:")
print(result['text'])