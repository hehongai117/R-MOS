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
from app.models.school import School
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login  # 复用既有登录基建


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
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        # AUTH-101 默认拒绝网关 + AUTH-104 身份只来自令牌：
        # 预置一位默认教师作为客户端默认身份；需要学生身份的用例用
        # register_and_login(client, ..., role="student") 切换。
        register_and_login(client, email_prefix="api_teaching_actor")
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def test_teacher_scope_access_for_student_attempt(
    teaching_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = teaching_api_env
    # AUTH-104：教师范围只能由令牌决定，不能再用 X-RMOS-Role / X-User-ID 伪装，
    # 因此这里注册两名真实教师：一名带班（in scope），一名不带班（out of scope）。
    teacher_id, _, owner_login = register_and_login(client, email_prefix="scope_owner_teacher")
    other_teacher_id, _, other_login = register_and_login(client, email_prefix="scope_other_teacher")

    def _act_as(login: dict) -> None:
        client.headers["Authorization"] = f"Bearer {login['access_token']}"

    _act_as(owner_login)
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
        json={"classId": class_id, "title": "Scope Assignment"},
    )
    assert assignment_resp.status_code == 201
    assignment_id = assignment_resp.json()["id"]

    # 审计 M-01：创建作业尝试已收紧为「本人或管理员」。原 setup 以教师身份为
    # 编造的学生 3001 建尝试；该学生既未注册也未选课，不构成「教师应可代建」的证据。
    # 本用例真正要验的是 replay 的**读**范围，故改为注册真实学生、选课后以其本人身份创建。
    student_id, _, student_login = register_and_login(
        client, email_prefix="scope_student", role="student", teacher_id=teacher_id
    )
    enroll_resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": student_id},
    )
    assert enroll_resp.status_code == 201

    _act_as(student_login)
    attempt_resp = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": student_id},
    )
    assert attempt_resp.status_code == 201
    attempt_id = attempt_resp.json()["id"]

    _act_as(owner_login)
    in_scope_resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
    assert in_scope_resp.status_code == 200
    assert in_scope_resp.json()["attemptId"] == attempt_id

    _act_as(other_login)
    out_scope_resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
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

    # 审计 M-02：force-submit 的操作人身份改由认证上下文决定后，
    # 编造的 id（原 901/902/9901）无法通过认证。改注册真实用户，
    # 并在每次调用前切换到对应身份——本用例要验的「管辖权强制」意图不变。
    teacher_id, _, owner_login = register_and_login(client, email_prefix="force_owner_teacher")
    outsider_teacher_id, _, outsider_login = register_and_login(
        client, email_prefix="force_outsider_teacher"
    )
    student_id, _, student_login = register_and_login(
        client, email_prefix="force_student", role="student", teacher_id=teacher_id
    )

    def _act_as(login: dict) -> None:
        client.headers["Authorization"] = f"Bearer {login['access_token']}"

    _act_as(owner_login)

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

    # 会话归学生本人所有，须以学生身份创建（M-01/M-02：不得为他人建会话）
    _act_as(student_login)
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

    # 无管辖权的教师：以其本人身份发起，应被管辖权检查拒绝（而非被身份不符拒绝）
    _act_as(outsider_login)
    denied_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/force-submit",
        json={"teacher_id": outsider_teacher_id},
    )
    assert denied_resp.status_code == 403

    _act_as(owner_login)
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


def test_grade_attempt_rejects_student_self_grading(
    teaching_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """审计 M-01：评分是教师职权，**学生本人必须被拒绝**。

    修复前该端点无身份、无归属校验（A4 记载「任意登录用户可给任意作业打分」）。
    若把它"修"成「仅对象所有者」，就会变成「学生可以给自己打分」——
    洞只是换了位置。本用例断言三种身份的结果：
    学生本人 403、管辖外教师 403、管辖内教师 200。
    """
    client, _ = teaching_api_env
    teacher_id, _, owner_login = register_and_login(client, email_prefix="grade_owner_teacher")
    _, _, outsider_login = register_and_login(client, email_prefix="grade_outsider_teacher")

    def _act_as(login: dict) -> None:
        client.headers["Authorization"] = f"Bearer {login['access_token']}"

    _act_as(owner_login)
    class_id = client.post(
        "/api/v1/classes",
        json={"name": f"grade-{uuid4().hex[:6]}", "teacherId": teacher_id},
    ).json()["id"]
    assignment_id = client.post(
        "/api/v1/assignments", json={"classId": class_id, "title": "Grade Assignment"}
    ).json()["id"]

    student_id, _, student_login = register_and_login(
        client, email_prefix="grade_student", role="student", teacher_id=teacher_id
    )
    assert client.post(
        "/api/v1/enrollments", json={"classId": class_id, "studentId": student_id}
    ).status_code == 201

    _act_as(student_login)
    attempt_id = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": student_id},
    ).json()["id"]
    assert client.patch(
        f"/api/v1/attempts/{attempt_id}", json={"status": "completed"}
    ).status_code == 200

    # 学生本人给自己打分：必须拒绝
    _act_as(student_login)
    self_grade = client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 100})
    assert self_grade.status_code == 403, f"学生给自己打分未被拒绝: {self_grade.status_code}"

    # 管辖外教师：必须拒绝
    _act_as(outsider_login)
    outsider_grade = client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 60})
    assert outsider_grade.status_code == 403, f"管辖外教师未被拒绝: {outsider_grade.status_code}"

    # 管辖内教师：放行
    _act_as(owner_login)
    ok = client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 88})
    assert ok.status_code == 200, f"管辖内教师被误拒: {ok.status_code} {ok.text[:200]}"
