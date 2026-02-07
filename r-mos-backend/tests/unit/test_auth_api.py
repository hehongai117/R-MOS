"""
认证 API 测试（Gate-1 / A-001）。
"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_token
from app.models.base import Base
from app.models.refresh_token import RefreshToken
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # 确保所有模型注册到 metadata


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


def test_auth_register_success_returns_user_id() -> None:
    client, session_factory = _build_client()
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new_user@example.com",
                "password": "StrongPass123",
                "full_name": "测试用户",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert isinstance(payload.get("user_id"), int)
        assert payload.get("email") == "new_user@example.com"
        assert payload.get("message") == "注册成功"

        async def assert_user_saved() -> None:
            async with session_factory() as session:
                result = await session.execute(select(User).where(User.email == "new_user@example.com"))
                user = result.scalar_one()
                assert user.password_hash != "StrongPass123"
                assert user.password_hash.startswith("pbkdf2_sha256$")

        asyncio.run(assert_user_saved())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_register_duplicate_email_returns_user_001() -> None:
    client, _ = _build_client()
    try:
        payload = {
            "email": "dup_user@example.com",
            "password": "StrongPass123",
            "full_name": "重复用户",
        }
        first = client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 400
        assert second.json()["details"]["code"] == "USER_001"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_register_weak_password_returns_user_002() -> None:
    client, _ = _build_client()
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak_user@example.com",
                "password": "123",
                "full_name": "弱密码用户",
            },
        )
        assert response.status_code == 400
        assert response.json()["details"]["code"] == "USER_002"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_login_success_returns_tokens() -> None:
    client, _ = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_user@example.com",
                "password": "StrongPass123",
                "full_name": "登录用户",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login_user@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        payload = login_resp.json()
        assert isinstance(payload.get("access_token"), str)
        assert isinstance(payload.get("refresh_token"), str)
        assert payload.get("expires_in") == 900
        assert payload.get("token_type") == "bearer"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_login_wrong_password_returns_auth_001() -> None:
    client, _ = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong_pass_user@example.com",
                "password": "StrongPass123",
                "full_name": "登录失败用户",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong_pass_user@example.com", "password": "WrongPass123"},
        )
        assert login_resp.status_code == 401
        assert login_resp.json()["details"]["code"] == "AUTH_001"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_login_unknown_user_returns_auth_001() -> None:
    client, _ = _build_client()
    try:
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "unknown_user@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 401
        assert login_resp.json()["details"]["code"] == "AUTH_001"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_refresh_success_returns_new_access_token() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh_user@example.com",
                "password": "StrongPass123",
                "full_name": "刷新用户",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "refresh_user@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        old_tokens = login_resp.json()

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_tokens["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] != old_tokens["access_token"]
        assert new_tokens["refresh_token"] != old_tokens["refresh_token"]
        assert new_tokens["expires_in"] == 900

        async def assert_refresh_rotation() -> None:
            async with session_factory() as session:
                old_result = await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.refresh_token_hash == hash_token(old_tokens["refresh_token"])
                    )
                )
                old_token = old_result.scalar_one()
                assert old_token.is_revoked is True
                assert old_token.revoked_at is not None

                new_result = await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.refresh_token_hash == hash_token(new_tokens["refresh_token"])
                    )
                )
                new_token = new_result.scalar_one()
                assert new_token.is_revoked is False

        asyncio.run(assert_refresh_rotation())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_refresh_revoked_or_expired_returns_401_code() -> None:
    client, _ = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh_denied_user@example.com",
                "password": "StrongPass123",
                "full_name": "刷新拒绝用户",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "refresh_denied_user@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 200

        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["details"]["code"] == "AUTH_004"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_auth_logout_revokes_refresh_token() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout_user@example.com",
                "password": "StrongPass123",
                "full_name": "登出用户",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "logout_user@example.com", "password": "StrongPass123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 200
        assert logout_resp.json()["success"] is True

        async def assert_token_revoked() -> None:
            async with session_factory() as session:
                token_result = await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.refresh_token_hash == hash_token(refresh_token)
                    )
                )
                token_row = token_result.scalar_one()
                assert token_row.is_revoked is True
                assert token_row.revoked_at is not None

        asyncio.run(assert_token_revoked())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
