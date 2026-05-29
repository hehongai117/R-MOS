"""
Adapter工厂类
"""
import asyncio
import json
from pathlib import Path
from typing import Optional
from .base import BaseRobotAdapter
from .mock import MockRobotAdapter
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _load_joint_names_from_manifest(robot_id: int = 1) -> list[str] | None:
    """从 assembly_manifest.json 读取非 fixed 类型关节名称列表。

    如果文件不存在或解析失败，返回 None（由 MockRobotAdapter 使用硬编码 fallback）。
    """
    manifest_path = (
        Path(__file__).parent.parent.parent
        / "data"
        / "robot-assets"
        / str(robot_id)
        / "manifests"
        / "assembly_manifest.json"
    )
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        joint_names = [
            j["name"]
            for j in manifest.get("joints", [])
            if j.get("type") != "fixed"
        ]
        logger.info("从 manifest 加载了 %d 个关节名称（robot_id=%s）", len(joint_names), robot_id)
        return joint_names if joint_names else None
    except FileNotFoundError:
        logger.debug("assembly_manifest.json 不存在（路径：%s），使用 MockRobotAdapter 硬编码列表", manifest_path)
        return None
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("解析 assembly_manifest.json 失败（%s），使用硬编码 fallback", exc)
        return None


class AdapterFactory:
    """Adapter工厂类

    职责：
    - 根据配置创建对应的Adapter实例
    - 管理Adapter生命周期
    - 提供全局单例访问
    """

    _instance: Optional[BaseRobotAdapter] = None
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    async def get_adapter(cls) -> BaseRobotAdapter:
        """获取Adapter实例（单例模式，双重检查锁定）

        Returns:
            BaseRobotAdapter: Adapter实例
        """
        if cls._instance is not None:
            return cls._instance

        # 懒初始化锁，避免在事件循环启动前创建 Lock
        if cls._lock is None:
            cls._lock = asyncio.Lock()

        async with cls._lock:
            # 二次检查：防止多个协程同时通过第一关
            if cls._instance is None:
                adapter_type = settings.ROBOT_ADAPTER_TYPE  # "mock" / "gazebo" / "real"

                logger.info(f"正在创建Adapter: {adapter_type}")

                if adapter_type == "mock":
                    mock_config: dict = {
                        "joint_count": settings.MOCK_JOINT_COUNT,
                        "simulation_speed": settings.MOCK_SIMULATION_SPEED,
                        "base_temperature": settings.MOCK_BASE_TEMPERATURE,
                    }
                    # 尝试从 assembly_manifest.json 读取关节列表，失败时由 adapter 自身 fallback 到硬编码
                    joint_names = _load_joint_names_from_manifest(robot_id=1)
                    if joint_names:
                        mock_config["joint_names"] = joint_names
                    cls._instance = MockRobotAdapter(config=mock_config)
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
                    cls._instance = None  # 连接失败时重置，允许下次重试
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