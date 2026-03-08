from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.diagnosis.maintenance_plan_generator import (
    MaintenanceAction,
    MaintenancePlanGenerator,
)
from app.services.diagnosis.schemas import DiagnosisResult, FaultHypothesis


def _diagnosis(
    *,
    fault_code: str = "E002_STALL",
    fault_name: str = "堵转",
    confidence: float = 0.92,
    affected_parts: list[str] | None = None,
    requires_supervisor: bool = False,
    success: bool = True,
) -> DiagnosisResult:
    primary = None
    if success:
        primary = FaultHypothesis(
            fault_code=fault_code,
            fault_name=fault_name,
            confidence=confidence,
            affected_parts=affected_parts or ["waist"],
            possible_causes=["test cause"],
            evidence={},
        )

    return DiagnosisResult(
        success=success,
        primary_hypothesis=primary,
        requires_supervisor=requires_supervisor,
        error_message=None if success else "诊断失败",
    )


class _FakeRouter:
    def __init__(self, content: str | None = None, error: Exception | None = None):
        self._content = content
        self._error = error

    async def chat(self, **_: object):
        if self._error:
            raise self._error
        return SimpleNamespace(content=self._content)


@pytest.mark.asyncio
async def test_stall_plan_contains_four_to_six_steps():
    generator = MaintenancePlanGenerator()

    plan = await generator.generate(_diagnosis())

    assert plan.success is True
    assert plan.fault_code == "E002_STALL"
    assert 4 <= len(plan.actions) <= 6
    assert plan.total_duration_minutes == sum(a.estimated_duration_minutes for a in plan.actions)


@pytest.mark.asyncio
async def test_first_step_is_safety_or_power_off_related():
    generator = MaintenancePlanGenerator()

    plan = await generator.generate(_diagnosis())
    first_action = plan.actions[0]

    safety_text = " ".join(first_action.safety_warnings + [first_action.description])
    assert "断电" in safety_text or "安全" in safety_text or "停机" in safety_text


@pytest.mark.asyncio
async def test_replace_or_calibrate_plan_requires_supervisor():
    generator = MaintenancePlanGenerator()

    plan = await generator.generate(_diagnosis(fault_code="E004_SENSOR_FAILURE", fault_name="传感器故障"))

    assert plan.success is True
    assert any(action.action_type in {"REPLACE", "CALIBRATE"} for action in plan.actions)
    assert plan.requires_supervisor is True
    assert plan.validation_required is True


def test_check_only_actions_do_not_require_supervisor():
    generator = MaintenancePlanGenerator()

    actions = [
        MaintenanceAction(
            action_id="T-1",
            action_type="CHECK",
            target_part="waist",
            description="检查状态",
            estimated_duration_minutes=5,
            required_tools=[],
            safety_warnings=[],
        )
    ]

    assert generator._check_requires_supervisor(_diagnosis(confidence=0.95), actions) is False


@pytest.mark.asyncio
async def test_low_confidence_requires_supervisor_even_for_check_only_actions():
    generator = MaintenancePlanGenerator()

    actions = [
        MaintenanceAction(
            action_id="T-2",
            action_type="CHECK",
            target_part="waist",
            description="检查状态",
            estimated_duration_minutes=5,
            required_tools=[],
            safety_warnings=[],
        )
    ]

    assert generator._check_requires_supervisor(_diagnosis(confidence=0.65), actions) is True


@pytest.mark.asyncio
async def test_llm_parse_failure_degrades_to_template_plan():
    generator = MaintenancePlanGenerator(
        knowledge_hub=object(),
        llm_router=_FakeRouter(content="{invalid json"),
    )

    plan = await generator.generate(_diagnosis(), use_llm=True)

    assert plan.success is True
    assert plan.fault_code == "E002_STALL"
    assert len(plan.actions) == 4


@pytest.mark.asyncio
async def test_llm_optimized_plan_replaces_template_actions():
    generator = MaintenancePlanGenerator(
        knowledge_hub=object(),
        llm_router=_FakeRouter(
            content="""
            {
              "optimized": true,
              "reason": "缩短步骤",
              "modified_actions": [
                {
                  "action_type": "CHECK",
                  "description": "先检查驱动器电流",
                  "estimated_duration_minutes": 6,
                  "required_tools": ["诊断电脑"],
                  "safety_warnings": ["确保断电"]
                },
                {
                  "action_type": "ADJUST",
                  "description": "重新调整驱动参数",
                  "estimated_duration_minutes": 8,
                  "required_tools": ["诊断电脑"],
                  "safety_warnings": []
                }
              ]
            }
            """
        ),
    )

    plan = await generator.generate(_diagnosis(), use_llm=True)

    assert plan.success is True
    assert [action.action_id for action in plan.actions] == ["E002_STALL-OPT1", "E002_STALL-OPT2"]
    assert plan.total_duration_minutes == 14
    assert plan.validation_required is True


@pytest.mark.asyncio
async def test_failed_diagnosis_returns_error_plan():
    generator = MaintenancePlanGenerator()

    plan = await generator.generate(_diagnosis(success=False))

    assert plan.success is False
    assert plan.error_message == "诊断失败"
    assert plan.actions == []


@pytest.mark.asyncio
async def test_unknown_fault_code_returns_error_plan():
    generator = MaintenancePlanGenerator()

    plan = await generator.generate(_diagnosis(fault_code="E999_UNKNOWN", fault_name="未知故障"))

    assert plan.success is False
    assert plan.error_message == "未知故障类型: E999_UNKNOWN"
