from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.orchestrator_v2 import IdempotencyCache, ModuleRegistry, TaskEventType
from app.services.diagnosis.schemas import DiagnosisResult, FaultHypothesis, MaintenanceAction, MaintenancePlan
from app.services.orchestrator_v2 import OrchestratorV2


@dataclass
class _Verification:
    success: bool
    plan_id: str
    before_state: dict
    after_state: dict
    delta_summary: dict
    verdict: str
    failed_steps: list[str]


class _FakeBuilder:
    def __init__(self, calls: list[str]):
        self.calls = calls

    def build_from_payload(self, payload):
        self.calls.append("build")

        @dataclass
        class _Context:
            robot_status: str = "ERROR"
            anomalies: list = None
            anomaly_joints: list = None

            def __post_init__(self):
                self.anomalies = ["anomaly"]
                self.anomaly_joints = [{"joint_id": payload["joints"][0]["joint_id"]}]

        return _Context()


class _FakeDiagnosisEngine:
    def __init__(self, calls: list[str]):
        self.calls = calls
        self.llm_router = None

    async def diagnose(self, telemetry_context, use_llm=True):
        self.calls.append("diagnose")
        assert telemetry_context.robot_status == "ERROR"
        return DiagnosisResult(
            success=True,
            primary_hypothesis=FaultHypothesis(
                fault_code="E002_STALL",
                fault_name="堵转",
                confidence=0.93,
                affected_parts=["knee_right"],
                possible_causes=["机械卡滞"],
                evidence={"joint_id": "knee_right"},
            ),
            recommended_actions=["检查机械卡滞"],
        )


class _FakePlanGenerator:
    def __init__(self, calls: list[str]):
        self.calls = calls
        self.llm_router = None

    async def generate(self, diagnosis_result, use_llm=False):
        self.calls.append("generate")
        assert diagnosis_result.primary_hypothesis.fault_code == "E002_STALL"
        return MaintenancePlan(
            success=True,
            plan_id="plan-diagnoser-001",
            fault_code="E002_STALL",
            fault_name="堵转",
            actions=[
                MaintenanceAction(
                    action_id="A-1",
                    action_type="CALIBRATE",
                    target_part="knee_right",
                    description="校准位置传感器",
                    estimated_duration_minutes=20,
                )
            ],
            total_duration_minutes=20,
            requires_supervisor=True,
            validation_required=True,
        )


class _FakeSimulationExecutor:
    def __init__(self, calls: list[str]):
        self.calls = calls

    async def execute_and_verify(self, plan, adapter):
        self.calls.append("verify")
        assert plan.plan_id == "plan-diagnoser-001"
        assert adapter == "fake-adapter"
        return _Verification(
            success=True,
            plan_id=plan.plan_id,
            before_state={"fault_count": 1},
            after_state={"fault_count": 0},
            delta_summary={"fault_count": "1 -> 0"},
            verdict="验证通过",
            failed_steps=[],
        )


def _telemetry_payload() -> dict:
    return {
        "joints": [
            {
                "joint_id": "knee_right",
                "position": 1.2,
                "velocity": 0.0,
                "torque": 0.1,
                "temperature": 75.0,
                "error_code": "E002_STALL",
            }
        ],
        "sensors": {
            "battery": 84.0,
            "temperature": 45.0,
            "voltage": {"main": 24.0},
        },
        "active_faults": ["E002_STALL"],
    }


@pytest.mark.asyncio
async def test_diagnoser_returns_structured_result_with_telemetry_payload(monkeypatch):
    calls: list[str] = []

    async def _fake_get_adapter():
        return "fake-adapter"

    monkeypatch.setattr("app.services.orchestrator_v2.AdapterFactory.get_adapter", _fake_get_adapter)

    orchestrator = OrchestratorV2(
        diagnosis_engine=_FakeDiagnosisEngine(calls),
        maintenance_plan_generator=_FakePlanGenerator(calls),
        simulation_executor=_FakeSimulationExecutor(calls),
    )
    orchestrator._telemetry_builder = _FakeBuilder(calls)

    response = await orchestrator.process_request(
        user_id="user-1",
        message="机器人异常，请诊断",
        intent_classification="delegate-diagnoser",
        telemetry_payload=_telemetry_payload(),
    )

    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    assert response["result"]["diagnosis"]["primary_hypothesis"]["fault_code"] == "E002_STALL"
    assert response["result"]["maintenance_plan"]["plan_id"] == "plan-diagnoser-001"
    assert response["result"]["verification"]["success"] is True
    assert response["result"]["trace_id"] == response["trace_id"]
    assert calls == ["build", "diagnose", "generate", "verify"]


