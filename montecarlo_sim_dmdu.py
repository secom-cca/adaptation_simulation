# multiple_simulation.py — timing study without touching simulation.py
import sys, os, time, json
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "backend"))

import numpy as np
import pandas as pd
from itertools import product

from backend.src.simulation import simulate_simulation
from backend.config import DEFAULT_PARAMS, rcp_climate_params

np.random.seed(42)

# -------------------
# 基本設定
# -------------------
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_YEAR = 2025
END_YEAR   = 2100
years = np.arange(START_YEAR, END_YEAR + 1)

# rcps = {'RCP1.9': 1.9, 'RCP2.6': 2.6, 'RCP2.6': 4.5, 'RCP6.0': 6.0, 'RCP8.5': 8.5}
rcps = {'RCP1.9': 1.9, 'RCP8.5': 8.5}
NUM_SIM = 1

# 意思決定タイミング（None=実施しない / 2025 / 2050 / 2075）
TIMING_OPTIONS = [None, 2025, 2050, 2075]

# 6レバー（基本＋追加）
DECISION_ITEMS = [
    "planting_trees", "planting_trees_additional",
    "dam_levee", "dam_levee_additional",
    "paddy_dam", "house_migration",
]
SHORT = {"planting_trees":"F","planting_trees_additional":"FA",
         "dam_levee":"D","dam_levee_additional":"DA",
         "paddy_dam":"P","house_migration":"M"}

# 投入量（その年に加算される量）
LEVEL_VALUE = {
    "planting_trees": 75.0,              # -> planting_trees_amount に加算
    "planting_trees_additional": 75.0,   # 同上
    "dam_levee": 1.0,                    # -> dam_levee_construction_cost
    "dam_levee_additional": 1.0,         # 同上
    "paddy_dam": 10.0,                   # -> paddy_dam_construction_cost
    "house_migration": 100.0,            # -> house_migration_amount
}

# モデル内部キー
ITEM_TO_MODELKEY = {
    "planting_trees": "planting_trees_amount",
    "planting_trees_additional": "planting_trees_amount",
    "dam_levee": "dam_levee_construction_cost",
    "dam_levee_additional": "dam_levee_construction_cost",
    "paddy_dam": "paddy_dam_construction_cost",
    "house_migration": "house_migration_amount",
}

# 世代・評価指標
GENERATIONS = {'Gen1': (2026, 2050), 'Gen2': (2051, 2075), 'Gen3': (2076, 2100)}
INDICATORS = ['Flood Damage', 'Ecosystem Level', 'Municipal Cost', 'Crop Yield']

# 出力パス
PANEL_CSV   = OUTPUT_DIR / "dmdu_panel_timing.csv"
SUMMARY_CSV = OUTPUT_DIR / "dmdu_summary_timing.csv"
PROGRESS_JSON = OUTPUT_DIR / "progress_timing.json"

# -------------------
# ユーティリティ
# -------------------
def bucket_year(y, start=START_YEAR):
    """simulate_simulation 内の 10年バケットと整合する年を返す"""
    return (y - start)//10*10 + start

def timing_code(y):
    return "N" if y is None else ("25" if y == 2025 else "50" if y == 2050 else "75")

def scenario_label_from_timing(tup):
    # 例) F25-FA50-DN-DA75-P50-MN
    return "-".join(f"{SHORT[item]}{timing_code(when)}" for item, when in zip(DECISION_ITEMS, tup))

# 10年バケットの全集合（KeyError回避のため、少なくとも1キーは各バケットに入れておく）
ALL_BUCKETS = sorted({bucket_year(int(y)) for y in years})

def make_series_schedule(timing_tuple):
    """
    simulation.py を変更せずに年別決定を渡すため、
    (Year, Var) -> value の MultiIndex Series を作る。
    .loc[bucket_year] で Var->value の Series が返る。
    """
    # 全バケットに「ダミー0」を入れて KeyError を防止（Varは何でも良い。既知キーを使う）
    pairs = { (by, "planting_trees_amount"): 0.0 for by in ALL_BUCKETS }

    # 指定タイミング→10年バケットへマッピングして加算
    for item, when in zip(DECISION_ITEMS, timing_tuple):
        if when is None:
            continue
        by = bucket_year(when)
        mkey = ITEM_TO_MODELKEY[item]
        val  = LEVEL_VALUE[item]
        pairs[(by, mkey)] = pairs.get((by, mkey), 0.0) + val

    # Series 化
    idx = pd.MultiIndex.from_tuples(pairs.keys(), names=["Year","Var"])
    ser = pd.Series(list(pairs.values()), index=idx, dtype=float)
    return ser

