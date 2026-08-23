from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


def _make_engine():
    """默认内存 SQLite；TEST_DATABASE_URL 设为 PG 时跑真 Postgres。

    PG 分支用 NullPool：每个 asyncio.run 是新事件循环，asyncpg 连接绑定
    事件循环，连接池跨循环复用会炸 "Event loop is closed"（P0-2 已知障碍）。
    NullPool 每次新建连接，彻底规避。
    """
    url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if url.startswith("sqlite"):
        return create_async_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        ), False
    return create_async_engine(url, poolclass=NullPool), True


@pytest.fixture()
def e2e_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    """Per-test isolated app+DB environment for E2E API tests."""
    engine, is_pg = _make_engine()

    async def _init_models() -> None:
        async with engine.begin() as conn:
            if is_pg:
                # PG 库跨测试持久，先清干净再建，保证每测试隔离
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        # AUTH-101 默认拒绝网关生效后，/api/v1 下的调用一律需要令牌。
        # 预置一位默认教师作为客户端默认身份，使"只验业务链路"的 E2E 用例
        # 不必各自造用户；需要特定身份的用例调用 helpers.register_and_login
        # 切换（它会覆盖默认身份），或用单次 headers= 覆盖。
        # 专门验证匿名行为的用例应先 client.headers.pop("Authorization", None)。
        register_and_login(client, email_prefix="e2e_default_actor")
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None

    async def _teardown() -> None:
        if is_pg:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_teardown())