@pytest.mark.asyncio
async def test_diagnoser_returns_preliminary_diagnosis_without_telemetry(monkeypatch):
    """无遥测时给出基于文字描述的初步诊断（旧行为是直接返回 error，已改）。"""

    async def _fake_chat(messages, **kwargs):
        class _Resp:
            content = "初步判断：1) 伺服使能未开启；2) 制动器未释放；3) 供电电压不足。"

        return _Resp()

    monkeypatch.setattr(
        "app.services.orchestrator_v2.llm_router.chat_with_fallback", _fake_chat
    )
    orchestrator = OrchestratorV2()

    response = await orchestrator.process_request(
        user_id="user-1",
        message="机器人异常，请诊断",
        intent_classification="delegate-diagnoser",
    )

    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    assert "伺服使能未开启" in response["result"]["message"]
    assert response["result"]["action"]["telemetry_available"] is False
    assert isinstance(response["trace_id"], str)


@pytest.mark.asyncio
async def test_trace_id_is_present_and_unique():
    orchestrator = OrchestratorV2()

    response1 = await orchestrator.process_request(
        user_id="user-1",
        message="读取知识",
        intent_classification="read-kb",
    )
    response2 = await orchestrator.process_request(
        user_id="user-1",
        message="读取知识",
        intent_classification="read-kb",
    )

    assert response1["trace_id"]
    assert response2["trace_id"]
    assert response1["trace_id"] != response2["trace_id"]


def test_module_registry_and_idempotency_cache_support_basic_operations():
    registry = ModuleRegistry()
    cache = IdempotencyCache(ttl_seconds=1)

    registry.register("demo", "Demo Module", lambda _: {"status": "ok"}, {"scope": "test"})
    assert registry.get_handler("demo") is not None
    assert registry.get_metadata("demo") == {"name": "Demo Module", "metadata": {"scope": "test"}}
    assert registry.list_modules() == ["demo"]

    cache.set("idem-1", {"status": "ok"})
    assert cache.get("idem-1") == {"status": "ok"}
    assert cache.has("idem-1") is True

    cache._timestamps["idem-1"] = 0
    assert cache.get("idem-1") is None
    assert cache.has("idem-1") is False

    cache.set("idem-2", {"status": "ok"})
    cache.clear()
    assert cache.has("idem-2") is False


