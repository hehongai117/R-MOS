from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME


@pytest.fixture()
def e2e_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    """Per-test isolated app+DB environment for E2E API tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init_models() -> None:
        async with engine.begin() as conn:
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
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())
