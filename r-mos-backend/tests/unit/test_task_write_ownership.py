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
