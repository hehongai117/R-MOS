"""
Evidence engine tests.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select

# Ensure teaching models are registered for metadata
import app.models.teaching  # noqa: F401

from app.models.evidence import EvidenceBundle
from app.models.teaching import EvidenceLink, Assignment
from app.schemas.task import StepExecutionRequest
from app.services.evidence_engine import EvidenceEngine
from app.services.task_service import TaskService
from app.services.teaching_service import TeachingService


@pytest.mark.asyncio
async def test_generate_evidence_bundle(db_session, sample_task):
    engine = EvidenceEngine(db_session)
    bundle = await engine.generate_bundle_for_task(sample_task.id)
    assert bundle.id is not None


@pytest.mark.asyncio
async def test_generate_link_when_attempt_exists(db_session, sample_task):
    teaching_service = TeachingService(db_session)
    teaching_class = await teaching_service.create_class(name="Class A")
    assignment = await teaching_service.create_assignment(
        class_id=teaching_class.id,
        title="Assignment 1",
    )

    sample_task.assignment_id = assignment.id
    await db_session.commit()

    attempt = await teaching_service.create_attempt(
        assignment_id=assignment.id,
        student_id=101,
        task_id=sample_task.id,
    )

    engine = EvidenceEngine(db_session)
    bundle = await engine.generate_bundle_for_task(sample_task.id)

    result = await db_session.execute(
        select(EvidenceLink).where(EvidenceLink.bundle_id == bundle.id)
    )
    link = result.scalar_one_or_none()
    assert link is not None
    assert link.task_id == sample_task.id
    assert link.attempt_id == attempt.id
    assert link.student_id == attempt.student_id

    assignment_row = await db_session.get(Assignment, attempt.assignment_id)
    assert link.class_id == assignment_row.class_id


@pytest.mark.asyncio
async def test_task_completion_hook_generates_bundle(db_session, sample_task):
    service = TaskService(db_session)

    await service.start_task(sample_task.id)

    await service.execute_step(
        sample_task.id,
        StepExecutionRequest(step_index=1, action="execute", parameters={}),
    )
    await service.execute_step(
        sample_task.id,
        StepExecutionRequest(step_index=2, action="execute", parameters={}),
    )

    result = await db_session.execute(
        select(EvidenceLink).where(EvidenceLink.task_id == sample_task.id)
    )
    link = result.scalar_one_or_none()
    assert link is not None

    bundle = await db_session.get(EvidenceBundle, link.bundle_id)
    assert bundle is not None
