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
        # 并行化蒙特卡洛仿真以充分利用多核CPU
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing

        def single_simulation(sim_index):
            """单次仿真函数，用于并行执行"""
            sim_result = simulate_simulation(
                years=params['years'],
                initial_values=req.current_year_index_seq.model_dump(),
                decision_vars_list=decision_df,
                params=params
            )
            df_sim = pd.DataFrame(sim_result)
            df_sim["Simulation"] = sim_index
            return df_sim

        # 使用所有可用CPU核心进行并行计算
        max_workers = min(multiprocessing.cpu_count(), req.num_simulations)
        print(f"🚀 [Monte Carlo] 使用 {max_workers} 个CPU核心并行计算 {req.num_simulations} 次仿真")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有仿真任务
            futures = [executor.submit(single_simulation, sim) for sim in range(req.num_simulations)]
            # 收集结果
            results = [future.result() for future in futures]

        all_df = pd.concat(results, ignore_index=True)
        block_scores = []
        print(f"✅ [Monte Carlo] 并行计算完成，共处理 {len(all_df)} 行数据")

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

        # 部署环境下不需要文件复制，数据通过API提供
        print(f"✅ [Record Results Mode] 数据已保存，可通过API访问")

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

@app.get("/api/user_data/{user_name}")
def get_user_data(user_name: str):
    """获取指定用户的所有数据，确保数据完整性"""
    try:
        print(f"🔍 [API] 获取用户数据: {user_name}")

        result = {
            "user_name": user_name,
            "your_name_csv": f"user_name\n{user_name}",
            "decision_log_csv": "",
            "block_scores_tsv": "",
            "found": False,
            "data_complete": False,
            "periods_found": 0
        }

        # 获取决策日志
        if ACTION_LOG_FILE.exists():
            df_log = pd.read_csv(ACTION_LOG_FILE)
            user_logs = df_log[df_log['user_name'] == user_name]
            if not user_logs.empty:
                result["decision_log_csv"] = user_logs.to_csv(index=False)
                result["found"] = True
                print(f"✅ [API] 找到决策日志: {len(user_logs)} 条记录")

        # 获取评分数据并验证完整性
        if RANK_FILE.exists():
            df_scores = pd.read_csv(RANK_FILE, sep='\t')
            user_scores = df_scores[df_scores['user_name'] == user_name]
            if not user_scores.empty:
                # 检查是否有3个时期的数据
                periods = user_scores['period'].unique()
                expected_periods = ['2026-2050', '2051-2075', '2076-2100']

                result["periods_found"] = len(periods)
                result["data_complete"] = len(periods) >= 3

                if result["data_complete"]:
                    # 按时期排序，确保顺序正确
                    user_scores_sorted = user_scores.sort_values('period')
                    result["block_scores_tsv"] = user_scores_sorted.to_csv(sep='\t', index=False)
                    print(f"✅ [API] 找到完整评分数据: {len(periods)} 个时期")
                else:
                    result["block_scores_tsv"] = user_scores.to_csv(sep='\t', index=False)
                    print(f"⚠️ [API] 评分数据不完整: 只有 {len(periods)} 个时期")

                result["found"] = True

        if not result["found"]:
            print(f"❌ [API] 未找到用户数据: {user_name}")
            raise HTTPException(status_code=404, detail=f"No data found for user: {user_name}")

        if not result["data_complete"]:
            print(f"⚠️ [API] 用户数据不完整: {user_name}, 时期数: {result['periods_found']}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] 获取用户数据失败: {str(e)}")
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

# 批量接收前端log数据的API端点
@app.post("/logs/batch")
async def receive_batch_logs(request: dict):
    """批量接收前端log数据"""
    try:
        logs = request.get("logs", [])
        if not logs:
            return {"status": "success", "message": "No logs to process"}

        log_path = Path(__file__).parent / "data" / "user_log.jsonl"

        # 确保data目录存在
        log_path.parent.mkdir(exist_ok=True)

        # 批量写入log数据
        with open(log_path, "a", encoding="utf-8") as f:
            for log_entry in logs:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        print(f"✅ [API] 批量接收 {len(logs)} 条log数据")
        return {
            "status": "success",
            "message": f"Successfully received {len(logs)} logs",
            "count": len(logs)
        }

    except Exception as e:
        print(f"❌ [API] 批量log接收失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save logs: {str(e)}")

