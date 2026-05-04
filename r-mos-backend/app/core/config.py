"""
配置管理 — 产品化版本
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./rmos_dev.db"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # 安全配置
    SECRET_KEY: str = "dev-only-change-me"

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Adapter配置
    ROBOT_MODE: str = "simulation"  # simulation / physical
    MOCK_JOINT_COUNT: int = 10
    MOCK_SIMULATION_SPEED: float = 1.0
    MOCK_BASE_TEMPERATURE: float = 40.0

    # WebSocket配置
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_PUSH_FREQUENCY: int = 5  # Hz

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # Agent V2 Feature Flag
    AGENT_V2_ENABLED: bool = False
    AGENT_V2_DEFAULT_BUDGET_MS: int = 300000
    AGENT_V2_IDEMPOTENCY_TTL_SECONDS: int = 3600

    # LLM Provider Config
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    LLM_PRIMARY_PROVIDER: str = "deepseek"
    LLM_FALLBACK_PROVIDER: str = "minimax"
    LLM_TIMEOUT_SECONDS: float = 10.0
    LLM_ENABLE_MOCK_FALLBACK: bool = True

    # AI Assistant
    AI_ASSISTANT_MAX_HISTORY: int = 20
    AI_ASSISTANT_SYSTEM_PROMPT: str = "你是 R-MOS 维保学习助手，帮助学生理解机器人维保操作。"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_production(self) -> None:
        """生产环境启动校验"""
        if not self.DEBUG:
            if self.SECRET_KEY == "dev-only-change-me":
                raise RuntimeError("SECRET_KEY must be set in production")
            if "sqlite" in self.DATABASE_URL:
                raise RuntimeError("SQLite not supported in production, use PostgreSQL")


settings = Settings()
