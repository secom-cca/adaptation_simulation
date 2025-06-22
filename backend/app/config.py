"""
Application Configuration
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)

# 应用配置
class Settings:
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS配置
    ALLOWED_ORIGINS: list = ["*"]  # 生产环境中应该限制具体域名
    
    # 数据文件路径
    RANK_FILE = DATA_DIR / "block_scores.tsv"
    ACTION_LOG_FILE = DATA_DIR / "decision_log.csv"
    YOUR_NAME_FILE = DATA_DIR / "your_name.csv"
    USER_LOG_FILE = DATA_DIR / "user_log.jsonl"

# 全局设置实例
settings = Settings()
