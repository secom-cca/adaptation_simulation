import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

from config import DEFAULT_PARAMS, rcp_climate_params, RANK_FILE, ACTION_LOG_FILE, YOUR_NAME_FILE
from models import (
    SimulationRequest, SimulationResponse, CompareRequest, CompareResponse,
    DecisionVar, CurrentValues, BlockRaw
)
from simulation import simulate_simulation, simulate_year
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

# DMDU データ管理用
dmdu_data: Optional[pd.DataFrame] = None

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/load-dmdu-data")
async def load_dmdu_data():
    """dmdu_panel.csvファイルを読み込んでメモリに保存"""
    global dmdu_data
    
    # データベースの読み込み
    dmdu_path = Path(__file__).parent.parent / "frontend" / "public" / "dmdu_panel.csv"
    if not dmdu_path.exists():
        raise HTTPException(status_code=404, detail="dmdu_panel.csv not found")

    if dmdu_data is not None:
        return {
            "message": f"Successfully loaded {len(dmdu_data)} rows",
            "sample_data": dmdu_data.head().to_dict('records'),
            "columns": dmdu_data.columns.tolist(),
            "size": f"{dmdu_data.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB"
        }
    
    #データベースの処理・フロントエンドへの送信
    try:
        # チャンク読み込みでメモリ効率化
        chunk_size = 10000
        chunks = []
        
        for chunk in pd.read_csv(dmdu_path, chunksize=chunk_size):
            chunks.append(chunk)
        
        dmdu_data = pd.concat(chunks, ignore_index=True)
        
        # 必要な列のみをフィルタリング
        input_cols = [
            'dam_levee_construction_cost_level',
            'paddy_dam_construction_cost_level', 
            'house_migration_amount_level',
            'planting_trees_amount_level'
        ]
        output_cols = [
            'Crop Yield',
            'Flood Damage',
            'Ecosystem Level',
            'Municipal Cost'
        ]
        
        # 列の存在確認
        available_cols = dmdu_data.columns.tolist()
        missing_inputs = [col for col in input_cols if col not in available_cols]
        missing_outputs = [col for col in output_cols if col not in available_cols]
        
        if missing_inputs or missing_outputs:
            return {
                "message": f"Loaded {len(dmdu_data)} rows",
                "available_columns": available_cols,
                "missing_input_columns": missing_inputs,
                "missing_output_columns": missing_outputs
            }
        
        dmdu_data = dmdu_data[input_cols + output_cols].dropna()
        
        return {
            "message": f"Successfully loaded {len(dmdu_data)} rows",
            "sample_data": dmdu_data.head().to_dict('records'),
            "columns": dmdu_data.columns.tolist(),
            "size": f"{dmdu_data.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")

@app.post("/query-data")
async def query_dmdu_data(
    input_values: Dict[str, float],
    output_metrics: List[str]
):
    """指定された入力値に基づいてデータをクエリ"""
    global dmdu_data
    
    if dmdu_data is None:
        raise HTTPException(status_code=400, detail="No DMDU data loaded")
    
    try:
        # 入力値に最も近いデータを検索（距離ベース）
        input_cols = [
            'dam_levee_construction_cost_level',
            'paddy_dam_construction_cost_level', 
            'house_migration_amount_level',
            'planting_trees_amount_level'
        ]
        
        # ユークリッド距離で最も近いデータポイントを特定
        distances = np.sqrt(
            sum((dmdu_data[col] - input_values.get(col, 0))**2 
                for col in input_cols if col in dmdu_data.columns)
        )
        closest_idx = distances.idxmin()
        
        result = dmdu_data.loc[closest_idx, ['Year'] + output_metrics].to_dict() \
            if 'Year' in dmdu_data.columns \
            else dmdu_data.loc[closest_idx, output_metrics].to_dict()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/get-data-summary")
async def get_data_summary():
    """データサマリー情報を取得"""
    global dmdu_data
    
    if dmdu_data is None:
        raise HTTPException(status_code=400, detail="No DMDU data loaded")
    
    return {
        "rows": len(dmdu_data),
        "columns": dmdu_data.columns.tolist(),
        "sample": dmdu_data.head(5).to_dict('records'),
        "statistics": dmdu_data.describe().to_dict()
    }

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
        year = req.decision_vars[0].year
        current_values_input = req.current_year_index_seq.model_dump()
        decision_vars = decision_df.iloc[0].to_dict()
        
        # simulate_yearを1年分だけ回す
        current_values_output, outputs = simulate_year(
            year=year,
            prev_values=current_values_input,
            decision_vars=decision_vars,
            params=params
        )
        result = [outputs]  # simulate_simulation と同じ形式で返すためリストに

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

    if mode == "Sequential Decision-Making Mode":
        return {
            "scenario_name": scenario_name,
            "data": result,
            "current_values": current_values_output,
            "block_scores": block_scores
        }
    else:
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
    log_path = Path(__file__).parent / "data" / "user_log.json"
    import json

    # 既存のログファイルを読み込む（なければ空リスト）
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    else:
        logs = []

    while True:
        try:
            data = await websocket.receive_text()
            # 受信データをJSONとしてパース
            try:
                log_obj = json.loads(data)
            except Exception:
                log_obj = {"raw": data}
            logs.append(log_obj)
            # ファイルに全件書き込み
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
