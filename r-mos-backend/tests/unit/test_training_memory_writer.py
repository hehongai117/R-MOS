"""
UF-11: TrainingMemoryWriter tests.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.skill_profile import StudentWeakStep
from app.models.skill_profile import StudentSkillProfile
from app.models.conversation import ConversationTurn
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
    assert weak_step.fail_count == 4
    assert weak_step.is_resolved is True


@pytest.mark.asyncio
async def test_training_memory_writer_writes_conversation_summary(monkeypatch, test_db, test_user, test_session):
    submission = TrainingSubmission(
        submission_id=str(uuid4()),
        session_id=test_session.session_id,
        user_id=test_user.id,
        submit_type="manual",
        submitted_at=datetime.utcnow(),
        payload=_submission_payload(),
    )
    test_db.add_all(
        [
            submission,
            ConversationTurn(
                session_id=test_session.session_id,
                role="user",
                content="机器人出现堵转现象",
                metadata_json='{"source":"chat"}',
            ),
            ConversationTurn(
                session_id=test_session.session_id,
                role="assistant",
                content="建议先检查机械卡滞和驱动器状态",
                metadata_json='{"source":"assistant"}',
            ),
        ]
    )
    await test_db.commit()

    written: dict = {}

    class _FakeMemoryHub:
        async def write(self, **kwargs):
            written.update(kwargs)
            return True

    writer = TrainingMemoryWriter(test_db)

    async def fake_generate_summary(_conversation_text: str) -> str:
        return "学员完成堵转排查对话，系统建议检查卡滞与驱动器。"

    monkeypatch.setattr("app.services.memory.training_memory_writer.MemoryHub", _FakeMemoryHub)
    monkeypatch.setattr(writer, "_generate_summary_with_llm", fake_generate_summary)

    await writer._write_conversation_summary(submission)

    assert written["session_id"] == submission.session_id
    assert written["user_id"] == str(test_user.id)
    assert written["is_long_term"] is True
    assert written["data"]["type"] == "conversation_summary"
    assert "堵转排查" in written["data"]["summary"]


@pytest.mark.asyncio
async def test_training_memory_writer_precomputes_next_recommendation(monkeypatch, test_db, test_user):
    profile = StudentSkillProfile(
        user_id=test_user.id,
        overall_level=2,
        total_sessions=3,
        score_safety=85,
        score_procedure=55,
        score_precision=78,
        score_efficiency=81,
        score_tools=80,
    )
    weak_step = StudentWeakStep(
        user_id=test_user.id,
        step_id="step-weak-1",
        sop_id="sop-1",
        fail_count=3,
        is_resolved=False,
    )
    test_db.add_all([profile, weak_step])
    await test_db.commit()

    cached: dict = {}

    class _FakeShortTerm:
        def __init__(self):
            self._ttl = 1800

        def write(self, session_id: str, data: dict) -> bool:
            cached["session_id"] = session_id
            cached["data"] = data
            cached["ttl"] = self._ttl
            return True

    class _FakeMemoryHub:
        def __init__(self):
            self.short_term = _FakeShortTerm()

    monkeypatch.setattr("app.services.memory.training_memory_writer.MemoryHub", _FakeMemoryHub)

    writer = TrainingMemoryWriter(test_db)
    await writer._precompute_next_recommendation(test_user.id)

    assert cached["session_id"] == f"recommendation:{test_user.id}"
    assert cached["ttl"] == 86400
    assert cached["data"]["weak_step_count"] == 1
    assert cached["data"]["recommended_steps"] == ["step-weak-1"]
