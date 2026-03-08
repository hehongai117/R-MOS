"""
FaultDiagnosisEngine - P1-2
故障诊断引擎 - 基于语义上下文的故障推理
"""
import json
import uuid
import logging
from typing import Optional, Any

from app.services.llm.telemetry_context_builder import TelemetryContext
from app.services.diagnosis.schemas import (
    DiagnosisResult,
    FaultHypothesis,
    FaultCode,
    Severity,
)

logger = logging.getLogger(__name__)

ANOMALY_TO_FAULT_CODE = {
    "OVERHEAT": "E001_OVERHEAT",
    "STALL": "E002_STALL",
    "VOLTAGE_DROP": "E003_VOLTAGE_DROP",
    "SENSOR_FAILURE": "E004_SENSOR_FAILURE",
    "JOINT_LOOSE": "E005_JOINT_LOOSE",
}


class FaultDiagnosisEngine:
    """
    故障诊断引擎

    功能：
    1. 基于 TelemetryContext 进行多假设推理
    2. 调用 LLM 生成诊断结论
    3. 支持 JSON 解析容错
    4. 提供 fallback 诊断逻辑

    故障类型映射（与 MockAdapter 的故障代码对齐）：
    - E001_OVERHEAT: 温度过高
    - E002_STALL: 堵转
    - E003_VOLTAGE_DROP: 电压跌落
    - E004_SENSOR_FAILURE: 传感器故障
    - E005_JOINT_LOOSE: 关节松动
    """

    # 故障代码到名称的映射
    FAULT_NAMES = {
        "E001_OVERHEAT": "温度过高",
        "E002_STALL": "堵转",
        "E003_VOLTAGE_DROP": "电压跌落",
        "E004_SENSOR_FAILURE": "传感器故障",
        "E005_JOINT_LOOSE": "关节松动",
        "UNKNOWN": "未知故障",
    }

    # 故障代码到可能原因的映射
    FAULT_CAUSES = {
        "E001_OVERHEAT": [
            "长时间高负载运行",
            "散热系统故障",
            "环境温度过高",
            "润滑油不足",
            "电机内部故障",
        ],
        "E002_STALL": [
            "机械卡滞",
            "负载过大",
            "电机驱动器故障",
            "传动机构损坏",
            "位置传感器异常",
        ],
        "E003_VOLTAGE_DROP": [
            "电池老化",
            "电源模块故障",
            "线路接触不良",
            "负载过大",
            "充电系统故障",
        ],
        "E004_SENSOR_FAILURE": [
            "传感器损坏",
            "传感器线路松动",
            "电磁干扰",
            "传感器校准失效",
            "环境干扰",
        ],
        "E005_JOINT_LOOSE": [
            "固定螺丝松动",
            "关节轴承磨损",
            "连接件损坏",
            "长期振动",
            "维护不到位",
        ],
    }

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, llm_router: Optional[Any] = None):
        """
        初始化诊断引擎

        Args:
            llm_router: LLM 路由器（用于 LLM 诊断）
        """
        self.llm_router = llm_router

    async def diagnose(
        self,
        telemetry_context: TelemetryContext,
        use_llm: bool = True,
    ) -> DiagnosisResult:
        """
        执行故障诊断

        Args:
            telemetry_context: 语义化遥测上下文
            use_llm: 是否使用 LLM 诊断

        Returns:
            DiagnosisResult: 诊断结果
        """
        # 1. 首先进行规则基础诊断
        rule_based_result = self._rule_based_diagnosis(telemetry_context)

        # 2. 如果没有检测到异常，返回正常
        if not telemetry_context.anomalies and not telemetry_context.anomaly_joints:
            return DiagnosisResult(
                success=True,
                primary_hypothesis=FaultHypothesis(
                    fault_code="NORMAL",
                    fault_name="正常",
                    confidence=1.0,
                    affected_parts=[],
                    possible_causes=[],
                    evidence={},
                ),
                reasoning="未检测到异常，机器人状态正常",
                recommended_actions=[],
            )

        # 3. 如果无法使用 LLM，返回规则诊断结果
        if not use_llm or not self.llm_router:
            return rule_based_result

        # 4. 尝试 LLM 诊断
        try:
            llm_result = await self._llm_diagnosis(telemetry_context)

            # 5. 合并结果：优先使用 LLM 结果
            if llm_result.success:
                # 检查是否需要上报
                requires_supervisor = self._check_requires_supervisor(llm_result)

                # 如果 LLM 结果置信度低于阈值，合并规则结果
                if llm_result.primary_hypothesis and \
                   llm_result.primary_hypothesis.confidence < self.CONFIDENCE_THRESHOLD:
                    llm_result.alternative_hypotheses.extend(rule_based_result.alternative_hypotheses)

                llm_result.requires_supervisor = requires_supervisor
                return llm_result

        except Exception as e:
            logger.warning(f"LLM diagnosis failed: {e}")

        # 6. LLM 失败时使用规则诊断结果
        return rule_based_result

    def _rule_based_diagnosis(self, context: TelemetryContext) -> DiagnosisResult:
        """
        基于规则的诊断

        根据异常检测结果构建故障假设
        """
        hypotheses = []

        # 处理关节异常
        for joint_anomaly in context.anomaly_joints:
            for anomaly in joint_anomaly.get("anomalies", []):
                anomaly_type = anomaly.get("type", "")
                severity = anomaly.get("severity", "medium")

                if anomaly_type == "OVERHEAT":
                    fault_code = "E001_OVERHEAT"
                    confidence = 0.95 if severity == "critical" else 0.8
                elif anomaly_type == "STALL":
                    fault_code = "E002_STALL"
                    confidence = 0.95 if severity == "critical" else 0.85
                elif anomaly_type == "ERROR_CODE":
                    # 从错误码推断故障类型
                    error_value = anomaly.get("value", "")
                    if "E001" in str(error_value):
                        fault_code = "E001_OVERHEAT"
                        confidence = 0.95
                    elif "E002" in str(error_value):
                        fault_code = "E002_STALL"
                        confidence = 0.95
                    else:
                        fault_code = "UNKNOWN"
                        confidence = 0.5
                else:
                    fault_code = "UNKNOWN"
                    confidence = 0.3

                if fault_code != "UNKNOWN":
                    hypotheses.append(FaultHypothesis(
                        fault_code=fault_code,
                        fault_name=self.FAULT_NAMES.get(fault_code, "未知"),
                        confidence=confidence,
                        affected_parts=[joint_anomaly["joint_id"]],
                        possible_causes=self.FAULT_CAUSES.get(fault_code, []),
                        evidence={
                            "joint_id": joint_anomaly["joint_id"],
                            "anomaly_type": anomaly_type,
                            "severity": severity,
                            "value": anomaly.get("value"),
                        },
                    ))

        # 处理传感器异常
        for anomaly in context.anomalies:
            if hasattr(anomaly, "anomaly_type"):
                fault_code = ANOMALY_TO_FAULT_CODE.get(anomaly.anomaly_type, "UNKNOWN")

                if fault_code != "UNKNOWN":
                    hypotheses.append(FaultHypothesis(
                        fault_code=fault_code,
                        fault_name=self.FAULT_NAMES.get(fault_code, "未知"),
                        confidence=anomaly.confidence,
                        affected_parts=anomaly.affected_parts,
                        possible_causes=self.FAULT_CAUSES.get(fault_code, []),
                        evidence=anomaly.evidence,
                    ))

        # 按置信度排序
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        # 构建结果
        if hypotheses:
            primary = hypotheses[0]
            alternatives = hypotheses[1:4] if len(hypotheses) > 1 else []

            return DiagnosisResult(
                success=True,
                primary_hypothesis=primary,
                alternative_hypotheses=alternatives,
                requires_supervisor=primary.confidence < self.CONFIDENCE_THRESHOLD,
                reasoning=f"基于规则诊断：检测到 {len(hypotheses)} 个可能的故障",
                recommended_actions=self._generate_recommended_actions(primary),
            )

        # 无法识别
        return DiagnosisResult(
            success=True,
            primary_hypothesis=FaultHypothesis(
                fault_code="UNKNOWN",
                fault_name="未知故障",
                confidence=0.3,
                affected_parts=[],
                possible_causes=["需要进一步检查"],
                evidence={},
            ),
            reasoning="规则诊断无法确定具体故障类型",
            recommended_actions=["请进行全面检查", "联系技术支持"],
        )

    async def _llm_diagnosis(self, context: TelemetryContext) -> DiagnosisResult:
        """
        LLM 诊断

        调用 LLM 进行多假设推理
        """
        from app.services.llm.router import LLMProvider

        # 构建提示词
        prompt = self._build_diagnosis_prompt(context)

        # 调用 LLM
        response = await self.llm_router.chat(
            messages=[
                {"role": "system", "content": "你是一个专业的机器人故障诊断专家。请根据提供的遥测数据，分析可能的故障原因。"},
                {"role": "user", "content": prompt}
            ],
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.3,
            max_tokens=1000,
        )

        # 解析 LLM 响应
        try:
            # 尝试解析 JSON
            diagnosis_data = json.loads(response.content)

            # 构建诊断结果
            hypotheses = []
            for h in diagnosis_data.get("hypotheses", []):
                hypotheses.append(FaultHypothesis(
                    fault_code=h.get("fault_code", "UNKNOWN"),
                    fault_name=h.get("fault_name", "未知"),
                    confidence=float(h.get("confidence", 0.5)),
                    affected_parts=h.get("affected_parts", []),
                    possible_causes=h.get("possible_causes", []),
                    evidence=h.get("evidence", {}),
                ))

            # 按置信度排序
            hypotheses.sort(key=lambda x: x.confidence, reverse=True)

            if hypotheses:
                return DiagnosisResult(
                    success=True,
                    primary_hypothesis=hypotheses[0],
                    alternative_hypotheses=hypotheses[1:4],
                    reasoning=diagnosis_data.get("reasoning", ""),
                    recommended_actions=self._normalize_recommended_actions(
                        diagnosis_data.get("recommended_actions", [])
                    ),
                )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # 尝试从文本中提取信息
            return self._parse_llm_text_response(response.content, context)

        # 无法解析
        return DiagnosisResult(
            success=False,
            error_message="LLM 响应格式无法解析",
        )

    def _build_diagnosis_prompt(self, context: TelemetryContext) -> str:
        """构建诊断提示词"""
        # 构建异常描述
        anomaly_parts = []

        for ja in context.anomaly_joints:
            joint_id = ja.get("joint_id", "unknown")
            for a in ja.get("anomalies", []):
                anomaly_parts.append(
                    f"- 关节 {joint_id}: {a.get('type', '未知')} (severity: {a.get('severity', 'unknown')})"
                )

        for a in context.anomalies:
            if hasattr(a, "anomaly_type"):
                anomaly_parts.append(
                    f"- 传感器: {a.anomaly_type} (confidence: {a.confidence})"
                )

        prompt = f"""请分析以下机器人遥测数据，诊断可能的故障。

机器人状态: {context.robot_status}
电池: {context.battery_level:.1f}%
核心温度: {context.core_temperature:.1f}°C

异常详情:
{chr(10).join(anomaly_parts) if anomaly_parts else "无"}

请以 JSON 格式返回诊断结果，格式如下：
{{
    "hypotheses": [
        {{
            "fault_code": "E001_OVERHEAT",
            "fault_name": "温度过高",
            "confidence": 0.85,
            "affected_parts": ["knee_right"],
            "possible_causes": ["长时间高负载运行", "散热系统故障"],
            "evidence": {{}}
        }}
    ],
    "reasoning": "推理过程...",
    "recommended_actions": ["操作1", "操作2"]
}}

请只返回 JSON，不要有其他内容。"""
        return prompt

    def _parse_llm_text_response(
        self,
        text: str,
        context: TelemetryContext,
    ) -> DiagnosisResult:
        """
        解析 LLM 文本响应

        当 JSON 解析失败时，尝试从文本中提取信息
        """
        text_lower = text.lower()

        # 尝试匹配故障类型
        fault_code = "UNKNOWN"
        confidence = 0.5

        if "过热" in text or "overheat" in text_lower:
            fault_code = "E001_OVERHEAT"
            confidence = 0.7
        elif "堵转" in text or "stall" in text_lower:
            fault_code = "E002_STALL"
            confidence = 0.7
        elif "电压" in text or "voltage" in text_lower or "电量" in text:
            fault_code = "E003_VOLTAGE_DROP"
            confidence = 0.7
        elif "传感器" in text or "sensor" in text_lower:
            fault_code = "E004_SENSOR_FAILURE"
            confidence = 0.6
        elif "松动" in text or "loose" in text_lower:
            fault_code = "E005_JOINT_LOOSE"
            confidence = 0.6

        return DiagnosisResult(
            success=True,
            primary_hypothesis=FaultHypothesis(
                fault_code=fault_code,
                fault_name=self.FAULT_NAMES.get(fault_code, "未知"),
                confidence=confidence,
                affected_parts=[a.get("joint_id", "") for a in context.anomaly_joints],
                possible_causes=self.FAULT_CAUSES.get(fault_code, []),
                evidence={"raw_text": text[:500]},
            ),
            reasoning=f"从文本响应中提取: {text[:200]}...",
            recommended_actions=self._generate_recommended_actions(
                FaultHypothesis(
                    fault_code=fault_code,
                    fault_name=self.FAULT_NAMES.get(fault_code, "未知"),
                    confidence=confidence,
                    affected_parts=[],
                    possible_causes=[],
                )
            ) if fault_code != "UNKNOWN" else [],
        )

    def _check_requires_supervisor(self, result: DiagnosisResult) -> bool:
        """
        检查是否需要上报

        当置信度低于阈值或故障严重时返回 True
        """
        if not result.primary_hypothesis:
            return False

        confidence = result.primary_hypothesis.confidence

        # 置信度低于阈值
        if confidence < self.CONFIDENCE_THRESHOLD:
            return True

        # 高严重程度的故障
        fault_code = result.primary_hypothesis.fault_code
        if fault_code in ["E001_OVERHEAT", "E002_STALL"]:
            # 这类故障可能需要监督
            if confidence < 0.9:
                return True

        return False

    def _generate_recommended_actions(
        self,
        hypothesis: FaultHypothesis,
    ) -> list[str]:
        """生成推荐操作"""
        fault_code = hypothesis.fault_code

        actions_map = {
            "E001_OVERHEAT": [
                "停止当前操作",
                "检查散热系统",
                "降低负载",
                "等待温度降低",
            ],
            "E002_STALL": [
                "停止运动",
                "检查机械卡滞",
                "检查电机驱动器",
                "尝试手动移动关节",
            ],
            "E003_VOLTAGE_DROP": [
                "检查电池电量",
                "检查电源模块",
                "检查线路连接",
                "考虑充电",
            ],
            "E004_SENSOR_FAILURE": [
                "检查传感器连接",
                "校准传感器",
                "更换传感器",
            ],
            "E005_JOINT_LOOSE": [
                "检查关节固定",
                "紧固螺丝",
                "检查轴承状态",
            ],
            "NORMAL": [
                "继续正常操作",
            ],
            "UNKNOWN": [
                "进行全面检查",
                "联系技术支持",
            ],
        }

        return actions_map.get(fault_code, actions_map["UNKNOWN"])

    def _normalize_recommended_actions(self, raw_actions: Any) -> list[str]:
        """把 LLM 输出的推荐动作规范化为字符串列表。"""
        if raw_actions is None:
            return []
        if isinstance(raw_actions, str):
            return [raw_actions]
        if isinstance(raw_actions, list):
            return [str(action) for action in raw_actions if str(action).strip()]
        return [str(raw_actions)]


# 全局实例
diagnosis_engine = FaultDiagnosisEngine()
