"""
WebSocket Routes
"""
from fastapi import APIRouter, WebSocket
from pathlib import Path

from ..config import settings

router = APIRouter()

@router.websocket("/ws/log")
async def websocket_log_endpoint(websocket: WebSocket):
    """WebSocket日志端点"""
    await websocket.accept()
    
    while True:
        try:
            data = await websocket.receive_text()
            with open(settings.USER_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(data + "\n")
        except Exception as e:
            # 客户端断开连接等错误时退出
            break