# 结束实验API端点
@app.post("/experiment/end")
async def end_experiment(request: dict):
    """处理实验结束请求"""
    try:
        user_name = request.get("user_name")
        logs = request.get("logs", [])

        if not user_name:
            raise HTTPException(status_code=400, detail="User name is required")

        log_path = Path(__file__).parent / "data" / "user_log.jsonl"
        log_path.parent.mkdir(exist_ok=True)

        # 写入结束实验的日志
        end_log = {
            "type": "ExperimentEnd",
            "user_name": user_name,
            "timestamp": datetime.now().isoformat(),
            "total_logs": len(logs)
        }

        with open(log_path, "a", encoding="utf-8") as f:
            # 写入所有用户行为日志
            for log_entry in logs:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            # 写入实验结束标记
            f.write(json.dumps(end_log, ensure_ascii=False) + "\n")

        print(f"✅ [Experiment End] 用户 {user_name} 实验结束，保存 {len(logs)} 条日志")

        return {
            "status": "success",
            "message": f"Experiment ended for user {user_name}",
            "logs_saved": len(logs)
        }

    except Exception as e:
        print(f"❌ [Experiment End] 处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to end experiment: {str(e)}")

# 获取用户日志API端点
@app.get("/user-logs/{user_name}")
async def get_user_logs(user_name: str):
    """获取指定用户的所有日志数据"""
    try:
        log_path = Path(__file__).parent / "data" / "user_log.jsonl"

        if not log_path.exists():
            return {"logs": [], "message": "No logs found"}

        user_logs = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line.strip())
                        if log.get('user_name') == user_name:
                            user_logs.append(log)
                    except json.JSONDecodeError:
                        continue

        print(f"✅ [User Logs] 获取用户 {user_name} 的日志: {len(user_logs)} 条")

        return {
            "user_name": user_name,
            "logs": user_logs,
            "total_count": len(user_logs)
        }

    except Exception as e:
        print(f"❌ [User Logs] 获取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user logs: {str(e)}")

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

