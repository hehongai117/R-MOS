from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.authz_guard import ActorContext, get_current_actor
from main import app


def _actor() -> ActorContext:
    return ActorContext(
        user_id=1,
        email="tester@example.com",
        roles={"teacher"},
        permissions={"agent:execute", "agent:read"},
    )


def _telemetry_payload() -> dict:
    return {
        "joints": [
            {
                "joint_id": "knee_right",
                "position": 1.1,
                "velocity": 0.0,
                "torque": 0.1,
                "temperature": 76.0,
                "error_code": "E002_STALL",
            }
        ],
        "sensors": {
            "battery": 82.0,
            "temperature": 45.0,
            "voltage": {"main": 24.0},
        },
        "active_faults": ["E002_STALL"],
    }


@pytest.mark.e2e
def test_agent_execute_diagnosis_flow_returns_diagnosis_plan_and_verification(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
):
    client, _ = e2e_env
    app.dependency_overrides[get_current_actor] = _actor

    try:
        start = time.perf_counter()
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "student-1",
                "mode": "message",
                "message": "机器人异常，请诊断",
                "intent_classification": "delegate-diagnoser",
                "telemetry_payload": _telemetry_payload(),
            },
        )
        elapsed = time.perf_counter() - start
    finally:
        app.dependency_overrides.pop(get_current_actor, None)

    assert response.status_code == 200
    assert elapsed < 2.0

    body = response.json()
    assert body["status"] == "success"
    assert isinstance(body["trace_id"], str) and body["trace_id"]

    result = body["result"]
    assert result["success"] is True
    assert result["trace_id"] == body["trace_id"]
    assert result["result"]["diagnosis"]["primary_hypothesis"]["fault_code"] == "E002_STALL"
    assert result["result"]["maintenance_plan"]["fault_code"] == "E002_STALL"
    assert "verification" in result["result"]
    assert result["result"]["verification"]["plan_id"] == result["result"]["maintenance_plan"]["plan_id"]


@pytest.mark.e2e
def test_websocket_telemetry_protocol_is_consistent(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
):
    client, _ = e2e_env

    with client.websocket_connect("/ws/robot/status") as websocket:
        message = json.loads(websocket.receive_text())

    assert message["type"] == "telemetry"
    assert isinstance(message["timestamp"], str) and message["timestamp"]
    assert set(message["payload"].keys()) == {"joints", "sensors", "active_faults"}
    assert isinstance(message["payload"]["joints"], list)
    assert isinstance(message["payload"]["active_faults"], list)
    assert "battery" in message["payload"]["sensors"]
    assert "temperature" in message["payload"]["sensors"]


@pytest.mark.e2e
def test_get_user_preference_uses_actor_user_id(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
):
    client, _ = e2e_env
    app.dependency_overrides[get_current_actor] = _actor
    captured: dict[str, int] = {}

    async def _fake_get_or_create_preference(self, user_id: int):
        captured["user_id"] = user_id
        return SimpleNamespace(
            user_id=user_id,
            guidance_mode="full_time",
            preferences={},
        )

    monkeypatch.setattr(
        "app.services.user_preference_service.UserPreferenceService.get_or_create_preference",
        _fake_get_or_create_preference,
    )

    try:
        response = client.get("/api/v1/agent/preference")
    finally:
        app.dependency_overrides.pop(get_current_actor, None)

    assert response.status_code == 200
    body = response.json()
    assert captured["user_id"] == 1
    assert body["user_id"] == 1
    assert body["guidance_mode"] == "full_time"
