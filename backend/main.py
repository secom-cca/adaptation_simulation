import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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

def _save_results_data(user_name: str, scenario_name: str, block_scores: list):
    """保存结果数据到文件"""
    import pandas as pd
    from pathlib import Path

    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    # 保存用户名
    user_name_file = data_dir / "your_name.csv"
    pd.DataFrame([{"user_name": user_name}]).to_csv(user_name_file, index=False)

    # 保存评分数据
    if block_scores:
        df_scores = pd.DataFrame(block_scores)
        df_scores['user_name'] = user_name
        df_scores['scenario_name'] = scenario_name
        df_scores['timestamp'] = pd.Timestamp.utcnow()

        # 保存到block_scores.tsv
        block_scores_file = data_dir / "block_scores.tsv"
        if block_scores_file.exists():
            # 读取现有数据
            existing_df = pd.read_csv(block_scores_file, sep='\t')
            # 删除同一用户的旧数据
            existing_df = existing_df[existing_df['user_name'] != user_name]
            # 合并新数据
            combined_df = pd.concat([existing_df, df_scores], ignore_index=True)
        else:
            combined_df = df_scores

        combined_df.to_csv(block_scores_file, sep='\t', index=False)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 本地开发
        "http://localhost:3001",  # 本地开发备用端口
        "https://climate-adaptation-backend.vercel.app",  # Vercel前端域名
        "https://climate-adaptation-backend-git-fix-y-axis-adaptation-and-ui-improvements-terryzhang-jp.vercel.app",  # Git分支域名
        "*"  # 临时允许所有域名进行调试
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
    if req.decision_vars and len(req.decision_vars) > 0:
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
        # 保存用户名文件
        pd.DataFrame([{"user_name": req.user_name}]).to_csv(YOUR_NAME_FILE, index=False)
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
        # 处理前端发送的完整仿真数据
        print(f"🔍 [Record Results Mode] 开始处理用户: {req.user_name}")
        print(f"🔍 [Record Results Mode] 接收到的仿真数据长度: {len(req.simulation_data) if req.simulation_data else 0}")

        if req.simulation_data and len(req.simulation_data) > 0:
            print(f"✅ [Record Results Mode] 仿真数据有效，开始处理...")
            # 将仿真数据转换为DataFrame
            all_df = pd.DataFrame(req.simulation_data)
            print(f"✅ [Record Results Mode] DataFrame创建成功，行数: {len(all_df)}")

            # 计算评分数据
            try:
                block_scores = aggregate_blocks(all_df)
                print(f"✅ [Record Results Mode] 评分计算成功，评分数量: {len(block_scores)}")
            except Exception as e:
                print(f"❌ [Record Results Mode] 评分计算失败: {str(e)}")
                block_scores = []

            # 保存数据到文件
            try:
                print(f"💾 [Record Results Mode] 开始保存数据...")
                _save_results_data(req.user_name, req.scenario_name, block_scores)
                print(f"✅ [Record Results Mode] 数据保存成功")
            except Exception as e:
                print(f"❌ [Record Results Mode] 数据保存失败: {str(e)}")
        else:
            print(f"⚠️ [Record Results Mode] 没有接收到有效的仿真数据")

        # 复制文件到前端目录
        print(f"📁 [Record Results Mode] 开始复制文件到前端目录...")
        import shutil
        import glob
        from pathlib import Path

        src_dir = Path(__file__).parent / "data"
        dst_dir = Path(__file__).parent.parent / "frontend" / "public" / "results" / "data"
        dst_dir.mkdir(parents=True, exist_ok=True)

        copied_files = []
        for filepath in glob.glob(str(src_dir / "*.csv")) + glob.glob(str(src_dir / "*.tsv")):
            try:
                shutil.copy(filepath, dst_dir)
                copied_files.append(Path(filepath).name)
            except Exception as e:
                print(f"❌ [Record Results Mode] 复制文件失败 {filepath}: {str(e)}")

        print(f"✅ [Record Results Mode] 复制完成，文件: {copied_files}")

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

@app.get("/api/your_name.csv")
def get_your_name_csv():
    """提供your_name.csv文件内容"""
    if not YOUR_NAME_FILE.exists():
        raise HTTPException(status_code=404, detail="your_name.csv not found")

    try:
        df = pd.read_csv(YOUR_NAME_FILE)
        # 返回CSV格式的文本
        return Response(content=df.to_csv(index=False), media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/decision_log.csv")
def get_decision_log_csv():
    """提供decision_log.csv文件内容"""
    if not ACTION_LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="decision_log.csv not found")

    try:
        df = pd.read_csv(ACTION_LOG_FILE)
        return Response(content=df.to_csv(index=False), media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/block_scores.tsv")
def get_block_scores_tsv():
    """提供block_scores.tsv文件内容"""
    if not RANK_FILE.exists():
        raise HTTPException(status_code=404, detail="block_scores.tsv not found")

    try:
        df = pd.read_csv(RANK_FILE, sep='\t')
        return Response(content=df.to_csv(sep='\t', index=False), media_type="text/tab-separated-values")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/file_status")
def get_file_status():
    """检查所有必需文件的状态"""
    from pathlib import Path

    data_dir = Path(__file__).parent / "data"
    frontend_data_dir = Path(__file__).parent.parent / "frontend" / "public" / "results" / "data"

    files_to_check = [
        ("your_name.csv", YOUR_NAME_FILE),
        ("decision_log.csv", ACTION_LOG_FILE),
        ("block_scores.tsv", RANK_FILE)
    ]

    status = {
        "backend_data_dir": str(data_dir),
        "frontend_data_dir": str(frontend_data_dir),
        "backend_files": {},
        "frontend_files": {},
        "summary": {
            "all_backend_files_exist": True,
            "all_frontend_files_exist": True,
            "missing_files": []
        }
    }

    # 检查后端文件
    for file_name, file_path in files_to_check:
        exists = file_path.exists()
        size = file_path.stat().st_size if exists else 0
        status["backend_files"][file_name] = {
            "exists": exists,
            "path": str(file_path),
            "size": size
        }
        if not exists:
            status["summary"]["all_backend_files_exist"] = False
            status["summary"]["missing_files"].append(f"backend/{file_name}")

    # 检查前端文件
    for file_name, _ in files_to_check:
        frontend_file = frontend_data_dir / file_name
        exists = frontend_file.exists()
        size = frontend_file.stat().st_size if exists else 0
        status["frontend_files"][file_name] = {
            "exists": exists,
            "path": str(frontend_file),
            "size": size
        }
        if not exists:
            status["summary"]["all_frontend_files_exist"] = False
            status["summary"]["missing_files"].append(f"frontend/{file_name}")

    return status


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
