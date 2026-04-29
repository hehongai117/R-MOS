"""Fault diagnosis service — rule engine + LLM enhancement."""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.simulation.fault_scenarios import FAULT_SCENARIOS

logger = logging.getLogger(__name__)

# Thresholds for rule-based diagnosis
TEMP_ALERT_THRESHOLD = 70.0
VOLTAGE_LOW_THRESHOLD = 20.0
POSITION_ERROR_THRESHOLD = 0.10


class FaultDiagnosisService:
    """
    Diagnoses faults from telemetry data.

    Strategy: rule engine first (always runs), then LLM enhancement (optional).
    """

    async def diagnose(
        self,
        telemetry: dict[str, Any],
        knowledge_context: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Analyze telemetry and return diagnosis result.

        Returns dict with: success, fault_type, confidence, affected_joints,
        reasoning, recommended_sop, is_compound
        """
        # Step 1: Rule-based analysis
        rule_result = self._rule_based_diagnose(telemetry)

        # Step 2: LLM enhancement (non-blocking, best-effort)
        llm_reasoning = None
        if rule_result["fault_type"]:
            try:
                llm_reasoning = await self._llm_enhance(telemetry, rule_result, knowledge_context)
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")

        # Step 3: Merge
        if llm_reasoning:
            rule_result["reasoning"] = llm_reasoning
            rule_result["llm_enhanced"] = True
        else:
            rule_result["llm_enhanced"] = False

        return rule_result

    def _rule_based_diagnose(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        """Pure rule-based fault detection."""
        joints = telemetry.get("joints", [])
        sensors = telemetry.get("sensors", {})
        voltage = sensors.get("voltage", {}).get("main", 24.0)

        # Check voltage first (compound fault root cause)
        voltage_low = voltage < VOLTAGE_LOW_THRESHOLD

        # Check joints for temperature / position errors
        hot_joints = []
        loose_joints = []

        for joint in joints:
            temp = joint.get("temperature", 0)
            pos_error = joint.get("position_error", 0)

            if temp >= TEMP_ALERT_THRESHOLD:
                hot_joints.append(joint["joint_id"])
            if pos_error >= POSITION_ERROR_THRESHOLD:
                loose_joints.append(joint["joint_id"])

        # Decision tree
        if voltage_low and hot_joints:
            # Compound: voltage drop causing overheating
            return {
                "success": True,
                "fault_type": "E003_VOLTAGE_DROP",
                "confidence": 0.88,
                "affected_joints": hot_joints,
                "reasoning": f"电压跌落至{voltage}V导致多关节过热补偿",
                "recommended_sop": "sop-e003-e001-compound",
                "is_compound": True,
            }
        elif loose_joints:
            return {
                "success": True,
                "fault_type": "E005_LOOSE",
                "confidence": 0.85,
                "affected_joints": loose_joints,
                "reasoning": "关节位置偏差超限，疑似机械松动",
                "recommended_sop": "sop-e005-loose",
                "is_compound": False,
            }
        elif hot_joints:
            return {
                "success": True,
                "fault_type": "E001_OVERHEAT",
                "confidence": 0.90,
                "affected_joints": hot_joints,
                "reasoning": f"关节温度超过{TEMP_ALERT_THRESHOLD}°C阈值",
                "recommended_sop": "sop-e001-overheat",
                "is_compound": False,
            }
        else:
            return {
                "success": True,
                "fault_type": None,
                "confidence": 1.0,
                "affected_joints": [],
                "reasoning": "遥测数据正常，未检测到故障",
                "recommended_sop": None,
                "is_compound": False,
            }

    async def _llm_enhance(
        self,
        telemetry: dict[str, Any],
        rule_result: dict[str, Any],
        knowledge_context: Optional[list[str]],
    ) -> Optional[str]:
        """Enhance diagnosis with LLM-generated natural language reasoning."""
        from app.services.llm.router import llm_router

        fault_type = rule_result["fault_type"]
        affected = rule_result["affected_joints"]

        system_prompt = (
            "你是机器人维保诊断专家。根据遥测数据和初步诊断结果，"
            "生成简明的故障分析说明（3-5句话），包含可能原因和建议措施。"
        )
        user_content = (
            f"故障类型: {fault_type}\n"
            f"受影响关节: {affected}\n"
            f"遥测摘要: {telemetry}\n"
        )
        if knowledge_context:
            user_content += f"\n参考知识: {knowledge_context[:2]}"

        response = await llm_router.chat_with_fallback(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return response.content if response.content else None
