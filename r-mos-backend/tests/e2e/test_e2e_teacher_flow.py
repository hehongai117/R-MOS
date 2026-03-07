from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.audit_event import AuditEvent
from tests.e2e.helpers import register_and_login, set_user_role


async def _find_notify_event(
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


def test_e2e_teacher_flow(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = e2e_env

    teacher_id, teacher_email, _ = register_and_login(client, email_prefix="e2e_teacher")
    student_id, _student_email, _ = register_and_login(client, email_prefix="e2e_student")
    asyncio.run(set_user_role(session_factory, user_id=teacher_id, role="teacher"))

    teacher_login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": teacher_email, "password": "StrongPass123"},
    )
    assert teacher_login_resp.status_code == 200
    assert teacher_login_resp.json()["role"] == "teacher"

    class_resp = client.post(
        "/api/v1/classes",
        json={"name": "E2E Teacher Class", "teacherId": teacher_id},
    )
    assert class_resp.status_code == 201
    class_id = class_resp.json()["id"]

    enroll_resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": student_id},
    )
    assert enroll_resp.status_code == 201

    class_list_resp = client.get("/api/v1/classes")
    assert class_list_resp.status_code == 200
    assert any(item["id"] == class_id for item in class_list_resp.json())

    session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": student_id,
            "project_id": "proj-teacher-flow",
            "project_snapshot": {"estimated_time": 20, "steps": ["step-1"]},
        },
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    step_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-1",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "tools_confirmed": [{"tool_id": "gauge", "status": "confirmed"}],
        },
    )
    assert step_resp.status_code == 200

    session_status_resp = client.get(f"/api/v1/training/sessions/{session_id}")
    assert session_status_resp.status_code == 200
    assert session_status_resp.json()["user_id"] == student_id

    force_submit_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/force-submit",
        json={"teacher_id": teacher_id},
    )
    assert force_submit_resp.status_code == 200
    assert force_submit_resp.json()["submit_type"] == "teacher"

    notify_event = asyncio.run(_find_notify_event(session_factory, session_id=session_id))
    assert notify_event is not None
    assert notify_event.reason == "teacher_force_submit"

    feedback_resp = client.get(f"/api/v1/training/feedback/{session_id}?role=teacher")
    assert feedback_resp.status_code == 200
    feedback_payload = feedback_resp.json()
    assert feedback_payload["teaching_diagnosis"]
    assert feedback_payload["ranking_percentile"] is not None
    assert feedback_payload["hint_level_suggestion"] is not None
