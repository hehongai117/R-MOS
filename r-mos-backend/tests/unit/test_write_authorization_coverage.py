"""Behavior regressions for runtime-discovered write authorization gaps."""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401 - register all SQLAlchemy models
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


@pytest.fixture
def write_auth_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory
    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def _act_as(client: TestClient, login: dict) -> None:
    client.headers["Authorization"] = f"Bearer {login['access_token']}"


def test_teaching_root_creates_reject_student_and_allow_teacher(
    write_auth_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = write_auth_env
    teacher_id, _, teacher_login = register_and_login(
        client, email_prefix="write_root_teacher"
    )
    _, _, student_login = register_and_login(
        client,
        email_prefix="write_root_student",
        role="student",
        teacher_id=teacher_id,
    )

    _act_as(client, student_login)
    denied_policy = client.post(
        "/api/v1/guidance-policies",
        json={"name": f"denied-policy-{uuid4().hex[:6]}"},
    )
    denied_class = client.post(
        "/api/v1/classes",
        json={"name": f"denied-class-{uuid4().hex[:6]}"},
    )
    assert denied_policy.status_code == 403
    assert denied_class.status_code == 403

    _act_as(client, teacher_login)
    allowed_policy = client.post(
        "/api/v1/guidance-policies",
        json={"name": f"allowed-policy-{uuid4().hex[:6]}"},
    )
    allowed_class = client.post(
        "/api/v1/classes",
        json={
            "name": f"allowed-class-{uuid4().hex[:6]}",
            "teacherId": teacher_id,
        },
    )
    assert allowed_policy.status_code == 201
    assert allowed_class.status_code == 201
    assert allowed_class.json()["teacherId"] == teacher_id


def test_class_scoped_writes_reject_outsider_and_allow_owner(
    write_auth_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = write_auth_env
    owner_id, _, owner_login = register_and_login(
        client, email_prefix="class_scope_owner"
    )
    _, _, outsider_login = register_and_login(
        client, email_prefix="class_scope_outsider"
    )
    student_id, _, _ = register_and_login(
        client,
        email_prefix="class_scope_student",
        role="student",
        teacher_id=owner_id,
    )

    _act_as(client, owner_login)
    class_response = client.post(
        "/api/v1/classes",
        json={"name": f"owned-class-{uuid4().hex[:6]}", "teacherId": owner_id},
    )
    assert class_response.status_code == 201
    class_id = class_response.json()["id"]

    _act_as(client, outsider_login)
    assert client.patch(
        f"/api/v1/classes/{class_id}", json={"name": "outsider-update"}
    ).status_code == 403
    assert client.post(
        "/api/v1/courses", json={"classId": class_id, "name": "outsider-course"}
    ).status_code == 403
    assert client.post(
        "/api/v1/enrollments", json={"classId": class_id, "studentId": student_id}
    ).status_code == 403
    assert client.post(
        "/api/v1/assignments", json={"classId": class_id, "title": "outsider-assignment"}
    ).status_code == 403

    _act_as(client, owner_login)
    assert client.patch(
        f"/api/v1/classes/{class_id}", json={"name": "owner-update"}
    ).status_code == 200
    assert client.post(
        "/api/v1/courses", json={"classId": class_id, "name": "owner-course"}
    ).status_code == 201
    assert client.post(
        "/api/v1/enrollments", json={"classId": class_id, "studentId": student_id}
    ).status_code == 201
    assert client.post(
        "/api/v1/assignments", json={"classId": class_id, "title": "owner-assignment"}
    ).status_code == 201


def test_attempt_create_requires_class_membership_and_allows_member(
    write_auth_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = write_auth_env
    teacher_id, _, teacher_login = register_and_login(
        client, email_prefix="attempt_scope_teacher"
    )
    student_id, _, student_login = register_and_login(
        client,
        email_prefix="attempt_scope_student",
        role="student",
        teacher_id=teacher_id,
    )

    _act_as(client, teacher_login)
    class_id = client.post(
        "/api/v1/classes",
        json={"name": f"attempt-class-{uuid4().hex[:6]}", "teacherId": teacher_id},
    ).json()["id"]
    assignment_id = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "membership-required"},
    ).json()["id"]

    _act_as(client, student_login)
    denied = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": student_id},
    )
    assert denied.status_code == 403

    _act_as(client, teacher_login)
    assert client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": student_id},
    ).status_code == 201

    _act_as(client, student_login)
    allowed = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": student_id},
    )
    assert allowed.status_code == 201
    assert allowed.json()["studentId"] == student_id


def test_session_submit_rejects_other_student_and_allows_owner(
    write_auth_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = write_auth_env
    owner_id, _, owner_login = register_and_login(
        client, email_prefix="submit_session_owner", role="student"
    )
    outsider_id, _, outsider_login = register_and_login(
        client, email_prefix="submit_session_outsider", role="student"
    )

    _act_as(client, owner_login)
    created = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": owner_id,
            "project_id": f"project-{uuid4().hex[:8]}",
            "project_snapshot": {"steps": []},
        },
    )
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    _act_as(client, outsider_login)
    denied = client.post(
        f"/api/v1/training/sessions/{session_id}/submit",
        json={"user_id": outsider_id, "confirm_incomplete": True},
    )
    assert denied.status_code == 403

    _act_as(client, owner_login)
    allowed = client.post(
        f"/api/v1/training/sessions/{session_id}/submit",
        json={"user_id": owner_id, "confirm_incomplete": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["user_id"] == owner_id