@pytest.mark.asyncio
async def test_classify_intent_falls_back_to_keywords(monkeypatch):
    """LLM 不可用时仍应降级到关键词匹配（_classify_intent 现为协程）。"""

    async def _raise(*args, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr("app.services.orchestrator_v2.intent_engine.recognize", _raise)

    orchestrator = OrchestratorV2()

    assert await orchestrator._classify_intent("为什么机器人停住了，需要诊断") == "delegate-diagnoser"
    assert await orchestrator._classify_intent("请开始执行当前练习") == "execute-task"
    assert await orchestrator._classify_intent("搜索相关知识") == "read-kb"
    assert await orchestrator._classify_intent("随便聊聊") == "general"


@pytest.mark.asyncio
async def test_process_request_handles_invalid_resource_binding_and_policy_denial(monkeypatch):
    orchestrator = OrchestratorV2()

    class _InvalidBinding:
        is_valid = False
        errors = ["invalid"]
        resources = []

    monkeypatch.setattr(
        "app.services.orchestrator_v2.resource_parser.parse_resource_ref",
        lambda _: _InvalidBinding(),
    )

    invalid_response = await orchestrator.process_request(
        user_id="user-1",
        message="读取知识",
        intent_classification="read-kb",
        resource_ref={"kind": "bad"},
    )

    assert invalid_response == {
        "success": False,
        "error": "Invalid resource binding",
        "errors": ["invalid"],
    }

    class _DeniedDecision:
        allowed = False
        risk_level = type("Risk", (), {"value": "high"})()
        requires_approval = True
        approval_level = "teacher"
        evidence_required = ["photo"]

    monkeypatch.setattr("app.services.orchestrator_v2.policy_matrix.evaluate", lambda *args, **kwargs: _DeniedDecision())

    denied_response = await orchestrator.process_request(
        user_id="user-1",
        message="读取知识",
        intent_classification="read-kb",
    )

    assert denied_response["success"] is False
    assert denied_response["error"] == "Policy denied"
    assert denied_response["policy_decision"]["value"].allowed is False


def test_task_lifecycle_budget_and_trace_events():
    orchestrator = OrchestratorV2()
    task = orchestrator.create_task(user_id="user-1", skill_id="skill-1", budget_limit_ms=1200)

    assert orchestrator.get_task_context(task.task_id) is not None
    assert orchestrator.check_budget("user-1", 500) == (True, 700)

    ok, _, state = orchestrator.transition_state(task.task_id, TaskEventType.START)
    assert ok is True
    assert state.value == "ready"
    ok, _, state = orchestrator.transition_state(task.task_id, TaskEventType.START)
    assert ok is True
    assert state.value == "running"
    ok, _, state = orchestrator.transition_state(task.task_id, TaskEventType.COMPLETE)
    assert ok is True
    assert state.value == "completed"

    orchestrator.consume_budget("user-1", 800)
    assert orchestrator.check_budget("user-1", 500) == (False, 400)

    missing = orchestrator.transition_state("task-missing", TaskEventType.START)
    assert missing[0] is False
    assert missing[1] == "Task not found"

    invalid = orchestrator.transition_state(task.task_id, TaskEventType.START)
    assert invalid[0] is False
    assert "Invalid transition" in invalid[1]

    events = orchestrator.get_trace_events(task.trace_id)
    assert len(events) >= 3


@pytest.mark.asyncio
async def test_classify_intent_uses_llm_inside_running_event_loop(monkeypatch):
    """回归：意图识别必须在运行中的事件循环里真正调用 LLM。

    此前用 asyncio.run() 调用异步的 intent_engine.recognize()，而 process_request
    本身跑在 FastAPI 的事件循环内 —— asyncio.run() 在事件循环中必抛 RuntimeError，
    异常被 except 吞掉后每次都降级到关键词匹配，LLM 意图识别 100% 失效。
    """
    from app.services.intent import IntentScene

    calls: list[str] = []

    async def _fake_recognize(message, use_llm=False):
        calls.append(message)

        class _Result:
            scene = IntentScene.DIAGNOSIS

        return _Result()

    monkeypatch.setattr(
        "app.services.orchestrator_v2.intent_engine.recognize", _fake_recognize
    )
    orchestrator = OrchestratorV2()

    # 这句话不含关键词表里的任何词（诊断/为什么/怎么办…），
    # 一旦降级到关键词匹配就会返回 "general"。
    result = await orchestrator._classify_intent("手臂抬不起来，帮我分析一下原因")

    assert calls, "intent_engine.recognize 应被真正调用（说明没有降级）"
    assert result == "delegate-diagnoser"


@pytest.mark.asyncio
async def test_general_handler_answers_via_llm(monkeypatch):
    """通用问答必须走 LLM，而不是返回硬编码模板。"""
    captured: dict = {}

    async def _fake_chat(messages, **kwargs):
        captured["messages"] = messages

        class _Resp:
            content = "可能原因：1) 关节电机过流保护；2) 减速器卡死；3) 编码器反馈异常。"

        return _Resp()

    monkeypatch.setattr(
        "app.services.orchestrator_v2.llm_router.chat_with_fallback", _fake_chat
    )
    orchestrator = OrchestratorV2()

    response = await orchestrator.process_request(
        user_id="u-1",
        message="W2 机器人手臂抬不起来，帮我分析可能的故障原因",
        intent_classification="general",
    )

    assert response["success"] is True
    assert "关节电机过流保护" in response["message"]
    assert "我可以在 AI 工作台帮你做四类事" not in response["message"]
    # 用户问题应被带进 prompt
    assert any("手臂抬不起来" in str(m.get("content", "")) for m in captured["messages"])


@pytest.mark.asyncio
async def test_diagnoser_falls_back_to_text_diagnosis_without_telemetry(monkeypatch):
    """无遥测数据时，应基于文字描述给出诊断，而不是直接拒绝。"""

    async def _fake_chat(messages, **kwargs):
        class _Resp:
            content = "初步判断为肩关节伺服驱动器欠压，建议先检查供电与制动器释放状态。"

        return _Resp()

    monkeypatch.setattr(
        "app.services.orchestrator_v2.llm_router.chat_with_fallback", _fake_chat
    )
    orchestrator = OrchestratorV2()

    response = await orchestrator.process_request(
        user_id="u-1",
        message="W2 手臂抬不起来，没有遥测数据",
        intent_classification="delegate-diagnoser",
    )

    assert response["success"] is True
    assert response["result"]["status"] != "error"
    assert "伺服驱动器欠压" in response["result"]["message"]
