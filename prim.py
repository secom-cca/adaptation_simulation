# prim.py — fix: aggregate only targets, then merge features
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from pathlib import Path
import pandas as pd
import numpy as np
from ema_workbench.analysis import prim
import matplotlib.pyplot as plt

PANEL_CSV = Path("output/dmdu_panel.csv")
OUTDIR = Path("output/prim")
OUTDIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(PANEL_CSV)

# --- 必須列 ---
need = ["ScenarioID","RCP","Sim","Year","Flood Damage","Ecosystem Level","Municipal Cost","Crop Yield"]
miss = [c for c in need if c not in df.columns]
if miss:
    raise RuntimeError(f"Missing columns: {miss}")

# --- キー型を揃える ---
keys = ["ScenarioID","RCP","Sim"]
for k in keys:
    df[k] = df[k].astype(str)

# --- 1) Gen3の目的指標だけを平均集計（featureはここに入れない）---
mask = (df["Year"]>=2076) & (df["Year"]<=2100)
targets = ["Flood Damage","Ecosystem Level","Municipal Cost","Crop Yield"]
g = (df.loc[mask, keys+targets]
       .groupby(keys, as_index=False)
       .mean())

# --- 2) feature 候補を抽出し、一意化してマージ ---
candidate_feats = [c for c in df.columns if c.endswith("_level") or c.startswith("unc_")]
if not candidate_feats:
    raise RuntimeError("No feature columns ('*_level' or 'unc_*') found in panel CSV.")

feat_df = df[keys + candidate_feats].drop_duplicates(subset=keys, keep="first")
g = g.merge(feat_df, on=keys, how="left", validate="one_to_one")

feat_cols = [c for c in candidate_feats if c in g.columns]  # 念のため再確認
if not feat_cols:
    raise RuntimeError("Feature columns vanished after merge.")

# --- 3) 欠損処理 ---
for c in feat_cols:
    if g[c].isna().any():
        g[c] = g[c].fillna(g[c].median())

# --- 4) 目的関数定義（例：FD 上位20%を bad）---
q = 0.80
fd_thr = g["Flood Damage"].quantile(q)
# y = (g["Flood Damage"] >= fd_thr).astype(bool).to_numpy()

# X = g[feat_cols].astype(float).to_numpy()

X = g[feat_cols].astype(float)              # DataFrame
y = (g["Flood Damage"] >= fd_thr).astype(bool)  # Series でも OK

print(f"[INFO] samples={len(y)}, bad share={y.mean():.3f}, FD threshold={fd_thr:.3f}")
print(f"[INFO] using features ({len(feat_cols)}): {feat_cols}")

# --- 5) PRIM 実行 ---
prim_alg = prim.Prim(X, y, threshold=0.8, peel_alpha=0.1)

# ここが重要: 結果オブジェクトを受け取る
res = prim_alg.find_box()

# tradeoff（peeling履歴）はバージョンによって名前が異なることがある
tradeoff = getattr(res, "tradeoff", None)
if tradeoff is None:
    tradeoff = getattr(res, "peeling_trajectory", None)
if tradeoff is None:
    raise RuntimeError("EMA workbenchのこの版は tradeoff/peeling_trajectory を公開していないようです。")

print("[INFO] tradeoff head:\n", tradeoff.head())

# 代表ボックスのインデックス（最後のボックスを採用。任意で変更）
i = tradeoff.index[-1] if hasattr(tradeoff, "index") else len(tradeoff) - 1
print(f"[INFO] Selected box #{i}")
print(res.inspect(i))         # ルールを表示

# 保存
OUTDIR.mkdir(parents=True, exist_ok=True)
tradeoff.to_csv(OUTDIR / "tradeoff.csv", index=False)
boxes_df = res.boxes_to_dataframe(feature_names=X.columns.tolist())
boxes_df.to_csv(OUTDIR / "boxes.csv", index=False)

sel_mask = res.select(i)      # ボックスに入るサンプルのマスク
g.loc[sel_mask, keys].to_csv(OUTDIR / "selected_keys.csv", index=False)

fig = res.show_tradeoff()
fig.savefig(OUTDIR / "tradeoff.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("[OK] Saved:", OUTDIR)
