"""学生机器人列表 API 测试"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility, TeacherRobotBinding
from app.services.authz_guard import ActorContext, get_current_actor
from main import app


# ---------------------------------------------------------------------------
# Test environment fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def student_robots_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    """每个模块独立的 in-memory SQLite 环境。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id: int, role: str) -> dict[str, str]:
    """构造绕过真实 token 校验的 mock headers（通过依赖覆盖注入）。"""
    return {"X-Test-User-Id": str(user_id), "X-Test-User-Role": role}


def _make_actor_override(user_id: int, role: str):
    """为指定用户/角色生成 get_current_actor 覆盖函数。"""
    async def _override():
        return ActorContext(
            user_id=user_id,
            email=f"user{user_id}@test.com",
            roles={role},
            permissions=set(),
        )
    return _override


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _setup_teacher_with_robots(session_factory):
    """创建教师 + 2 个 READY 机器人 + 1 个 DRAFT 机器人，返回 (teacher, ready_robots, draft_robot)。"""
    async with session_factory() as session:
        teacher = User(
            email="teacher_robot@test.com",
            password_hash="hashed",
            role="teacher",
            full_name="Robot Teacher",
        )
        session.add(teacher)
        await session.flush()

        robot_ready_1 = RobotModel(
            brand="FANUC", model_name="M-20iA", version="1.0",
            owner_teacher_id=teacher.id, status=RobotStatus.READY,
            visibility=RobotVisibility.PRIVATE,
        )
        robot_ready_2 = RobotModel(
            brand="ABB", model_name="IRB 1200", version="2.0",
            owner_teacher_id=teacher.id, status=RobotStatus.READY,
            visibility=RobotVisibility.SHARED,
        )
        robot_draft = RobotModel(
            brand="KUKA", model_name="KR 10", version="1.0",
            owner_teacher_id=teacher.id, status=RobotStatus.DRAFT,
            visibility=RobotVisibility.PRIVATE,
        )
        session.add_all([robot_ready_1, robot_ready_2, robot_draft])
        await session.flush()

        for robot in [robot_ready_1, robot_ready_2, robot_draft]:
            session.add(TeacherRobotBinding(
                teacher_id=teacher.id,
                robot_model_id=robot.id,
                binding_type="owner",
            ))
        await session.commit()

        # 刷新获取最新 id
        await session.refresh(teacher)
        await session.refresh(robot_ready_1)
        await session.refresh(robot_ready_2)
        await session.refresh(robot_draft)
        return (
            teacher.id,
            [robot_ready_1.id, robot_ready_2.id],
            robot_draft.id,
        )


async def _create_student(session_factory, *, teacher_id: int | None) -> int:
    """创建学生用户，返回其 id。"""
    from uuid import uuid4
    async with session_factory() as session:
        student = User(
            email=f"student_{uuid4().hex[:8]}@test.com",
            password_hash="hashed",
            role="student",
            full_name="Robot Student",
            teacher_id=teacher_id,
        )
        session.add(student)
        await session.commit()
        await session.refresh(student)
        return student.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_student_robots_returns_only_ready(student_robots_env):
    """学生只能看到绑定教师名下 status=READY 的机器人"""
    client, session_factory = student_robots_env

    teacher_id, ready_ids, _ = asyncio.run(_setup_teacher_with_robots(session_factory))
    student_id = asyncio.run(_create_student(session_factory, teacher_id=teacher_id))

    app.dependency_overrides[get_current_actor] = _make_actor_override(student_id, "student")
    try:
        response = client.get(f"/api/v1/students/{student_id}/robots")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        ids = {item["id"] for item in data["items"]}
        assert ids == set(ready_ids)
    finally:
        app.dependency_overrides.pop(get_current_actor, None)


def test_student_robots_no_teacher_returns_empty(student_robots_env):
    """没有绑定教师的学生返回空列表"""
    client, session_factory = student_robots_env

    orphan_id = asyncio.run(_create_student(session_factory, teacher_id=None))

    app.dependency_overrides[get_current_actor] = _make_actor_override(orphan_id, "student")
    try:
        response = client.get(f"/api/v1/students/{orphan_id}/robots")
        assert response.status_code == 200
        assert response.json()["total"] == 0
    finally:
        app.dependency_overrides.pop(get_current_actor, None)


def test_student_robots_forbidden_for_other_student(student_robots_env):
    """学生不能查看其他学生的机器人列表"""
    client, session_factory = student_robots_env

    student_id = asyncio.run(_create_student(session_factory, teacher_id=None))
    other_id = asyncio.run(_create_student(session_factory, teacher_id=None))

    # 以 other_id 身份请求 student_id 的机器人列表
    app.dependency_overrides[get_current_actor] = _make_actor_override(other_id, "student")
    try:
        response = client.get(f"/api/v1/students/{student_id}/robots")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
