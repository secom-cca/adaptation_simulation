from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import pandas as pd

# simulate_simulation, compare_scenarios, compare_scenarios_yearly 等は既存の scr ディレクトリからインポート
# 例）
from scr.simulation import simulate_simulation
from scr.utils import compare_scenarios, compare_scenarios_yearly

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            
    allow_credentials=True,
    allow_methods=["*"],              
    allow_headers=["*"],              
)

# main.py 冒頭あたり
from pathlib import Path, PosixPath
DATA_DIR: PosixPath = Path("data")
DATA_DIR.mkdir(exist_ok=True)
RANK_FILE = DATA_DIR / "block_scores.tsv"    # 追記用
ACTION_LOG_FILE = DATA_DIR / "decision_log.csv"
YOUR_NAME_FILE = DATA_DIR / "your_name.csv"  # ユーザ名を保存するファイル

# ======================
# 1) グローバルに保持するパラメータとデータ
# ======================
# Streamlit 版でハードコーディングしていたパラメータをそのまま辞書に定義
start_year = 2025
end_year = 2100
years = np.arange(start_year, end_year - start_year + 1)
total_years = len(years)

DEFAULT_PARAMS = {
    'start_year': start_year,
    'end_year': end_year,
    'total_years': total_years,
    'years': years,
    'temp_trend': 0.04,
    'temp_uncertainty': 0.5,
    'precip_trend': 0,
    'base_precip_uncertainty': 50,
    'precip_uncertainty_trend': 5,
    # 'base_extreme_precip_freq': 0.1,
    'extreme_precip_freq_trend': 0.05,
    # 'extreme_precip_freq_uncertainty': 0.1,
    'extreme_precip_intensity_trend': 0.2,
    'extreme_precip_uncertainty_trend': 0.05,
    'municipal_demand_trend': 0,
    'municipal_demand_uncertainty': 0.01,
    # 'initial_hot_days': 30.0,
    # 'base_temp': 15.0,
    # 'base_precip': 1000.0,
    'temp_to_hot_days_coeff': 2.0,
    'hot_days_uncertainty': 2.0,
    'ecosystem_threshold': 800.0, # 使っている？
    'temp_coefficient': 1.0,
    'max_potential_yield': 5000.0, # [kg/ha]
    'optimal_irrigation_amount': 30.0,
    'flood_damage_coefficient': 100000, # 1mm越水あたりのダメージ，パラメータ調整
    'levee_level_increment': 20.0,
    'high_temp_tolerance_increment': 0.2,
    'levee_investment_threshold': 2.0,
    'RnD_investment_threshold': 5.0,
    'levee_investment_required_years': 10,
    'RnD_investment_required_years': 5,
    'max_available_water': 3000.0,
    'evapotranspiration_amount': 300.0,
}

rcp_climate_params = {
    1.9: {
        'temp_trend': 0.02,  # ℃/年
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.05,      # λの年増加量
        'extreme_precip_intensity_trend': 0.2,  # μの年増加量 [mm/年]
        'extreme_precip_uncertainty_trend': 0.05  # βの年増加量 [mm/年]
    },
    2.6: {
        'temp_trend': 0.025,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.07,
        'extreme_precip_intensity_trend': 0.4,
        'extreme_precip_uncertainty_trend': 0.07
    },
    4.5: {
        'temp_trend': 0.035,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.1,
        'extreme_precip_intensity_trend': 0.8,
        'extreme_precip_uncertainty_trend': 0.1
    },
    6.0: {
        'temp_trend': 0.045,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.13,
        'extreme_precip_intensity_trend': 1.1,
        'extreme_precip_uncertainty_trend': 0.13
    },
    8.5: {
        'temp_trend': 0.06,
        'precip_uncertainty_trend': 0,
        'extreme_precip_freq_trend': 0.17,
        'extreme_precip_intensity_trend': 1.5,
        'extreme_precip_uncertainty_trend': 0.15
    }
}

# 複数シナリオをサーバ側で一時的に保持するための辞書
# 例: {"シナリオ1": pd.DataFrame(...), "シナリオ2": pd.DataFrame(...)}
scenarios_data: Dict[str, pd.DataFrame] = {}


