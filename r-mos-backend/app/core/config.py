"""
配置管理 — 产品化版本
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


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
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 存储后端配置
    STORAGE_BACKEND: str = "local"  # local / s3（P1-2 实现）
    STORAGE_BASE_DIR: str = "data/robot-assets"
    # S3 兼容对象存储（STORAGE_BACKEND=s3 时生效；MinIO/OSS 传自定义 endpoint）
    S3_ENDPOINT_URL: Optional[str] = None
    S3_PUBLIC_ENDPOINT_URL: Optional[str] = None  # 浏览器可达域名（presign 用），空则同 endpoint
    S3_BUCKET: str = "rmos-assets"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_PRESIGN_EXPIRE_SECONDS: int = 900

    # Adapter配置
    ROBOT_MODE: str = "simulation"  # simulation / physical
    MOCK_JOINT_COUNT: int = 10
    MOCK_SIMULATION_SPEED: float = 1.0
    MOCK_BASE_TEMPERATURE: float = 40.0
    DEFAULT_ROBOT_MODEL_ID: int = 1

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
    LLM_MODEL_ADVANCED: str = "deepseek-chat"    # 复杂任务（诊断、生成、报告）
    LLM_MODEL_BASIC: str = "deepseek-chat"       # 简单任务（意图识别、聊天、增强）

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

    @property
    def ROBOT_ADAPTER_TYPE(self) -> str:
        """向后兼容: adapter factory 仍然用这个名字。
        ROBOT_MODE="simulation" 映射到 factory 期望的 "mock"。
        """
        mode_map = {"simulation": "mock", "physical": "real"}
        return mode_map.get(self.ROBOT_MODE, self.ROBOT_MODE)


settings = Settings()
