from __future__ import annotations

import pytest

from app.adapters.schemas import JointState, SensorData
from app.services.diagnosis.fault_diagnosis_engine import FaultDiagnosisEngine
from app.services.diagnosis.maintenance_plan_generator import MaintenancePlanGenerator
from app.services.llm.telemetry_context_builder import TelemetryContextBuilder


@pytest.mark.asyncio
async def test_telemetry_context_builder_does_not_flag_idle_joint_as_stall():
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="waist",
                position=0.0,
                velocity=0.0,
                torque=1.0,
                temperature=42.0,
            )
        ],
        sensor_data=SensorData(
            battery=88.0,
            temperature=45.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "NORMAL"
    assert context.anomaly_joints == []
    assert context.anomalies == []


@pytest.mark.asyncio
async def test_fault_diagnosis_engine_rule_based_detects_voltage_drop():
    builder = TelemetryContextBuilder()
    engine = FaultDiagnosisEngine()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            battery=20.0,
            temperature=40.0,
            voltage={"main": 19.0},
        ),
    )

    result = await engine.diagnose(context, use_llm=False)

    assert result.success is True
    assert result.primary_hypothesis is not None
    assert result.primary_hypothesis.fault_code == "E003_VOLTAGE_DROP"
    assert "battery" in result.primary_hypothesis.affected_parts or "power_module" in result.primary_hypothesis.affected_parts


@pytest.mark.asyncio
async def test_maintenance_plan_generator_marks_stall_plan_for_supervision():
    builder = TelemetryContextBuilder()
    engine = FaultDiagnosisEngine()
    generator = MaintenancePlanGenerator()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="knee_right",
                position=1.2,
                velocity=0.0,
                torque=0.1,
                temperature=75.0,
                error_code="E002_STALL",
            )
        ],
        sensor_data=SensorData(
            battery=86.0,
            temperature=46.0,
            voltage={"main": 24.0},
        ),
    )

    diagnosis = await engine.diagnose(context, use_llm=False)
    plan = await generator.generate(diagnosis)

    assert plan.success is True
    assert plan.fault_code == "E002_STALL"
    assert len(plan.actions) >= 4
    assert plan.requires_supervisor is True
    assert plan.validation_required is True
