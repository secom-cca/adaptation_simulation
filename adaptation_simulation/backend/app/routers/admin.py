"""
管理员API路由
"""
import os
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pandas as pd

from ..config import settings

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()

# 管理员认证
def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """验证管理员身份"""
    correct_username = "admin"
    correct_password = "climate2025"  # 可以通过环境变量配置
    
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=401,
            detail="管理员认证失败",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.get("/dashboard")
async def get_admin_dashboard(admin: str = Depends(authenticate_admin)):
    """获取管理员仪表板数据"""
    try:
        data_dir = Path(settings.DATA_DIR)
        
        # 读取用户日志
        user_log_file = data_dir / "user_log.jsonl"
        user_logs = []
        if user_log_file.exists():
            with open(user_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        user_logs.append(json.loads(line.strip()))
        
        # 读取评分数据
        block_scores_file = data_dir / "block_scores.tsv"
        block_scores = []
        if block_scores_file.exists():
            df = pd.read_csv(block_scores_file, sep='\t')
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
                "block_scores_size": block_scores_file.stat().st_size if block_scores_file.exists() else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")

@router.get("/users/{user_name}")
async def get_user_detail(user_name: str, admin: str = Depends(authenticate_admin)):
    """获取特定用户的详细数据 - 包含所有数据文件"""
    try:
        data_dir = Path(settings.DATA_DIR)

        # 1. 用户操作日志 (user_log.jsonl)
        user_log_file = data_dir / "user_log.jsonl"
        user_logs = []
        if user_log_file.exists():
            with open(user_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            log = json.loads(line.strip())
                            if log.get('user_name') == user_name:
                                user_logs.append(log)
                        except json.JSONDecodeError:
                            continue

        # 2. 仿真评分数据 (block_scores.tsv)
        block_scores_file = data_dir / "block_scores.tsv"
        user_scores = []
        if block_scores_file.exists():
            try:
                df = pd.read_csv(block_scores_file, sep='\t')
                user_data = df[df['user_name'] == user_name]
                user_scores = user_data.to_dict('records')
            except Exception as e:
                print(f"读取block_scores.tsv失败: {e}")

        # 3. 决策记录 (decision_log.csv)
        decision_log_file = data_dir / "decision_log.csv"
        user_decisions = []
        if decision_log_file.exists():
            try:
                df = pd.read_csv(decision_log_file)
                if not df.empty and 'user_name' in df.columns:
                    user_data = df[df['user_name'] == user_name]
                    user_decisions = user_data.to_dict('records')
            except Exception as e:
                print(f"读取decision_log.csv失败: {e}")

        # 4. 参数区域配置 (parameter_zones.csv)
        parameter_zones_file = data_dir / "parameter_zones.csv"
        parameter_zones = []
        if parameter_zones_file.exists():
            try:
                df = pd.read_csv(parameter_zones_file)
                parameter_zones = df.to_dict('records')
            except Exception as e:
                print(f"读取parameter_zones.csv失败: {e}")

        # 5. 用户名记录 (your_name.csv)
        your_name_file = data_dir / "your_name.csv"
        user_info = {"registered": False}
        if your_name_file.exists():
            try:
                df = pd.read_csv(your_name_file)
                if not df.empty and 'user_name' in df.columns:
                    if user_name in df['user_name'].values:
                        user_info["registered"] = True
            except Exception as e:
                print(f"读取your_name.csv失败: {e}")

        # 检查用户是否存在
        if not user_logs and not user_scores and not user_decisions:
            raise HTTPException(status_code=404, detail="用户不存在或无数据")

        # 统计信息
        timestamps = []
        if user_logs:
            timestamps.extend([log.get('timestamp') for log in user_logs if log.get('timestamp')])
        if user_scores:
            timestamps.extend([score.get('timestamp') for score in user_scores if score.get('timestamp')])
        if user_decisions:
            timestamps.extend([decision.get('timestamp') for decision in user_decisions if decision.get('timestamp')])

        # 操作类型统计
        action_types = {}
        for log in user_logs:
            action_type = log.get('type', 'Unknown')
            action_types[action_type] = action_types.get(action_type, 0) + 1

        return {
            "user_name": user_name,
            "user_logs": user_logs,
            "block_scores": user_scores,
            "decision_log": user_decisions,
            "parameter_zones": parameter_zones,
            "user_info": user_info,
            "statistics": {
                "total_actions": len(user_logs),
                "total_decisions": len(user_decisions),
                "simulation_periods": len(user_scores),
                "action_types": action_types,
                "first_activity": min(timestamps) if timestamps else None,
                "last_activity": max(timestamps) if timestamps else None,
                "data_files_found": {
                    "user_logs": len(user_logs) > 0,
                    "block_scores": len(user_scores) > 0,
                    "decision_log": len(user_decisions) > 0,
                    "parameter_zones": len(parameter_zones) > 0,
                    "user_registered": user_info["registered"]
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取用户详细数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户数据失败: {str(e)}")

@router.get("/download/all")
async def download_all_data(admin: str = Depends(authenticate_admin)):
    """下载所有数据的压缩包"""
    try:
        data_dir = Path(settings.DATA_DIR)
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
            
            # 添加统计报告
            dashboard_data = await get_admin_dashboard(admin)
            report_content = json.dumps(dashboard_data, ensure_ascii=False, indent=2)
            zipf.writestr("admin_report.json", report_content)
        
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.get("/download/logs")
async def download_user_logs(admin: str = Depends(authenticate_admin)):
    """下载用户日志文件"""
    try:
        data_dir = Path(settings.DATA_DIR)
        log_file = data_dir / "user_log.jsonl"
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="日志文件不存在")
        
        return FileResponse(
            path=log_file,
            filename=f"user_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            media_type="application/json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载日志失败: {str(e)}")

@router.get("/download/scores")
async def download_scores(admin: str = Depends(authenticate_admin)):
    """下载评分数据文件"""
    try:
        data_dir = Path(settings.DATA_DIR)
        scores_file = data_dir / "block_scores.tsv"
        
        if not scores_file.exists():
            raise HTTPException(status_code=404, detail="评分文件不存在")
        
        return FileResponse(
            path=scores_file,
            filename=f"block_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv",
            media_type="text/tab-separated-values"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载评分数据失败: {str(e)}")

@router.delete("/data/clear")
async def clear_all_data(admin: str = Depends(authenticate_admin)):
    """清空所有数据（谨慎使用）"""
    try:
        data_dir = Path(settings.DATA_DIR)
        
        # 备份当前数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_zip = data_dir / f"backup_before_clear_{timestamp}.zip"
        
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in data_dir.glob("*.jsonl"):
                zipf.write(file_path, file_path.name)
            for file_path in data_dir.glob("*.tsv"):
                zipf.write(file_path, file_path.name)
            for file_path in data_dir.glob("*.csv"):
                zipf.write(file_path, file_path.name)
        
        # 清空数据文件
        files_cleared = []
        for file_path in data_dir.glob("*.jsonl"):
            file_path.unlink()
            files_cleared.append(file_path.name)
        for file_path in data_dir.glob("*.tsv"):
            file_path.unlink()
            files_cleared.append(file_path.name)
        for file_path in data_dir.glob("*.csv"):
            file_path.unlink()
            files_cleared.append(file_path.name)
        
        return {
            "message": "数据清空成功",
            "backup_file": backup_zip.name,
            "cleared_files": files_cleared,
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空数据失败: {str(e)}")
