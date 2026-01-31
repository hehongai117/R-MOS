"""
Diagnosis service for teaching attempts (Phase2 P0).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation
from app.models.evidence import EvidenceBundle
from app.models.task import TaskStatus
from app.models.teaching import EvidenceLink
from app.schemas.teaching import (
    DiagnosisReport,
    DiagnosisSeverity,
    DiagnosisSourceRefs,
    StepDiagnosis,
    StepDiagnosisSourceRefs,
)
from app.services.evidence_engine import EvidenceEngine
from app.services.event_service import EventService
from app.services.scoring_service import ScoringService
from app.services.task_service import TaskService
from app.services.teaching_service import TeachingService

logger = logging.getLogger(__name__)


class EvidenceFallbackError(Exception):
    """Evidence fallback failed when generating diagnosis."""

    def __init__(self, *, attempt_id: int, task_id: Optional[int]):
        self.attempt_id = attempt_id
        self.task_id = task_id
        super().__init__("EVIDENCE_FALLBACK_FAILED")


class DiagnosisService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_diagnosis_report(self, attempt_id: int) -> DiagnosisReport:
        teaching_service = TeachingService(self.db)
        attempt = await teaching_service.get_attempt(attempt_id)

        summary, evidence_link_id, fallback_used = await self._load_evidence_summary(attempt_id, attempt.task_id)
        report_fields = await self._load_task_report_fields(attempt.task_id) if attempt.task_id else {}

        error_count = self._resolve_int(summary, "error_count", report_fields.get("error_count"))
        skip_count = self._resolve_int(summary, "skip_count", report_fields.get("skip_count"))
        duration_ms = self._resolve_int(summary, "duration_ms", report_fields.get("duration_ms"))

        rule_id, diagnosis_code, severity, findings, recommendations = self._apply_rules(
            error_count=error_count,
            skip_count=skip_count,
            duration_ms=duration_ms,
        )
        step_diagnoses = self._build_step_diagnoses(summary)

        report = DiagnosisReport(
            report_version="v1",
            attempt_id=attempt_id,
            diagnosis_code=diagnosis_code,
            rule_id=rule_id,
            severity=severity,
            findings=findings,
            recommendations=recommendations,
            step_diagnoses=step_diagnoses,
            generated_at=datetime.utcnow(),
            source_refs=DiagnosisSourceRefs(attempt_evidence_id=evidence_link_id),
        )

        logger.info(
            "Diagnosis generated: attempt_id=%s diagnosis_code=%s rule_id=%s evidence_fallback=%s",
            attempt_id,
            diagnosis_code,
            rule_id,
            fallback_used,
        )
        return report

    async def _load_evidence_summary(
        self,
        attempt_id: int,
        task_id: Optional[int],
    ) -> tuple[dict[str, Any], int, bool]:
        async def load_latest_link() -> EvidenceLink | None:
            result = await self.db.execute(
                select(EvidenceLink)
                .where(EvidenceLink.attempt_id == attempt_id)
                .order_by(EvidenceLink.created_at.desc())
            )
            return result.scalars().first()

        link = await load_latest_link()
        fallback_used = False

        if not link:
            fallback_used = True
            if not task_id:
                raise EvidenceFallbackError(attempt_id=attempt_id, task_id=task_id)
            try:
                engine = EvidenceEngine(self.db)
                await engine.generate_bundle_for_task(
                    task_id,
                    preferred_attempt_id=attempt_id,
                )
            except BusinessRuleViolation as exc:
                logger.error(
                    "Evidence fallback failed: attempt_id=%s task_id=%s code=%s",
                    attempt_id,
                    task_id,
                    exc.code,
                )
                raise EvidenceFallbackError(attempt_id=attempt_id, task_id=task_id) from exc
            link = await load_latest_link()

        if not link:
            raise EvidenceFallbackError(attempt_id=attempt_id, task_id=task_id)

        bundle = await self.db.get(EvidenceBundle, link.bundle_id)
        if not bundle:
            raise EvidenceFallbackError(attempt_id=attempt_id, task_id=task_id)

        return bundle.machine_tags or {}, link.id, fallback_used

    async def _load_task_report_fields(self, task_id: int) -> dict[str, int]:
        task_service = TaskService(self.db)
        task = await task_service.get_task(task_id)
        if task.status != TaskStatus.COMPLETED:
            return {}

        scoring_service = ScoringService(self.db)
        score_result = await scoring_service.calculate_score(task_id)

        event_service = EventService(self.db)
        events = await event_service.get_task_events(task_id)
        error_count = sum(1 for event in events if event.is_error)

        skipped_steps = sum(
            1 for step_score in score_result["step_scores"] if step_score.remarks == "已跳过"
        )

        total_duration_seconds = 0
        if task.started_at and task.completed_at:
            total_duration_seconds = int((task.completed_at - task.started_at).total_seconds())

        return {
            "error_count": error_count,
            "skip_count": skipped_steps,
            "duration_ms": total_duration_seconds * 1000,
        }

    def _resolve_int(self, summary: dict[str, Any], key: str, fallback_value: Optional[int]) -> int:
        raw = summary.get(key)
        if isinstance(raw, (int, float)):
            return int(raw)
        if isinstance(fallback_value, (int, float)):
            return int(fallback_value)
        return 0

    def _build_step_diagnoses(self, summary: dict[str, Any]) -> list[StepDiagnosis]:
        total_steps = self._resolve_int(summary, "total_steps", None)
        if total_steps <= 0:
            total_steps = self._resolve_int(summary, "totalSteps", None)
        if total_steps <= 0:
            return []
        return [
            StepDiagnosis(
                step_index=step_index,
                step_diagnosis_code="OK",
                severity=DiagnosisSeverity.LOW,
                findings=[],
                recommendations=[],
                rule_id="R-DIAG-S-000",
                source_refs=StepDiagnosisSourceRefs(),
            )
            for step_index in range(1, total_steps + 1)
        ]

    def _apply_rules(
        self,
        *,
        error_count: int,
        skip_count: int,
        duration_ms: int,
    ) -> tuple[str, str, DiagnosisSeverity, list[str], list[str]]:
        if error_count > 0:
            return (
                "R-DIAG-001",
                "E_ERROR_OCCURRED",
                DiagnosisSeverity.HIGH,
                ["存在错误步骤"],
                ["建议复核错误步骤的输入与预期输出"],
            )
        if skip_count > 0:
            return (
                "R-DIAG-002",
                "E_STEP_SKIPPED",
                DiagnosisSeverity.MEDIUM,
                ["存在跳过步骤"],
                ["建议完成所有步骤，避免跳过"],
            )
        if duration_ms > 5000:
            return (
                "R-DIAG-003",
                "E_TOO_SLOW",
                DiagnosisSeverity.LOW,
                ["完成耗时偏长"],
                ["建议优化步骤执行效率"],
            )
        return (
            "R-DIAG-000",
            "OK",
            DiagnosisSeverity.LOW,
            [],
            [],
        )
