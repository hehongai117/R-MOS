"""
Gate-1 B-001：RBAC 守卫最小门禁测试。
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
import app.models as app_models  # noqa: F401  # 确保模型全部注册

# onboarding 注册需要的白名单学校（测试统一使用）
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


def test_admin_users_route_allows_admin_authz_t001() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin_authz@example.com",
                "password": "StrongPass123",
                "full_name": "管理员",
                "role": "teacher",
                "school_name": TEST_SCHOOL_NAME,
            },
        )
        assert register_resp.status_code == 201
        asyncio.run(
            _grant_role(
                session_factory,
                email="admin_authz@example.com",
                role_name="admin",
                permission_keys=["users:read"],
            )
        )

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin_authz@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        list_resp = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["total"] >= 1
        assert any(
            item["email"] == "admin_authz@example.com" for item in payload["items"]
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_admin_users_route_teacher_denied_authz_t002() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "teacher_authz@example.com",
                "password": "StrongPass123",
                "full_name": "教师",
                "role": "teacher",
                "school_name": TEST_SCHOOL_NAME,
            },
        )
        assert register_resp.status_code == 201
        asyncio.run(
            _grant_role(
                session_factory,
                email="teacher_authz@example.com",
                role_name="teacher",
                permission_keys=["teaching:read"],
            )
        )

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "teacher_authz@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        deny_resp = client.get(
            "/api/v1/admin/users",
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
                        AuditEvent.resource_id == "/api/v1/admin/users",
                        AuditEvent.decision == "deny",
                    )
                    .order_by(AuditEvent.id.desc())
                )
                event = result.scalars().first()
                assert event is not None
                assert event.actor_user_id is not None
                assert event.reason == "missing_role:admin"

        asyncio.run(assert_deny_audit())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_admin_users_route_without_token_returns_auth_003() -> None:
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/admin/users")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error_type"] == "AuthenticationRequiredError"
        assert body["details"]["code"] == "AUTH_003"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
