"""任务写端点的对象归属回归测试（审计 M-01）。

修复前 `tasks.py` 的三个**读**端点均调用 `ensure_task_scope`，
而 `start` / `step` / `pause` / `resume` 四个**写**端点无身份、无归属校验
——「读有写没有」的典型。这四个端点此前也没有任何 HTTP 层测试，
因此补上守卫时没有任何用例失败；本文件即为该空白的补齐。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from app.models.task import Task, TaskStatus
from app.models.task_execution import TaskExecution
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


def _client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init())
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with sf() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.state.test_sessionmaker = sf
    return TestClient(app), sf


def _seed_task(sf: async_sessionmaker, owner_id: int | None) -> int:
    async def _run() -> int:
        async with sf() as session:
            task = Task(title="归属测试任务", user_id=owner_id, status=TaskStatus.PENDING)
            session.add(task)
            await session.commit()
            return task.id

    return asyncio.run(_run())


@pytest.mark.regression
def test_task_write_endpoints_reject_non_owner():
    """非所有者对四个写端点必须全部被拒。"""
    client, sf = _client()
    try:
        owner_id, _, _ = register_and_login(client, email_prefix="task_owner")
        task_id = _seed_task(sf, owner_id)

        # 切换到另一位已认证用户
        register_and_login(client, email_prefix="task_intruder")

        results = {
            "start": client.post(f"/api/v1/tasks/{task_id}/start"),
            "pause": client.post(f"/api/v1/tasks/{task_id}/pause"),
            "resume": client.post(f"/api/v1/tasks/{task_id}/resume"),
            "step": client.post(
                f"/api/v1/tasks/{task_id}/step",
                json={"step_index": 1, "action": "check"},
            ),
        }
        denied = {k: r.status_code for k, r in results.items()}
        assert all(code == 403 for code in denied.values()), f"非所有者未被拒绝: {denied}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_unowned_task_is_not_writable_by_ordinary_user():
    """无主任务（`user_id is None`）只有管理员可写。"""
    client, sf = _client()
    try:
        register_and_login(client, email_prefix="task_ordinary")
        task_id = _seed_task(sf, None)

        resp = client.post(f"/api/v1/tasks/{task_id}/start")
        assert resp.status_code == 403, f"无主任务被普通用户写入: {resp.status_code}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def _seed_execution(sf: async_sessionmaker, student_id: int) -> int:
    async def _run() -> int:
        async with sf() as session:
            task = Task(title="执行归属测试", user_id=student_id, status=TaskStatus.IN_PROGRESS)
            session.add(task)
            await session.flush()
            execution = TaskExecution(task_id=task.id, student_id=student_id, status="in_progress")
            session.add(execution)
            await session.commit()
            return execution.id

    return asyncio.run(_run())


@pytest.mark.regression
def test_pipeline_execution_endpoints_reject_non_owner():
    """审计 M-01：执行记录的完成动作必须限于归属学生。"""
    client, sf = _client()
    try:
        owner_id, _, _ = register_and_login(client, email_prefix="exec_owner")
        execution_id = _seed_execution(sf, owner_id)

        register_and_login(client, email_prefix="exec_intruder")

        step = client.post(
            f"/api/v1/pipeline/executions/{execution_id}/steps/complete",
            json={"step_index": 1, "evidence_type": "photo", "evidence_value": {"url": "x"}},
        )
        done = client.post(f"/api/v1/pipeline/executions/{execution_id}/complete")
        assert step.status_code == 403, f"非归属学生完成步骤未被拒绝: {step.status_code}"
        assert done.status_code == 403, f"非归属学生完成执行未被拒绝: {done.status_code}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ---------------------------------------------------------------------------
# 创建路径的身份收敛（审计 M-02 残留）
#
# 上一批把 M-02 记为已关闭，但收敛的只是**已有身份注入**的端点。运行期扫描
# （载入真实 app 枚举路由，因此不漏 router 前缀——A1 指出过的同一个坑）显示
# 仍有写端点把请求体自述的 `user_id` / `student_id` 直接当作操作人。
# 下列三条断言的是行为：拿 A 的令牌、在请求体里写 B 的编号，必须 403。
#
# 每条都同时断言「不声称他人身份时不被拒」——否则把守卫写成无条件拒绝
# 也能让拒绝断言全绿，测试就分不出「拒对了」和「全拒了」。
# ---------------------------------------------------------------------------


def _seed_sop(sf: async_sessionmaker) -> int:
    from app.models.sop import SOP

    async def _run() -> int:
        async with sf() as session:
            sop = SOP(name="身份收敛测试 SOP", description="fixture", applicable_model="ATOM-01")
            session.add(sop)
            await session.commit()
            return sop.id

    return asyncio.run(_run())


@pytest.mark.regression
def test_create_task_rejects_impersonated_owner():
    """`POST /tasks` 曾无身份注入：请求体给谁的编号，任务就归谁。"""
    client, sf = _client()
    try:
        victim_id, _, _ = register_and_login(client, email_prefix="task_create_victim")
        sop_id = _seed_sop(sf)
        actor_id, _, _ = register_and_login(client, email_prefix="task_create_actor")

        impersonated = client.post(
            "/api/v1/tasks",
            json={"title": "冒用他人身份建任务", "sop_id": sop_id, "user_id": victim_id},
        )
        assert impersonated.status_code == 403, (
            f"请求体声称他人身份未被拒绝: {impersonated.status_code} {impersonated.text}"
        )

        own = client.post(
            "/api/v1/tasks",
            json={"title": "以本人身份建任务", "sop_id": sop_id},
        )
        assert own.status_code != 403, f"本人建任务被误拒: {own.status_code} {own.text}"
        assert own.json()["user_id"] == actor_id, "任务未归属到认证身份"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_create_task_from_diagnosis_rejects_impersonated_student():
    """`POST /pipeline/tasks/from-diagnosis` 的 student_id 曾直接落库为执行记录归属。"""
    client, sf = _client()
    try:
        victim_id, _, _ = register_and_login(client, email_prefix="diag_victim")
        register_and_login(client, email_prefix="diag_actor")

        resp = client.post(
            "/api/v1/pipeline/tasks/from-diagnosis",
            json={
                "diagnosis_trace_id": "trace-identity-001",
                "fault_type": "joint_overheat",
                "student_id": victim_id,
            },
        )
        assert resp.status_code == 403, (
            f"为他人创建维保任务未被拒绝: {resp.status_code} {resp.text}"
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_generate_training_project_rejects_impersonated_user():
    """`POST /training/projects/generate` 用该编号读画像/弱项/训练历史。

    拒绝必须发生在 SSE 生成器**之前**：生成器内的 `except Exception` 会把
    拒绝异常吞成一条 200 的 error 事件，那样的"拒绝"对调用方不可见。
    """
    client, sf = _client()
    try:
        victim_id, _, _ = register_and_login(client, email_prefix="proj_victim")
        register_and_login(client, email_prefix="proj_actor")

        resp = client.post(
            "/api/v1/training/projects/generate",
            json={"user_id": victim_id, "robot_id": "atom-01", "difficulty": "medium"},
        )
        assert resp.status_code == 403, (
            f"以他人编号生成训练项目未被拒绝: {resp.status_code} {resp.text[:300]}"
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
