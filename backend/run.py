"""
Application Entry Point
"""
import os
import uvicorn

if __name__ == "__main__":
    # Railway会自动设置PORT环境变量
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    # 生产环境不使用reload
    reload = os.environ.get("ENVIRONMENT", "development") == "development"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