def summarize_generations_one_run(df):
    out = {}
    for glabel, (s, e) in GENERATIONS.items():
        mask = (df['Year'] >= s) & (df['Year'] <= e)
        for ind in INDICATORS:
            out[f'{ind}_{glabel}'] = float(df.loc[mask, ind].mean())
    return out

def write_progress(done, total, t0):
    pct = 100.0*done/total if total else 100.0
    el  = time.time() - t0
    eta = el*(100/pct-1) if pct>0 else None
    with open(PROGRESS_JSON, "w") as f:
        json.dump({"runs_done":done,"total_runs":total,"percent":round(pct,2),
                   "elapsed_sec":int(el),"eta_sec":None if eta is None else int(eta)}, f)
    if done==total or done % 50 == 0:
        print(f"[Progress] {done}/{total} ({pct:.1f}%)", flush=True)

# -------------------
# 初期化
# -------------------
for p in [PANEL_CSV, SUMMARY_CSV]:
    if p.exists(): p.unlink()
panel_header_written = False
summary_accum = []

total_runs = (len(TIMING_OPTIONS)**len(DECISION_ITEMS)) * len(rcps) * NUM_SIM
runs_done = 0
t0 = time.time()

# -------------------
# 実行
# -------------------
for timing_tuple in product(TIMING_OPTIONS, repeat=len(DECISION_ITEMS)):
    scen_label = scenario_label_from_timing(timing_tuple)
    # 衝突しにくいID（タイミングを基数4で符号化）
    sid = 0
    base = 1
    for when in timing_tuple:
        code = {None:0, 2025:1, 2050:2, 2075:3}[when]
        sid += code * base
        base *= 4

    dec_series = make_series_schedule(timing_tuple)  # <- ここが肝（DataFrameではなく Series）

    for rcp_name, rcp_val in rcps.items():
        base_params = DEFAULT_PARAMS.copy()
        base_params.update(rcp_climate_params[rcp_val])
        # 期間を明示（内部の decision_year 計算に使われる）
        base_params['start_year'] = START_YEAR
        base_params['end_year']   = END_YEAR

        for sim_id in range(NUM_SIM):
            # 不確実性乗数は今回は固定（= base_params のまま）
            sim_data = simulate_simulation(years, {}, dec_series, base_params)
            df = pd.DataFrame(sim_data)

            # メタ列
            df['ScenarioID'] = sid
            df['ScenarioLabel'] = scen_label
            df['RCP'] = rcp_name
            df['Sim'] = sim_id
            for item, when in zip(DECISION_ITEMS, timing_tuple):
                df[f'{item}_timing'] = timing_code(when)

            # パネルを逐次追記
            cols = ['ScenarioID','ScenarioLabel','RCP','Sim','Year'] + INDICATORS + \
                   [f'{it}_timing' for it in DECISION_ITEMS]
            if not panel_header_written:
                df[cols].to_csv(PANEL_CSV, index=False, mode='w')
                panel_header_written = True
            else:
                df[cols].to_csv(PANEL_CSV, index=False, mode='a', header=False)

            # 世代要約（Sim単位）
            gen = summarize_generations_one_run(df)
            gen.update({'ScenarioID':sid,'ScenarioLabel':scen_label,'RCP':rcp_name,'Sim':sim_id})
            summary_accum.append(gen)

            runs_done += 1
            write_progress(runs_done, total_runs, t0)

# Sim方向の平均・標準偏差
sim_level = pd.DataFrame(summary_accum)
agg_rows = []
for (sid, slabel, rcp), g in sim_level.groupby(['ScenarioID','ScenarioLabel','RCP']):
    row = {'ScenarioID':sid, 'ScenarioLabel':slabel, 'RCP':rcp}
    for ind in INDICATORS:
        for glabel in GENERATIONS.keys():
            col = f'{ind}_{glabel}'
            row[col] = float(g[col].mean())
            row[f'{col}_std'] = float(g[col].std())
    agg_rows.append(row)

pd.DataFrame(agg_rows).to_csv(SUMMARY_CSV, index=False)

print(f"[OK] Saved panel:   {PANEL_CSV}")
print(f"[OK] Saved summary: {SUMMARY_CSV}")
print(f"[OK] Progress json: {PROGRESS_JSON}")
