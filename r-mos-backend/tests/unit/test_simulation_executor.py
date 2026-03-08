from __future__ import annotations

import pytest

from app.adapters.mock import MockRobotAdapter
from app.services.diagnosis.schemas import MaintenanceAction, MaintenancePlan
from app.services.simulation.simulation_executor import SimulationExecutor


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
