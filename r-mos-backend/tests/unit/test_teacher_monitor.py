"""
UF-07: TeacherMonitorService tests.
"""
from __future__ import annotations

import logging
from datetime import datetime

import pytest

from app.services.identity.teacher_monitor import TeacherMonitorService


@pytest.mark.asyncio
async def test_teacher_monitor_publish_update_and_message(monkeypatch):
    service = TeacherMonitorService()
    captured = {"broadcast": [], "direct": []}

    async def fake_broadcast(channel: str, message: dict):
        captured["broadcast"].append((channel, message))
        return 1

    async def fake_send(user_id: int, message: dict):
        captured["direct"].append((user_id, message))
        return 1

    monkeypatch.setattr("app.services.identity.teacher_monitor.manager.broadcast_to_channel", fake_broadcast)
    monkeypatch.setattr("app.services.identity.teacher_monitor.manager.send_to_user", fake_send)

    await service.publish_session_update(
        class_id=101,
        event_type="step_completed",
        data={"student_id": 1, "step_id": "s1"},
    )
    await service.publish_teacher_message(
        class_id=101,
        user_id=1,
        message="请先确认电源",
    )

    assert captured["broadcast"][0][0] == "class:101"
    assert captured["broadcast"][0][1]["type"] == "step_completed"
    for _, message in captured["broadcast"]:
        assert message["timestamp"].endswith("Z")
        assert "+00:00Z" not in message["timestamp"]
        datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
    assert captured["direct"][0][0] == 1
    assert captured["direct"][0][1]["type"] == "teacher_message"
    direct_timestamp = captured["direct"][0][1]["timestamp"]
    assert direct_timestamp.endswith("Z")
    assert "+00:00Z" not in direct_timestamp
    datetime.fromisoformat(direct_timestamp.replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_teacher_monitor_does_not_log_success_when_nothing_delivered(
    monkeypatch, caplog
):
    service = TeacherMonitorService()

    async def deliver_nothing(*args, **kwargs):
        return 0

    monkeypatch.setattr(
        "app.services.identity.teacher_monitor.manager.broadcast_to_channel",
        deliver_nothing,
    )
    monkeypatch.setattr(
        "app.services.identity.teacher_monitor.manager.send_to_user",
        deliver_nothing,
    )

    with caplog.at_level(logging.INFO):
        await service.publish_session_update(101, "step_completed", {"student_id": 1})
        await service.publish_teacher_message(101, 1, "请先确认电源")

    messages = [record.getMessage() for record in caplog.records]
    assert any("not delivered" in message for message in messages)
    assert not any("Published step_completed" in message for message in messages)
    assert not any("Sent teacher message" in message for message in messages)
