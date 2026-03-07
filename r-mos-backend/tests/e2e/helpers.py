from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User


def register_and_login(
    client: TestClient,
    *,
    email_prefix: str,
    password: str = "StrongPass123",
    full_name: str = "E2E User",
) -> tuple[int, str, dict]:
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"

    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200

    return user_id, email, login_resp.json()


def parse_sse_events(raw_text: str) -> list[dict]:
    events: list[dict] = []
    for line in raw_text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line.removeprefix("data: ").strip()
        if not payload:
            continue
        events.append(json.loads(payload))
    return events


async def set_user_role(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    role: str,
) -> None:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def set_user_hint_level(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    hint_level: int,
) -> None:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.hint_level = hint_level
        await session.commit()
