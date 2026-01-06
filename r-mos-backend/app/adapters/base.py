"""
机器人适配器抽象基类
定义统一的接口规范，所有具体Adapter必须实现
"""
from abc import ABC, abstractmethod
from typing import List
from .schemas import (
    RobotInfo,
    RobotStructure,
    JointState,
    SensorData,
    FaultInjectionResult
)


class BaseRobotAdapter(ABC):
    """机器人适配器抽象基类
    
    设计原则：
    1. R-MOS Core只能依赖此抽象类，不能依赖具体实现
    2. 所有方法必须是异步的（async）
    3. 所有返回值必须符合schemas.py中定义的Pydantic模型
    4. 异常处理由具体实现负责
    """

    @abstractmethod
    async def connect(self) -> bool:
        """建立与机器人的连接
        
        Returns:
            bool: 连接是否成功
            
        Raises:
            ConnectionError: 连接失败时抛出，包含详细错误信息
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开与机器人的连接
        
        Returns:
            bool: 断开是否成功
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """检查当前连接状态
        
        Returns:
            bool: 是否已连接
        """
        pass

    @abstractmethod
    async def get_robot_info(self) -> RobotInfo:
        """获取机器人基础信息
        
        Returns:
            RobotInfo: 机器人信息对象
            
        Raises:
            ConnectionError: 未连接时抛出
        """
        pass

    @abstractmethod
    async def get_robot_structure(self) -> RobotStructure:
        """获取机器人结构描述
        
        此方法返回机器人的静态结构信息，通常在连接后调用一次即可。
        
        Returns:
            RobotStructure: 结构描述对象，包含关节、传感器、电源模块列表
        """
        pass

    @abstractmethod
    async def get_joint_states(self) -> List[JointState]:
        """获取所有关节的当前状态快照
        
        ⚠️ 重要语义约束：
        - 本方法返回Adapter内部缓存的最近一次采样数据
        - 不保证每次调用都进行实时采样（采样由Adapter内部控制）
        - Core层/WebSocket层不得假设"每次调用=一次硬件采样"
        - Adapter必须自行维护采样频率与数据缓存
        
        Returns:
            List[JointState]: 所有关节的状态列表
            
        Raises:
            ConnectionError: 未连接时抛出
        """
        pass

    @abstractmethod
    async def get_sensor_data(self) -> SensorData:
        """获取传感器数据快照
        
        Returns:
            SensorData: 传感器数据对象
            
        Raises:
            ConnectionError: 未连接时抛出
        """
        pass

    @abstractmethod
    async def inject_fault(
        self,
        fault_code: str,
        target_part: str,
        severity: str = "medium"
    ) -> FaultInjectionResult:
        """注入故障（用于训练场景）
        
        此方法用于模拟机器人故障，供教学训练使用。
        注入的故障应该影响后续的状态读取（如get_joint_states）。
        
        Args:
            fault_code: 故障代码，如 "E001_OVERHEAT"
            target_part: 目标部件ID，如 "knee_right"
            severity: 严重程度，可选值: "low" / "medium" / "high"
            
        Returns:
            FaultInjectionResult: 注入结果
            
        Raises:
            ValueError: 故障代码或部件不存在
            ConnectionError: 未连接时抛出
        """
        pass

    @abstractmethod
    async def clear_fault(self, fault_code: str) -> bool:
        """清除指定的故障
        
        Args:
            fault_code: 要清除的故障代码
            
        Returns:
            bool: 是否成功清除
        """
        pass

    @abstractmethod
    async def get_active_faults(self) -> List[str]:
        """获取当前所有活动的故障列表
        
        Returns:
            List[str]: 故障代码列表，如 ["E001_OVERHEAT", "E002_STALL"]
        """
        pass
