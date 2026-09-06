"""RMOS-S3-003 模块 E 的 HTTP 行为覆盖网。

本文件只补现有测试缺少的放行、响应内容和边界证据。对象归属拒绝路径继续复用
``tests/unit/test_task_write_ownership.py`` 与
``tests/e2e/test_object_ownership_boundary.py``，不在这里重复造用例。
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.models.event import Event
from app.models.sop import SOP, SOPStep
from app.models.task import Task, TaskStatus
from app.models.task_execution import TaskExecution, TaskStepResult
from app.services.preflight_check import preflight_check_service
from main import app
from tests.e2e.helpers import register_and_login


MODULE_E_ROUTES = {
    ("POST", "/api/v1/tasks"),
    ("POST", "/api/v1/tasks/{task_id}/start"),
    ("POST", "/api/v1/tasks/{task_id}/step"),
    ("POST", "/api/v1/tasks/{task_id}/pause"),
    ("POST", "/api/v1/tasks/{task_id}/resume"),
    ("GET", "/api/v1/tasks"),
    ("GET", "/api/v1/tasks/{task_id}"),
    ("GET", "/api/v1/tasks/{task_id}/report"),
    ("GET", "/api/v1/tasks/{task_id}/events"),
    ("POST", "/api/v1/pipeline/diagnose"),
    ("POST", "/api/v1/pipeline/tasks/from-diagnosis"),
    ("POST", "/api/v1/pipeline/executions/{execution_id}/steps/complete"),
    ("POST", "/api/v1/pipeline/executions/{execution_id}/complete"),
}


def _seed_sop(
    session_factory,
    *,
    step_count: int = 2,
    required_tools: list[str] | None = None,
) -> int:
    async def _seed() -> int:
        async with session_factory() as session:
            sop = SOP(
                name="模块 E 行为测试 SOP",
                description="覆盖任务执行接口",
                applicable_model="MOCK_HUMANOID_V1",
            )
            session.add(sop)
            await session.flush()
            session.add_all(
                [
                    SOPStep(
                        sop_id=sop.id,
                        step_index=index,
                        title=f"步骤 {index}",
                        description=f"执行步骤 {index}",
                        expected_action="inspect",
                        severity_level="INFO",
                        allow_skip=False,
                        tools_required=required_tools,
                    )
                    for index in range(1, step_count + 1)
                ]
            )
            await session.commit()
            return int(sop.id)

    return asyncio.run(_seed())


def _seed_task(
    session_factory,
    *,
    owner_id: int,
    status: str = TaskStatus.PENDING.value,
    with_event: bool = False,
) -> int:
    async def _seed() -> int:
        async with session_factory() as session:
            task = Task(title="模块 E 查询任务", user_id=owner_id, status=status)
            session.add(task)
            await session.flush()
            if with_event:
                session.add(
                    Event(
                        task_id=task.id,
                        event_type="task_started",
                        action="start",
                        result="started",
                    )
                )
            await session.commit()
            return int(task.id)

    return asyncio.run(_seed())


def _seed_execution(
    session_factory,
    *,
    owner_id: int,
    task_status: str = TaskStatus.IN_PROGRESS.value,
) -> tuple[int, int]:
    async def _seed() -> tuple[int, int]:
        async with session_factory() as session:
            task = Task(title="模块 E 执行记录", user_id=owner_id, status=task_status)
            session.add(task)
            await session.flush()
            execution = TaskExecution(
                task_id=task.id,
                student_id=owner_id,
                status="in_progress",
            )
            session.add(execution)
            await session.commit()
            return int(task.id), int(execution.id)

    return asyncio.run(_seed())


def _load_execution_state(session_factory, execution_id: int) -> tuple[str, str, int]:
    async def _load() -> tuple[str, str, int]:
        async with session_factory() as session:
            execution = await session.get(TaskExecution, execution_id)
            assert execution is not None
            task = await session.get(Task, execution.task_id)
            assert task is not None
            count_result = await session.execute(
                select(TaskStepResult).where(TaskStepResult.execution_id == execution_id)
            )
            return (
                str(execution.status),
                str(task.status),
                len(list(count_result.scalars().all())),
            )

    return asyncio.run(_load())


def test_module_e_route_census_uses_runtime_app() -> None:
    """从真实应用枚举路由，锁定模块 E 当前实际为 13 条而不是估算值。"""
    actual = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.endpoint.__module__
        in {"app.api.v1.endpoints.tasks", "app.api.v1.endpoints.pipeline"}
        for method in route.methods
    }
    assert actual == MODULE_E_ROUTES


def test_m22_terminal_status_writer_census_uses_ast() -> None:
    """用 AST 锁定 tasks/task_executions 当前全部终态赋值位置。"""
    app_root = Path(__file__).parents[2] / "app"
    terminal_tokens = {
        "COMPLETED",
        "FAILED",
        "TIMEOUT",
        "CANCELLED",
        "completed",
        "failed",
        "timeout",
        "cancelled",
        "abandoned",
    }
    writers: set[tuple[str, str, str, str]] = set()

    for source_path in app_root.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        if "app.models.task import" not in source and "app.models.task_execution import" not in source:
            continue
        tree = ast.parse(source)
        scope: list[str] = []

        class TerminalWriterVisitor(ast.NodeVisitor):
            def _visit_scope(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()

            visit_ClassDef = _visit_scope
            visit_FunctionDef = _visit_scope
            visit_AsyncFunctionDef = _visit_scope

            def visit_Assign(self, node: ast.Assign) -> None:
                value = ast.unparse(node.value)
                for target in node.targets:
                    target_text = ast.unparse(target)
                    if target_text not in {"task.status", "execution.status"}:
                        continue
                    if not any(token in value for token in terminal_tokens):
                        continue
                    writers.add(
                        (
                            source_path.relative_to(app_root.parent).as_posix(),
                            ".".join(scope),
                            target_text,
                            value,
                        )
                    )
                self.generic_visit(node)

        TerminalWriterVisitor().visit(tree)

    assert writers == {
        (
            "app/services/task_service.py",
            "TaskService._complete_task",
            "task.status",
            "TaskStatus.COMPLETED",
        ),
        (
            "app/services/pipeline/task_pipeline_service.py",
            "TaskPipelineService.complete_task",
            "execution.status",
            "'completed'",
        ),
        (
            "app/services/pipeline/task_pipeline_service.py",
            "TaskPipelineService.complete_task",
            "task.status",
            "TaskStatus.COMPLETED.value",
        ),
    }


def test_task_owner_can_run_create_start_step_pause_resume_lifecycle(e2e_env) -> None:
    """五条任务写路由均有本人放行证据，且响应内容反映真实状态变化。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_lifecycle", role="student"
    )
    sop_id = _seed_sop(session_factory)

    created = client.post(
        "/api/v1/tasks",
        json={"title": "本人任务", "sop_id": sop_id, "pass_score": 80},
    )
    assert created.status_code == 200, created.text
    created_body = created.json()
    assert created_body["title"] == "本人任务"
    assert created_body["user_id"] == owner_id
    assert created_body["status"] == "pending"
    task_id = int(created_body["id"])

    started = client.post(f"/api/v1/tasks/{task_id}/start")
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_progress"
    assert started.json()["started_at"] is not None

    stepped = client.post(
        f"/api/v1/tasks/{task_id}/step",
        json={"step_index": 1, "action": "inspect"},
    )
    assert stepped.status_code == 200, stepped.text
    assert {
        "task_id": task_id,
        "step_index": 1,
        "status": "success",
        "next_step_index": 2,
        "is_task_completed": False,
    }.items() <= stepped.json().items()

    paused = client.post(f"/api/v1/tasks/{task_id}/pause")
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"
    assert paused.json()["paused_at"] is not None

    resumed = client.post(f"/api/v1/tasks/{task_id}/resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "in_progress"
    assert resumed.json()["paused_at"] is None


def test_task_list_detail_and_events_return_owner_content(e2e_env) -> None:
    """此前无正向 HTTP 证据的列表、详情和事件接口返回本人数据及正确内容。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_reader", role="student"
    )
    task_id = _seed_task(session_factory, owner_id=owner_id, with_event=True)

    listing = client.get("/api/v1/tasks")
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert [item["id"] for item in listing.json()["items"]] == [task_id]

    detail = client.get(f"/api/v1/tasks/{task_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == task_id
    assert detail.json()["user_id"] == owner_id

    events = client.get(f"/api/v1/tasks/{task_id}/events")
    assert events.status_code == 200, events.text
    assert len(events.json()) == 1
    assert events.json()[0]["event_type"] == "task_started"
    assert events.json()[0]["result"] == "started"


def test_pipeline_diagnose_rejects_anonymous_and_returns_structured_result(e2e_env) -> None:
    """诊断路由没有对象归属边界；当前拒绝口径是匿名 401、登录用户放行。"""
    client, _ = e2e_env
    token = client.headers.pop("Authorization")
    anonymous = client.post("/api/v1/pipeline/diagnose", json={"telemetry": {}})
    assert anonymous.status_code == 401, anonymous.text
    client.headers["Authorization"] = token

    response = client.post(
        "/api/v1/pipeline/diagnose",
        json={"telemetry": {"joints": [], "sensors": {"voltage": {"main": 24.0}}}},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "success": True,
        "fault_type": None,
        "confidence": 1.0,
        "affected_joints": [],
        "reasoning": "遥测数据正常，未检测到故障",
        "recommended_sop": None,
        "is_compound": False,
        "llm_enhanced": False,
    }


def test_pipeline_creation_bypasses_blocked_preflight_current_behavior(
    e2e_env, monkeypatch
) -> None:
    """这是当前行为，疑似缺陷 E-PREFLIGHT-01，待模块 E 改造时处置。

    同一执行前检查被强制设为阻止时，普通任务创建返回 400；诊断转任务接口却仍可
    创建任务与执行记录，说明存在绕过执行前检查的入口。
    """
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_preflight", role="student"
    )
    sop_id = _seed_sop(session_factory)
    monkeypatch.setattr(
        preflight_check_service,
        "can_proceed",
        AsyncMock(return_value=(False, "测试阻止")),
    )

    blocked = client.post(
        "/api/v1/tasks",
        json={"title": "应被阻止", "sop_id": sop_id},
    )
    assert blocked.status_code == 400, blocked.text
    assert blocked.json()["message"]["reason"] == "测试阻止"

    bypassed = client.post(
        "/api/v1/pipeline/tasks/from-diagnosis",
        json={"diagnosis_trace_id": "trace-preflight-bypass", "fault_type": "E001_OVERHEAT"},
    )
    assert bypassed.status_code == 200, bypassed.text
    assert bypassed.json()["fault_type"] == "E001_OVERHEAT"
    assert bypassed.json()["task_id"] > 0
    assert bypassed.json()["execution_id"] > 0

    execution_status, task_status, _ = _load_execution_state(
        session_factory, bypassed.json()["execution_id"]
    )
    assert execution_status == "in_progress"
    assert task_status == "in_progress"


def test_task_creation_without_tool_inventory_still_passes_preflight_current_behavior(
    e2e_env,
) -> None:
    """这是当前行为，疑似缺陷 E-PREFLIGHT-02，待模块 E 改造时处置。

    SOP 明确要求专用工具，但创建接口不传可用工具清单，工具检查会把“没有清单”
    当作全部可用，任务仍创建成功。
    """
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_tools", role="student"
    )
    sop_id = _seed_sop(session_factory, required_tools=["专用扭矩扳手"])

    response = client.post(
        "/api/v1/tasks",
        json={"title": "缺少工具清单仍创建", "sop_id": sop_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == owner_id
    assert response.json()["status"] == "pending"


def test_pipeline_step_completion_allows_owner_and_persists_content(e2e_env) -> None:
    """执行记录所有者可完成步骤，响应和落库内容都正确。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_step_owner", role="student"
    )
    _, execution_id = _seed_execution(session_factory, owner_id=owner_id)

    response = client.post(
        f"/api/v1/pipeline/executions/{execution_id}/steps/complete",
        json={
            "step_index": 1,
            "evidence_type": "photo",
            "evidence_value": {"url": "evidence.jpg"},
            "duration_seconds": 12,
            "is_compliant": False,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "step_index": 1,
        "is_compliant": False,
        "feedback": None,
    }
    _, _, result_count = _load_execution_state(session_factory, execution_id)
    assert result_count == 1


def test_pipeline_step_accepts_negative_values_current_behavior(e2e_env) -> None:
    """这是当前行为，疑似缺陷 E-INPUT-01，待模块 E 改造时处置。

    步骤编号和耗时均为负数时接口仍返回成功，并把记录写入数据库。
    """
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_negative_step", role="student"
    )
    _, execution_id = _seed_execution(session_factory, owner_id=owner_id)

    response = client.post(
        f"/api/v1/pipeline/executions/{execution_id}/steps/complete",
        json={"step_index": -1, "duration_seconds": -5},
    )
    assert response.status_code == 200, response.text
    assert response.json()["step_index"] == -1
    _, _, result_count = _load_execution_state(session_factory, execution_id)
    assert result_count == 1


