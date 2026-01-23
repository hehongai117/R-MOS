"""
配置管理（V2.2补充版）
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置（新增）
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/rmos_dev"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Adapter配置
    ROBOT_ADAPTER_TYPE: str = "mock"  # mock / gazebo / real
    MOCK_JOINT_COUNT: int = 10
    MOCK_SIMULATION_SPEED: float = 1.0
    MOCK_BASE_TEMPERATURE: float = 40.0
    
    # WebSocket配置
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_PUSH_FREQUENCY: int = 5  # Hz
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
