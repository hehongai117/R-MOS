from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.adapters.schemas import JointState, SensorData
from app.services.diagnosis.fault_diagnosis_engine import FaultDiagnosisEngine
from app.services.llm.telemetry_context_builder import TelemetryContextBuilder


def _stall_context():
    builder = TelemetryContextBuilder()
    return builder.build(
        joint_states=[
            JointState(
                joint_id="waist",
                position=0.0,
                velocity=0.0,
                torque=0.1,
                temperature=75.0,
                error_code="E002_STALL",
            )
        ],
        sensor_data=SensorData(
            battery=82.0,
            temperature=46.0,
            voltage={"main": 24.0},
        ),
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
async def test_llm_diagnosis_parses_three_ranked_hypotheses():
    engine = FaultDiagnosisEngine(
        llm_router=_FakeRouter(
            """
            {
              "hypotheses": [
                {"fault_code": "E001_OVERHEAT", "fault_name": "过热", "confidence": 0.72, "affected_parts": ["waist"], "possible_causes": ["散热不足"], "evidence": {}},
                {"fault_code": "E002_STALL", "fault_name": "堵转", "confidence": 0.91, "affected_parts": ["waist"], "possible_causes": ["机械卡滞"], "evidence": {}},
                {"fault_code": "E003_VOLTAGE_DROP", "fault_name": "电压跌落", "confidence": 0.66, "affected_parts": ["power_module"], "possible_causes": ["供电波动"], "evidence": {}}
              ],
              "reasoning": "综合遥测特征判断为堵转优先。",
              "recommended_actions": ["立即停机", "检查机械卡滞"]
            }
            """
        )
    )

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "E002_STALL"
    assert [item.fault_code for item in result.alternative_hypotheses] == [
        "E001_OVERHEAT",
        "E003_VOLTAGE_DROP",
    ]
    assert result.requires_supervisor is False


@pytest.mark.asyncio
async def test_invalid_json_falls_back_to_text_parsing_without_raising():
    engine = FaultDiagnosisEngine(llm_router=_FakeRouter("检测到关节堵转，建议立即停机并检查机械卡滞。"))

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "E002_STALL"
    assert isinstance(result.recommended_actions, list)


@pytest.mark.asyncio
async def test_llm_timeout_falls_back_to_rule_based_result():
    engine = FaultDiagnosisEngine(llm_router=_FakeRouter(error=TimeoutError("timeout")))

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "E002_STALL"
    assert result.reasoning.startswith("基于规则诊断")


@pytest.mark.asyncio
async def test_invalid_recommended_actions_are_normalized_to_list():
    engine = FaultDiagnosisEngine(
        llm_router=_FakeRouter(
            """
            {
              "hypotheses": [
                {"fault_code": "E002_STALL", "fault_name": "堵转", "confidence": 0.88, "affected_parts": ["waist"], "possible_causes": ["机械卡滞"], "evidence": {}}
              ],
              "reasoning": "堵转置信度较高。",
              "recommended_actions": "立即停机"
            }
            """
        )
    )

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.recommended_actions == ["立即停机"]


@pytest.mark.asyncio
async def test_requires_supervisor_is_set_for_low_confidence_result():
    engine = FaultDiagnosisEngine(
        llm_router=_FakeRouter(
            """
            {
              "hypotheses": [
                {"fault_code": "E002_STALL", "fault_name": "堵转", "confidence": 0.62, "affected_parts": ["waist"], "possible_causes": ["机械卡滞"], "evidence": {}}
              ],
              "reasoning": "证据不足，需要人工复核。",
              "recommended_actions": ["立即停机"]
            }
            """
        )
    )

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.requires_supervisor is True


@pytest.mark.asyncio
async def test_normal_context_returns_normal_result_without_llm():
    builder = TelemetryContextBuilder()
    engine = FaultDiagnosisEngine()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            battery=90.0,
            temperature=40.0,
            voltage={"main": 24.0},
        ),
    )

    result = await engine.diagnose(context, use_llm=False)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "NORMAL"
    assert result.recommended_actions == []


@pytest.mark.asyncio
async def test_rule_based_unknown_error_code_returns_unknown_fault():
    builder = TelemetryContextBuilder()
    engine = FaultDiagnosisEngine()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="waist",
                position=0.0,
                velocity=0.2,
                torque=0.5,
                temperature=42.0,
                error_code="E999_CUSTOM",
            )
        ],
        sensor_data=SensorData(
            battery=86.0,
            temperature=42.0,
            voltage={"main": 24.0},
        ),
    )

    result = await engine.diagnose(context, use_llm=False)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "UNKNOWN"
    assert result.recommended_actions == ["请进行全面检查", "联系技术支持"]


@pytest.mark.asyncio
async def test_empty_llm_hypotheses_returns_parse_error_result():
    engine = FaultDiagnosisEngine(
        llm_router=_FakeRouter(
            """
            {
              "hypotheses": [],
              "reasoning": "没有足够证据。"
            }
            """
        )
    )

    result = await engine._llm_diagnosis(_stall_context())

    assert result.success is False
    assert result.error_message == "LLM 响应格式无法解析"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "fault_code"),
    [
        ("检测到电机过热，请暂停任务。", "E001_OVERHEAT"),
        ("电量不足，疑似电压跌落。", "E003_VOLTAGE_DROP"),
        ("sensor 校准失败，需要检查。", "E004_SENSOR_FAILURE"),
        ("joint appears loose and unstable.", "E005_JOINT_LOOSE"),
    ],
)
async def test_text_fallback_maps_multiple_fault_keywords(text: str, fault_code: str):
    engine = FaultDiagnosisEngine(llm_router=_FakeRouter(text))

    result = await engine.diagnose(_stall_context(), use_llm=True)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == fault_code
