"""
Teaching domain model tests.
"""
import pytest

from app.models.teaching import GuidancePolicy, TeachingClass, Assignment, AssignmentAttempt


@pytest.mark.asyncio
async def test_guidance_policy_defaults(db_session):
    policy = GuidancePolicy(name="Level 1", base_mode="teaching")
    db_session.add(policy)
    await db_session.flush()

    assert policy.allow_ghost_hand is True
    assert policy.allow_hint_button is True
    assert policy.show_error_details is True
    assert policy.max_retry_count == -1


@pytest.mark.asyncio
async def test_assignment_attempt_status_default(db_session):
    teaching_class = TeachingClass(name="Class A")
    db_session.add(teaching_class)
    await db_session.flush()

    policy = GuidancePolicy(name="Level 1", base_mode="teaching")
    db_session.add(policy)
    await db_session.flush()

    assignment = Assignment(
        class_id=teaching_class.id,
        title="Assignment 1",
        guidance_policy_id=policy.id,
    )
    db_session.add(assignment)
    await db_session.flush()

    attempt = AssignmentAttempt(
        assignment_id=assignment.id,
        student_id=1,
    )
    db_session.add(attempt)
    await db_session.flush()

    assert attempt.status == "in_progress"
