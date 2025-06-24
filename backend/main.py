import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from typing import Dict

from config import DEFAULT_PARAMS, rcp_climate_params, RANK_FILE, ACTION_LOG_FILE, YOUR_NAME_FILE
from models import (
    SimulationRequest, SimulationResponse, CompareRequest, CompareResponse,
    DecisionVar, CurrentValues, BlockRaw
)
from simulation import simulate_simulation
from utils import calculate_scenario_indicators, aggregate_blocks

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scenarios_data: Dict[str, pd.DataFrame] = {}

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    scenario_name = req.scenario_name
    mode = req.mode
    decision_df = pd.DataFrame([dv.model_dump() for dv in req.decision_vars]) if req.decision_vars else pd.DataFrame()

    # Update params based on RCP scenario and current values
    params = DEFAULT_PARAMS.copy()
    
    # RCPパラメータの取得を修正
    rcp_value = req.decision_vars[0].cp_climate_params
    
    # 浮動小数点数の比較問題を回避するため、最も近い値を見つける
    available_rcp_values = list(rcp_climate_params.keys())
    closest_rcp = min(available_rcp_values, key=lambda x: abs(x - rcp_value))
    
    rcp_param = rcp_climate_params[closest_rcp]
    params.update(rcp_param)
    

    all_df = pd.DataFrame()
    block_scores = []

    if mode == "Monte Carlo Simulation Mode":
        results = []
        for sim in range(req.num_simulations):
            sim_result = simulate_simulation(
                years=params['years'],
                initial_values=req.current_year_index_seq.model_dump(),
                decision_vars_list=decision_df,
                params=params
            )
            df_sim = pd.DataFrame(sim_result)
            df_sim["Simulation"] = sim
            results.append(df_sim)
        all_df = pd.concat(results, ignore_index=True)
        block_scores = []

    elif mode == "Sequential Decision-Making Mode":
        sim_years = np.arange(req.decision_vars[0].year, req.decision_vars[0].year + 1)
        result = simulate_simulation(
            years=sim_years,
            initial_values=req.current_year_index_seq.model_dump(),
            decision_vars_list=decision_df,
            params=params
        )
        all_df = pd.DataFrame(result)
        block_scores = aggregate_blocks(all_df)

        # ログ保存
        df_log = pd.DataFrame([dv.model_dump() for dv in req.decision_vars])
        df_log['user_name'] = req.user_name
        df_log['scenario_name'] = scenario_name
        df_log['timestamp'] = pd.Timestamp.utcnow()
        if ACTION_LOG_FILE.exists():
            df_old = pd.read_csv(ACTION_LOG_FILE)
            df_combined = pd.concat([df_old, df_log], ignore_index=True)
        else:
            df_combined = df_log
        df_combined.to_csv(ACTION_LOG_FILE, index=False)

        df_csv = pd.DataFrame(block_scores)
        df_csv['user_name'] = req.user_name
        df_csv['scenario_name'] = scenario_name
        df_csv['timestamp'] = pd.Timestamp.utcnow()
        df_csv['user_name'].to_csv(YOUR_NAME_FILE, index=False)
        if RANK_FILE.exists():
            old = pd.read_csv(RANK_FILE, sep='\t')
            merged = (
                old.set_index(['user_name', 'scenario_name', 'period'])
                .combine_first(df_csv.set_index(['user_name', 'scenario_name', 'period']))
                .reset_index()
            )
            merged.to_csv(RANK_FILE, sep='\t', index=False)
        else:
            df_csv.to_csv(RANK_FILE, sep='\t', index=False)

    
    elif mode == "Predict Simulation Mode":
        # 全期間の予測値を計算する
        # paramsは既にRCPパラメータで更新済みなので、再度コピーしない
        sim_years = np.arange(req.decision_vars[0].year, params['end_year'] + 1)
        seq_result = simulate_simulation(
            years=sim_years,
            initial_values=req.current_year_index_seq.model_dump(),
            decision_vars_list=decision_df,
            params=params
        )

        all_df = pd.DataFrame(seq_result)
        block_scores = []

    elif mode == "Record Results Mode":
        import shutil
        import glob
        from pathlib import Path

        src_dir = Path(__file__).parent / "data"
        dst_dir = Path(__file__).parent.parent / "frontend" / "public" / "results" / "data"
        dst_dir.mkdir(parents=True, exist_ok=True)

        for filepath in glob.glob(str(src_dir / "*.csv")) + glob.glob(str(src_dir / "*.tsv")):
            shutil.copy(filepath, dst_dir)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    if mode != "Predict Simulation Mode":
        scenarios_data[scenario_name] = all_df.copy()

    return SimulationResponse(
        scenario_name=scenario_name,
        data=all_df.to_dict(orient="records"),
        block_scores=block_scores
    )

@app.get("/ranking")
def get_ranking():
    if not RANK_FILE.exists():
        return []
    df = pd.read_csv(RANK_FILE, sep='\t')
    latest = df.sort_values('timestamp').drop_duplicates(['user_name', 'scenario_name', 'period'], keep='last')
    rank_df = (
        latest.groupby('user_name')['total_score']
        .mean()
        .reset_index()
        .sort_values('total_score', ascending=False)
        .reset_index(drop=True)
    )
    rank_df['rank'] = rank_df.index + 1
    return rank_df.to_dict(orient='records')

@app.post("/compare", response_model=CompareResponse)
def compare_scenario_data(req: CompareRequest):
    selected_data = {name: scenarios_data[name] for name in req.scenario_names if name in scenarios_data}
    if not selected_data:
        raise HTTPException(status_code=404, detail="No scenarios found for given names.")
    indicators_result = {name: calculate_scenario_indicators(df) for name, df in selected_data.items()}
    return CompareResponse(message="Comparison results", comparison=indicators_result)

@app.get("/scenarios")
def list_scenarios():
    return {"scenarios": list(scenarios_data.keys())}

@app.get("/export/{scenario_name}")
def export_scenario_data(scenario_name: str):
    if scenario_name not in scenarios_data:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return scenarios_data[scenario_name].to_csv(index=False)

@app.get("/block_scores")
def get_block_scores():
    if not RANK_FILE.exists():
        return []
    try:
        df = pd.read_csv(RANK_FILE, sep="\t")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# サーバに送信されているログをWebSocketで受信。現在はbackendに保存中
@app.websocket("/ws/log")
async def websocket_log_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_path = Path(__file__).parent / "data" / "user_log.jsonl"
    while True:
        try:
            data = await websocket.receive_text()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(data + "\n")
        except Exception as e:
            # クライアント切断などでエラーが出たら終了
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