# ======================
# 2) リクエスト/レスポンス用モデル定義 (pydantic)
# ======================
class DecisionVar(BaseModel):
    """1つの意思決定変数レコードを表すクラス."""
    year: int
    planting_trees_amount: float
    house_migration_amount: float  
    dam_levee_construction_cost: float
    paddy_dam_construction_cost: float
    capacity_building_cost: float
    # irrigation_water_amount: float
    # released_water_amount: float
    # levee_construction_cost: float
    transportation_invest: float
    agricultural_RnD_cost: float
    cp_climate_params: float

class CurrentValues(BaseModel):
    temp: float
    precip: float
    municipal_demand: float
    available_water: float
    crop_yield: float
    hot_days: float
    extreme_precip_freq: float
    ecosystem_level: float
    levee_level: Optional[float] = 0.0
    high_temp_tolerance_level: Optional[float] = 0.0
    forest_area: Optional[float] = 0.0
    planting_history: Optional[Dict[int, float]] = {}
    urban_level: Optional[float] = 0.0
    resident_capacity: Optional[float] = 0.0
    transportation_level: Optional[float] = 0.0
    levee_investment_total: Optional[float] = 0.0
    RnD_investment_total: Optional[float] = 0.0
    risky_house_total: Optional[float] = 10000.0
    non_risky_house_total: Optional[float] = 0.0
    resident_burden: Optional[float] = 0.0
    biodiversity_level: Optional[float] = 0.0
    

class BlockRaw(BaseModel):
    period: str            # '2026-2050' など
    raw:   Dict[str, float]   # 5 指標の合計／平均
    score: Dict[str, float]   # 0-100 化した 5 指標
    total_score: float        # 5 指標平均


class SimulationRequest(BaseModel):
    """シミュレーション実行時にフロントエンドから送られる想定パラメータ."""
    user_name: str                   # ★追加
    scenario_name: str
    mode: str  # "Monte Carlo Simulation Mode" or "Sequential Decision-Making Mode"
    decision_vars: List[DecisionVar] = []   # Monte Carlo のときは 10年ごとの意思決定、Sequential でも可
    num_simulations: int = 100             # Monte Carlo シミュレーション回数
    current_year_index_seq: CurrentValues  # Sequentialモードの現在年インデックスなど
    # 必要に応じて追加フィールドを定義


class SimulationResponse(BaseModel):
    """シミュレーション結果を返すレスポンス用."""
    scenario_name: str
    data: List[Dict[str, Any]]  # DataFrameを JSON 化したもの
    block_scores: List[BlockRaw]     # ★追加


class CompareRequest(BaseModel):
    """シナリオ比較用のリクエストデータ."""
    scenario_names: List[str]  # 比較したいシナリオ名のリスト
    variables: List[str]       # 例: ["Flood Damage", "Crop Yield", "Ecosystem Level", "Municipal Cost"]


class CompareResponse(BaseModel):
    """シナリオ比較結果（散布図やインジケータ計算など）を返す想定."""
    message: str
    comparison: Dict[str, Any]  # 実際にはグラフ描画用のデータ等を含める


# ======================
# 3) ユーティリティ関数
# ======================
def calculate_scenario_indicators(df: pd.DataFrame) -> Dict[str, float]:
    """シナリオ指標を計算して返す."""
    # end_year 時点の生態系レベルなど、Streamlit コードのロジックを踏襲
    last_ecosystem = df.loc[df['Year'] == end_year, 'Ecosystem Level']
    if not last_ecosystem.empty:
        ecosystem_level_end = last_ecosystem.values[0]
    else:
        ecosystem_level_end = float('nan')

    indicators = {
        '収量': df['Crop Yield'].sum() if 'Crop Yield' in df.columns else 0.0,
        '洪水被害': df['Flood Damage'].sum() if 'Flood Damage' in df.columns else 0.0,
        '生態系': ecosystem_level_end,
        '予算': df['Municipal Cost'].sum() if 'Municipal Cost' in df.columns else 0.0
    }
    return indicators

