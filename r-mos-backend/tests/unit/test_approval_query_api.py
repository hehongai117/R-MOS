"""Gate-2 F-002：Approvals Query API 最小门禁测试。"""
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
import app.models as app_models  # noqa: F401  # 确保模型注册完整


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


def _register_and_login(client: TestClient, *, email: str, full_name: str) -> tuple[str, int]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": full_name},
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


def _create_pending_approval(client: TestClient, token: str, title: str) -> dict:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "intent": "create_sop_draft",
            "skill_id": "sop.write.create_draft",
            "tool_name": "sops.create_draft",
            "tool_args": {"title": title},
            "side_effects": ["sops.write"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_approval"
    return payload


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    actor_user_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.actor_user_id == actor_user_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def test_admin_can_query_approvals_and_records_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, creator_user_id = _register_and_login(
            client,
            email="approval_query_creator@example.com",
            full_name="创建者A",
        )
        _create_pending_approval(client, creator_token, "审批查询测试A")

        creator_token_b, _ = _register_and_login(
            client,
            email="approval_query_creator_b@example.com",
            full_name="创建者B",
        )
        _create_pending_approval(client, creator_token_b, "审批查询测试B")

        admin_token, _ = _register_and_login(
            client,
            email="approval_query_admin@example.com",
            full_name="管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_query_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            f"/api/v1/ai/approvals?status=pending&actor_user_id={creator_user_id}&limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] >= 1
        assert body["items"]
        assert all(item["status"] == "pending" for item in body["items"])
        assert all(item["created_by_user_id"] == str(creator_user_id) for item in body["items"])

        trace_id = response.headers.get("X-Trace-ID")
        assert trace_id
        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="approval_query",
                decision="allow",
                actor_user_id=str(admin_user_id),
            )
        )
        assert event is not None
        assert event.trace_id == trace_id
        assert event.resource_type == "Approval"
        assert event.resource_id == "*"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auditor_can_query_approvals() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="approval_query_creator_2@example.com",
            full_name="创建者",
        )
        _create_pending_approval(client, creator_token, "审批查询测试")

        auditor_token, _ = _register_and_login(
            client,
            email="approval_query_auditor@example.com",
            full_name="审计员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_query_auditor@example.com",
                role_name="auditor",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            "/api/v1/ai/approvals?limit=5&offset=0",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert response.status_code == 200
        assert response.json()["count"] >= 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_teacher_query_approvals_forbidden_and_records_deny_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="approval_query_creator_3@example.com",
            full_name="创建者",
        )
        _create_pending_approval(client, creator_token, "审批查询测试")

        teacher_token, _ = _register_and_login(
            client,
            email="approval_query_teacher@example.com",
            full_name="教师",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_query_teacher@example.com",
                role_name="teacher",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            "/api/v1/ai/approvals",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error_type"] == "RoleRequiredError"
        assert body["details"]["code"] == "AUTHZ_002"
        assert body["details"]["details"]["reason"] == "missing_role:admin_or_auditor"

        trace_id = response.headers.get("X-Trace-ID")
        assert trace_id
        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="permission_denied",
                decision="deny",
                actor_user_id=str(teacher_user_id),
            )
        )
        assert event is not None
        assert event.trace_id == trace_id
        assert event.resource_type == "Route"
        assert event.resource_id == "/api/v1/ai/approvals"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_query_approvals_without_token_returns_401() -> None:
    client, _session_factory = _build_client()
    try:
        response = client.get("/api/v1/ai/approvals")
        assert response.status_code == 401
        body = response.json()
        assert body["error_type"] == "AuthenticationRequiredError"
        assert body["details"]["code"] == "AUTH_003"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
