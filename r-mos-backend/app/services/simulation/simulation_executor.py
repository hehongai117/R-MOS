from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.adapters.mock import MockRobotAdapter
from app.services.diagnosis.schemas import MaintenanceAction, MaintenancePlan


@dataclass
class VerificationResult:
    success: bool
    plan_id: str
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    delta_summary: dict[str, str]
    verdict: str
    failed_steps: list[str] = field(default_factory=list)


class SimulationExecutor:
    """在 MockAdapter 中预执行维保方案，验证方案是否改善故障状态。"""

    async def execute_and_verify(
        self,
        plan: MaintenancePlan,
        adapter: MockRobotAdapter,
    ) -> VerificationResult:
        before_state = await self._capture_state(adapter)
        failed_steps: list[str] = []

        for action in plan.actions:
            adapter_actions = self._resolve_adapter_actions(plan, action)
            for adapter_action in adapter_actions:
                ok = await adapter.apply_maintenance_action(
                    adapter_action["action_type"],
                    target_joint=adapter_action.get("target_joint"),
                )
                if not ok:
                    failed_steps.append(action.action_id)
                    break
            await asyncio.sleep(0)

        after_state = await self._capture_state(adapter)
        delta_summary = self._compute_delta(before_state, after_state)
        success = self._evaluate_success(before_state, after_state, failed_steps)

        return VerificationResult(
            success=success,
            plan_id=plan.plan_id,
            before_state=before_state,
            after_state=after_state,
            delta_summary=delta_summary,
            verdict=self._build_verdict(success, before_state, after_state),
            failed_steps=failed_steps,
        )

    async def _capture_state(self, adapter: MockRobotAdapter) -> dict[str, Any]:
        joints = await adapter.get_joint_states()
        sensors = await adapter.get_sensor_data()
        faults = await adapter.get_active_faults()

        return {
            "fault_count": len(faults),
            "active_faults": faults,
            "battery": sensors.battery,
            "temperature": sensors.temperature,
            "joints": {
                joint.joint_id: {
                    "position": joint.position,
                    "velocity": joint.velocity,
                    "torque": joint.torque,
                    "temperature": joint.temperature,
                    "error_code": joint.error_code,
                }
                for joint in joints
            },
        }

    def _resolve_adapter_actions(
        self,
        plan: MaintenancePlan,
        action: MaintenanceAction,
    ) -> list[dict[str, str]]:
        if "停机" in action.description or "急停" in action.description:
            return [{"action_type": "emergency_stop"}]

        if plan.fault_code == "E001_OVERHEAT" and action.action_type in {"CLEAN", "ADJUST"}:
            return [{"action_type": "cool_down"}, {"action_type": "clear_fault"}]

        if plan.fault_code == "E002_STALL" and action.action_type in {"CALIBRATE", "ADJUST"}:
            return [
                {"action_type": "reset_joint", "target_joint": action.target_part.split(",")[0].strip()},
                {"action_type": "clear_fault"},
                {"action_type": "resume_operation"},
            ]

        if plan.fault_code == "E003_VOLTAGE_DROP" and action.action_type == "REPLACE":
            return [{"action_type": "recharge_battery"}, {"action_type": "clear_fault"}]

        if plan.fault_code == "E004_SENSOR_FAILURE" and action.action_type in {"CALIBRATE", "REPLACE"}:
            return [{"action_type": "stabilize_sensor"}, {"action_type": "clear_fault"}]

        if plan.fault_code == "E005_JOINT_LOOSE" and action.action_type in {"ADJUST", "CALIBRATE"}:
            return [{"action_type": "tighten_joint"}, {"action_type": "clear_fault"}]

        return []

    def _compute_delta(self, before_state: dict[str, Any], after_state: dict[str, Any]) -> dict[str, str]:
        delta: dict[str, str] = {}
        if before_state["fault_count"] != after_state["fault_count"]:
            delta["fault_count"] = f"{before_state['fault_count']} -> {after_state['fault_count']}"
        if before_state["battery"] != after_state["battery"]:
            delta["battery"] = f"{before_state['battery']} -> {after_state['battery']}"

        for joint_id, before_joint in before_state["joints"].items():
            after_joint = after_state["joints"].get(joint_id, {})
            if before_joint.get("velocity") != after_joint.get("velocity"):
                delta[f"{joint_id}.velocity"] = f"{before_joint.get('velocity')} -> {after_joint.get('velocity')}"
                continue
            if before_joint.get("temperature") != after_joint.get("temperature"):
                delta[f"{joint_id}.temperature"] = (
                    f"{before_joint.get('temperature')} -> {after_joint.get('temperature')}"
                )
                continue

        return delta

    def _evaluate_success(
        self,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        failed_steps: list[str],
    ) -> bool:
        if failed_steps:
            return False
        if after_state["fault_count"] < before_state["fault_count"]:
            return True
        return False

    def _build_verdict(
        self,
        success: bool,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
    ) -> str:
        if success:
            return (
                f"验证通过：故障数从 {before_state['fault_count']} 降至 {after_state['fault_count']}。"
            )
        return "验证未通过：方案执行后未观察到明确改善。"
