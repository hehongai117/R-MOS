"""
Mock机器人适配器（V2.2完整版）
用于在没有真实硬件的情况下模拟完整的机器人行为
"""
import math
import random
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from .base import BaseRobotAdapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认故障参数（当 YAML 文件不可用时的兜底）
# ---------------------------------------------------------------------------
_DEFAULT_FAULT_EFFECTS: Dict[str, Dict] = {
    "E001_OVERHEAT": {
        "temperature_increase": 30.0,
        "torque_multiplier": 0.7,
        "position_noise": 0.3,
    },
    "E002_STALL": {
        "velocity_multiplier": 0.0,
        "position_frozen": True,
    },
    "E003_VOLTAGE_DROP": {
        "battery_drain": 50.0,
        "torque_multiplier": 0.5,
    },
    "E004_SENSOR_FAILURE": {
        "sensor_noise": True,
    },
    "E005_JOINT_LOOSE": {
        "position_noise": 0.5,
        "torque_multiplier": 0.3,
    },
}

_DEFAULT_SENSOR_DEFAULTS: Dict[str, float] = {
    "imu_gravity_z": 9.8,
    "imu_noise_stddev": 0.2,
    "voltage_main": 24.0,
    "voltage_logic": 5.0,
    "pressure_baseline": 100.0,
    "pressure_noise_stddev": 10.0,
    "battery_drain_rate": 0.1,
}

# ---------------------------------------------------------------------------
# 从 YAML 加载配置（模块级，只加载一次）
# ---------------------------------------------------------------------------
_MOCK_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "config" / "mock_faults.yaml"