@app.get("/admin/data-files")
async def list_data_files(admin: str = Depends(authenticate_admin)):
    """获取data文件夹下所有文件的列表和信息"""
    try:
        data_dir = Path(__file__).parent / "data"
        files_info = []

        if data_dir.exists():
            for file_path in data_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files_info.append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": file_path.suffix.lower()
                    })

        return {"files": files_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルリストの取得に失敗しました: {str(e)}")

@app.get("/admin/preview-file/{filename}")
async def preview_file_content(filename: str, admin: str = Depends(authenticate_admin)):
    """ファイル内容をプレビュー用に取得"""
    try:
        data_dir = Path(__file__).parent / "data"
        file_path = data_dir / filename

        print(f"Preview request for file: {filename}")
        print(f"File path: {file_path}")
        print(f"File exists: {file_path.exists()}")

        # セキュリティチェック
        if not file_path.resolve().is_relative_to(data_dir.resolve()):
            raise HTTPException(status_code=400, detail="無効なファイルパスです")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")

        file_extension = file_path.suffix.lower()
        print(f"File extension: {file_extension}")

        # ファイルサイズチェック（大きすぎる場合は制限）
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = file_path.stat().st_size
        print(f"File size: {file_size}")

        if file_size > max_size:
            return {
                "filename": filename,
                "type": "error",
                "message": "ファイルサイズが大きすぎます（5MB以上）",
                "data": []
            }

        try:
            if file_extension in ['.csv']:
                # CSV ファイルの処理
                print(f"Processing CSV file: {filename}")
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='shift_jis')

                print(f"CSV loaded successfully. Shape: {df.shape}")
                print(f"Columns: {df.columns.tolist()}")

                return {
                    "filename": filename,
                    "type": "table",
                    "columns": df.columns.tolist(),
                    "data": df.head(100).fillna('').to_dict('records'),  # 最初の100行のみ、NaNを空文字に
                    "total_rows": len(df)
                }

            elif file_extension in ['.tsv']:
                # TSV ファイルの処理
                print(f"Processing TSV file: {filename}")
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, sep='\t', encoding='shift_jis')

                print(f"TSV loaded successfully. Shape: {df.shape}")
                print(f"Columns: {df.columns.tolist()}")

                return {
                    "filename": filename,
                    "type": "table",
                    "columns": df.columns.tolist(),
                    "data": df.head(100).fillna('').to_dict('records'),
                    "total_rows": len(df)
                }

            elif file_extension in ['.jsonl']:
                # JSONL ファイルの処理
                import json
                lines = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= 100:  # 最初の100行のみ
                            break
                        if line.strip():
                            try:
                                lines.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                continue

                # 総行数を取得
                total_lines = sum(1 for line in open(file_path, 'r', encoding='utf-8') if line.strip())

                return {
                    "filename": filename,
                    "type": "json",
                    "data": lines,
                    "total_rows": total_lines
                }

            else:
                # その他のテキストファイル
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(10000)  # 最初の10KB

                return {
                    "filename": filename,
                    "type": "text",
                    "data": content,
                    "total_size": file_path.stat().st_size
                }

        except Exception as parse_error:
            # ファイル解析エラーの場合、生テキストとして表示
            print(f"Parse error for {filename}: {str(parse_error)}")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)
            except Exception as read_error:
                print(f"Read error for {filename}: {str(read_error)}")
                content = f"ファイル読み込みエラー: {str(read_error)}"

            return {
                "filename": filename,
                "type": "text",
                "data": content,
                "error": f"解析エラー: {str(parse_error)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"General error for {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ファイルプレビューに失敗しました: {str(e)}")

@app.get("/admin/download/file/{filename}")
async def download_single_file(filename: str, admin: str = Depends(authenticate_admin)):
    """指定されたファイルをダウンロード"""
    try:
        data_dir = Path(__file__).parent / "data"
        file_path = data_dir / filename

        # セキュリティチェック：パストラバーサル攻撃を防ぐ
        if not file_path.resolve().is_relative_to(data_dir.resolve()):
            raise HTTPException(status_code=400, detail="無効なファイルパスです")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルのダウンロードに失敗しました: {str(e)}")

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

@app.get("/admin/data-stats")
async def get_data_stats(admin: str = Depends(authenticate_admin)):
    """获取数据统计信息，用于清空前确认"""
    try:
        data_dir = Path(__file__).parent / "data"

        # 统计用户日志
        user_log_file = data_dir / "user_log.jsonl"
        user_logs = []
        unique_users = set()

        if user_log_file.exists():
            with open(user_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            log = json.loads(line.strip())
                            user_logs.append(log)
                            if 'user_name' in log:
                                unique_users.add(log['user_name'])
                        except json.JSONDecodeError:
                            continue

        # 统计评分数据
        block_scores = []
        simulation_periods = set()

        if RANK_FILE.exists():
            df = pd.read_csv(RANK_FILE, sep='\t')
            block_scores = df.to_dict('records')
            simulation_periods = set(df['period'].unique()) if 'period' in df.columns else set()

        # 统计决策日志
        decision_logs = []
        if ACTION_LOG_FILE.exists():
            df_log = pd.read_csv(ACTION_LOG_FILE)
            decision_logs = df_log.to_dict('records')

        # 计算文件大小
        file_sizes = {}
        data_files = [
            ("user_log.jsonl", user_log_file),
            ("block_scores.tsv", RANK_FILE),
            ("decision_log.csv", ACTION_LOG_FILE),
            ("your_name.csv", YOUR_NAME_FILE)
        ]

        total_size = 0
        for file_name, file_path in data_files:
            if file_path.exists():
                size = file_path.stat().st_size
                file_sizes[file_name] = {
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "exists": True
                }
                total_size += size
            else:
                file_sizes[file_name] = {
                    "size_bytes": 0,
                    "size_mb": 0,
                    "exists": False
                }

        # 获取最早和最新的活动时间
        earliest_activity = None
        latest_activity = None

        if user_logs:
            timestamps = [log.get('timestamp') for log in user_logs if log.get('timestamp')]
            if timestamps:
                earliest_activity = min(timestamps)
                latest_activity = max(timestamps)

        stats = {
            "summary": {
                "total_users": len(unique_users),
                "total_logs": len(user_logs),
                "total_simulations": len(block_scores),
                "total_decision_logs": len(decision_logs),
                "simulation_periods": len(simulation_periods),
                "earliest_activity": earliest_activity,
                "latest_activity": latest_activity,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            },
            "files": file_sizes,
            "users": list(unique_users),
            "periods": list(simulation_periods)
        }

        return stats

    except Exception as e:
        print(f"❌ [Admin] 数据统计获取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"データ統計の取得に失敗しました: {str(e)}")

@app.post("/admin/clear-data")
async def clear_all_data(admin: str = Depends(authenticate_admin)):
    """清空所有数据文件内容（保留文件但清空内容）"""
    try:
        data_dir = Path(__file__).parent / "data"

        # 获取清空前的统计信息
        stats_before = await get_data_stats(admin)

        # 定义需要清空的文件
        files_to_clear = [
            ("user_log.jsonl", data_dir / "user_log.jsonl"),
            ("block_scores.tsv", RANK_FILE),
            ("decision_log.csv", ACTION_LOG_FILE),
            ("your_name.csv", YOUR_NAME_FILE)
        ]

        cleared_files = []
        errors = []

        # 清空每个文件的内容
        for file_name, file_path in files_to_clear:
            try:
                if file_path.exists():
                    # 获取文件原始大小
                    original_size = file_path.stat().st_size

                    # 清空文件内容但保留文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        # 对于TSV和CSV文件，保留表头
                        if file_name == "block_scores.tsv":
                            f.write("user_name\tscenario_name\tperiod\ttotal_score\ttimestamp\n")
                        elif file_name == "decision_log.csv":
                            f.write("year,planting_trees_amount,house_migration_amount,dam_levee_construction_cost,paddy_dam_construction_cost,capacity_building_cost,transportation_invest,agricultural_RnD_cost,cp_climate_params,user_name,scenario_name,timestamp\n")
                        elif file_name == "your_name.csv":
                            f.write("user_name\n")
                        # user_log.jsonl 完全清空

                    cleared_files.append({
                        "file": file_name,
                        "original_size_bytes": original_size,
                        "original_size_mb": round(original_size / (1024 * 1024), 2),
                        "status": "cleared"
                    })
                    print(f"✅ [Admin] 已清空文件: {file_name} (原大小: {original_size} bytes)")
                else:
                    cleared_files.append({
                        "file": file_name,
                        "original_size_bytes": 0,
                        "original_size_mb": 0,
                        "status": "not_existed"
                    })
                    print(f"ℹ️ [Admin] 文件不存在，跳过: {file_name}")

            except Exception as file_error:
                error_msg = f"文件 {file_name} 清空失败: {str(file_error)}"
                errors.append(error_msg)
                print(f"❌ [Admin] {error_msg}")

        # 清空内存中的scenarios_data
        global scenarios_data
        scenarios_data.clear()
        print("✅ [Admin] 已清空内存中的scenarios_data")

        # 准备响应
        result = {
            "success": len(errors) == 0,
            "message": "データクリアが完了しました" if len(errors) == 0 else f"一部のファイルでエラーが発生しました: {len(errors)}件",
            "stats_before": stats_before["summary"],
            "cleared_files": cleared_files,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
            "total_files_processed": len(files_to_clear),
            "successful_clears": len(cleared_files) - len(errors)
        }

        print(f"🧹 [Admin] 数据清空操作完成: 成功 {result['successful_clears']}/{result['total_files_processed']} 个文件")

        return result

    except Exception as e:
        print(f"❌ [Admin] 数据清空操作失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"データクリアに失敗しました: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
