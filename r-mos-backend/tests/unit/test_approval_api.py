"""Gate-2 F-001：最小审批流测试。"""
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
from app.models.command_runtime import AIToolCall, Command
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


def _register_and_login(client: TestClient, *, email: str, full_name: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": full_name},
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


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
        return user.id


async def _load_command_bundle(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> tuple[Command, AIToolCall, Approval]:
    async with session_factory() as session:
        command_result = await session.execute(
            select(Command).where(Command.trace_id == trace_id)
        )
        command = command_result.scalar_one()

        tool_result = await session.execute(
            select(AIToolCall).where(AIToolCall.trace_id == trace_id)
        )
        tool_call = tool_result.scalar_one()

        approval_result = await session.execute(
            select(Approval).where(Approval.trace_id == trace_id)
        )
        approval = approval_result.scalar_one()

        return command, tool_call, approval


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    resource_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.resource_type == "Approval",
                AuditEvent.resource_id == resource_id,
                AuditEvent.decision == "allow",
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def _create_write_command(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "intent": "create_sop_draft",
            "skill_id": "sop.write.create_draft",
            "tool_name": "sops.create_draft",
            "tool_args": {"title": "F001测试"},
            "side_effects": ["sops.write"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_approval"
    assert payload["approval_id"] is not None
    return payload


def test_write_tool_creates_pending_approval() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="approval_creator@example.com", full_name="创建者")
        payload = _create_write_command(client, token)

        command, tool_call, approval = asyncio.run(
            _load_command_bundle(session_factory, trace_id=payload["trace_id"])
        )
        assert command.status == "pending_approval"
        assert tool_call.status == "pending"
        assert approval.status == "pending"
        assert command.approval_id == approval.id
        assert tool_call.approval_id == approval.id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_admin_can_grant_pending_approval_records_audit_and_updates_status() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(client, email="approval_creator_grant@example.com", full_name="创建者")
        payload = _create_write_command(client, creator_token)
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(client, email="approval_admin_grant@example.com", full_name="管理员")
        admin_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_admin_grant@example.com",
                role_name="admin",
                permission_keys=["approvals:grant"],
            )
        )

        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "审批通过"},
        )
        assert grant_resp.status_code == 200
        grant_payload = grant_resp.json()
        assert grant_payload["status"] == "granted"

        _command, _tool_call, approval = asyncio.run(
            _load_command_bundle(session_factory, trace_id=payload["trace_id"])
        )
        assert approval.status == "granted"
        assert approval.decided_by_user_id == str(admin_id)

        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="approval_granted",
                resource_id=str(approval_id),
            )
        )
        assert event is not None
        assert event.trace_id == payload["trace_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_admin_can_reject_pending_approval_records_audit_and_updates_status() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(client, email="approval_creator_reject@example.com", full_name="创建者")
        payload = _create_write_command(client, creator_token)
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(client, email="approval_admin_reject@example.com", full_name="管理员")
        admin_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="approval_admin_reject@example.com",
                role_name="admin",
                permission_keys=["approvals:reject"],
            )
        )

        reject_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "审批拒绝"},
        )
        assert reject_resp.status_code == 200
        reject_payload = reject_resp.json()
        assert reject_payload["status"] == "rejected"

        command, tool_call, approval = asyncio.run(
            _load_command_bundle(session_factory, trace_id=payload["trace_id"])
        )
        assert approval.status == "rejected"
        assert approval.decided_by_user_id == str(admin_id)

        event = asyncio.run(
            _latest_audit(
                session_factory,
                action="approval_rejected",
                resource_id=str(approval_id),
            )
        )
        assert event is not None
        assert event.trace_id == payload["trace_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
