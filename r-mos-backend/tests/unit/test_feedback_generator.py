"""
UF-09: FeedbackGenerator score rule tests.
"""
from __future__ import annotations

import pytest

from app.services.training.feedback_generator import FeedbackGenerator


def _base_payload():
    return {
        "project_snapshot": {"estimated_time": 60},
        "steps_summary": [
            {
                "step_id": "step_001",
                "step_index": 0,
                "status": "pass",
                "attempt_count": 1,
                "tools_confirmed": [{"tool_id": "tool-1", "status": "confirmed"}],
            },
            {
                "step_id": "step_002",
                "step_index": 1,
                "status": "pass",
                "attempt_count": 1,
                "tools_confirmed": [{"tool_id": "tool-2", "status": "confirmed"}],
            },
        ],
        "total_duration": 3000,
        "total_attempts": 2,
    }


@pytest.mark.asyncio
async def test_feedback_generator_score_full_score_case(test_db):
    generator = FeedbackGenerator(test_db)
    payload = _base_payload()

    score = generator._calculate_comprehensive_score(payload)
    assert score["total_score"] >= 95
    assert score["completion_rate"] == 100.0
    assert score["failed_steps"] == 0


@pytest.mark.asyncio
async def test_feedback_generator_score_timeout_penalty(test_db):
    generator = FeedbackGenerator(test_db)
    payload = _base_payload()
    payload["total_duration"] = 9000  # expected 3600, now overtime

    score = generator._calculate_comprehensive_score(payload)
    assert score["time_score"] < 20.0
    assert score["total_score"] < 95


@pytest.mark.asyncio
async def test_feedback_generator_score_failed_step_penalty(test_db):
    generator = FeedbackGenerator(test_db)
    payload = _base_payload()
    payload["steps_summary"][1]["status"] = "fail"
    payload["total_attempts"] = 3

    score = generator._calculate_comprehensive_score(payload)
    assert score["failed_steps"] == 1
    assert score["completion_rate"] == 50.0
    assert score["total_score"] < 80
