"""AUTH-104 / AUTH-101：教学域身份与对象归属边界（新规格）。

改造前 `app/api/v1/endpoints/teaching_roster.py` 用可伪造的 `X-RMOS-Role` /
`X-User-ID` 头做权限分支，且写法为 `if x_rmos_role and role not in {...}`
——**省略该头即可绕过整条判断**；`role == "student"` 之外的取值一律不限范围。
`app/services/access_control.py` 的审计操作者同样从 `X-User-ID` 头兜底。

本文件锁定新规格：

1. 授权分支与审计主体**只来自令牌**，客户端头对结果零影响；
2. 角色判断改为白名单式——省略/未知角色不再等于"不限制"；
3. 跨对象读取对外 404、跨对象写入 403，且拒绝审计带**真实资源编号**与令牌主体。

对应门禁：`AUTH-GATE-03`、`AUTH-GATE-04`、`AUTH-GATE-05`、`AUTH-GATE-06`、`AUTH-GATE-07`。
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.school import School
from app.models.teaching import Assignment, AssignmentAttempt, Enrollment, TeachingClass
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


def _build_client() -> tuple[TestClient, async_sessionmaker]:
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
    return TestClient(app), session_factory


def _act_as(client: TestClient, token: str) -> None:
    """把客户端默认身份切到指定令牌。"""
    client.headers["Authorization"] = f"Bearer {token}"


async def _seed_class_with_attempt(
    session_factory: async_sessionmaker,
    *,
    teacher_id: int,
    student_id: int,
) -> tuple[int, int, int]:
    """建 班级 → 选课 → 作业 → 尝试，返回 (class_id, assignment_id, attempt_id)。"""
    async with session_factory() as session:
        teaching_class = TeachingClass(name="身份边界测试班", teacher_id=teacher_id)
        session.add(teaching_class)
        await session.flush()

        session.add(Enrollment(class_id=teaching_class.id, student_id=student_id))

        assignment = Assignment(class_id=teaching_class.id, title="身份边界测试作业")
        session.add(assignment)
        await session.flush()

        attempt = AssignmentAttempt(
            assignment_id=assignment.id,
            student_id=student_id,
            attempt_index=1,
            status="in_progress",
        )
        session.add(attempt)
        await session.commit()
        return teaching_class.id, assignment.id, attempt.id


async def _deny_events(session_factory: async_sessionmaker) -> list[AuditEvent]:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent).where(AuditEvent.decision == "deny").order_by(AuditEvent.id)
        )
        return list(result.scalars().all())


@pytest.fixture()
def roster_env():
    """两名同校学生 + 两名教师；班级归教师 A，尝试归学生 A。"""
    client, session_factory = _build_client()
    try:
        teacher_a, _, login_a = register_and_login(client, email_prefix="ident_teacher_a")
        teacher_b, _, login_b = register_and_login(client, email_prefix="ident_teacher_b")
        student_a, _, login_sa = register_and_login(
            client, email_prefix="ident_student_a", role="student", teacher_id=teacher_a
        )
        student_b, _, login_sb = register_and_login(
            client, email_prefix="ident_student_b", role="student", teacher_id=teacher_a
        )

        class_id, assignment_id, attempt_id = asyncio.run(
            _seed_class_with_attempt(
                session_factory, teacher_id=teacher_a, student_id=student_a
            )
        )

        yield {
            "client": client,
            "session_factory": session_factory,
            "teacher_a": (teacher_a, login_a["access_token"]),
            "teacher_b": (teacher_b, login_b["access_token"]),
            "student_a": (student_a, login_sa["access_token"]),
            "student_b": (student_b, login_sb["access_token"]),
            "class_id": class_id,
            "assignment_id": assignment_id,
            "attempt_id": attempt_id,
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_forged_role_header_does_not_widen_scope(roster_env) -> None:
    """AUTH-GATE-03：学生令牌 + 伪造 `X-RMOS-Role: teacher`，仍受学生范围限制。"""
    client = roster_env["client"]
    _act_as(client, roster_env["student_b"][1])

    resp = client.get(
        f"/api/v1/attempts/{roster_env['attempt_id']}",
        headers={"X-RMOS-Role": "teacher", "X-User-ID": str(roster_env["student_a"][0])},
    )
    assert resp.status_code == 404, resp.text


def test_omitted_role_header_does_not_widen_scope(roster_env) -> None:
    """AUTH-GATE-04：省略角色头不得放宽范围。

    改造前 `if x_rmos_role and ...` 的写法使"不发头"直接跳过判断。
    """
    client = roster_env["client"]
    _act_as(client, roster_env["student_b"][1])

    resp = client.get(f"/api/v1/attempts/{roster_env['attempt_id']}")
    assert resp.status_code == 404, resp.text


def test_forged_user_id_header_does_not_change_scope(roster_env) -> None:
    """AUTH-GATE-03：伪造 `X-User-ID` 不能把范围换成他人。"""
    client = roster_env["client"]
    _act_as(client, roster_env["student_b"][1])

    resp = client.get(
        f"/api/v1/attempts/{roster_env['attempt_id']}",
        headers={"X-User-ID": str(roster_env["student_a"][0])},
    )
    assert resp.status_code == 404, resp.text


def test_owner_student_can_read_own_attempt(roster_env) -> None:
    """正向边界：本人读自己的尝试必须成功，收紧不能误伤正常路径。"""
    client = roster_env["client"]
    _act_as(client, roster_env["student_a"][1])

    resp = client.get(f"/api/v1/attempts/{roster_env['attempt_id']}")
    assert resp.status_code == 200, resp.text


def test_student_cannot_write_class(roster_env) -> None:
    """AUTH-GATE-06：学生写班级返回 403，且省略角色头不能绕过。"""
    client = roster_env["client"]
    _act_as(client, roster_env["student_a"][1])

    resp = client.patch(
        f"/api/v1/classes/{roster_env['class_id']}",
        json={"name": "学生不该改得动"},
    )
    assert resp.status_code == 403, resp.text


def test_cross_teacher_attempt_replay_denied(roster_env) -> None:
    """AUTH-GATE-05：教师 B 读教师 A 班级下的尝试回放返回 404。"""
    client = roster_env["client"]
    _act_as(client, roster_env["teacher_b"][1])

    resp = client.get(f"/api/v1/teaching/attempts/{roster_env['attempt_id']}/replay")
    assert resp.status_code == 404, resp.text


def test_deny_audit_uses_token_subject_and_real_resource_id(roster_env) -> None:
    """AUTH-GATE-07：拒绝审计的操作者恒等于令牌主体，资源编号为真实编号。

    即使请求里伪造了 `X-User-ID`，审计也不得采用它。
    """
    client = roster_env["client"]
    student_b_id, student_b_token = roster_env["student_b"]
    _act_as(client, student_b_token)

    resp = client.get(
        f"/api/v1/attempts/{roster_env['attempt_id']}",
        headers={"X-User-ID": "999999"},
    )
    assert resp.status_code == 404

    events = asyncio.run(_deny_events(roster_env["session_factory"]))
    assert events, "越权读取必须留下 deny 审计"
    event = events[-1]
    assert event.actor_user_id == str(student_b_id), (
        f"审计操作者应为令牌主体 {student_b_id}，实际 {event.actor_user_id}"
    )
    assert event.resource_id == str(roster_env["attempt_id"]), (
        f"审计资源编号应为真实 attempt {roster_env['attempt_id']}，实际 {event.resource_id}"
    )
    assert event.resource_type == "AssignmentAttempt"
