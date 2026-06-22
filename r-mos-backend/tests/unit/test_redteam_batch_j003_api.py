"""Gate-3 J-003：红队用例跑批最小闭环测试。"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # 确保模型注册完整

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"

J003_METRIC_ID = "sec_t001_t007_batch"


def _build_client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=TEST_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory
    return TestClient(app), session_factory


def _register_and_login(client: TestClient, *, email: str, full_name: str) -> tuple[str, int]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": full_name,
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"], user_id


async def _grant_role_permissions(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> int:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        role_result = await session.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} 角色")
            session.add(role)
            await session.flush()

        for permission_key in permission_keys:
            permission_result = await session.execute(
                select(Permission).where(Permission.key == permission_key)
            )
            permission = permission_result.scalar_one_or_none()
            if permission is None:
                resource_type, action = permission_key.split(":", 1)
                permission = Permission(
                    key=permission_key,
                    description=f"{permission_key} 权限",
                    resource_type=resource_type,
                    action=action,
                )
                session.add(permission)
                await session.flush()

            role_permission_result = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission_result.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        user_role_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if user_role_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        return int(user.id)


async def _seed_redteam_audits(session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_BLACKLIST_KEYWORD",
                    trace_id="j003-seed-sec-001",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_INJECTION_PATTERN",
                    trace_id="j003-seed-sec-002",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_INVALID_REFERENCE",
                    trace_id="j003-seed-sec-003",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_PARAM_OUT_OF_RANGE",
                    trace_id="j003-seed-sec-004",
                ),
                AuditEvent(
                    actor_user_id="2002",
                    action="access_denied",
                    decision="deny",
                    resource_type="AssignmentAttempt",
                    resource_id="10001",
                    reason="student_attempt_scope_mismatch",
                    trace_id="j003-seed-sec-005",
                ),
                AuditEvent(
                    actor_user_id="7002",
                    action="access_denied",
                    decision="deny",
                    resource_type="AssignmentAttempt",
                    resource_id="10002",
                    reason="teacher_course_scope_mismatch",
                    trace_id="j003-seed-sec-006",
                ),
                AuditEvent(
                    actor_user_id="7001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="AIToolCall",
                    resource_id="501",
                    reason="feature_flag_disabled",
                    trace_id="j003-seed-sec-007",
                ),
            ]
        )
        await session.commit()


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    resource_type: str,
    resource_id: str,
    actor_user_id: str | None = None,
    trace_id: str | None = None,
) -> AuditEvent | None:
    async with session_factory() as session:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if trace_id is not None:
            stmt = stmt.where(AuditEvent.trace_id == trace_id)

        result = await session.execute(stmt)
        return result.scalars().first()


def test_j003_admin_redteam_batch_returns_summary_and_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        asyncio.run(_seed_redteam_audits(session_factory))

        admin_token, _ = _register_and_login(
            client,
            email="j003_admin@example.com",
            full_name="J003 管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="j003_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )

        trace_id = "j003-admin-trace"
        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": trace_id},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == J003_METRIC_ID
        assert body["trace_id"] == trace_id
        assert body["total"] == 7
        assert body["pass_count"] == 7
        assert body["meets_target"] is True
        assert set(body["cases"].keys()) == {
            "SEC-T001",
            "SEC-T002",
            "SEC-T003",
            "SEC-T004",
            "SEC-T005",
            "SEC-T006",
            "SEC-T007",
        }

        allow_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="redteam_batch_read",
                decision="allow",
                resource_type="RedTeamBatch",
                resource_id=J003_METRIC_ID,
                actor_user_id=str(admin_user_id),
                trace_id=trace_id,
            )
        )
        assert allow_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_j003_teacher_without_permission_returns_403_and_records_route_deny() -> None:
    client, session_factory = _build_client()
    try:
        teacher_token, teacher_user_id = _register_and_login(
            client,
            email="j003_teacher_no_perm@example.com",
            full_name="J003 教师无权限",
        )
        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error_type"] == "PermissionDeniedError"
        assert body["details"]["code"] == "AUTHZ_001"

        deny_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="permission_denied",
                decision="deny",
                resource_type="Route",
                resource_id="/api/v1/ai/replay/metrics/red-team-pass-rate",
                actor_user_id=str(teacher_user_id),
            )
        )
        assert deny_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_j003_teacher_with_permission_returns_404_and_records_real_resource_id() -> None:
    client, session_factory = _build_client()
    try:
        teacher_token, _ = _register_and_login(
            client,
            email="j003_teacher_perm@example.com",
            full_name="J003 教师有权限",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="j003_teacher_perm@example.com",
                role_name="teacher",
                permission_keys=["audit_events:read"],
            )
        )

        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload["error_type"] == "ReadAccessDeniedError"
        assert payload["details"]["code"] == "READ_ACCESS_DENIED"
        assert payload["details"]["details"]["resource_id"] == J003_METRIC_ID

        deny_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="access_denied",
                decision="deny",
                resource_type="RedTeamBatch",
                resource_id=J003_METRIC_ID,
                actor_user_id=str(teacher_user_id),
            )
        )
        assert deny_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
