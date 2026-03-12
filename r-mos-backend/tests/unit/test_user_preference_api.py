from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User
from main import app


@pytest.fixture(scope="module")
def preference_api_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Preference User",
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _get_user_id(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
) -> int:
    async with session_factory() as session:
        result = await session.execute(select(User.id).where(User.email == email))
        return int(result.scalar_one())


def test_user_can_save_llm_preferences_without_leaking_raw_api_key(
    preference_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = preference_api_env
    email = f"prefs_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    user_id = asyncio.run(_get_user_id(session_factory, email=email))

    update_resp = client.put(
        "/api/v1/agent/preference/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-1234567890",
        },
    )

    assert update_resp.status_code == 200
    update_payload = update_resp.json()
    assert update_payload["user_id"] == user_id
    assert update_payload["preferences"]["llm"]["provider"] == "openai"
    assert update_payload["preferences"]["llm"]["model"] == "gpt-4.1-mini"
    assert update_payload["preferences"]["llm"]["base_url"] == "https://api.openai.com/v1"
    assert update_payload["preferences"]["llm"]["has_api_key"] is True
    assert update_payload["preferences"]["llm"]["api_key_masked"].startswith("sk-")
    assert "api_key" not in update_payload["preferences"]["llm"]

    get_resp = client.get(
        "/api/v1/agent/preference",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    get_payload = get_resp.json()
    assert get_payload["preferences"]["llm"]["provider"] == "openai"
    assert get_payload["preferences"]["llm"]["model"] == "gpt-4.1-mini"
    assert get_payload["preferences"]["llm"]["base_url"] == "https://api.openai.com/v1"
    assert get_payload["preferences"]["llm"]["has_api_key"] is True
    assert get_payload["preferences"]["llm"]["api_key_masked"].startswith("sk-")
    assert "api_key" not in get_payload["preferences"]["llm"]