BENCHMARK = {
    '収量':        dict(best=300_000, worst=0,     invert=False),
    '洪水被害':    dict(best=0,       worst=200_000_000, invert=True),
    '生態系':      dict(best=100,     worst=0,     invert=False),
    '都市利便性':  dict(best=100,     worst=0,     invert=False),
    '予算':        dict(best=0,       worst=100_000_000_000, invert=True),
}

BLOCKS = [
    (2026, 2050, '2026-2050'),
    (2051, 2075, '2051-2075'),
    (2076, 2100, '2076-2100')
]

def _aggregate_blocks(df: pd.DataFrame) -> list[dict]:
    records = []
    for s, e, label in BLOCKS:
        # ブロック内のデータが最低でも1年分ある場合のみ集計
        mask = (df['Year'] >= s) & (df['Year'] <= e)
        if df.loc[mask].empty:
            continue  # このブロックはスキップ
        raw = _raw_values(df, s, e)
        score = {k: _scale_to_100(v, k) for k, v in raw.items()}
        total = float(np.mean(list(score.values())))
        records.append(dict(period=label, raw=raw, score=score, total_score=total))
    return records

def _scale_to_100(raw_val: float, metric: str) -> float:
    """単一値を 0-100 点に変換（ベンチマーク利用）"""
    b = BENCHMARK[metric]
    v = np.clip(raw_val, b['worst'], b['best']) if b['worst'] < b['best'] \
        else np.clip(raw_val, b['best'], b['worst'])
    if b['invert']:                               # 小さいほど良い
        score = 100 * (b['best'] - v) / (b['best'] - b['worst'])
    else:                                         # 大きいほど良い
        score = 100 * (v - b['worst']) / (b['best'] - b['worst'])
    return float(np.round(score, 1))

def _raw_values(df: pd.DataFrame, start: int, end: int) -> dict:
    """2050・2075・2100 年時点の raw 指標を取り出す"""
    mask = (df['Year'] >= start) & (df['Year'] <= end)
    return {
        '収量':       df.loc[mask, 'Crop Yield'].sum(),
        '洪水被害':   df.loc[mask, 'Flood Damage'].sum(),
        '予算':       df.loc[mask, 'Municipal Cost'].sum(),
        '生態系':     df.loc[mask, 'Ecosystem Level'].mean(),
        '都市利便性': df.loc[mask, 'Urban Level'].mean(),
    }

# ======================
# 4) エンドポイント定義
# ======================

@app.get("/ping")
def ping():
    return {"message": "pong"}