def _load_mock_config() -> tuple[Dict[str, Dict], Dict[str, float]]:
    """从 YAML 加载故障参数和传感器默认值；文件不存在时返回内置默认值。"""
    try:
        import yaml  # noqa: PLC0415 — 仅在需要时导入
        with open(_MOCK_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        fault_effects = data.get("fault_effects", _DEFAULT_FAULT_EFFECTS)
        sensor_defaults = data.get("sensor_defaults", _DEFAULT_SENSOR_DEFAULTS)
        logger.debug("已从 %s 加载 mock 故障参数", _MOCK_CONFIG_PATH)
        return fault_effects, sensor_defaults
    except FileNotFoundError:
        logger.warning("未找到 mock_faults.yaml，使用内置默认参数（路径：%s）", _MOCK_CONFIG_PATH)
        return _DEFAULT_FAULT_EFFECTS, _DEFAULT_SENSOR_DEFAULTS
    except Exception as exc:  # noqa: BLE001
        logger.warning("加载 mock_faults.yaml 失败（%s），使用内置默认参数", exc)
        return _DEFAULT_FAULT_EFFECTS, _DEFAULT_SENSOR_DEFAULTS

_FAULT_EFFECTS, _SENSOR_DEFAULTS = _load_mock_config()

if TYPE_CHECKING:
    from app.services.simulation.fault_scenarios import GradualFault
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

        # Demo 模式：渐进式故障（随时间 ramp up，惰性导入避免循环引用）
        self._gradual_faults: List["GradualFault"] = []
        
        # 故障影响配置（从 YAML 加载，含内置兜底）
        self._fault_effects = _FAULT_EFFECTS
        
        # 生成关节列表
        joint_count = self._config.get("joint_count", 10)
        self._joints = self._generate_joints(joint_count)
        
        # 记录故障注入的关节状态（用于STALL等冻结效果）
        self._frozen_joint_positions: Dict[str, float] = {}
        self._emergency_stopped = False
        self._battery_level_override: Optional[float] = None
        
        # 后台任务句柄
        self._simulation_task: Optional[asyncio.Task] = None
    
    def _generate_joints(self, count: int) -> List[str]:
        """生成模拟关节列表

        优先使用 config["joint_names"]；若未提供则 fallback 到硬编码列表（截取前 count 个）。
        """
        # 优先使用 config 中的关节名称列表
        if self._config.get("joint_names"):
            return list(self._config["joint_names"])

        # Fallback：硬编码 14 个关节，按 count 截取
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
            robot_id=self._config.get("robot_id", "mock_robot_001"),
            model=self._config.get("model_name", "MOCK_HUMANOID_V1"),
            firmware_version="1.0.0-mock",
            runtime_status=(
                RobotStatus.MAINTENANCE
                if self._emergency_stopped
                else (RobotStatus.ONLINE if not self._active_faults else RobotStatus.ERROR)
            ),
            last_update=datetime.now(timezone.utc)
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

            if self._emergency_stopped:
                velocity = 0.0
                torque = 0.0
                current = 0.0
            
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

            # 应用 Demo 渐进故障效果（独立于 _active_faults 的即时故障）
            for gf in self._gradual_faults:
                if gf.joint_id != joint_id:
                    continue
                temp_increase = gf.current_temp_increase()
                torque_noise = gf.current_torque_noise()
                temperature += temp_increase
                torque += random.gauss(0, torque_noise)
                current += temp_increase * 0.05  # 温升伴随电流增大
                # ramp 完成后标记 error_code 以触发前端告警
                if gf.is_complete and not error_code:
                    error_code = "E001_OVERHEAT"
                    if "E001_OVERHEAT" not in self._active_faults:
                        self._active_faults.append("E001_OVERHEAT")

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
        battery = self._battery_level_override if self._battery_level_override is not None else 100.0 - (self._simulation_time * _SENSOR_DEFAULTS["battery_drain_rate"])  # 随时间缓慢降低
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
        
        sd = _SENSOR_DEFAULTS
        return SensorData(
            imu=IMUData(
                acceleration={
                    "x": random.gauss(0, 0.1),
                    "y": random.gauss(0, 0.1),
                    "z": sd["imu_gravity_z"] + random.gauss(0, sd["imu_noise_stddev"]),
                },
                angular_velocity={"x": random.gauss(0, 0.05), "y": random.gauss(0, 0.05), "z": random.gauss(0, 0.05)},
            ),
            battery=battery,
            temperature=temperature,
            voltage={
                "main": sd["voltage_main"] + random.gauss(0, 0.5),
                "logic": sd["voltage_logic"] + random.gauss(0, 0.1),
            },
            pressure={
                "foot_left": sd["pressure_baseline"] + random.gauss(0, sd["pressure_noise_stddev"]),
                "foot_right": sd["pressure_baseline"] + random.gauss(0, sd["pressure_noise_stddev"]),
            },
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
            injected_at=datetime.now(timezone.utc),
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

    async def start_gradual_fault(
        self,
        fault_type: str,
        joint_id: str,
        ramp_duration: float = 30.0,
        target_temp_increase: float = 30.0,
    ) -> dict:
        """启动一个随时间 ramp up 的渐进式故障（Demo 模式专用）。"""
        from app.services.simulation.fault_scenarios import GradualFault  # noqa: PLC0415 — 惰性导入规避循环依赖
        gf = GradualFault(
            fault_type=fault_type,
            joint_id=joint_id,
            ramp_duration=ramp_duration,
            target_temp_increase=target_temp_increase,
        )
        self._gradual_faults.append(gf)
        return {"status": "started", "fault_type": fault_type, "joint_id": joint_id}

    async def reset_gradual_faults(self) -> dict:
        """清除所有渐进式故障并重置激活故障列表。"""
        self._gradual_faults.clear()
        self._active_faults.clear()
        self._frozen_joint_positions.clear()
        return {"status": "reset"}

    async def apply_maintenance_action(
        self,
        action_type: str,
        target_joint: Optional[str] = None,
    ) -> bool:
        """应用维保动作，供 SimulationExecutor 预执行方案验证。"""
        if not self._connected:
            raise ConnectionError("Adapter not connected")

        if action_type == "clear_fault":
            self._active_faults.clear()
            self._frozen_joint_positions.clear()
            return True

        if action_type == "emergency_stop":
            self._emergency_stopped = True
            return True

        if action_type == "resume_operation":
            self._emergency_stopped = False
            return True

        if action_type == "reset_joint":
            if target_joint:
                self._frozen_joint_positions.pop(target_joint, None)
            else:
                self._frozen_joint_positions.clear()
            return True

        if action_type == "cool_down":
            self._active_faults = [code for code in self._active_faults if code != "E001_OVERHEAT"]
            return True

        if action_type == "recharge_battery":
            self._battery_level_override = 100.0
            self._active_faults = [code for code in self._active_faults if code != "E003_VOLTAGE_DROP"]
            return True

        if action_type == "stabilize_sensor":
            self._active_faults = [code for code in self._active_faults if code != "E004_SENSOR_FAILURE"]
            return True

        if action_type == "tighten_joint":
            self._active_faults = [code for code in self._active_faults if code != "E005_JOINT_LOOSE"]
            return True

        return False

    async def get_active_faults(self) -> List[str]:
        """获取活动故障列表"""
        return self._active_faults.copy()
