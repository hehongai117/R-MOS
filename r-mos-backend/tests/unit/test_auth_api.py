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
from app.models.base import Base
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
