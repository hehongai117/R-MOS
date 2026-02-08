"""Gate-2 E-004：Tool Executor 安全门禁测试。"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.command_runtime import Command
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


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "安全门禁用户"},
    )
    assert register_resp.status_code == 201
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _find_latest_audit(
    session_factory: async_sessionmaker,
    *,
    reason: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "tool_call_failed",
                AuditEvent.reason == reason,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


async def _count_commands(session_factory: async_sessionmaker) -> int:
    async with session_factory() as session:
        result = await session.execute(select(func.count(Command.id)))
        return int(result.scalar_one())


@pytest.mark.parametrize(
    "tool_args, expected_code",
    [
        ({"sql": "DROP TABLE users"}, "SECURITY_BLACKLIST_KEYWORD"),
        ({"note": "<script>alert(1)</script>"}, "SECURITY_INJECTION_PATTERN"),
        ({"evidence_refs": ["fake-id-123"]}, "SECURITY_INVALID_REFERENCE"),
        ({"difficulty": "超级困难"}, "SECURITY_PARAM_OUT_OF_RANGE"),
    ],
)
def test_tool_security_guard_rejects_illegal_args_and_records_deny_audit(
    tool_args: dict,
    expected_code: str,
) -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email=f"guard_{expected_code}@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "create_sop_draft",
                "skill_id": "sop.write.create_draft",
                "tool_name": "sops.create_draft",
                "tool_args": tool_args,
                "side_effects": ["sops.write"],
            },
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["error_type"] == "SecurityViolationError"
        assert payload["details"]["code"] == expected_code

        event = asyncio.run(
            _find_latest_audit(
                session_factory,
                reason=expected_code,
            )
        )
        assert event is not None
        assert event.decision == "deny"
        assert event.resource_type == "Skill"
        assert event.resource_id == "sop.write.create_draft"

        command_count = asyncio.run(_count_commands(session_factory))
        assert command_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_write_tool_with_side_effects_must_wait_approval_without_direct_success() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="guard_pending_approval@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "create_sop_draft",
                "skill_id": "sop.write.create_draft",
                "tool_name": "sops.create_draft",
                "tool_args": {"title": "E-004安全门禁"},
                "side_effects": ["sops.write"],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "pending_approval"
        assert payload["approval_id"] is not None
        assert payload["result"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
