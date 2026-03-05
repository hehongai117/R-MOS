"""
UF-11: TrainingMemoryWriter tests.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.skill_profile import StudentWeakStep
from app.models.training_submission import TrainingSubmission
from app.services.memory.training_memory_writer import TrainingMemoryWriter


def _submission_payload():
    return {
        "steps_summary": [
            {"step_id": "step_fail", "status": "fail", "attempt_count": 2},
            {"step_id": "step_pass", "status": "pass", "attempt_count": 1},
        ],
        "total_duration": 1200,
        "project_snapshot": {"estimated_time": 60},
    }


@pytest.mark.asyncio
async def test_training_memory_writer_process_order_and_update_scores_args(monkeypatch, test_db, test_user, test_session):
    submission_id = str(uuid4())
    submission = TrainingSubmission(
        submission_id=submission_id,
        session_id=test_session.session_id,
        user_id=test_user.id,
        submit_type="manual",
        submitted_at=datetime.utcnow(),
        payload=_submission_payload(),
    )
    test_db.add(submission)
    await test_db.commit()

    call_order: list[str] = []
    score_calls: list[tuple[int, dict]] = []

    class _FakeSkillService:
        def __init__(self, _db):
            pass

        async def update_scores(self, user_id: int, payload: dict):
            call_order.append("update_scores")
            score_calls.append((user_id, payload))

        async def update_weak_step(self, **_kwargs):
            pass

    writer = TrainingMemoryWriter(test_db)

    original_update_weak_steps = writer._update_weak_steps

    async def wrapped_update_weak_steps(user_id: int, steps_summary: list[dict]):
        call_order.append("update_weak_steps")
        await original_update_weak_steps(user_id, steps_summary)

    async def fake_update_training_history(_submission):
        call_order.append("update_training_history")

    async def fake_write_conversation_summary(_submission):
        call_order.append("write_conversation_summary")

    async def fake_precompute_next_recommendation(_user_id: int):
        call_order.append("precompute_next_recommendation")

    monkeypatch.setattr("app.services.memory.training_memory_writer.SkillProfileService", _FakeSkillService)
    monkeypatch.setattr(writer, "_update_weak_steps", wrapped_update_weak_steps)
    monkeypatch.setattr(writer, "_update_training_history", fake_update_training_history)
    monkeypatch.setattr(writer, "_write_conversation_summary", fake_write_conversation_summary)
    monkeypatch.setattr(writer, "_precompute_next_recommendation", fake_precompute_next_recommendation)

    ok = await writer.process_submission(submission_id)
    assert ok is True
    assert call_order == [
        "update_weak_steps",
        "update_scores",
        "update_training_history",
        "write_conversation_summary",
        "precompute_next_recommendation",
    ]
    assert score_calls[0][0] == test_user.id
    assert score_calls[0][1]["steps_summary"][0]["step_id"] == "step_fail"


@pytest.mark.asyncio
async def test_training_memory_writer_weak_step_fail_count_and_resolved(test_db, test_user):
    writer = TrainingMemoryWriter(test_db)

    await writer._update_weak_steps(
        test_user.id,
        [{"step_id": "step_x", "status": "fail", "attempt_count": 2}],
    )
    await writer._update_weak_steps(
        test_user.id,
        [{"step_id": "step_x", "status": "fail", "attempt_count": 2}],
    )
    await writer._update_weak_steps(
        test_user.id,
        [{"step_id": "step_x", "status": "pass", "attempt_count": 1}],
    )

    weak_step = await test_db.scalar(
        select(StudentWeakStep).where(
            StudentWeakStep.user_id == test_user.id,
            StudentWeakStep.step_id == "step_x",
        )
    )
    assert weak_step is not None
    assert weak_step.fail_count == 2
    assert weak_step.is_resolved is True
