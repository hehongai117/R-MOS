from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User

# onboarding 注册需要白名单学校；E2E 统一使用此校名（conftest 中预置）
E2E_SCHOOL_NAME = "测试学校"


def register_and_login(
    client: TestClient,
    *,
    email_prefix: str,
    password: str = "StrongPass123",
    full_name: str = "E2E User",
    role: str = "teacher",
    teacher_id: int | None = None,
) -> tuple[int, str, dict]:
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"

    # 学生注册必须绑定同校教师；未指定时自动创建一位教师用于绑定
    if role == "student" and teacher_id is None:
        teacher_id, _, _ = register_and_login(
            client, email_prefix=f"{email_prefix}_teacher", role="teacher"
        )

    payload: dict = {
        "email": email,
        "password": password,
        "full_name": full_name,
        "role": role,
        "school_name": E2E_SCHOOL_NAME,
    }
    if teacher_id is not None:
        payload["teacher_id"] = teacher_id

    register_resp = client.post("/api/v1/auth/register", json=payload)
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_json = login_resp.json()

    # AUTH-101 默认拒绝网关生效后，/api/v1 下的调用一律需要令牌。
    # 把刚登录的身份设为客户端默认身份——这也让"当前以谁的身份行事"在用例里
    # 与最后一次 register_and_login 调用一致；需要别的身份时用单次 headers= 覆盖。
    # 注意：学生分支会先递归创建一位教师，因此这里必须在递归返回之后再设置。
    client.headers["Authorization"] = f"Bearer {login_json['access_token']}"

    return user_id, email, login_json


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
