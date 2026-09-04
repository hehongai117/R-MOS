"""证据包、事件、观测创建归属的 HTTP 行为回归测试。"""
import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保模型注册完整
from app.core.database import get_db
from app.models.base import Base
from app.models.evidence import EvidenceBundle
from app.models.incident import Incident
from app.models.observation import Observation
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


def _client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.state.test_sessionmaker = session_factory
    return TestClient(app), session_factory


def _evidence_payload() -> dict:
    return {
        "bundle_type": "event_log",
        "observed_time_start": "2026-09-04T08:00:00Z",
        "items": [
            {
                "evidence_id": f"evidence-{uuid4()}",
                "evidence_type": "event",
                "content_uri": "memory://ownership-test",
                "content_hash": "a" * 64,
                "content_hash_algo": "sha256",
                "content_mime_type": "application/json",
                "size_bytes": 12,
                "observed_time": "2026-09-04T08:00:00Z",
                "ingest_time": "2026-09-04T08:00:01Z",
            }
        ],
    }


def _incident_payload() -> dict:
    return {
        "robot_id": "ownership-robot",
        "incident_type": "operational",
        "incident_level": "warning",
        "event_time_start": "2026-09-04T08:00:00Z",
    }


def _observation_payload() -> dict:
    return {
        "observation_type": "event",
        "robot_id": "ownership-robot",
        "observed_time": "2026-09-04T08:00:00Z",
    }


CREATE_CASES = (
    ("/api/v1/evidence-bundles", _evidence_payload, EvidenceBundle, "evidence_bundle_id"),
    ("/api/v1/incidents", _incident_payload, Incident, "incident_id"),
    ("/api/v1/observations", _observation_payload, Observation, "observation_id"),
)


@pytest.mark.regression
@pytest.mark.parametrize(("path", "payload_factory", "model", "id_key"), CREATE_CASES)
def test_create_record_rejects_anonymous(path, payload_factory, model, id_key):
    """三个创建入口均须拒绝未登录请求。"""
    client, _ = _client()
    try:
        response = client.post(path, json=payload_factory())
        assert response.status_code == 401, response.text
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
@pytest.mark.parametrize(("path", "payload_factory", "model", "id_key"), CREATE_CASES)
def test_create_record_persists_actor_ownership(
    path, payload_factory, model, id_key
):
    """已登录用户可创建，且创建者与学校必须真实落库。"""
    client, session_factory = _client()
    try:
        user_id, _, _ = register_and_login(client, email_prefix="record_owner")

        response = client.post(path, json=payload_factory())
        assert response.status_code == 201, response.text
        record_id = response.json()[id_key]

        async def _load_record():
            async with session_factory() as session:
                return await session.get(model, record_id)

        record = asyncio.run(_load_record())
        assert record is not None
        assert record.created_by_user_id == user_id
        assert record.school_name == E2E_SCHOOL_NAME
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
