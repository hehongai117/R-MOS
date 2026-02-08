"""Gate-2 F-003：Approval Detail Query API 最小门禁测试。"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.approval import Approval
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
    resource_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.actor_user_id == actor_user_id,
                AuditEvent.resource_type == "Approval",
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


async def _approval_trace_id(session_factory: async_sessionmaker, approval_id: int) -> str:
    async with session_factory() as session:
        result = await session.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one()
        return approval.trace_id


def test_admin_can_read_approval_detail_and_records_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="approval_read_creator_admin@example.com",
            full_name="创建者",
        )
        payload = _create_pending_approval(client, creator_token, "审批详情查询")
        approval_id = int(payload["approval_id"])

        admin_token, _ = _register_and_login(
            client,
            email="approval_read_admin@example.com",
            full_name="管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_read_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.request.url.path == f"/api/v1/ai/approvals/{approval_id}"
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == approval_id
        assert body["status"] == "pending"

        trace_id = asyncio.run(_approval_trace_id(session_factory, approval_id))
        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="approval_read",
                decision="allow",
                actor_user_id=str(admin_user_id),
                resource_id=str(approval_id),
            )
        )
        assert event is not None
        assert event.trace_id == trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auditor_can_read_approval_detail() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="approval_read_creator_auditor@example.com",
            full_name="创建者",
        )
        payload = _create_pending_approval(client, creator_token, "审批详情查询")
        approval_id = int(payload["approval_id"])

        auditor_token, _ = _register_and_login(
            client,
            email="approval_read_auditor@example.com",
            full_name="审计员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_read_auditor@example.com",
                role_name="auditor",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == approval_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_teacher_read_approval_detail_returns_404_and_records_deny() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="approval_read_creator_teacher@example.com",
            full_name="创建者",
        )
        payload = _create_pending_approval(client, creator_token, "审批详情查询")
        approval_id = int(payload["approval_id"])

        teacher_token, _ = _register_and_login(
            client,
            email="approval_read_teacher@example.com",
            full_name="教师",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_read_teacher@example.com",
                role_name="teacher",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.request.url.path == f"/api/v1/ai/approvals/{approval_id}"
        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
        assert body["details"]["details"]["resource_id"] == str(approval_id)

        trace_id = asyncio.run(_approval_trace_id(session_factory, approval_id))
        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="permission_denied",
                decision="deny",
                actor_user_id=str(teacher_user_id),
                resource_id=str(approval_id),
            )
        )
        assert event is not None
        assert event.trace_id == trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_read_approval_without_token_returns_401() -> None:
    client, _session_factory = _build_client()
    try:
        response = client.get("/api/v1/ai/approvals/1")
        assert response.status_code == 401
        body = response.json()
        assert body["error_type"] == "AuthenticationRequiredError"
        assert body["details"]["code"] == "AUTH_003"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_read_approval_not_found_returns_404() -> None:
    client, session_factory = _build_client()
    try:
        admin_token, _ = _register_and_login(
            client,
            email="approval_read_not_found_admin@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_read_not_found_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:read"],
            )
        )

        response = client.get(
            "/api/v1/ai/approvals/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
