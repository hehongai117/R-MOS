"""
Diagnosis service unit tests.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.models.evidence import EvidenceBundle
from app.models.teaching import EvidenceLink
from app.schemas.teaching import DiagnosisSeverity
from app.services.diagnosis_service import DiagnosisService
from app.services.teaching_service import TeachingService


async def _create_attempt(db_session):
    teaching_service = TeachingService(db_session)
    teaching_class = await teaching_service.create_class(name="诊断班级")
    assignment = await teaching_service.create_assignment(
        class_id=teaching_class.id,
        title="诊断作业",
    )
    attempt = await teaching_service.create_attempt(
        assignment_id=assignment.id,
        student_id=1,
        task_id=None,
    )
    return attempt


async def _attach_evidence(db_session, *, attempt_id: int, summary: dict):
    bundle = EvidenceBundle(
        id=str(uuid4()),
        bundle_type="sop_execution",
        bundle_hash="hash",
        bundle_hash_algo="sha256",
        observed_time_start=datetime.utcnow(),
        ingest_time=datetime.utcnow(),
        is_sealed=True,
        sealed_at=datetime.utcnow(),
        machine_tags=summary,
    )
    db_session.add(bundle)
    await db_session.flush()

    link = EvidenceLink(
        bundle_id=bundle.id,
        attempt_id=attempt_id,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


@pytest.mark.asyncio
async def test_diagnosis_rule_error_count(db_session):
    attempt = await _create_attempt(db_session)
    link = await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={"error_count": 1, "skip_count": 0, "duration_ms": 1000},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert report.diagnosis_code == "E_ERROR_OCCURRED"
    assert report.rule_id == "R-DIAG-001"
    assert report.severity == DiagnosisSeverity.HIGH
    assert report.source_refs.attempt_evidence_id == link.id
    assert isinstance(report.findings, list)
    assert isinstance(report.recommendations, list)


@pytest.mark.asyncio
async def test_diagnosis_rule_skip_count(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={"error_count": 0, "skip_count": 2, "duration_ms": 1000},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert report.diagnosis_code == "E_STEP_SKIPPED"
    assert report.rule_id == "R-DIAG-002"
    assert report.severity == DiagnosisSeverity.MEDIUM


@pytest.mark.asyncio
async def test_diagnosis_rule_duration(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={"error_count": 0, "skip_count": 0, "duration_ms": 6000},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert report.diagnosis_code == "E_TOO_SLOW"
    assert report.rule_id == "R-DIAG-003"
    assert report.severity == DiagnosisSeverity.LOW


@pytest.mark.asyncio
async def test_diagnosis_no_match_defaults(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert report.diagnosis_code == "OK"
    assert report.rule_id == "R-DIAG-000"
    assert report.severity == DiagnosisSeverity.LOW


@pytest.mark.asyncio
async def test_diagnosis_idempotent(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={"error_count": 0, "skip_count": 1, "duration_ms": 1000},
    )
    service = DiagnosisService(db_session)
    first = await service.get_diagnosis_report(attempt.id)
    second = await service.get_diagnosis_report(attempt.id)
    assert first.diagnosis_code == second.diagnosis_code


@pytest.mark.asyncio
async def test_diagnosis_report_placeholders(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert report.step_diagnoses == []
    assert report.factors == []
    assert report.attachments == []


@pytest.mark.asyncio
async def test_step_diagnoses_generated_from_total_steps(db_session):
    attempt = await _create_attempt(db_session)
    await _attach_evidence(
        db_session,
        attempt_id=attempt.id,
        summary={"total_steps": 2},
    )
    service = DiagnosisService(db_session)
    report = await service.get_diagnosis_report(attempt.id)
    assert len(report.step_diagnoses) == 2
    assert report.step_diagnoses[0].step_index == 1
    assert report.step_diagnoses[1].step_index == 2
    for step in report.step_diagnoses:
        assert step.step_diagnosis_code == "OK"
        assert step.severity == DiagnosisSeverity.LOW
        assert step.rule_id == "R-DIAG-S-000"
        assert step.findings == []
        assert step.recommendations == []
        assert step.source_refs is not None
