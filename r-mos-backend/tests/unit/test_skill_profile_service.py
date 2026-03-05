"""
UF-10: SkillProfileService level-up rule tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.skill_profile import StudentSkillProfile
from app.models.training import TrainingSession
from app.services.memory.skill_profile_service import SkillProfileService


def _make_session(user_id: int, score: float, submitted_at: datetime) -> TrainingSession:
    return TrainingSession(
        session_id=f"sess-{user_id}-{submitted_at.timestamp()}",
        project_id="project-1",
        user_id=user_id,
        status="submitted",
        current_step=1,
        project_snapshot={"estimated_time": 60},
        total_duration=1800,
        score=score,
        submitted_at=submitted_at,
        started_at=submitted_at - timedelta(minutes=30),
    )


@pytest.mark.asyncio
async def test_skill_profile_level_up_when_all_conditions_met(test_db, test_user):
    profile = StudentSkillProfile(
        user_id=test_user.id,
        overall_level=1,
        total_sessions=5,
        score_safety=82,
        score_procedure=83,
        score_precision=84,
        score_efficiency=81,
        score_tools=82,
    )
    now = datetime.utcnow()
    test_db.add_all(
        [
            profile,
            _make_session(test_user.id, 90, now - timedelta(days=1)),
            _make_session(test_user.id, 88, now - timedelta(days=2)),
            _make_session(test_user.id, 85, now - timedelta(days=3)),
        ]
    )
    await test_db.commit()

    service = SkillProfileService(test_db)
    upgraded = await service._check_level_up(profile)
    assert upgraded is True
    assert profile.overall_level == 2


@pytest.mark.asyncio
async def test_skill_profile_level_not_upgraded_when_conditions_not_met(test_db, test_user):
    profile = StudentSkillProfile(
        user_id=test_user.id,
        overall_level=1,
        total_sessions=4,  # 未达到次数门槛
        score_safety=90,
        score_procedure=90,
        score_precision=90,
        score_efficiency=90,
        score_tools=90,
    )
    now = datetime.utcnow()
    test_db.add_all(
        [
            profile,
            _make_session(test_user.id, 92, now - timedelta(days=1)),
            _make_session(test_user.id, 91, now - timedelta(days=2)),
            _make_session(test_user.id, 90, now - timedelta(days=3)),
        ]
    )
    await test_db.commit()

    service = SkillProfileService(test_db)
    upgraded = await service._check_level_up(profile)
    assert upgraded is False
    assert profile.overall_level == 1


@pytest.mark.asyncio
async def test_skill_profile_level_up_boundary_values(test_db, test_user):
    profile = StudentSkillProfile(
        user_id=test_user.id,
        overall_level=1,
        total_sessions=5,
        score_safety=80,
        score_procedure=80,
        score_precision=80,
        score_efficiency=80,
        score_tools=80,
    )
    now = datetime.utcnow()
    test_db.add_all(
        [
            profile,
            _make_session(test_user.id, 60, now - timedelta(hours=1)),
            _make_session(test_user.id, 60, now - timedelta(hours=2)),
            _make_session(test_user.id, 60, now - timedelta(hours=3)),
        ]
    )
    await test_db.commit()

    service = SkillProfileService(test_db)
    upgraded = await service._check_level_up(profile)
    assert upgraded is True
    assert profile.overall_level == 2
