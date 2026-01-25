"""
TeachingService unit tests.
"""
import pytest

from app.core.exceptions import BusinessRuleViolation
from app.services.teaching_service import TeachingService


@pytest.mark.asyncio
async def test_create_guidance_policy_defaults(db_session):
    service = TeachingService(db_session)
    policy = await service.create_guidance_policy(name="Level 1", base_mode="teaching")

    assert policy.id is not None
    assert policy.allow_ghost_hand is True
    assert policy.allow_hint_button is True
    assert policy.show_error_details is True
    assert policy.max_retry_count == -1


@pytest.mark.asyncio
async def test_create_class_and_course(db_session):
    service = TeachingService(db_session)
    teaching_class = await service.create_class(name="Class A")
    course = await service.create_course(class_id=teaching_class.id, name="Course 1")

    assert course.id is not None
    assert course.class_id == teaching_class.id


@pytest.mark.asyncio
async def test_enroll_student_duplicate(db_session):
    service = TeachingService(db_session)
    teaching_class = await service.create_class(name="Class A")

    enrollment = await service.enroll_student(class_id=teaching_class.id, student_id=1)
    assert enrollment.id is not None

    with pytest.raises(BusinessRuleViolation) as exc:
        await service.enroll_student(class_id=teaching_class.id, student_id=1)

    assert exc.value.code == "ALREADY_ENROLLED"


@pytest.mark.asyncio
async def test_create_assignment_and_attempt(db_session):
    service = TeachingService(db_session)
    teaching_class = await service.create_class(name="Class A")
    policy = await service.create_guidance_policy(name="Level 1", base_mode="teaching")

    assignment = await service.create_assignment(
        class_id=teaching_class.id,
        title="Assignment 1",
        guidance_policy_id=policy.id,
    )

    attempt1 = await service.create_attempt(assignment_id=assignment.id, student_id=10)
    attempt2 = await service.create_attempt(assignment_id=assignment.id, student_id=10)

    assert attempt1.attempt_index == 1
    assert attempt2.attempt_index == 2
    assert attempt1.status == "in_progress"


@pytest.mark.asyncio
async def test_attempt_status_transitions(db_session):
    service = TeachingService(db_session)
    teaching_class = await service.create_class(name="Class A")
    assignment = await service.create_assignment(class_id=teaching_class.id, title="Assignment 1")

    attempt = await service.create_attempt(assignment_id=assignment.id, student_id=1)
    attempt = await service.update_attempt_status(attempt.id, "completed")
    graded = await service.grade_attempt(attempt.id, score=88.5)

    assert graded.status == "graded"
    assert graded.score == 88.5

    attempt2 = await service.create_attempt(assignment_id=assignment.id, student_id=2)
    attempt2 = await service.update_attempt_status(attempt2.id, "abandoned")

    with pytest.raises(BusinessRuleViolation):
        await service.update_attempt_status(attempt2.id, "completed")

    attempt3 = await service.create_attempt(assignment_id=assignment.id, student_id=3)
    await service.update_attempt_status(attempt3.id, "completed")

    with pytest.raises(BusinessRuleViolation):
        await service.update_attempt_status(attempt3.id, "in_progress")

    with pytest.raises(BusinessRuleViolation):
        await service.update_attempt_status(graded.id, "completed")
