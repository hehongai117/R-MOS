"""
Gate-1 C-002/C-003：审计查询接口最小门禁测试。
"""
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
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # 确保模型全部注册


def _build_client() -> tuple[TestClient, async_sessionmaker]:
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
    return TestClient(app), session_factory


async def _grant_role(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> None:
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


async def _seed_audit_events(session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                AuditEvent(
                    actor_user_id="1001",
                    action="access_denied",
                    resource_type="AssignmentAttempt",
                    resource_id="201",
                    decision="deny",
                    reason="owner_mismatch",
                    request_meta={"path": "/api/v1/teaching/attempts/201"},
                    trace_id="trace-deny-1",
                ),
                AuditEvent(
                    actor_user_id="1002",
                    action="login_success",
                    resource_type="Auth",
                    resource_id="*",
                    decision="allow",
                    reason="credentials_ok",
                    request_meta={"path": "/api/v1/auth/login"},
                    trace_id="trace-allow-1",
                ),
            ]
        )
        await session.commit()


def _register_and_login(client: TestClient, email: str) -> tuple[int, str]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "审计测试用户",
        },
    )
    assert register_resp.status_code == 201
    user_id = register_resp.json()["user_id"]

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return user_id, login_resp.json()["access_token"]


def test_audit_events_admin_can_query_returns_200() -> None:
    client, session_factory = _build_client()
    try:
        admin_id, token = _register_and_login(client, "audit_admin@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="audit_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )
        asyncio.run(_seed_audit_events(session_factory))

        resp = client.get(
            "/api/v1/audit/events",
            params={"decision": "deny", "limit": 10, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["limit"] == 10
        assert payload["offset"] == 0
        assert payload["count"] >= 1
        assert isinstance(payload["items"], list)
        assert payload["items"]

        required_keys = {
            "id",
            "action",
            "decision",
            "actor_user_id",
            "resource_type",
            "resource_id",
            "reason",
            "trace_id",
            "created_at",
        }
        assert required_keys.issubset(set(payload["items"][0].keys()))
        assert admin_id > 0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_audit_events_auditor_can_query_returns_200() -> None:
    client, session_factory = _build_client()
    try:
        _, token = _register_and_login(client, "audit_auditor@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="audit_auditor@example.com",
                role_name="auditor",
                permission_keys=["audit_events:read"],
            )
        )
        asyncio.run(_seed_audit_events(session_factory))

        resp = client.get(
            "/api/v1/audit/events",
            params={"limit": 5, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["count"] >= 2
        assert len(payload["items"]) >= 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_audit_events_teacher_denied_and_records_deny_audit() -> None:
    client, session_factory = _build_client()
    try:
        teacher_id, token = _register_and_login(client, "audit_teacher@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="audit_teacher@example.com",
                role_name="teacher",
                permission_keys=["audit_events:read"],
            )
        )

        deny_resp = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert deny_resp.status_code == 403
        body = deny_resp.json()
        assert body["error_type"] == "RoleRequiredError"
        assert body["details"]["code"] == "AUTHZ_002"

        async def assert_deny_audit() -> None:
            async with session_factory() as session:
                result = await session.execute(
                    select(AuditEvent)
                    .where(
                        AuditEvent.action == "permission_denied",
                        AuditEvent.resource_type == "Route",
                        AuditEvent.resource_id == "/api/v1/audit/events",
                        AuditEvent.decision == "deny",
                    )
                    .order_by(AuditEvent.id.desc())
                )
                event = result.scalars().first()
                assert event is not None
                assert event.reason == "missing_role:admin_or_auditor"
                assert event.actor_user_id == str(teacher_id)

        asyncio.run(assert_deny_audit())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_audit_events_admin_query_records_audit_query_allow() -> None:
    client, session_factory = _build_client()
    try:
        admin_id, token = _register_and_login(client, "audit_admin_trace@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="audit_admin_trace@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )
        asyncio.run(_seed_audit_events(session_factory))

        resp = client.get(
            "/api/v1/audit/events",
            params={"actor_user_id": "1001", "limit": 20},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        async def assert_query_audit() -> None:
            async with session_factory() as session:
                result = await session.execute(
                    select(AuditEvent)
                    .where(
                        AuditEvent.action == "audit_query",
                        AuditEvent.decision == "allow",
                        AuditEvent.actor_user_id == str(admin_id),
                    )
                    .order_by(AuditEvent.id.desc())
                )
                event = result.scalars().first()
                assert event is not None
                assert event.resource_type == "AuditEvent"
                assert event.resource_id == "*"

        asyncio.run(assert_query_audit())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
