"""
T-03-c teaching management API tests.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from main import app


@pytest.fixture(scope="module")
def teaching_api_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def test_teacher_scope_access_for_student_attempt(
    teaching_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = teaching_api_env
    teacher_id = 101
    other_teacher_id = 202

    class_resp = client.post(
        "/api/v1/classes",
        json={
            "name": f"T03-class-{uuid4().hex[:6]}",
            "teacherId": teacher_id,
        },
    )
    assert class_resp.status_code == 201
    class_id = class_resp.json()["id"]

    assignment_resp = client.post(
        "/api/v1/assignments",
        headers={"X-RMOS-Role": "teacher"},
        json={"classId": class_id, "title": "Scope Assignment"},
    )
    assert assignment_resp.status_code == 201
    assignment_id = assignment_resp.json()["id"]

    attempt_resp = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": 3001},
    )
    assert attempt_resp.status_code == 201
    attempt_id = attempt_resp.json()["id"]

    in_scope_resp = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={"X-RMOS-Role": "teacher", "X-User-ID": str(teacher_id)},
    )
    assert in_scope_resp.status_code == 200
    assert in_scope_resp.json()["attemptId"] == attempt_id

    out_scope_resp = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={"X-RMOS-Role": "teacher", "X-User-ID": str(other_teacher_id)},
    )
    assert out_scope_resp.status_code == 404
    assert out_scope_resp.json()["error_type"] == "ReadAccessDeniedError"


def test_class_create_and_add_member(
    teaching_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = teaching_api_env

    class_resp = client.post(
        "/api/v1/classes",
        json={"name": f"T03-members-{uuid4().hex[:6]}", "teacherId": 501},
    )
    assert class_resp.status_code == 201
    class_id = class_resp.json()["id"]

    enroll_resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": 7001},
    )
    assert enroll_resp.status_code == 201

    list_resp = client.get(f"/api/v1/enrollments?class_id={class_id}")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["studentId"] == 7001 for item in items)


async def _find_force_submit_notify_event(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "student_notified",
                AuditEvent.resource_type == "TrainingSession",
                AuditEvent.resource_id == session_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def test_teacher_force_submit_requires_scope_and_records_notification_event(
    teaching_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = teaching_api_env
    teacher_id = 901
    outsider_teacher_id = 902
    student_id = 9901

    class_resp = client.post(
        "/api/v1/classes",
        json={"name": f"T03-force-{uuid4().hex[:6]}", "teacherId": teacher_id},
    )
    assert class_resp.status_code == 201
    class_id = class_resp.json()["id"]

    enroll_resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": student_id},
    )
    assert enroll_resp.status_code == 201

    session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": student_id,
            "project_id": f"proj-{uuid4().hex[:8]}",
            "project_snapshot": {"estimated_time": 20},
        },
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    denied_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/force-submit",
        json={"teacher_id": outsider_teacher_id},
    )
    assert denied_resp.status_code == 403

    allowed_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/force-submit",
        json={"teacher_id": teacher_id},
    )
    assert allowed_resp.status_code == 200
    assert allowed_resp.json()["submit_type"] == "teacher"

    event = asyncio.run(
        _find_force_submit_notify_event(session_factory, session_id=session_id)
    )
    assert event is not None
    assert event.actor_user_id == str(teacher_id)
    assert event.reason == "teacher_force_submit"