@app.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    """
    シミュレーションを実行するエンドポイント。
    - mode="Monte Carlo Simulation Mode" の場合はモンテカルロを実行
    - mode="Sequential Decision-Making Mode" の場合は一括実行 (デモ用)
    """
    scenario_name = req.scenario_name
    mode = req.mode

    # フロントエンドから受け取った意思決定変数を DataFrame 化
    if req.decision_vars:
        df_decisions = pd.DataFrame([dv.dict() for dv in req.decision_vars])
        df_decisions.set_index("year", inplace=True)
        DEFAULT_PARAMS['start_year'] = req.decision_vars[0].year - 1
        DEFAULT_PARAMS['end_year'] = end_year
        DEFAULT_PARAMS['temp_trend'] = rcp_climate_params[req.decision_vars[0].cp_climate_params]['temp_trend']
        DEFAULT_PARAMS['precip_uncertainty_trend'] = rcp_climate_params[req.decision_vars[0].cp_climate_params]['precip_uncertainty_trend']
        DEFAULT_PARAMS['extreme_precip_freq_trend'] = rcp_climate_params[req.decision_vars[0].cp_climate_params]['extreme_precip_freq_trend']
    else:
        # デフォルト (10年おき100,100,0,3) など、必要に応じて決める
        df_decisions = pd.DataFrame()
    print('[PARAMS]フロントエンドからdecision varを受け取りました：' + str(df_decisions))

    # print(f"[INFO] Scenario: {scenario_name}, Mode: {mode}, Decision:{df_decisions}")

    if req.current_year_index_seq:
        current_values = req.current_year_index_seq.dict()
        print('[PARAMS]フロントエンドからcurrent valuesを受け取りました：' + str(current_values))
        DEFAULT_PARAMS['base_extreme_precip_freq'] = current_values["extreme_precip_freq"]
        DEFAULT_PARAMS['initial_hot_days'] = current_values["hot_days"]
        DEFAULT_PARAMS['base_temp'] = current_values["temp"]
        DEFAULT_PARAMS['base_precip'] = current_values["precip"]
    else:
        # 初期値: Streamlit コードのロジックをそのまま踏襲
        SystemError
        print('フロントエンドからcurrent valuesを受け取れませんでした')

    # シミュレーション結果を格納するための変数
    all_results_df = pd.DataFrame()
    blocks = []

    if mode == "Monte Carlo Simulation Mode":
        simulation_results = []

        for sim in range(req.num_simulations):
            # 初期値: Streamlit コードのロジックをそのまま踏襲
            # 実行
            sim_result = simulate_simulation(
                years=DEFAULT_PARAMS['years'],
                initial_values=current_values,
                decision_vars_list=df_decisions,
                params=DEFAULT_PARAMS
            )
            df_sim = pd.DataFrame(sim_result)
            df_sim["Simulation"] = sim
            simulation_results.append(df_sim)

        all_results_df = pd.concat(simulation_results, ignore_index=True)
        blocks = []

    elif mode == "Sequential Decision-Making Mode":
        # Streamlit 版では「10年ごとに意思決定 & 次へ進む」という操作を対話的にやっていた
        # ここでは一年毎のシミュレーションを行う
        DEFAULT_PARAMS['years'] = np.arange(req.decision_vars[0].year, req.decision_vars[0].year + 1)
        DEFAULT_PARAMS['total_years'] = len(years)
        DEFAULT_PARAMS['temp_uncertainty'] = 0.1

        seq_result = simulate_simulation(
            years=DEFAULT_PARAMS['years'],
            initial_values=current_values,
            decision_vars_list=df_decisions,
            params=DEFAULT_PARAMS
        )
        all_results_df = pd.DataFrame(seq_result)

        # === アクションログ出力 ===
        df_log = pd.DataFrame([dv.dict() for dv in req.decision_vars])
        df_log['user_name'] = req.user_name
        df_log['scenario_name'] = scenario_name
        df_log['timestamp'] = pd.Timestamp.utcnow()

        if ACTION_LOG_FILE.exists():
            df_old = pd.read_csv(ACTION_LOG_FILE)
            df_combined = pd.concat([df_old, df_log], ignore_index=True)
        else:
            df_combined = df_log

        df_combined.to_csv(ACTION_LOG_FILE, index=False)

        blocks = _aggregate_blocks(all_results_df)

        # ---- CSV へ追記 or 更新（ユーザ名×シナリオ名×period が unique） ----

        df_csv = pd.DataFrame(blocks)
        df_csv['user_name']     = req.user_name
        df_csv['scenario_name'] = scenario_name
        df_csv['timestamp']     = pd.Timestamp.utcnow()

        df_csv['user_name'].to_csv(YOUR_NAME_FILE, index=False)
        
        if RANK_FILE.exists():
            old = pd.read_csv(RANK_FILE, sep='\t')
            # すでに同じ user_name + scenario_name + period があれば置き換え
            merged = (old.set_index(['user_name','scenario_name','period'])
                        .combine_first(df_csv.set_index(['user_name','scenario_name','period']))
                        .reset_index())
            merged.to_csv(RANK_FILE, sep='\t', index=False)
        else:
            df_csv.to_csv(RANK_FILE, sep='\t', index=False)
    
    elif mode == "Predict Simulation Mode":
        # 全期間の予測値を計算する
        params = DEFAULT_PARAMS.copy()
        params['years'] = np.arange(req.decision_vars[0].year, end_year + 1)
        params['total_years'] = len(years)
        params['temp_uncertainty'] = 0.01
        # params['base_precip_uncertainty'] = 0
        params['extreme_precip_freq_uncertainty'] = 0.001
        params['municipal_demand_uncertainty'] = 0.005
        params['hot_days_uncertainty'] = 0.1

        print(f"[Params]意思決定項目をsimulation.pyに渡します:{df_decisions}")

        seq_result = simulate_simulation(
            years=params['years'],
            initial_values=current_values,
            decision_vars_list=df_decisions,
            params=params
        )

        all_results_df = pd.DataFrame(seq_result)
        blocks = []

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    # シナリオ名で結果を保存 (サーバー側に一時保管)
    if mode != "Predict Simulation Mode":
        scenarios_data[scenario_name] = all_results_df.copy()

    # JSON で返せるように変換
    # print('バックエンドの計算結果：' + str(all_results_df.to_dict))
    response = SimulationResponse(
        scenario_name=scenario_name,
        data=all_results_df.to_dict(orient="records"),
        block_scores=blocks
    )
    return response


