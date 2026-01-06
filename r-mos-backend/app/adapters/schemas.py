"""
机器人适配器数据模型定义（V2.2补充版）
所有Adapter返回的数据必须符合这些Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime
from enum import Enum


class RobotStatus(str, Enum):
    """机器人运行状态"""
    OFFLINE = "offline"
    ONLINE = "online"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class JointState(BaseModel):
    """关节状态
    
    所有角度单位：弧度（radians）
    所有速度单位：弧度/秒（rad/s）
    所有扭矩单位：牛·米（N·m）
    """
    joint_id: str = Field(..., description="关节唯一标识，如 'knee_right'")
    position: float = Field(..., description="当前位置（弧度）")
    velocity: float = Field(..., description="当前速度（弧度/秒）")
    torque: Optional[float] = Field(None, description="当前扭矩（牛·米）")
    current: Optional[float] = Field(None, description="电机电流（安培）")
    temperature: Optional[float] = Field(None, description="关节温度（摄氏度）")
    error_code: Optional[str] = Field(None, description="错误码（如有）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "joint_id": "knee_right",
                "position": 1.57,
                "velocity": 0.1,
                "torque": 5.2,
                "current": 2.3,
                "temperature": 45.0,
                "error_code": None
            }
        }


class IMUData(BaseModel):
    """惯性测量单元数据"""
    acceleration: Dict[str, float] = Field(
        ..., 
        description="加速度 (m/s²)，格式: {'x': 0.0, 'y': 0.0, 'z': 9.8}"
    )
    angular_velocity: Dict[str, float] = Field(
        ...,
        description="角速度 (rad/s)，格式: {'x': 0.0, 'y': 0.0, 'z': 0.0}"
    )
    orientation: Optional[Dict[str, float]] = Field(
        None,
        description="姿态四元数，格式: {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0}"
    )


class SensorData(BaseModel):
    """传感器数据集合"""
    imu: Optional[IMUData] = Field(None, description="IMU数据")
    battery: Optional[float] = Field(None, ge=0, le=100, description="电池电量（%）")
    temperature: Optional[float] = Field(None, description="核心温度（℃）")
    voltage: Optional[Dict[str, float]] = Field(None, description="各模块电压（V）")
    pressure: Optional[Dict[str, float]] = Field(None, description="压力传感器（Pa）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "imu": {
                    "acceleration": {"x": 0.0, "y": 0.0, "z": 9.8},
                    "angular_velocity": {"x": 0.0, "y": 0.0, "z": 0.0}
                },
                "battery": 88.5,
                "temperature": 45.2,
                "voltage": {"main": 24.0, "logic": 5.0}
            }
        }


class RobotInfo(BaseModel):
    """机器人基础信息"""
    robot_id: str = Field(..., description="机器人唯一标识")
    model: str = Field(..., description="机器人型号")
    firmware_version: str = Field(..., description="固件版本")
    runtime_status: RobotStatus = Field(..., description="运行状态")
    last_update: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")


class PartDefinition(BaseModel):
    """部件定义"""
    id: str = Field(..., description="部件唯一标识")
    name: str = Field(..., description="部件显示名称")
    type: str = Field(..., description="部件类型：joint/sensor/power_module")


class RobotStructure(BaseModel):
    """机器人结构描述"""
    joints: List[PartDefinition] = Field(..., description="关节列表")
    sensors: List[PartDefinition] = Field(..., description="传感器列表")
    power_modules: List[PartDefinition] = Field(..., description="电源模块列表")


class FaultInjectionResult(BaseModel):
    """故障注入结果"""
    success: bool = Field(..., description="是否成功")
    fault_code: str = Field(..., description="故障代码")
    target_part: str = Field(..., description="目标部件")
    severity: str = Field(..., description="严重程度")
    injected_at: datetime = Field(default_factory=datetime.utcnow, description="注入时间")
    message: Optional[str] = Field(None, description="附加信息")


# ===== V2.2补充：WebSocket消息Schema =====

class TelemetryPayload(BaseModel):
    """遥测数据载荷（V2.2新增）"""
    joints: List[JointState] = Field(..., description="所有关节状态")
    sensors: SensorData = Field(..., description="传感器数据")
    active_faults: List[str] = Field(..., description="当前活动故障列表")


class TelemetryMessage(BaseModel):
    """WebSocket遥测消息（V2.2完整定义）
    
    ⚠️ 强制约束：
    - 前后端必须严格遵循此Schema
    - type字段固定为'telemetry'
    - payload包含joints、sensors、active_faults三个字段
    - 推送频率：5Hz（200ms间隔）
    """
    type: Literal["telemetry"] = Field(default="telemetry", description="消息类型（固定值）")
    timestamp: str = Field(..., description="ISO 8601格式时间戳")
    payload: TelemetryPayload = Field(..., description="遥测数据载荷")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "telemetry",
                "timestamp": "2026-01-02T15:30:45.123Z",
                "payload": {
                    "joints": [
                        {
                            "joint_id": "knee_right",
                            "position": 1.57,
                            "velocity": 0.1,
                            "torque": 5.2,
                            "current": 2.3,
                            "temperature": 45.0,
                            "error_code": None
                        }
                    ],
                    "sensors": {
                        "imu": {
                            "acceleration": {"x": 0.0, "y": 0.0, "z": 9.8},
                            "angular_velocity": {"x": 0.0, "y": 0.0, "z": 0.0}
                        },
                        "battery": 88.5,
                        "temperature": 42.3,
                        "voltage": {"main": 24.0, "logic": 5.0}
                    },
                    "active_faults": ["E001_OVERHEAT"]
                }
            }
        }