def test_completed_execution_still_accepts_step_writes_current_behavior(e2e_env) -> None:
    """这是当前行为，疑似缺陷 E-STATE-02，待模块 E 改造时处置。

    执行记录已处于 completed 终态后，步骤完成接口仍允许继续写入新结果。
    """
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_terminal_step", role="student"
    )
    _, execution_id = _seed_execution(session_factory, owner_id=owner_id)
    completed = client.post(f"/api/v1/pipeline/executions/{execution_id}/complete")
    assert completed.status_code == 200, completed.text

    response = client.post(
        f"/api/v1/pipeline/executions/{execution_id}/steps/complete",
        json={"step_index": 1},
    )
    assert response.status_code == 200, response.text
    execution_status, _, result_count = _load_execution_state(
        session_factory, execution_id
    )
    assert execution_status == "completed"
    assert result_count == 1


def test_pipeline_completion_jumps_pending_task_to_completed_current_behavior(e2e_env) -> None:
    """这是当前行为，疑似缺陷 E-STATE-01，待模块 E 改造时处置。

    父任务仍为 pending 且没有任何步骤结果时，完成执行记录接口仍把父任务和执行
    记录同时写成 completed，形成 pending 直接跳终态且终态可空步骤写入。
    """
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(
        client, email_prefix="module_e_complete_owner", role="student"
    )
    task_id, execution_id = _seed_execution(
        session_factory,
        owner_id=owner_id,
        task_status=TaskStatus.PENDING.value,
    )

    response = client.post(f"/api/v1/pipeline/executions/{execution_id}/complete")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "execution_id": execution_id,
        "task_id": task_id,
        "status": "completed",
        "report_generation": "triggered",
    }
    execution_status, task_status, result_count = _load_execution_state(
        session_factory, execution_id
    )
    assert execution_status == "completed"
    assert task_status == "completed"
    assert result_count == 0


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        pytest.param("post", "/api/v1/tasks/999999/start", None, id="task-start"),
        pytest.param(
            "post",
            "/api/v1/tasks/999999/step",
            {"step_index": 1, "action": "inspect"},
            id="task-step",
        ),
        pytest.param("post", "/api/v1/tasks/999999/pause", None, id="task-pause"),
        pytest.param("post", "/api/v1/tasks/999999/resume", None, id="task-resume"),
        pytest.param("get", "/api/v1/tasks/999999", None, id="task-detail"),
        pytest.param("get", "/api/v1/tasks/999999/report", None, id="task-report"),
        pytest.param("get", "/api/v1/tasks/999999/events", None, id="task-events"),
    ],
)
def test_missing_task_id_currently_returns_409_instead_of_404(
    e2e_env, method: str, path: str, json_body: dict | None
) -> None:
    """这是当前行为，疑似缺陷 E-HTTP-01，待模块 E 改造时处置。

    TaskService 把不存在资源包装成业务冲突，导致任务读写接口统一返回 409，而不是
    任务要求和既有资源口径中的 404。
    """
    client, _ = e2e_env
    response = client.request(method.upper(), path, json=json_body)
    assert response.status_code == 409, response.text
    assert response.json()["details"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        pytest.param(
            "/api/v1/pipeline/executions/999999/steps/complete",
            {"step_index": 1},
            id="pipeline-step",
        ),
        pytest.param(
            "/api/v1/pipeline/executions/999999/complete",
            None,
            id="pipeline-complete",
        ),
    ],
)
def test_missing_pipeline_execution_returns_404(
    e2e_env, path: str, json_body: dict | None
) -> None:
    """两个执行记录写接口对不存在编号沿用 404 口径。"""
    client, _ = e2e_env
    response = client.post(path, json=json_body)
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        pytest.param("/api/v1/tasks", {"title": "缺 SOP"}, id="task-create"),
        pytest.param("/api/v1/tasks/not-an-id/start", None, id="task-start"),
        pytest.param(
            "/api/v1/tasks/1/step",
            {"step_index": 0, "action": "inspect"},
            id="task-step",
        ),
        pytest.param("/api/v1/tasks/not-an-id/pause", None, id="task-pause"),
        pytest.param("/api/v1/tasks/not-an-id/resume", None, id="task-resume"),
        pytest.param("/api/v1/pipeline/diagnose", {}, id="pipeline-diagnose"),
        pytest.param(
            "/api/v1/pipeline/tasks/from-diagnosis",
            {"diagnosis_trace_id": "missing-fault-type"},
            id="pipeline-create",
        ),
        pytest.param(
            "/api/v1/pipeline/executions/1/steps/complete",
            {},
            id="pipeline-step",
        ),
        pytest.param(
            "/api/v1/pipeline/executions/not-an-id/complete",
            None,
            id="pipeline-complete",
        ),
    ],
)
def test_module_e_write_routes_reject_invalid_input_with_422(
    e2e_env, path: str, json_body: dict | None
) -> None:
    """每条 POST 路由都有非法请求边界；校验失败不得进入业务写入。"""
    client, _ = e2e_env
    response = client.post(path, json=json_body)
    assert response.status_code == 422, response.text
