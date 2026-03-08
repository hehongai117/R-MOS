from __future__ import annotations

import pytest

from app.adapters.mock import MockRobotAdapter
from app.services.diagnosis.schemas import MaintenanceAction, MaintenancePlan
from app.services.simulation.simulation_executor import SimulationExecutor


def _overheat_plan() -> MaintenancePlan:
    return MaintenancePlan(
        success=True,
        plan_id="plan-overheat-001",
        fault_code="E001_OVERHEAT",
        fault_name="过热",
        actions=[
            MaintenanceAction(
                action_id="E001-A1",
                action_type="CHECK",
                target_part="knee_right",
                description="检查散热风扇状态",
                estimated_duration_minutes=5,
            ),
            MaintenanceAction(
                action_id="E001-A2",
                action_type="CLEAN",
                target_part="knee_right",
                description="清洁散热系统并降温",
                estimated_duration_minutes=15,
            ),
        ],
        total_duration_minutes=20,
        requires_supervisor=False,
        validation_required=True,
    )


def _stall_plan() -> MaintenancePlan:
    return MaintenancePlan(
        success=True,
        plan_id="plan-stall-001",
        fault_code="E002_STALL",
        fault_name="堵转",
        actions=[
            MaintenanceAction(
                action_id="E002-A1",
                action_type="CHECK",
                target_part="knee_right",
                description="检查关节是否有机械卡滞",
                estimated_duration_minutes=10,
            ),
            MaintenanceAction(
                action_id="E002-A2",
                action_type="CALIBRATE",
                target_part="knee_right",
                description="校准位置传感器并恢复运行",
                estimated_duration_minutes=20,
            ),
        ],
        total_duration_minutes=30,
        requires_supervisor=True,
        validation_required=True,
    )


@pytest.mark.asyncio
async def test_simulation_executor_verifies_stall_plan_success():
    adapter = MockRobotAdapter()
    await adapter.connect()
    await adapter.inject_fault(
        fault_code="E002_STALL",
        target_part="knee_right",
        severity="high",
    )

    executor = SimulationExecutor()
    result = await executor.execute_and_verify(_stall_plan(), adapter)

    assert result.success is True
    assert result.failed_steps == []
    assert result.before_state["fault_count"] == 1
    assert result.after_state["fault_count"] == 0
    assert "fault_count" in result.delta_summary


@pytest.mark.asyncio
async def test_overheat_plan_reduces_temperature_signal():
    adapter = MockRobotAdapter()
    await adapter.connect()
    await adapter.inject_fault(
        fault_code="E001_OVERHEAT",
        target_part="knee_right",
        severity="high",
    )

    executor = SimulationExecutor()
    result = await executor.execute_and_verify(_overheat_plan(), adapter)

    assert result.success is True
    assert result.after_state["fault_count"] == 0
    assert (
        result.after_state["joints"]["knee_right"]["temperature"]
        < result.before_state["joints"]["knee_right"]["temperature"]
    )
    assert "knee_right.temperature" in result.delta_summary


@pytest.mark.asyncio
async def test_failed_steps_are_recorded_when_action_returns_false(monkeypatch: pytest.MonkeyPatch):
    adapter = MockRobotAdapter()
    await adapter.connect()
    await adapter.inject_fault(
        fault_code="E001_OVERHEAT",
        target_part="knee_right",
        severity="high",
    )

    original_apply = adapter.apply_maintenance_action

    async def _fail_cool_down(action_type: str, target_joint: str | None = None) -> bool:
        if action_type == "cool_down":
            return False
        return await original_apply(action_type, target_joint=target_joint)

    monkeypatch.setattr(adapter, "apply_maintenance_action", _fail_cool_down)

    executor = SimulationExecutor()
    result = await executor.execute_and_verify(_overheat_plan(), adapter)

    assert result.success is False
    assert result.failed_steps == ["E001-A2"]
    assert result.verdict == "验证未通过：方案执行后未观察到明确改善。"
