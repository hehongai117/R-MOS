"""
Evidence engine for generating summary evidence bundles from task execution data.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation
from app.models.evidence import EvidenceBundle
from app.models.event import Event, EventType
from app.models.snapshot import Snapshot
from app.models.task import Task
from app.models.teaching import AssignmentAttempt, Assignment, EvidenceLink


class EvidenceEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_bundle_for_task(self, task_id: int) -> EvidenceBundle:
        task = await self._load_task(task_id)
        events = await self._load_events(task_id)
        snapshots = await self._load_snapshots(task_id)

        observed_start, observed_end = self._observed_window(task, events, snapshots)
        summary = self._build_summary(task, events, snapshots, observed_start, observed_end)

        bundle_id = str(uuid.uuid4())
        bundle_hash = self._compute_bundle_hash(task_id, summary, observed_start, observed_end)
        ingest_time = datetime.utcnow()

        bundle = EvidenceBundle(
            id=bundle_id,
            bundle_type="sop_execution",
            bundle_hash=bundle_hash,
            bundle_hash_algo="sha256",
            observed_time_start=observed_start,
            observed_time_end=observed_end,
            ingest_time=ingest_time,
            is_sealed=True,
            sealed_at=ingest_time,
            human_summary="Auto-generated evidence bundle",
            machine_tags=summary,
        )
        self.db.add(bundle)
        await self.db.flush()

        await self._create_link(task, bundle_id)

        await self.db.commit()
        await self.db.refresh(bundle)
        return bundle

    async def _load_task(self, task_id: int) -> Task:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise BusinessRuleViolation(
                message="Task不存在",
                code="TASK_NOT_FOUND",
                details={"task_id": task_id},
            )
        return task

    async def _load_events(self, task_id: int) -> List[Event]:
        result = await self.db.execute(
            select(Event).where(Event.task_id == task_id).order_by(Event.timestamp)
        )
        return result.scalars().all()

    async def _load_snapshots(self, task_id: int) -> List[Snapshot]:
        result = await self.db.execute(
            select(Snapshot).where(Snapshot.task_id == task_id).order_by(Snapshot.timestamp)
        )
        return result.scalars().all()

    def _observed_window(
        self,
        task: Task,
        events: List[Event],
        snapshots: List[Snapshot],
    ) -> Tuple[datetime, Optional[datetime]]:
        times: List[datetime] = []
        if task.started_at:
            times.append(task.started_at)
        if task.completed_at:
            times.append(task.completed_at)
        times.extend([event.timestamp for event in events if event.timestamp])
        times.extend([snapshot.timestamp for snapshot in snapshots if snapshot.timestamp])

        if not times:
            now = datetime.utcnow()
            return now, None

        start = min(times)
        end = max(times)
        return start, end

    def _build_summary(
        self,
        task: Task,
        events: List[Event],
        snapshots: List[Snapshot],
        observed_start: datetime,
        observed_end: Optional[datetime],
    ) -> Dict[str, Any]:
        total_steps = sum(1 for event in events if event.event_type == EventType.STEP_EXECUTED.value)
        skip_count = sum(1 for event in events if event.event_type == EventType.STEP_SKIPPED.value)
        error_count = sum(1 for event in events if event.is_error)

        duration_ms = 0
        if task.started_at and task.completed_at:
            duration_ms = int((task.completed_at - task.started_at).total_seconds() * 1000)
        elif observed_end:
            duration_ms = int((observed_end - observed_start).total_seconds() * 1000)

        return {
            "task_id": task.id,
            "task_status": task.status,
            "total_events": len(events),
            "snapshot_count": len(snapshots),
            "total_steps": total_steps,
            "skip_count": skip_count,
            "error_count": error_count,
            "duration_ms": duration_ms,
            "final_score": task.final_score,
            "is_passed": task.is_passed,
        }

    def _compute_bundle_hash(
        self,
        task_id: int,
        summary: Dict[str, Any],
        observed_start: datetime,
        observed_end: Optional[datetime],
    ) -> str:
        manifest = {
            "task_id": task_id,
            "bundle_type": "sop_execution",
            "observed_time_start": observed_start.isoformat(),
            "observed_time_end": observed_end.isoformat() if observed_end else None,
            "summary": summary,
        }
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def _find_attempt(self, task_id: int) -> Optional[AssignmentAttempt]:
        result = await self.db.execute(
            select(AssignmentAttempt)
            .where(
                AssignmentAttempt.task_id == task_id,
                AssignmentAttempt.status != "abandoned",
            )
            .order_by(desc(AssignmentAttempt.attempt_index))
        )
        return result.scalar_one_or_none()

    async def _create_link(self, task: Task, bundle_id: str) -> EvidenceLink:
        attempt: Optional[AssignmentAttempt] = None
        class_id: Optional[int] = None
        student_id: Optional[int] = None
        attempt_id: Optional[int] = None

        if task.assignment_id is not None:
            attempt = await self._find_attempt(task.id)

        if attempt:
            attempt_id = attempt.id
            student_id = attempt.student_id
            assignment = await self.db.get(Assignment, attempt.assignment_id)
            class_id = assignment.class_id if assignment else None
            attempt.evidence_bundle_id = bundle_id

        link = EvidenceLink(
            bundle_id=bundle_id,
            task_id=task.id,
            attempt_id=attempt_id,
            student_id=student_id,
            class_id=class_id,
        )
        self.db.add(link)
        await self.db.flush()
        return link
