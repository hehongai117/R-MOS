"""
Adapter工厂类
"""
from typing import Optional
from .base import BaseRobotAdapter
from .mock import MockRobotAdapter
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Adapter工厂类
    
    职责：
    - 根据配置创建对应的Adapter实例
    - 管理Adapter生命周期
    - 提供全局单例访问
    """
    
    _instance: Optional[BaseRobotAdapter] = None
    
    @classmethod
    async def get_adapter(cls) -> BaseRobotAdapter:
        """获取Adapter实例（单例模式）
        
        Returns:
            BaseRobotAdapter: Adapter实例
        """
        if cls._instance is None:
            adapter_type = settings.ROBOT_ADAPTER_TYPE  # "mock" / "gazebo" / "real"
            
            logger.info(f"正在创建Adapter: {adapter_type}")
            
            if adapter_type == "mock":
                cls._instance = MockRobotAdapter(config={
                    "joint_count": settings.MOCK_JOINT_COUNT,
                    "simulation_speed": settings.MOCK_SIMULATION_SPEED,
                    "base_temperature": settings.MOCK_BASE_TEMPERATURE
                })
            elif adapter_type == "gazebo":
                # 由后续拆包扩展实现
                raise NotImplementedError("Gazebo Adapter 未实现")
            elif adapter_type == "real":
                # 由后续拆包扩展实现
                raise NotImplementedError("Real Adapter 未实现")
            else:
                raise ValueError(f"Unknown adapter type: {adapter_type}")
            
            # 自动连接
            connected = await cls._instance.connect()
            if not connected:
                raise ConnectionError("Adapter连接失败")
            
            logger.info(f"Adapter已连接: {cls._instance.__class__.__name__}")
        
        return cls._instance
    
    @classmethod
    async def close_adapter(cls):
        """关闭并释放Adapter实例"""
        if cls._instance is not None:
            await cls._instance.disconnect()
            cls._instance = None
            logger.info("Adapter已断开")