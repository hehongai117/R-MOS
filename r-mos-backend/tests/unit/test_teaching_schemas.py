"""
Teaching domain schema tests.
"""
from datetime import datetime

from app.schemas.teaching import (
    GuidancePolicyResponse,
    AttemptStatus,
    AssignmentAttemptResponse,
    DiagnosisReport,
    DiagnosisSeverity,
    DiagnosisSourceRefs,
)


def test_guidance_policy_response_fields():
    payload = GuidancePolicyResponse(
        id=1,
        name="Level 1",
        base_mode="teaching",
        allow_ghost_hand=True,
        allow_hint_button=True,
        show_error_details=True,
        max_retry_count=-1,
    )
    data = payload.model_dump(by_alias=True)
    assert data["id"] == 1
    assert data["name"] == "Level 1"
    assert data["baseMode"] == "teaching"
    assert data["allowGhostHand"] is True
    assert data["allowHintButton"] is True
    assert data["showErrorDetails"] is True
    assert data["maxRetryCount"] == -1


def test_attempt_status_enum_values():
    assert AttemptStatus.IN_PROGRESS.value == "in_progress"
    assert AttemptStatus.COMPLETED.value == "completed"
    assert AttemptStatus.GRADED.value == "graded"
    assert AttemptStatus.ABANDONED.value == "abandoned"


def test_assignment_attempt_response_fields():
    payload = AssignmentAttemptResponse(
        id=10,
        assignment_id=20,
        student_id=30,
        task_id=None,
        status=AttemptStatus.IN_PROGRESS,
        score=None,
        attempt_index=1,
        diagnosis_code=None,
        path_score=None,
        evidence_quality_score=None,
    )
    data = payload.model_dump(by_alias=True)
    assert data["id"] == 10
    assert data["assignmentId"] == 20
    assert data["studentId"] == 30
    assert "taskId" in data
    assert data["status"] == "in_progress"
    assert data["attemptIndex"] == 1
    assert "diagnosisCode" in data
    assert "pathScore" in data
    assert "evidenceQualityScore" in data


def test_diagnosis_report_schema_fields():
    payload = DiagnosisReport(
        report_version="v1",
        attempt_id=101,
        diagnosis_code="OK",
        rule_id="R-DIAG-000",
        severity=DiagnosisSeverity.LOW,
        findings=[],
        recommendations=[],
        generated_at=datetime(2026, 1, 1, 0, 0, 0),
        source_refs=DiagnosisSourceRefs(attempt_evidence_id=555),
    )
    data = payload.model_dump(by_alias=True)
    assert data["reportVersion"] == "v1"
    assert data["attemptId"] == 101
    assert data["diagnosisCode"] == "OK"
    assert data["ruleId"] == "R-DIAG-000"
    assert data["severity"] == "LOW"
    assert "generatedAt" in data
    assert isinstance(data["findings"], list)
    assert isinstance(data["recommendations"], list)
    assert data["sourceRefs"]["attemptEvidenceId"] == 555
