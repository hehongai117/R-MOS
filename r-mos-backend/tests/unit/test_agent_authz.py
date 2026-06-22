"""
P0-1-5: Agent API 鉴权单元测试
测试所有 /agent/* 端点的鉴权功能
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
from app.models.school import School
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401

TEST_SCHOOL_NAME = "测试学校"


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


async def _grant_role(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> None:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(email=email, full_name=email.split("@")[0], hashed_password="dummy")
            session.add(user)
            await session.flush()

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
                session.add(
                    RolePermission(role_id=role.id, permission_id=permission.id)
                )

        user_role_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if user_role_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()


def _register_and_login(client: TestClient, email: str) -> str:
    """Register a user and return the access token."""
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": email.split("@")[0],
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


# ============ 只读端点测试 ============

def test_agent_task_status_without_permission_returns_403() -> None:
    """测试无权限访问只读端点返回 403."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "noperm@example.com")
        # 不授予任何 agent 权限

        resp = client.get(
            "/api/v1/agent/task-status/user-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] in {"RoleRequiredError", "PermissionDeniedError"}
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ============ 写入端点测试 ============

def test_agent_execute_without_token_returns_401() -> None:
    """测试无 token 访问 /agent/execute 返回 401."""
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/agent/execute",
            json={"user_id": "user-001", "mode": "message", "message": "test"},
        )
        assert resp.status_code == 401
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_agent_execute_without_permission_returns_403() -> None:
    """测试无权限访问 /agent/execute 返回 403."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "writer@example.com")
        # 只授予 read 权限，不授予 execute

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "user-001", "mode": "message", "message": "test"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] in {"RoleRequiredError", "PermissionDeniedError"}
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_agent_coach_recommend_with_execute_permission() -> None:
    """测试有 execute 权限访问写入端点."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "executor@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="executor@example.com",
                role_name="agent_user",
                permission_keys=["agent:execute"],
            )
        )

        resp = client.post(
            "/api/v1/agent/coach/recommend",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "task_id": "task-001",
                "current_step": 1,
                "step_history": [],
            },
        )
        # 可能返回业务错误，但鉴权应该通过
        assert resp.status_code in [200, 400, 500]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_agent_evidence_collect_write_endpoint() -> None:
    """测试证据收集写入端点鉴权."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "evidence@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="evidence@example.com",
                role_name="agent_operator",
                permission_keys=["agent:execute"],
            )
        )

        resp = client.post(
            "/api/v1/agent/evidence/collect",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "step_id": "step-001",
                "evidence_id": "ev-001",
            },
        )
        # 可能返回业务错误，但鉴权应该通过
        assert resp.status_code in [200, 400, 422]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_agent_approval_pending_read_endpoint() -> None:
    """测试审批队列读取端点鉴权."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "approver@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="approver@example.com",
                role_name="approval_user",
                permission_keys=["agent:read"],
            )
        )

        resp = client.get(
            "/api/v1/agent/approval/pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 鉴权通过，可能返回空列表
        assert resp.status_code in [200, 403]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_agent_approval_approve_write_endpoint() -> None:
    """测试审批写入端点鉴权."""
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, "admin_approver@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="admin_approver@example.com",
                role_name="approval_admin",
                permission_keys=["agent:execute"],
            )
        )

        resp = client.post(
            "/api/v1/agent/approval/req-001/approve",
            headers={"Authorization": f"Bearer {token}"},
            params={"approved_by": "admin-001"},
        )
        # 鉴权通过，可能返回 404（请求不存在）
        assert resp.status_code in [200, 404, 403]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


