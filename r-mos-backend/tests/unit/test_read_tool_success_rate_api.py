"""Gate-3 J-002：Read Tool 成功率统计最小闭环测试。"""
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


def _create_read_command(client: TestClient, token: str, trace_id: str) -> dict:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}", "X-Trace-ID": trace_id},
        json={
            "intent": "replay",
            "skill_id": "rag.read.replay",
            "tool_name": "rag.query",
            "tool_args": {"query": "回放摘要"},
            "side_effects": [],
        },
    )
    assert response.status_code == 201
    return response.json()


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


def test_j002_admin_read_tool_success_rate_returns_metrics_and_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="j002_creator@example.com",
            full_name="创建者",
        )
        _create_read_command(client, creator_token, "j002-read-1")
        _create_read_command(client, creator_token, "j002-read-2")

        admin_token, _ = _register_and_login(
            client,
            email="j002_admin@example.com",
            full_name="管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="j002_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )

        query_trace_id = "j002-metrics-trace"
        response = client.get(
            "/api/v1/ai/replay/metrics/read-tool-success-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": query_trace_id},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == "read_tool_success_rate"
        assert body["trace_id"] == query_trace_id
        assert body["total"] >= 2
        assert body["success"] >= 2
        assert body["success_rate"] >= 99.0
        assert body["meets_target"] is True

        allow_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="read_tool_success_rate_read",
                decision="allow",
                resource_type="ReadToolMetric",
                resource_id="read_tool_success_rate",
                actor_user_id=str(admin_user_id),
                trace_id=query_trace_id,
            )
        )
        assert allow_event is not None
        assert allow_event.trace_id == query_trace_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_j002_teacher_without_permission_returns_403_and_records_route_deny() -> None:
    client, session_factory = _build_client()
    try:
        teacher_token, teacher_user_id = _register_and_login(
            client,
            email="j002_teacher_no_perm@example.com",
            full_name="教师无权限",
        )
        response = client.get(
            "/api/v1/ai/replay/metrics/read-tool-success-rate",
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
                resource_id="/api/v1/ai/replay/metrics/read-tool-success-rate",
                actor_user_id=str(teacher_user_id),
            )
        )
        assert deny_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_j002_teacher_with_permission_returns_404_and_records_deny_real_resource_id() -> None:
    client, session_factory = _build_client()
    try:
        teacher_token, _ = _register_and_login(
            client,
            email="j002_teacher_perm@example.com",
            full_name="教师有权限",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="j002_teacher_perm@example.com",
                role_name="teacher",
                permission_keys=["audit_events:read"],
            )
        )

        response = client.get(
            "/api/v1/ai/replay/metrics/read-tool-success-rate",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
        assert body["details"]["details"]["resource_id"] == "read_tool_success_rate"

        deny_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="access_denied",
                decision="deny",
                resource_type="ReadToolMetric",
                resource_id="read_tool_success_rate",
                actor_user_id=str(teacher_user_id),
            )
        )
        assert deny_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
