from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd

# simulate_simulation, compare_scenarios, compare_scenarios_yearly 等は既存の scr ディレクトリからインポート
# 例）
from scr.simulation import simulate_simulation
from scr.utils import compare_scenarios, compare_scenarios_yearly

app = FastAPI()

# ======================
# 1) グローバルに保持するパラメータとデータ
# ======================
# Streamlit 版でハードコーディングしていたパラメータをそのまま辞書に定義
start_year = 2021
end_year = 2100
years = np.arange(start_year, end_year + 1)
total_years = len(years)

DEFAULT_PARAMS = {
    'start_year': start_year,
    'end_year': end_year,
    'total_years': total_years,
    'years': years,
    'temp_trend': 0.04,
    'temp_uncertainty': 1.0,
    'precip_trend': 0,
    'base_precip_uncertainty': 50,
    'precip_uncertainty_trend': 5,
    'base_extreme_precip_freq': 0.1,
    'extreme_precip_freq_trend': 0.05,
    'extreme_precip_freq_uncertainty': 0.1,
    'municipal_demand_trend': 0,
    'municipal_demand_uncertainty': 0.05,
    'initial_hot_days': 30.0,
    'base_temp': 15.0,
    'base_precip': 1000.0,
    'temp_to_hot_days_coeff': 2.0,
    'hot_days_uncertainty': 2.0,
    'ecosystem_threshold': 800.0,
    'temp_coefficient': 1.0,
    'max_potential_yield': 100.0,
    'optimal_irrigation_amount': 30.0,
    'flood_damage_coefficient': 100000,
    'levee_level_increment': 0.1,
    'high_temp_tolerance_increment': 0.1,
    'levee_investment_threshold': 5.0,
    'RnD_investment_threshold': 5.0,
    'levee_investment_required_years': 10,
    'RnD_investment_required_years': 10,
    'max_available_water': 2000.0,
    'evapotranspiration_amount': 600.0,
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
    irrigation_water_amount: float
    released_water_amount: float
    levee_construction_cost: float
    agricultural_RnD_cost: float


class SimulationRequest(BaseModel):
    """シミュレーション実行時にフロントエンドから送られる想定パラメータ."""
    scenario_name: str
    mode: str  # "Monte Carlo Simulation Mode" or "Sequential Decision-Making Mode"
    decision_vars: List[DecisionVar] = []   # Monte Carlo のときは 10年ごとの意思決定、Sequential でも可
    num_simulations: int = 100             # Monte Carlo シミュレーション回数
    current_year_index_seq: Optional[int] = 0  # Sequentialモードの現在年インデックスなど
    # 必要に応じて追加フィールドを定義


class SimulationResponse(BaseModel):
    """シミュレーション結果を返すレスポンス用."""
    scenario_name: str
    data: List[Dict[str, Any]]  # DataFrameを JSON 化したもの


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
    # (Monte Carlo向けに 10年ごとに定義されている想定)
    if req.decision_vars:
        df_decisions = pd.DataFrame([dv.dict() for dv in req.decision_vars])
        df_decisions.set_index("year", inplace=True)
    else:
        # デフォルト (10年おき100,100,0,3) など、必要に応じて決める
        df_decisions = pd.DataFrame()

    # シミュレーション結果を格納するための変数
    all_results_df = pd.DataFrame()

    if mode == "Monte Carlo Simulation Mode":
        simulation_results = []

        for sim in range(req.num_simulations):
            # 初期値: Streamlit コードのロジックをそのまま踏襲
            initial_values = {
                'temp': 15.0,
                'precip': 1000.0,
                'municipal_demand': 100.0,
                'available_water': 1000.0,
                'crop_yield': 100.0,
                'levee_level': 0.5,
                'high_temp_tolerance_level': 0.0,
                'hot_days': 30.0,
                'extreme_precip_freq': 0.1,
                'ecosystem_level': 100.0,
                'levee_investment_years': 0,
                'RnD_investment_years': 0
            }
            # 実行
            sim_result = simulate_simulation(
                years=DEFAULT_PARAMS['years'],
                initial_values=initial_values,
                decision_df=df_decisions,
                params=DEFAULT_PARAMS
            )
            df_sim = pd.DataFrame(sim_result)
            df_sim["Simulation"] = sim
            simulation_results.append(df_sim)

        all_results_df = pd.concat(simulation_results, ignore_index=True)

    elif mode == "Sequential Decision-Making Mode":
        # Streamlit 版では「10年ごとに意思決定 & 次へ進む」という操作を対話的にやっていた
        # ここでは一括で全期間を計算するサンプル実装にする
        # （本当に段階的なシミュレーションを行いたい場合は、フロントから毎回 current_year_index_seq 等を送って繰り返し呼ぶ仕組みが必要）
        current_values = {
            'temp': 15.0,
            'precip': 1000.0,
            'municipal_demand': 100.0,
            'available_water': 1000.0,
            'crop_yield': 100.0,
            'levee_level': 0.5,
            'high_temp_tolerance_level': 0.0,
            'hot_days': 30.0,
            'extreme_precip_freq': 0.1,
            'ecosystem_level': 100.0,
            'levee_investment_years': 0,
            'RnD_investment_years': 0
        }

        # まとめて全期間を計算
        seq_result = simulate_simulation(
            years=DEFAULT_PARAMS['years'],
            initial_values=current_values,
            decision_df=df_decisions,
            params=DEFAULT_PARAMS
        )
        all_results_df = pd.DataFrame(seq_result)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    # シナリオ名で結果を保存 (サーバー側に一時保管)
    scenarios_data[scenario_name] = all_results_df.copy()

    # JSON で返せるように変換
    response = SimulationResponse(
        scenario_name=scenario_name,
        data=all_results_df.to_dict(orient="records")
    )
    return response


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


# ======================
# 5) アプリ起動（ローカルテスト用）
# ======================
# 直接このファイルを python コマンドで起動したい場合は以下のように。
# uvicorn で起動 (例: python main.py)。
# 本番環境では gunicorn + uvicorn worker を使うなどが一般的。
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
