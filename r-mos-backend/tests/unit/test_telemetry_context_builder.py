from __future__ import annotations

from types import SimpleNamespace

from app.adapters.schemas import JointState, SensorData
from app.services.llm.telemetry_context_builder import TelemetryContextBuilder


def test_builder_detects_joint_overheat() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="waist",
                position=0.0,
                velocity=0.2,
                torque=0.8,
                temperature=76.0,
            )
        ],
        sensor_data=SensorData(
            battery=88.0,
            temperature=45.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "ERROR"
    assert len(context.anomaly_joints) == 1
    assert context.anomaly_joints[0]["anomalies"][0]["type"] == "OVERHEAT"
    assert context.anomaly_joints[0]["anomalies"][0]["severity"] == "high"


def test_builder_detects_stall_from_low_velocity_and_low_torque() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="knee_right",
                position=1.2,
                velocity=0.0,
                torque=0.1,
                temperature=42.0,
            )
        ],
        sensor_data=SensorData(
            battery=88.0,
            temperature=44.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "ERROR"
    assert context.anomaly_joints[0]["anomalies"][0]["type"] == "STALL"


def test_builder_detects_voltage_drop() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            battery=42.0,
            temperature=40.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "WARNING"
    assert {anomaly.anomaly_type for anomaly in context.anomalies} == {"VOLTAGE_DROP"}
    assert context.voltage_status == "LOW"


def test_builder_returns_normal_for_nominal_state() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="waist",
                position=0.0,
                velocity=0.3,
                torque=0.8,
                temperature=42.0,
            )
        ],
        sensor_data=SensorData(
            battery=92.0,
            temperature=40.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "NORMAL"
    assert context.anomalies == []
    assert context.anomaly_joints == []


def test_builder_preserves_active_fault_hints_from_payload() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build_from_payload(
        {
            "joints": [],
            "sensors": {
                "battery": 92.0,
                "temperature": 41.0,
                "voltage": {"main": 24.0},
            },
            "active_faults": ["E002_STALL", "E003_VOLTAGE_DROP"],
        }
    )

    assert context.fault_hints == ["E002_STALL", "E003_VOLTAGE_DROP"]
    assert context.raw_summary["active_faults"] == ["E002_STALL", "E003_VOLTAGE_DROP"]
    assert context.to_context_block()["fault_hints"] == ["E002_STALL", "E003_VOLTAGE_DROP"]


def test_to_context_block_contains_expected_shape() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            battery=55.0,
            temperature=40.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.to_context_block() == {
        "robot_status": "NORMAL",
        "fault_hints": [],
        "joint_summary": {"total": 0, "anomalies": 0},
        "battery": 55.0,
        "temperature": 40.0,
        "voltage": "WARNING",
        "anomalies": [],
    }


def test_builder_detects_medium_overheat_and_error_code() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[
            JointState(
                joint_id="left_arm",
                position=0.1,
                velocity=0.2,
                torque=0.6,
                temperature=65.0,
                error_code="E099_UNKNOWN",
            )
        ],
        sensor_data=SensorData(
            battery=85.0,
            temperature=42.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.robot_status == "CRITICAL"
    assert [item["type"] for item in context.anomaly_joints[0]["anomalies"]] == ["OVERHEAT", "ERROR_CODE"]
    assert {anomaly.anomaly_type for anomaly in context.anomalies} == {"OVERHEAT", "ERROR_CODE"}


def test_builder_detects_sensor_overheat_and_main_voltage_drop() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            battery=25.0,
            temperature=73.0,
            voltage={"main": 19.0},
        ),
    )

    assert context.robot_status == "CRITICAL"
    assert context.voltage_status == "CRITICAL"
    assert {anomaly.anomaly_type for anomaly in context.anomalies} == {"VOLTAGE_DROP", "OVERHEAT"}
    assert context.raw_summary["battery"] == 25.0


def test_builder_reports_unknown_voltage_when_battery_missing() -> None:
    builder = TelemetryContextBuilder()

    context = builder.build(
        joint_states=[],
        sensor_data=SensorData(
            temperature=35.0,
            voltage={"main": 24.0},
        ),
    )

    assert context.voltage_status == "UNKNOWN"


class _FakeRouter:
    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.content)


def test_build_with_llm_description_returns_description_and_prompt() -> None:
    router = _FakeRouter(content="机器人右臂出现过热风险。")
    builder = TelemetryContextBuilder(llm_router=router)

    context, description = __import__("asyncio").run(
        builder.build_with_llm_description(
            joint_states=[
                JointState(
                    joint_id="right_arm",
                    position=0.0,
                    velocity=0.0,
                    torque=0.1,
                    temperature=82.0,
                    error_code="E002_STALL",
                )
            ],
            sensor_data=SensorData(
                battery=78.0,
                temperature=45.0,
                voltage={"main": 24.0},
            ),
        )
    )

    assert description == "机器人右臂出现过热风险。"
    assert context.robot_status == "CRITICAL"
    assert "right_arm" in router.calls[0]["messages"][0]["content"]


def test_build_with_llm_description_returns_none_on_router_error() -> None:
    builder = TelemetryContextBuilder(llm_router=_FakeRouter(error=RuntimeError("llm down")))

    context, description = __import__("asyncio").run(
        builder.build_with_llm_description(
            joint_states=[],
            sensor_data=SensorData(
                battery=80.0,
                temperature=35.0,
                voltage={"main": 24.0},
            ),
        )
    )

    assert context.robot_status == "NORMAL"
    assert description is None
