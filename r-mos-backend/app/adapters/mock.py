"""
Mock机器人适配器（V2.2完整版）
用于在没有真实硬件的情况下模拟完整的机器人行为
"""
import math
import random
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseRobotAdapter
from .schemas import (
    RobotInfo,
    RobotStructure,
    JointState,
    SensorData,
    IMUData,
    FaultInjectionResult,
    RobotStatus,
    PartDefinition
)


class MockRobotAdapter(BaseRobotAdapter):
    """Mock机器人适配器（V2.2完整版）
    
    特性：
    1. 不连接任何真实硬件
    2. 返回动态变化的模拟数据（基于时间和故障状态）
    3. 支持配置化的关节和传感器数量
    4. 故障注入会真实影响返回的数据
    5. 后台任务驱动模拟时间推进
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化Mock Adapter
        
        Args:
            config: 配置字典，可选参数：
                - joint_count: 关节数量（默认10）
                - simulation_speed: 模拟速度倍率（默认1.0）
                - base_temperature: 基础温度（默认40℃）
        """
        self._config = config or {}
        self._connected = False
        self._simulation_time = 0.0
        self._simulation_speed = self._config.get("simulation_speed", 1.0)
        self._base_temperature = self._config.get("base_temperature", 40.0)
        
        # 活动故障列表
        self._active_faults: List[str] = []
        
        # 故障影响配置（V2.2完整定义）
        self._fault_effects = {
            "E001_OVERHEAT": {
                "temperature_increase": 30.0,
                "torque_multiplier": 0.7,
                "position_noise": 0.3
            },
            "E002_STALL": {
                "velocity_multiplier": 0.0,
                "position_frozen": True
            },
            "E003_VOLTAGE_DROP": {
                "battery_drain": 50.0,
                "torque_multiplier": 0.5
            },
            "E004_SENSOR_FAILURE": {
                "sensor_noise": True
            },
            "E005_JOINT_LOOSE": {
                "position_noise": 0.5,
                "torque_multiplier": 0.3
            }
        }
        
        # 生成关节列表
        joint_count = self._config.get("joint_count", 10)
        self._joints = self._generate_joints(joint_count)
        
        # 记录故障注入的关节状态（用于STALL等冻结效果）
        self._frozen_joint_positions: Dict[str, float] = {}
        
        # 后台任务句柄
        self._simulation_task: Optional[asyncio.Task] = None
    
    def _generate_joints(self, count: int) -> List[str]:
        """生成模拟关节列表"""
        joint_types = [
            "knee_right", "knee_left",
            "hip_right", "hip_left",
            "ankle_right", "ankle_left",
            "shoulder_right", "shoulder_left",
            "elbow_right", "elbow_left",
            "wrist_right", "wrist_left",
            "neck", "waist"
        ]
        return joint_types[:count]
    
    async def _simulation_loop(self):
        """后台模拟时间推进任务（V2.2新增）"""
        while self._connected:
            await asyncio.sleep(0.1)  # 10Hz更新
            self._simulation_time += 0.1 * self._simulation_speed
    
    async def connect(self) -> bool:
        """模拟连接"""
        await asyncio.sleep(0.1)  # 模拟连接延迟
        self._connected = True
        self._simulation_time = 0.0
        
        # 启动后台模拟任务（V2.2新增）
        self._simulation_task = asyncio.create_task(self._simulation_loop())
        
        return True
    
    async def disconnect(self) -> bool:
        """模拟断开"""
        self._connected = False
        
        # 停止后台任务（V2.2新增）
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
        
        return True
    
    async def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    async def get_robot_info(self) -> RobotInfo:
        """获取机器人信息"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
            
        return RobotInfo(
            robot_id="mock_robot_001",
            model="MOCK_HUMANOID_V1",
            firmware_version="1.0.0-mock",
            runtime_status=RobotStatus.ONLINE if not self._active_faults else RobotStatus.ERROR,
            last_update=datetime.utcnow()
        )
    
    async def get_robot_structure(self) -> RobotStructure:
        """获取机器人结构"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
            
        joints = [
            PartDefinition(id=joint, name=joint.replace("_", " ").title(), type="joint")
            for joint in self._joints
        ]
        
        sensors = [
            PartDefinition(id="imu_main", name="Main IMU", type="sensor"),
            PartDefinition(id="battery_monitor", name="Battery Monitor", type="sensor"),
            PartDefinition(id="temp_sensor", name="Temperature Sensor", type="sensor")
        ]
        
        power_modules = [
            PartDefinition(id="main_power", name="Main Power Supply", type="power_module")
        ]
        
        return RobotStructure(
            joints=joints,
            sensors=sensors,
            power_modules=power_modules
        )
    
    async def get_joint_states(self) -> List[JointState]:
        """获取关节状态（动态变化 + 故障影响）【V2.2完整实现】"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
        
        joint_states = []
        
        for joint_id in self._joints:
            # 基础动态数据（正弦波模拟运动）
            base_position = math.sin(self._simulation_time * 0.5) * 1.5
            base_velocity = math.cos(self._simulation_time * 0.5) * 0.1
            base_torque = 5.0 + random.gauss(0, 0.5)
            base_current = 2.0 + random.gauss(0, 0.2)
            base_temperature = self._base_temperature + random.gauss(0, 2.0)
            
            # 应用故障影响
            position = base_position
            velocity = base_velocity
            torque = base_torque
            current = base_current
            temperature = base_temperature
            error_code = None
            
            # 检查是否有故障影响此关节
            for fault_code in self._active_faults:
                if fault_code not in self._fault_effects:
                    continue
                
                effect = self._fault_effects[fault_code]
                
                # E001_OVERHEAT: 温度升高，扭矩下降
                if "temperature_increase" in effect:
                    temperature += effect["temperature_increase"]
                if "torque_multiplier" in effect:
                    torque *= effect["torque_multiplier"]
                
                # E002_STALL: 速度冻结，位置固定
                if effect.get("position_frozen"):
                    if joint_id not in self._frozen_joint_positions:
                        self._frozen_joint_positions[joint_id] = position
                    position = self._frozen_joint_positions[joint_id]
                    velocity = 0.0
                
                # 位置噪声
                if "position_noise" in effect:
                    position += random.gauss(0, effect["position_noise"])
                
                # 传感器错误码
                if temperature > 70.0:
                    error_code = "E001_OVERHEAT"
                elif velocity == 0.0 and fault_code == "E002_STALL":
                    error_code = "E002_STALL"
            
            joint_states.append(JointState(
                joint_id=joint_id,
                position=position,
                velocity=velocity,
                torque=torque,
                current=current,
                temperature=temperature,
                error_code=error_code
            ))
        
        return joint_states
    
    async def get_sensor_data(self) -> SensorData:
        """获取传感器数据（动态变化 + 故障影响）【V2.2完整实现】"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
        
        # 基础传感器数据
        battery = 100.0 - (self._simulation_time * 0.1)  # 随时间缓慢降低
        battery = max(0.0, min(100.0, battery))
        
        temperature = self._base_temperature + math.sin(self._simulation_time * 0.1) * 5.0
        
        # 应用故障影响
        for fault_code in self._active_faults:
            if fault_code not in self._fault_effects:
                continue
            
            effect = self._fault_effects[fault_code]
            
            # E003_VOLTAGE_DROP: 电池快速消耗
            if "battery_drain" in effect:
                battery -= effect["battery_drain"]
            
            # E004_SENSOR_FAILURE: 传感器噪声
            if effect.get("sensor_noise"):
                temperature += random.gauss(0, 10.0)
        
        battery = max(0.0, min(100.0, battery))
        
        return SensorData(
            imu=IMUData(
                acceleration={"x": random.gauss(0, 0.1), "y": random.gauss(0, 0.1), "z": 9.8 + random.gauss(0, 0.2)},
                angular_velocity={"x": random.gauss(0, 0.05), "y": random.gauss(0, 0.05), "z": random.gauss(0, 0.05)}
            ),
            battery=battery,
            temperature=temperature,
            voltage={"main": 24.0 + random.gauss(0, 0.5), "logic": 5.0 + random.gauss(0, 0.1)},
            pressure={"foot_left": 100.0 + random.gauss(0, 10.0), "foot_right": 100.0 + random.gauss(0, 10.0)}
        )
    
    async def inject_fault(
        self,
        fault_code: str,
        target_part: str,
        severity: str = "medium"
    ) -> FaultInjectionResult:
        """注入故障【V2.2完整实现】"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
        
        # 验证故障代码
        if fault_code not in self._fault_effects:
            raise ValueError(f"Unknown fault code: {fault_code}")
        
        # 验证目标部件
        if target_part not in self._joints:
            raise ValueError(f"Unknown target part: {target_part}")
        
        # 记录故障
        if fault_code not in self._active_faults:
            self._active_faults.append(fault_code)
        
        return FaultInjectionResult(
            success=True,
            fault_code=fault_code,
            target_part=target_part,
            severity=severity,
            injected_at=datetime.utcnow(),
            message=f"故障 {fault_code} 已注入到 {target_part}"
        )
    
    async def clear_fault(self, fault_code: str) -> bool:
        """清除故障"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")
        
        if fault_code in self._active_faults:
            self._active_faults.remove(fault_code)
            # 清除冻结的关节位置
            if fault_code == "E002_STALL":
                self._frozen_joint_positions.clear()
            return True
        
        return False
    
    async def get_active_faults(self) -> List[str]:
        """获取活动故障列表"""
        return self._active_faults.copy()
