"""
UF-07: TeacherMonitorService tests.
"""
from __future__ import annotations

import pytest

from app.services.identity.teacher_monitor import TeacherMonitorService


@pytest.mark.asyncio
async def test_teacher_monitor_publish_update_and_message(monkeypatch):
    service = TeacherMonitorService()
    captured = {"broadcast": [], "direct": []}

    async def fake_broadcast(channel: str, message: dict):
        captured["broadcast"].append((channel, message))

    async def fake_send(user_id: int, message: dict):
        captured["direct"].append((user_id, message))

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
    assert captured["direct"][0][0] == 1
    assert captured["direct"][0][1]["type"] == "teacher_message"
