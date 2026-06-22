"""
Diagnosis service for teaching attempts (Phase2 P0).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation
from app.models.evidence import EvidenceBundle
from app.models.event import EventType
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
        step_diagnoses = await self._build_step_diagnoses(
            summary,
            task_id=attempt.task_id,
            rule_id=rule_id,
            diagnosis_code=diagnosis_code,
            severity=severity,
        )

        report = DiagnosisReport(
            report_version="v1",
            attempt_id=attempt_id,
            diagnosis_code=diagnosis_code,
            rule_id=rule_id,
            severity=severity,
            findings=findings,
            recommendations=recommendations,
            step_diagnoses=step_diagnoses,
            generated_at=datetime.now(timezone.utc),
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

    async def _build_step_diagnoses(
        self,
        summary: dict[str, Any],
        *,
        task_id: Optional[int],
        rule_id: str,
        diagnosis_code: str,
        severity: DiagnosisSeverity,
    ) -> list[StepDiagnosis]:
        total_steps = self._resolve_int(summary, "total_steps", None)
        if total_steps <= 0:
            total_steps = self._resolve_int(summary, "totalSteps", None)
        if total_steps <= 0:
            return []
        step_diagnoses = [
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
        if rule_id == "R-DIAG-000":
            return step_diagnoses

        step_index = await self._resolve_step_index(task_id, rule_id)
        fallback_used = False
        if step_index is None:
            step_index = 1
            fallback_used = True
        if step_index < 1 or step_index > total_steps:
            step_index = 1
            fallback_used = True

        findings, recommendations = self._step_rule_messages(rule_id)
        if fallback_used:
            findings = [*findings, "未定位具体步骤，默认标记步骤 1"]

        target = step_diagnoses[step_index - 1]
        target.step_diagnosis_code = diagnosis_code
        target.severity = severity
        target.rule_id = rule_id
        target.findings = findings
        target.recommendations = recommendations
        return step_diagnoses

    async def _resolve_step_index(self, task_id: Optional[int], rule_id: str) -> Optional[int]:
        if not task_id:
            return None
        event_service = EventService(self.db)
        events = await event_service.get_task_events(task_id)
        if rule_id == "R-DIAG-001":
            step_index = self._pick_step_index(events, lambda event: event.is_error)
            if step_index is not None:
                return step_index
        if rule_id == "R-DIAG-002":
            step_index = self._pick_step_index(
                events,
                lambda event: event.event_type == EventType.STEP_SKIPPED.value,
            )
            if step_index is not None:
                return step_index
        if rule_id == "R-DIAG-003":
            step_index = self._pick_slowest_step_index(events)
            if step_index is not None:
                return step_index

        return self._pick_step_index(events, lambda event: event.step_index is not None)

    @staticmethod
    def _pick_step_index(events: list[Any], predicate) -> Optional[int]:
        for event in events:
            if predicate(event) and event.step_index is not None:
                return event.step_index
        return None

    @staticmethod
    def _pick_slowest_step_index(events: list[Any]) -> Optional[int]:
        duration_by_step: dict[int, int] = {}
        for event in events:
            if event.step_index is None:
                continue
            if event.duration_ms is not None:
                duration_by_step[event.step_index] = duration_by_step.get(event.step_index, 0) + int(
                    event.duration_ms
                )
        if duration_by_step:
            return max(duration_by_step.items(), key=lambda item: item[1])[0]

        timestamp_by_step: dict[int, list[datetime]] = {}
        for event in events:
            if event.step_index is None or not event.timestamp:
                continue
            timestamp_by_step.setdefault(event.step_index, []).append(event.timestamp)
        if not timestamp_by_step:
            return None

        def span(step_times: list[datetime]) -> float:
            return (max(step_times) - min(step_times)).total_seconds()

        return max(timestamp_by_step.items(), key=lambda item: span(item[1]))[0]

    @staticmethod
    def _step_rule_messages(rule_id: str) -> tuple[list[str], list[str]]:
        if rule_id == "R-DIAG-001":
            return ["该步骤存在错误"], ["建议复核该步骤的输入与预期输出"]
        if rule_id == "R-DIAG-002":
            return ["该步骤被跳过"], ["建议完成该步骤，避免跳过"]
        if rule_id == "R-DIAG-003":
            return ["步骤耗时偏长"], ["建议优化该步骤执行效率"]
        return [], []

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
                ["步骤耗时偏长"],
                ["建议优化步骤执行效率"],
            )
        return (
            "R-DIAG-000",
            "OK",
            DiagnosisSeverity.LOW,
            [],
            [],
        )
