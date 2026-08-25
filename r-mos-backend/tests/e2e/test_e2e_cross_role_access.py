from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import register_and_login, set_user_role


def test_e2e_cross_role_access(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = e2e_env

    teacher_id, _teacher_email, teacher_login = register_and_login(
        client, email_prefix="e2e_teacher_scope"
    )
    # AUTH-104：改造后角色只来自令牌，不能再用 X-RMOS-Role 头伪装身份，
    # 因此这里必须注册一个**真的**学生账号，并以它的令牌发起越权请求。
    student_id, _student_email, student_login = register_and_login(
        client, email_prefix="e2e_student_scope", role="student", teacher_id=teacher_id
    )

    import asyncio

    asyncio.run(set_user_role(session_factory, user_id=teacher_id, role="teacher"))

    def _act_as(login: dict) -> None:
        client.headers["Authorization"] = f"Bearer {login['access_token']}"

    _act_as(teacher_login)
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

    _act_as(student_login)
    forbidden_resp = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "Forbidden Assignment"},
    )
    assert forbidden_resp.status_code == 403

    payload = forbidden_resp.json()
    assert payload["error_type"] == "WriteAccessDeniedError"

    serialized = json.dumps(payload, ensure_ascii=False)
    assert str(other_student_id) not in serialized
    assert "students" not in serialized.lower()
    assert "enrollments" not in serialized.lower()
