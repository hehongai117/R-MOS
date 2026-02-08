"""Gate-2 E-002：审批结果驱动工具执行闭环测试。"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import func, select
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


def _create_pending_write_command(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "intent": "create_sop_draft",
            "skill_id": "sop.write.create_draft",
            "tool_name": "sops.create_draft",
            "tool_args": {"title": "E002测试"},
            "side_effects": ["sops.write"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_approval"
    assert payload["approval_id"] is not None
    return payload


async def _load_runtime_by_trace(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> tuple[Command, AIToolCall, Approval]:
    async with session_factory() as session:
        command = (
            await session.execute(select(Command).where(Command.trace_id == trace_id))
        ).scalar_one()
        tool_call = (
            await session.execute(select(AIToolCall).where(AIToolCall.trace_id == trace_id))
        ).scalar_one()
        approval = (
            await session.execute(select(Approval).where(Approval.trace_id == trace_id))
        ).scalar_one()
        return command, tool_call, approval


async def _find_latest_audit(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
    action: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.trace_id == trace_id,
                AuditEvent.action == action,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


async def _count_audit_by_action(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
    action: str,
) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.trace_id == trace_id,
                AuditEvent.action == action,
            )
        )
        return int(result.scalar_one())


def test_grant_approval_executes_write_stub_and_records_tool_success_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(
            client,
            email="e002_creator_grant@example.com",
            full_name="创建者",
        )
        payload = _create_pending_write_command(client, creator_token)
        trace_id = payload["trace_id"]
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(
            client,
            email="e002_admin_grant@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e002_admin_grant@example.com",
                role_name="admin",
                permission_keys=["approvals:grant"],
            )
        )

        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "E-002审批通过"},
        )
        assert grant_resp.status_code == 200
        grant_payload = grant_resp.json()
        assert grant_payload["status"] == "granted"
        assert grant_payload["command_status"] == "succeeded"
        assert grant_payload["tool_call_status"] == "success"
        assert grant_payload["tool_call_event_written"] is True

        command, tool_call, approval = asyncio.run(
            _load_runtime_by_trace(session_factory, trace_id=trace_id)
        )
        assert command.status == "succeeded"
        assert tool_call.status == "success"
        assert approval.status == "granted"
        assert command.trace_id == tool_call.trace_id == approval.trace_id == trace_id

        success_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_success",
            )
        )
        pending_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_pending",
            )
        )
        assert pending_event is not None
        assert pending_event.tool_call_args == {"title": "E002测试"}
        assert pending_event.side_effects_applied == ["sops.write"]

        assert success_event is not None
        assert success_event.trace_id == trace_id
        assert success_event.approval_id == approval_id
        assert success_event.side_effects_applied == ["sops.write"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_reject_approval_marks_runtime_failed_and_records_tool_failed_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(
            client,
            email="e002_creator_reject@example.com",
            full_name="创建者",
        )
        payload = _create_pending_write_command(client, creator_token)
        trace_id = payload["trace_id"]
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(
            client,
            email="e002_admin_reject@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e002_admin_reject@example.com",
                role_name="admin",
                permission_keys=["approvals:reject"],
            )
        )

        reject_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "E-002审批拒绝"},
        )
        assert reject_resp.status_code == 200
        reject_payload = reject_resp.json()
        assert reject_payload["status"] == "rejected"
        assert reject_payload["command_status"] == "failed"
        assert reject_payload["tool_call_status"] == "failed"
        assert reject_payload["tool_call_event_written"] is True

        command, tool_call, approval = asyncio.run(
            _load_runtime_by_trace(session_factory, trace_id=trace_id)
        )
        assert command.status == "failed"
        assert tool_call.status == "failed"
        assert tool_call.error_message == "approval_rejected"
        assert approval.status == "rejected"
        assert command.trace_id == tool_call.trace_id == approval.trace_id == trace_id

        failed_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_failed",
            )
        )
        pending_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_pending",
            )
        )
        assert pending_event is not None
        assert pending_event.tool_call_args == {"title": "E002测试"}
        assert pending_event.side_effects_applied == ["sops.write"]

        assert failed_event is not None
        assert failed_event.trace_id == trace_id
        assert failed_event.approval_id == approval_id
        assert failed_event.side_effects_applied == ["sops.write"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_repeated_grant_is_idempotent_without_duplicate_tool_success_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(
            client,
            email="e002_creator_idempotent@example.com",
            full_name="创建者",
        )
        payload = _create_pending_write_command(client, creator_token)
        trace_id = payload["trace_id"]
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(
            client,
            email="e002_admin_idempotent@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e002_admin_idempotent@example.com",
                role_name="admin",
                permission_keys=["approvals:grant"],
            )
        )

        first_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "首次通过"},
        )
        assert first_resp.status_code == 200
        assert first_resp.json()["tool_call_event_written"] is True

        second_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "重复通过"},
        )
        assert second_resp.status_code == 200
        second_payload = second_resp.json()
        assert second_payload["changed"] is False
        assert second_payload["tool_call_event_written"] is False
        assert second_payload["tool_call_status"] == "success"

        success_count = asyncio.run(
            _count_audit_by_action(
                session_factory,
                trace_id=trace_id,
                action="tool_call_success",
            )
        )
        assert success_count == 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_grant_critical_tool_when_feature_disabled_records_failed_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(
            client,
            email="e003_creator_disabled_feature@example.com",
            full_name="创建者",
        )
        payload = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {creator_token}"},
            json={
                "intent": "inject_fault",
                "skill_id": "adapter.inject_fault",
                "tool_name": "adapter.inject_fault",
                "tool_args": {"fault_code": "E003"},
                "side_effects": ["fault.inject"],
            },
        ).json()
        assert payload["status"] == "pending_approval"
        trace_id = payload["trace_id"]
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(
            client,
            email="e003_admin_disabled_feature@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e003_admin_disabled_feature@example.com",
                role_name="admin",
                permission_keys=["approvals:grant"],
            )
        )

        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "E-003审批通过"},
        )
        assert grant_resp.status_code == 200
        grant_payload = grant_resp.json()
        assert grant_payload["status"] == "granted"
        assert grant_payload["command_status"] == "failed"
        assert grant_payload["tool_call_status"] == "failed"
        assert grant_payload["tool_call_event_written"] is True

        success_count = asyncio.run(
            _count_audit_by_action(
                session_factory,
                trace_id=trace_id,
                action="tool_call_success",
            )
        )
        failed_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_failed",
            )
        )
        assert success_count == 0
        assert failed_event is not None
        assert failed_event.reason == "feature_flag_disabled"
        assert failed_event.approval_id == approval_id
        assert failed_event.trace_id == trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_grant_unexpected_tool_status_records_deny_audit(
    monkeypatch,
) -> None:
    client, session_factory = _build_client()
    try:
        creator_token = _register_and_login(
            client,
            email="e003_creator_unexpected_status@example.com",
            full_name="创建者",
        )
        payload = _create_pending_write_command(client, creator_token)
        trace_id = payload["trace_id"]
        approval_id = payload["approval_id"]

        admin_token = _register_and_login(
            client,
            email="e003_admin_unexpected_status@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e003_admin_unexpected_status@example.com",
                role_name="admin",
                permission_keys=["approvals:grant"],
            )
        )

        from app.services.approval_service import ApprovalService

        async def _fake_execute_after_grant(self, approval):
            command, tool_call = await self.get_runtime_bundle(approval)
            tool_call.status = "pending"
            command.status = "pending_approval"
            return command, tool_call, True

        monkeypatch.setattr(ApprovalService, "execute_after_grant", _fake_execute_after_grant)

        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "E-003未知状态分支"},
        )
        assert grant_resp.status_code == 200
        grant_payload = grant_resp.json()
        assert grant_payload["tool_call_status"] == "pending"
        assert grant_payload["tool_call_event_written"] is True

        _command, tool_call, _approval = asyncio.run(
            _load_runtime_by_trace(session_factory, trace_id=trace_id)
        )
        failed_event = asyncio.run(
            _find_latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_failed",
            )
        )
        assert failed_event is not None
        assert failed_event.reason == "unexpected_tool_call_status:pending"
        assert failed_event.resource_id == str(tool_call.id)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
