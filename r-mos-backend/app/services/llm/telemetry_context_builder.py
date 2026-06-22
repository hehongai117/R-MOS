"""
TelemetryContextBuilder - P1-2
将原始遥测数据转换为语义上下文，用于 LLM 诊断
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone

from app.adapters.schemas import JointState, SensorData


@dataclass
class AnomalyDetection:
    """异常检测结果"""
    anomaly_type: str  # OVERHEAT, STALL, VOLTAGE_DROP, SENSOR_FAILURE, JOINT_LOOSE
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 - 1.0
    affected_parts: list[str]
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetryContext:
    """语义化遥测上下文"""
    timestamp: str
    robot_status: str  # NORMAL, WARNING, ERROR, CRITICAL

    # 关节摘要
    joint_count: int
    anomaly_joints: list[dict]  # [{joint_id, position, velocity, torque, temperature, error}]

    # 传感器摘要
    battery_level: float
    core_temperature: float
    voltage_status: str  # NORMAL, LOW, CRITICAL

    # 异常列表
    anomalies: list[AnomalyDetection]
    fault_hints: list[str] = field(default_factory=list)

    # 原始数据摘要（用于调试）
    raw_summary: dict[str, Any] = field(default_factory=dict)

    def to_context_block(self) -> dict:
        """转换为 PromptTemplateEngine 的 ContextBlock 格式"""
        return {
            "robot_status": self.robot_status,
            "fault_hints": self.fault_hints,
            "joint_summary": {
                "total": self.joint_count,
                "anomalies": len(self.anomaly_joints)
            },
            "battery": self.battery_level,
            "temperature": self.core_temperature,
            "voltage": self.voltage_status,
            "anomalies": [
                {
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "confidence": a.confidence,
                    "parts": a.affected_parts,
                    "description": a.description
                }
                for a in self.anomalies
            ]
        }


class TelemetryContextBuilder:
    """
    遥测上下文构建器

    功能：
    1. 将原始 JointState + SensorData 转换为语义上下文
    2. 基于阈值检测异常（与 MockAdapter 故障注入参数对齐）
    3. 可选：调用 LLM 生成自然语言描述

    阈值配置（与 mock.py 的 _fault_effects 对齐）：
    - OVERHEAT: temperature > 70°C
    - STALL: velocity == 0 且 position_frozen
    - VOLTAGE_DROP: battery < 50%
    - SENSOR_FAILURE: temperature 异常波动
    - JOINT_LOOSE: position_noise > 0.3
    """

    # 阈值配置（与 mock.py _fault_effects 对齐）
    THRESHOLDS = {
        "OVERHEAT": {
            "temperature_high": 70.0,  # E001_OVERHEAT 触发温度
            "temperature_warning": 60.0,
        },
        "STALL": {
            "velocity_zero": 0.0,
            "velocity_threshold": 0.01,  # 小于此值视为静止
            "torque_drop_threshold": 0.3,
        },
        "VOLTAGE_DROP": {
            "battery_low": 50.0,  # E003_VOLTAGE_DROP 阈值
            "battery_warning": 30.0,
        },
        "SENSOR_FAILURE": {
            "temperature_noise_std": 10.0,  # E004_SENSOR_FAILURE 噪声标准差
        },
        "JOINT_LOOSE": {
            "position_noise_threshold": 0.3,  # E005_JOINT_LOOSE 噪声阈值
        }
    }

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        knowledge_hub: Optional[Any] = None,
    ):
        """
        初始化构建器

        Args:
            llm_router: LLM 路由器（可选，用于生成自然语言描述）
            knowledge_hub: 知识中枢（可选，用于检索相关知识）
        """
        self.llm_router = llm_router
        self.knowledge_hub = knowledge_hub

    def build(
        self,
        joint_states: list[Any],
        sensor_data: Any,
    ) -> TelemetryContext:
        """
        构建语义化遥测上下文

        Args:
            joint_states: 关节状态列表
            sensor_data: 传感器数据

        Returns:
            TelemetryContext: 语义化上下文
        """
        # 1. 检测关节异常
        anomaly_joints = self._detect_joint_anomalies(joint_states)
        joint_anomalies = self._normalize_joint_anomalies(anomaly_joints)

        # 2. 检测传感器异常
        sensor_anomalies = self._detect_sensor_anomalies(sensor_data)

        # 3. 合并所有异常
        all_anomalies = joint_anomalies + sensor_anomalies

        # 4. 确定整体状态
        robot_status = self._determine_robot_status(all_anomalies)

        # 5. 电压状态
        voltage_status = self._determine_voltage_status(sensor_data)

        # 6. 构建上下文
        context = TelemetryContext(
            timestamp=datetime.now(timezone.utc).isoformat(),
            robot_status=robot_status,
            joint_count=len(joint_states),
            anomaly_joints=anomaly_joints,
            battery_level=sensor_data.battery or 0.0,
            core_temperature=sensor_data.temperature or 0.0,
            voltage_status=voltage_status,
            anomalies=all_anomalies,
            raw_summary=self._create_raw_summary(joint_states, sensor_data)
        )

        return context

    def build_from_payload(self, telemetry_payload: dict[str, Any]) -> TelemetryContext:
        """从标准 telemetry payload 字典构建上下文。"""
        joints_raw = telemetry_payload.get("joints", [])
        sensor_raw = telemetry_payload.get("sensors", {})
        active_faults = [fault for fault in telemetry_payload.get("active_faults", []) if fault]
        joint_states = [
            joint if isinstance(joint, JointState) else JointState.model_validate(joint)
            for joint in joints_raw
        ]
        sensor_data = sensor_raw if isinstance(sensor_raw, SensorData) else SensorData.model_validate(sensor_raw)
        context = self.build(joint_states=joint_states, sensor_data=sensor_data)
        if active_faults:
            context.fault_hints = active_faults
            context.raw_summary["active_faults"] = active_faults
        return context

    def _detect_joint_anomalies(self, joint_states: list[Any]) -> list[dict]:
        """检测关节异常"""
        anomalies = []
        thresholds = self.THRESHOLDS

        for joint in joint_states:
            joint_anomaly = {
                "joint_id": joint.joint_id,
                "position": joint.position,
                "velocity": joint.velocity,
                "torque": joint.torque,
                "temperature": joint.temperature,
                "error_code": joint.error_code,
                "anomalies": []
            }

            # 检查温度异常 (OVERHEAT)
            if joint.temperature and joint.temperature > thresholds["OVERHEAT"]["temperature_high"]:
                joint_anomaly["anomalies"].append({
                    "type": "OVERHEAT",
                    "severity": "critical" if joint.temperature > 80 else "high",
                    "value": joint.temperature
                })
            elif joint.temperature and joint.temperature > thresholds["OVERHEAT"]["temperature_warning"]:
                joint_anomaly["anomalies"].append({
                    "type": "OVERHEAT",
                    "severity": "medium",
                    "value": joint.temperature
                })

            # 检查堵转 (STALL)
            # 仅在速度接近 0 且伴随明显扭矩异常或明确错误码时判为堵转，
            # 避免把正常静止状态误报为 STALL。
            has_stall_signal = (
                joint.velocity is not None
                and abs(joint.velocity) < thresholds["STALL"]["velocity_threshold"]
                and (
                    (joint.torque is not None and joint.torque <= thresholds["STALL"]["torque_drop_threshold"])
                    or ("E002" in str(joint.error_code))
                )
            )
            if has_stall_signal:
                joint_anomaly["anomalies"].append({
                    "type": "STALL",
                    "severity": "high",
                    "value": joint.velocity
                })

            # 检查错误码
            if joint.error_code:
                joint_anomaly["anomalies"].append({
                    "type": "ERROR_CODE",
                    "severity": "critical",
                    "value": joint.error_code
                })

            # 如果有关联异常，加入列表
            if joint_anomaly["anomalies"]:
                anomalies.append(joint_anomaly)

        return anomalies

    def _detect_sensor_anomalies(self, sensor_data: Any) -> list[AnomalyDetection]:
        """检测传感器异常"""
        anomalies = []
        thresholds = self.THRESHOLDS

        # 检查电池 (VOLTAGE_DROP)
        if sensor_data.battery is not None:
            if sensor_data.battery < thresholds["VOLTAGE_DROP"]["battery_low"]:
                severity = "critical" if sensor_data.battery < thresholds["VOLTAGE_DROP"]["battery_warning"] else "medium"
                anomalies.append(AnomalyDetection(
                    anomaly_type="VOLTAGE_DROP",
                    severity=severity,
                    confidence=0.95,
                    affected_parts=["battery"],
                    description=f"电池电量过低: {sensor_data.battery:.1f}%",
                    evidence={"battery": sensor_data.battery}
                ))

        # 检查核心温度 (OVERHEAT)
        if sensor_data.temperature is not None:
            if sensor_data.temperature > thresholds["OVERHEAT"]["temperature_high"]:
                anomalies.append(AnomalyDetection(
                    anomaly_type="OVERHEAT",
                    severity="critical",
                    confidence=0.95,
                    affected_parts=["core"],
                    description=f"核心温度过高: {sensor_data.temperature:.1f}°C",
                    evidence={"temperature": sensor_data.temperature}
                ))

        # 检查电压异常
        if sensor_data.voltage:
            main_voltage = sensor_data.voltage.get("main", 24.0)
            if main_voltage < 20.0:  # 低于 20V 视为异常
                anomalies.append(AnomalyDetection(
                    anomaly_type="VOLTAGE_DROP",
                    severity="high",
                    confidence=0.9,
                    affected_parts=["power_module"],
                    description=f"主电压过低: {main_voltage:.1f}V",
                    evidence={"voltage": main_voltage}
                ))

        return anomalies

    def _normalize_joint_anomalies(self, anomaly_joints: list[dict]) -> list[AnomalyDetection]:
        """把关节异常摘要转换为统一的 AnomalyDetection 结构。"""
        normalized: list[AnomalyDetection] = []

        for joint in anomaly_joints:
            for anomaly in joint.get("anomalies", []):
                normalized.append(
                    AnomalyDetection(
                        anomaly_type=anomaly.get("type", "UNKNOWN"),
                        severity=anomaly.get("severity", "medium"),
                        confidence=0.95 if anomaly.get("severity") in {"critical", "high"} else 0.8,
                        affected_parts=[joint.get("joint_id", "unknown")],
                        description=(
                            f"关节 {joint.get('joint_id', 'unknown')} 出现 {anomaly.get('type', 'UNKNOWN')} "
                            f"异常，观测值={anomaly.get('value', 'N/A')}"
                        ),
                        evidence={
                            "joint_id": joint.get("joint_id"),
                            "value": anomaly.get("value"),
                            "error_code": joint.get("error_code"),
                        },
                    )
                )

        return normalized

    def _determine_robot_status(self, anomalies: list) -> str:
        """确定机器人整体状态"""
        if not anomalies:
            return "NORMAL"

        # 检查是否有 critical 级别异常
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                for a in anomaly.get("anomalies", []):
                    if a.get("severity") == "critical":
                        return "CRITICAL"
            elif hasattr(anomaly, "severity") and anomaly.severity == "critical":
                return "CRITICAL"

        # 检查是否有 high 级别异常
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                for a in anomaly.get("anomalies", []):
                    if a.get("severity") == "high":
                        return "ERROR"
            elif hasattr(anomaly, "severity") and anomaly.severity == "high":
                return "ERROR"

        # 检查是否有 medium 级别异常
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                for a in anomaly.get("anomalies", []):
                    if a.get("severity") == "medium":
                        return "WARNING"
            elif hasattr(anomaly, "severity") and anomaly.severity == "medium":
                return "WARNING"

        return "NORMAL"

    def _determine_voltage_status(self, sensor_data: Any) -> str:
        """确定电压状态"""
        if sensor_data.battery is None:
            return "UNKNOWN"

        if sensor_data.battery < 30.0:
            return "CRITICAL"
        elif sensor_data.battery < 50.0:
            return "LOW"
        elif sensor_data.battery < 80.0:
            return "WARNING"
        return "NORMAL"

    def _create_raw_summary(
        self,
        joint_states: list[Any],
        sensor_data: Any
    ) -> dict:
        """创建原始数据摘要（用于调试）"""
        temperatures = [j.temperature for j in joint_states if j.temperature]
        velocities = [j.velocity for j in joint_states if j.velocity is not None]

        return {
            "joint_count": len(joint_states),
            "avg_temperature": sum(temperatures) / len(temperatures) if temperatures else 0,
            "max_temperature": max(temperatures) if temperatures else 0,
            "avg_velocity": sum(velocities) / len(velocities) if velocities else 0,
            "battery": sensor_data.battery,
            "sensor_temperature": sensor_data.temperature,
        }

    async def build_with_llm_description(
        self,
        joint_states: list[Any],
        sensor_data: Any,
        use_llm: bool = True,
    ) -> tuple[TelemetryContext, Optional[str]]:
        """
        构建上下文并可选地生成 LLM 描述

        Args:
            joint_states: 关节状态列表
            sensor_data: 传感器数据
            use_llm: 是否使用 LLM 生成描述

        Returns:
            (TelemetryContext, llm_description): 上下文和自然语言描述
        """
        context = self.build(joint_states, sensor_data)

        if not use_llm or not self.llm_router:
            return context, None

        # 生成自然语言描述
        prompt = self._generate_description_prompt(context)

        try:
            from app.services.llm.router import LLMProvider
            from app.core.config import settings

            response = await self.llm_router.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_ADVANCED,
                temperature=0.3,
                max_tokens=500,
            )

            return context, response.content
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM description generation failed: {e}")
            return context, None

    def _generate_description_prompt(self, context: TelemetryContext) -> str:
        """生成描述提示词"""
        anomalies_desc = []
        for a in context.anomaly_joints:
            for an in a.get("anomalies", []):
                anomalies_desc.append(
                    f"- {a['joint_id']}: {an['type']} ({an.get('value', 'N/A')})"
                )

        prompt = f"""请用一句话描述机器人当前状态：

状态: {context.robot_status}
电池: {context.battery_level:.1f}%
温度: {context.core_temperature:.1f}°C

异常关节:
{chr(10).join(anomalies_desc) if anomalies_desc else "无"}

请直接输出描述，不要有额外解释。"""
        return prompt


# 全局实例
telemetry_builder = TelemetryContextBuilder()