@app.get("/ranking")
def get_ranking():
    if not RANK_FILE.exists():
        return []
    df = pd.read_csv(RANK_FILE, sep='\t')
    latest = (df.sort_values('timestamp')
                .drop_duplicates(['user_name','scenario_name','period'], keep='last'))
    # 直近シナリオの period ごと平均点
    rank_df = (latest.groupby('user_name')['total_score']
                      .mean()
                      .reset_index()
                      .sort_values('total_score', ascending=False)
                      .reset_index(drop=True))
    rank_df['rank'] = rank_df.index + 1
    return rank_df.to_dict(orient='records')


@app.post("/compare", response_model=CompareResponse)
def compare_scenario_data(req: CompareRequest):
    """
    複数シナリオのデータを比較して返すエンドポイント。
    例: Flood Damage vs Crop Yield vs Ecosystem Level vs Municipal Cost
    """
    # 該当シナリオの DataFrame を集める
    selected_data = {name: scenarios_data[name] for name in req.scenario_names if name in scenarios_data}

    if not selected_data:
        raise HTTPException(status_code=404, detail="No scenarios found for given names.")

    # compare_scenarios や compare_scenarios_yearly などの関数は
    # Streamlit 用にグラフを表示していたが、ここでは計算結果のみ返す形に変えるのが望ましい。
    # 必要に応じて compare_scenarios 内部ロジックを改造して
    # グラフの元になる数値や集計値を取得する。

    # ここでは例として指標を計算してまとめる
    # （本来は散布図用データなども生成し、フロントエンドに返して可視化する）
    indicators_result = {}
    for scenario_name, df in selected_data.items():
        indicators = calculate_scenario_indicators(df)
        indicators_result[scenario_name] = indicators

    return CompareResponse(
        message="Comparison results",
        comparison=indicators_result
    )


@app.get("/scenarios")
def list_scenarios():
    """現在サーバに保存されているシナリオ一覧を返す."""
    return {"scenarios": list(scenarios_data.keys())}


@app.get("/export/{scenario_name}")
def export_scenario_data(scenario_name: str):
    """
    指定シナリオのデータを CSV 形式で返す簡易エンドポイント。
    実際にはファイルとしてダウンロード可能なレスポンスにするか、
    S3 にアップロードして署名付きURLを返す等の実装が考えられる。
    """
    if scenario_name not in scenarios_data:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    df = scenarios_data[scenario_name]
    csv_str = df.to_csv(index=False)
    # text/plain を返す場合など、mime タイプを適宜変える
    return csv_str

@app.get("/block_scores")
def get_block_scores():
    """ユーザ名確認用の block_scores.tsv 読み出しエンドポイント"""
    if not RANK_FILE.exists():
        return []
    
    try:
        df = pd.read_csv(RANK_FILE, sep="\t")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================
# 5) アプリ起動（ローカルテスト用）
# ======================
# 直接このファイルを python コマンドで起動したい場合は以下のように。
# uvicorn で起動 (例: python main.py)。
# 本番環境では gunicorn + uvicorn worker を使うなどが一般的。
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
