"""
FastAPI Application Factory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import simulation, analysis, websocket, admin

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="Climate Adaptation Simulation API",
        description="气候变化适应策略仿真平台API",
        version="1.0.0",
        debug=settings.DEBUG
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(simulation.router)
    app.include_router(analysis.router)
    app.include_router(websocket.router)
    app.include_router(admin.router)
    
    # 健康检查端点
    @app.get("/ping")
    def ping():
        return {"message": "pong"}
    
    # 根路径
    @app.get("/")
    def root():
        return {
            "message": "Climate Adaptation Simulation API",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
    return app

# 创建应用实例
app = create_app()
