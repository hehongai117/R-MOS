"""Gate-3 J-001：trace_id 回放接口最小闭环测试。"""
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


def _create_pending_write_command(client: TestClient, token: str, title: str) -> dict:
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
    resource_type: str,
    resource_id: str,
    actor_user_id: str | None = None,
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
        result = await session.execute(stmt)
        return result.scalars().first()


def test_trace_replay_admin_returns_sequence_and_records_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="trace_replay_creator@example.com",
            full_name="创建者",
        )
        command_payload = _create_pending_write_command(client, creator_token, "J001 回放链路")
        trace_id = command_payload["trace_id"]
        approval_id = int(command_payload["approval_id"])

        admin_token, _ = _register_and_login(
            client,
            email="trace_replay_admin@example.com",
            full_name="管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="trace_replay_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:grant", "audit_events:read"],
            )
        )

        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "同意执行"},
        )
        assert grant_resp.status_code == 200

        replay_resp = client.get(
            f"/api/v1/ai/replay/{trace_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert replay_resp.status_code == 200
        body = replay_resp.json()
        assert body["trace_id"] == trace_id
        assert body["count"] >= 3
        actions = [item["action"] for item in body["items"]]
        assert "tool_call_pending" in actions
        assert "approval_granted" in actions
        assert "tool_call_success" in actions
        assert actions.index("tool_call_pending") < actions.index("approval_granted") < actions.index("tool_call_success")
        assert all(item["trace_id"] == trace_id for item in body["items"])

        allow_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="trace_replay_read",
                decision="allow",
                resource_type="TraceReplay",
                resource_id=trace_id,
                actor_user_id=str(admin_user_id),
            )
        )
        assert allow_event is not None
        assert allow_event.trace_id == trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_trace_replay_teacher_returns_404_and_records_deny() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="trace_replay_creator2@example.com",
            full_name="创建者",
        )
        command_payload = _create_pending_write_command(client, creator_token, "J001 回放链路-越权")
        trace_id = command_payload["trace_id"]
        approval_id = int(command_payload["approval_id"])

        admin_token, _ = _register_and_login(
            client,
            email="trace_replay_admin2@example.com",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="trace_replay_admin2@example.com",
                role_name="admin",
                permission_keys=["approvals:grant", "audit_events:read"],
            )
        )
        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "同意执行"},
        )
        assert grant_resp.status_code == 200

        teacher_token, _ = _register_and_login(
            client,
            email="trace_replay_teacher@example.com",
            full_name="教师",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="trace_replay_teacher@example.com",
                role_name="teacher",
                permission_keys=["audit_events:read"],
            )
        )

        response = client.get(
            f"/api/v1/ai/replay/{trace_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
        assert body["details"]["details"]["resource_id"] == trace_id

        deny_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="access_denied",
                decision="deny",
                resource_type="TraceReplay",
                resource_id=trace_id,
                actor_user_id=str(teacher_user_id),
            )
        )
        assert deny_event is not None
        assert deny_event.trace_id == trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_trace_replay_without_token_returns_401() -> None:
    client, _session_factory = _build_client()
    try:
        response = client.get("/api/v1/ai/replay/trace-no-auth")
        assert response.status_code == 401
        body = response.json()
        assert body["error_type"] == "AuthenticationRequiredError"
        assert body["details"]["code"] == "AUTH_003"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
