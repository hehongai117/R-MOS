"""Gate-2 D-002：Skill 治理 API 最小闭环测试。"""
from __future__ import annotations

import asyncio
from typing import Any

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


async def _latest_audit_event(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    resource_type: str,
    resource_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def _register_and_login(client: TestClient, *, email: str, password: str, full_name: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def _create_skill(client: TestClient, token: str, *, skill_id: str, risk_level: str, side_effects: list[str]) -> dict[str, Any]:
    response = client.post(
        "/api/v1/ai/skills",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "skill_id": skill_id,
            "version": "1.0.0",
            "name": "技能",
            "risk_level": risk_level,
            "side_effects": side_effects,
            "allowlist_resources": ["sops"],
            "description": "测试技能",
            "feature_flag": "ff_skill" if risk_level == "critical" else None,
            "rollback_strategy": {"type": "undo"} if risk_level == "critical" else None,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_skill_create_admin_success_records_audit() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(
            client,
            email="skill_admin_create@example.com",
            password="StrongPass123",
            full_name="技能管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_admin_create@example.com",
                role_name="admin",
                permission_keys=["skills:write"],
            )
        )

        create_resp = client.post(
            "/api/v1/ai/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "skill_id": "skill-create-admin",
                "version": "1.0.0",
                "name": "管理员创建技能",
                "risk_level": "medium",
                "side_effects": ["sops"],
                "allowlist_resources": ["sops"],
            },
        )
        assert create_resp.status_code == 201
        payload = create_resp.json()
        assert payload["status"] == "draft"

        event = asyncio.run(
            _latest_audit_event(
                session_factory,
                action="skill_created",
                decision="allow",
                resource_type="Skill",
                resource_id=str(payload["id"]),
            )
        )
        assert event is not None
        assert event.actor_user_id == str(admin_user_id)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_skill_create_non_admin_denied_records_deny_audit() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(
            client,
            email="skill_teacher_create@example.com",
            password="StrongPass123",
            full_name="教师",
        )
        teacher_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_teacher_create@example.com",
                role_name="teacher",
                permission_keys=["skills:write"],
            )
        )

        create_resp = client.post(
            "/api/v1/ai/skills",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "skill_id": "skill-create-teacher",
                "version": "1.0.0",
                "name": "教师创建技能",
                "risk_level": "medium",
                "side_effects": ["sops"],
                "allowlist_resources": ["sops"],
            },
        )
        assert create_resp.status_code == 403
        body = create_resp.json()
        assert body["error_type"] == "RoleRequiredError"
        assert body["details"]["code"] == "AUTHZ_002"

        event = asyncio.run(
            _latest_audit_event(
                session_factory,
                action="permission_denied",
                decision="deny",
                resource_type="Route",
                resource_id="/api/v1/ai/skills",
            )
        )
        assert event is not None
        assert event.actor_user_id == str(teacher_user_id)
        assert event.reason == "missing_role:admin"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_skill_submit_review_creator_success_and_teacher_denied() -> None:
    client, session_factory = _build_client()
    try:
        admin_token = _register_and_login(
            client,
            email="skill_admin_review@example.com",
            password="StrongPass123",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_admin_review@example.com",
                role_name="admin",
                permission_keys=["skills:write"],
            )
        )
        created = _create_skill(
            client,
            admin_token,
            skill_id="skill-submit-review",
            risk_level="medium",
            side_effects=["sops"],
        )
        skill_pk = int(created["id"])

        submit_resp = client.post(
            f"/api/v1/ai/skills/{skill_pk}/submit-review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"review_notes": "管理员提交审核"},
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "in_review"

        teacher_token = _register_and_login(
            client,
            email="skill_teacher_review@example.com",
            password="StrongPass123",
            full_name="教师",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_teacher_review@example.com",
                role_name="teacher",
                permission_keys=["skills:write"],
            )
        )

        deny_resp = client.post(
            f"/api/v1/ai/skills/{skill_pk}/submit-review",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={"review_notes": "教师尝试提审"},
        )
        assert deny_resp.status_code == 403
        deny_body = deny_resp.json()
        assert deny_body["error_type"] == "PermissionDeniedError"
        assert deny_body["details"]["code"] == "AUTHZ_001"

        event = asyncio.run(
            _latest_audit_event(
                session_factory,
                action="permission_denied",
                decision="deny",
                resource_type="Skill",
                resource_id=str(skill_pk),
            )
        )
        assert event is not None
        assert event.reason == "not_creator_or_admin"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_skill_publish_risk_denied_records_audit() -> None:
    client, session_factory = _build_client()
    try:
        admin_token = _register_and_login(
            client,
            email="skill_admin_publish_deny@example.com",
            password="StrongPass123",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_admin_publish_deny@example.com",
                role_name="admin",
                permission_keys=["skills:write", "skills:publish"],
            )
        )
        created = _create_skill(
            client,
            admin_token,
            skill_id="skill-publish-deny",
            risk_level="low",
            side_effects=["sops"],
        )
        skill_pk = int(created["id"])

        publish_resp = client.post(
            f"/api/v1/ai/skills/{skill_pk}/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"release_notes": "尝试发布"},
        )
        assert publish_resp.status_code == 403
        body = publish_resp.json()
        assert body["error_type"] == "WriteAccessDeniedError"
        assert body["details"]["code"] == "WRITE_ACCESS_DENIED"
        assert body["details"]["details"]["reason"] == "violates_RISK_001"

        event = asyncio.run(
            _latest_audit_event(
                session_factory,
                action="skill_publish_denied",
                decision="deny",
                resource_type="Skill",
                resource_id=str(skill_pk),
            )
        )
        assert event is not None
        assert event.reason == "violates_RISK_001"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_skill_publish_success_records_audit() -> None:
    client, session_factory = _build_client()
    try:
        admin_token = _register_and_login(
            client,
            email="skill_admin_publish_ok@example.com",
            password="StrongPass123",
            full_name="管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="skill_admin_publish_ok@example.com",
                role_name="admin",
                permission_keys=["skills:write", "skills:publish"],
            )
        )
        created = _create_skill(
            client,
            admin_token,
            skill_id="skill-publish-success",
            risk_level="medium",
            side_effects=["sops"],
        )
        skill_pk = int(created["id"])

        publish_resp = client.post(
            f"/api/v1/ai/skills/{skill_pk}/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"release_notes": "发布成功"},
        )
        assert publish_resp.status_code == 200
        payload = publish_resp.json()
        assert payload["status"] == "published"

        event = asyncio.run(
            _latest_audit_event(
                session_factory,
                action="skill_published",
                decision="allow",
                resource_type="Skill",
                resource_id=str(skill_pk),
            )
        )
        assert event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
