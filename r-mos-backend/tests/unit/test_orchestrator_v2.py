"""
OrchestratorV2 basic flow tests.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.diagnosis.schemas import DiagnosisResult, FaultHypothesis, MaintenanceAction, MaintenancePlan
from app.services.orchestrator_v2 import OrchestratorV2


@pytest.mark.asyncio
async def test_orchestrator_v2_process_request_and_idempotency_cache():
    orchestrator = OrchestratorV2()

    response1 = await orchestrator.process_request(
        user_id="u-1",
        message="读取知识",
        intent_classification="read-kb",
        idempotency_key="idem-001",
    )
    assert response1["success"] is True
    assert response1["from_cache"] is False
    assert response1["policy_decision"]["allowed"] is True

    response2 = await orchestrator.process_request(
        user_id="u-1",
        message="读取知识",
        intent_classification="read-kb",
        idempotency_key="idem-001",
    )
    assert response2["success"] is True
    assert response2["from_cache"] is True


@pytest.mark.asyncio
async def test_orchestrator_v2_general_workbench_summary_returns_real_message():
    orchestrator = OrchestratorV2()

    response = await orchestrator.process_request(
        user_id="u-1",
        message="查看我当前进行中的任务和状态。",
        intent_classification="general",
    )

    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    assert "当前任务" in response["message"]


@pytest.mark.asyncio
async def test_orchestrator_v2_execution_returns_structured_dispatch_steps():
    orchestrator = OrchestratorV2()

    response = await orchestrator.process_request(
        user_id="u-1",
        message="请为我创建一个维保派单，并给出执行步骤。",
        intent_classification="execute-task",
    )

    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    assert response["result"]["action"]["type"] == "maintenance_dispatch"
    assert len(response["result"]["action"]["steps"]) >= 3


@pytest.mark.asyncio
async def test_orchestrator_v2_knowledge_and_coach_intents_return_actionable_guidance():
    orchestrator = OrchestratorV2()

    knowledge_response = await orchestrator.process_request(
        user_id="u-1",
        message="查询减速器相关 SOP 和注意事项。",
        intent_classification="read-kb",
    )
    coach_response = await orchestrator.process_request(
        user_id="u-1",
        message="请给我一份训练指导建议。",
        intent_classification="delegate-coach",
    )

    assert knowledge_response["success"] is True
    assert knowledge_response["result"]["status"] == "ok"
    assert knowledge_response["result"]["action"]["type"] == "knowledge_summary"
    assert coach_response["success"] is True
    assert coach_response["result"]["status"] == "ok"
    assert coach_response["result"]["action"]["type"] == "training_guidance"


@pytest.mark.asyncio
async def test_orchestrator_v2_diagnoser_dispatches_real_result(monkeypatch):
    @dataclass
    class _Verification:
        success: bool
        plan_id: str
        before_state: dict
        after_state: dict
        delta_summary: dict
        verdict: str
        failed_steps: list[str]

    class _FakeDiagnosisEngine:
        llm_router = None

        async def diagnose(self, telemetry_context, use_llm=True):
            assert telemetry_context.robot_status in {"ERROR", "CRITICAL"}
            return DiagnosisResult(
                success=True,
                primary_hypothesis=FaultHypothesis(
                    fault_code="E002_STALL",
                    fault_name="堵转",
                    confidence=0.92,
                    affected_parts=["waist"],
                    possible_causes=["机械卡滞"],
                    evidence={"joint_id": "waist"},
                ),
                recommended_actions=["检查机械卡滞"],
            )

    class _FakePlanGenerator:
        llm_router = None

        async def generate(self, diagnosis_result, use_llm=False):
            assert diagnosis_result.primary_hypothesis.fault_code == "E002_STALL"
            return MaintenancePlan(
                success=True,
                plan_id="plan-001",
                fault_code="E002_STALL",
                fault_name="堵转",
                actions=[
                    MaintenanceAction(
                        action_id="A-1",
                        action_type="CALIBRATE",
                        target_part="waist",
                        description="校准位置传感器并恢复运行",
                        estimated_duration_minutes=15,
                    )
                ],
                total_duration_minutes=15,
                requires_supervisor=True,
                validation_required=True,
            )

    class _FakeSimulationExecutor:
        async def execute_and_verify(self, plan, adapter):
            assert plan.plan_id == "plan-001"
            return _Verification(
                success=True,
                plan_id=plan.plan_id,
                before_state={"fault_count": 1},
                after_state={"fault_count": 0},
                delta_summary={"fault_count": "1 -> 0"},
                verdict="验证通过",
                failed_steps=[],
            )

    class _FakeAdapter:
        pass

    async def fake_get_adapter():
        return _FakeAdapter()

    monkeypatch.setattr("app.services.orchestrator_v2.AdapterFactory.get_adapter", fake_get_adapter)

    orchestrator = OrchestratorV2(
        diagnosis_engine=_FakeDiagnosisEngine(),
        maintenance_plan_generator=_FakePlanGenerator(),
        simulation_executor=_FakeSimulationExecutor(),
    )

    response = await orchestrator.process_request(
        user_id="u-1",
        message="机器人异常，请诊断",
        intent_classification="delegate-diagnoser",
        telemetry_payload={
            "joints": [
                {
                    "joint_id": "waist",
                    "position": 0.0,
                    "velocity": 0.0,
                    "torque": 0.1,
                    "temperature": 76.0,
                    "error_code": "E002_STALL",
                }
            ],
            "sensors": {
                "battery": 82.0,
                "temperature": 45.0,
                "voltage": {"main": 24.0},
            },
            "active_faults": ["E002_STALL"],
        },
    )

    assert response["success"] is True
    assert response["message"] == "诊断完成"
    assert response["result"]["diagnosis"]["primary_hypothesis"]["fault_code"] == "E002_STALL"
    assert response["result"]["maintenance_plan"]["plan_id"] == "plan-001"
    assert response["result"]["verification"]["success"] is True
