import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pandas as pd
import numpy as np
import json
import zipfile
from datetime import datetime
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
    allow_origins=[
        "http://localhost:3000",  # 本地开发
        "http://localhost:3001",  # 本地开发备用端口
        "https://climate-adaptation-backend.vercel.app",  # Vercel前端域名
        "https://*.vercel.app",  # 允许所有Vercel子域名
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

scenarios_data: Dict[str, pd.DataFrame] = {}

# 管理员认证
security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """验证管理员身份"""
    correct_username = "admin"
    correct_password = "climate2025"

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=401,
            detail="管理者認証に失敗しました",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

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
    rcp_param = rcp_climate_params.get(req.decision_vars[0].cp_climate_params, {})
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
        params = DEFAULT_PARAMS.copy()
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

# 管理员路由
@app.get("/admin/dashboard")
async def get_admin_dashboard(admin: str = Depends(authenticate_admin)):
    """获取管理员仪表板数据"""
    try:
        data_dir = Path(__file__).parent / "data"

        # 读取用户日志
        user_log_file = data_dir / "user_log.jsonl"
        user_logs = []
        if user_log_file.exists():
            with open(user_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        user_logs.append(json.loads(line.strip()))

        # 读取评分数据
        block_scores = []
        if RANK_FILE.exists():
            df = pd.read_csv(RANK_FILE, sep='\t')
            block_scores = df.to_dict('records')

        # 统计信息
        unique_users = set()
        for log in user_logs:
            if 'user_name' in log:
                unique_users.add(log['user_name'])

        # 按用户分组的评分数据
        user_scores = {}
        for score in block_scores:
            user_name = score['user_name']
            if user_name not in user_scores:
                user_scores[user_name] = []
            user_scores[user_name].append(score)

        # 最近活动
        recent_logs = sorted(user_logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:50]

        return {
            "summary": {
                "total_users": len(unique_users),
                "total_logs": len(user_logs),
                "total_simulations": len(block_scores),
                "last_activity": recent_logs[0]['timestamp'] if recent_logs else None
            },
            "users": list(unique_users),
            "user_scores": user_scores,
            "recent_activity": recent_logs,
            "data_files": {
                "user_log_size": user_log_file.stat().st_size if user_log_file.exists() else 0,
                "block_scores_size": RANK_FILE.stat().st_size if RANK_FILE.exists() else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データの取得に失敗しました: {str(e)}")

@app.get("/admin/download/all")
async def download_all_data(admin: str = Depends(authenticate_admin)):
    """下载所有数据的压缩包"""
    try:
        data_dir = Path(__file__).parent / "data"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"climate_simulation_data_{timestamp}.zip"
        zip_path = data_dir / zip_filename

        # 创建压缩包
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有数据文件
            for file_path in data_dir.glob("*.jsonl"):
                zipf.write(file_path, file_path.name)
            for file_path in data_dir.glob("*.tsv"):
                zipf.write(file_path, file_path.name)
            for file_path in data_dir.glob("*.csv"):
                zipf.write(file_path, file_path.name)

        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ダウンロードに失敗しました: {str(e)}")

@app.get("/admin/download/logs")
async def download_user_logs(admin: str = Depends(authenticate_admin)):
    """下载用户日志文件"""
    try:
        data_dir = Path(__file__).parent / "data"
        log_file = data_dir / "user_log.jsonl"

        if not log_file.exists():
            raise HTTPException(status_code=404, detail="ログファイルが存在しません")

        return FileResponse(
            path=log_file,
            filename=f"user_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            media_type="application/json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログのダウンロードに失敗しました: {str(e)}")

@app.get("/admin/download/scores")
async def download_scores(admin: str = Depends(authenticate_admin)):
    """下载评分数据文件"""
    try:
        if not RANK_FILE.exists():
            raise HTTPException(status_code=404, detail="評価ファイルが存在しません")

        return FileResponse(
            path=RANK_FILE,
            filename=f"block_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv",
            media_type="text/tab-separated-values"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"評価データのダウンロードに失敗しました: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
