from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import register_and_login, set_user_role


def test_e2e_cross_role_access(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = e2e_env

    teacher_id, _teacher_email, _ = register_and_login(client, email_prefix="e2e_teacher_scope")
    student_id, _student_email, _ = register_and_login(client, email_prefix="e2e_student_scope")

    import asyncio

    asyncio.run(set_user_role(session_factory, user_id=teacher_id, role="teacher"))

    class_resp = client.post(
        "/api/v1/classes",
        json={"name": "Cross Role Class", "teacherId": teacher_id},
    )
    assert class_resp.status_code == 201
    class_id = class_resp.json()["id"]

    other_student_id = 88199
    enroll_resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": other_student_id},
    )
    assert enroll_resp.status_code == 201

    forbidden_resp = client.post(
        "/api/v1/assignments",
        headers={"X-RMOS-Role": "student", "X-User-ID": str(student_id)},
        json={"classId": class_id, "title": "Forbidden Assignment"},
    )
    assert forbidden_resp.status_code == 403

    payload = forbidden_resp.json()
    assert payload["error_type"] == "WriteAccessDeniedError"

    serialized = json.dumps(payload, ensure_ascii=False)
    assert str(other_student_id) not in serialized
    assert "students" not in serialized.lower()
    assert "enrollments" not in serialized.lower()
