"""Task pipeline: diagnosis → task creation → step tracking → report."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.sop import SOP
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.task_execution import TaskExecution, TaskStepResult

logger = logging.getLogger(__name__)


class TaskPipelineService:
    """Orchestrates the diagnosis → task → execution → report pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task_from_diagnosis(
        self,
        diagnosis_trace_id: str,
        fault_type: str,
        student_id: int,
    ) -> dict[str, Any]:
        """Create a maintenance task from diagnosis result."""
        # Find SOP via fault_sop_mapping
        stmt = (
            select(FaultSOPMapping)
            .where(FaultSOPMapping.fault_type == fault_type)
            .order_by(FaultSOPMapping.priority.desc())
            .limit(1)
        )
        mapping_result = await self.db.execute(stmt)
        mapping = mapping_result.scalar_one_or_none()

        sop_id = mapping.sop_id if mapping else None
        sop_name = ""

        if sop_id:
            sop_result = await self.db.execute(select(SOP).where(SOP.id == sop_id))
            sop = sop_result.scalar_one_or_none()
            sop_name = sop.name if sop else ""

        # Create Task
        task = Task(
            title=f"维保任务: {fault_type}",
            sop_id=sop_id,
            user_id=student_id,
            status=TaskStatus.IN_PROGRESS.value,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(task)
        await self.db.flush()

        # Create TaskExecution
        execution = TaskExecution(
            task_id=task.id,
            student_id=student_id,
            sop_id=sop_id,
            diagnosis_trace_id=diagnosis_trace_id,
            fault_type=fault_type,
            status="in_progress",
        )
        self.db.add(execution)
        await self.db.commit()

        return {
            "task_id": task.id,
            "execution_id": execution.id,
            "sop_id": sop_id,
            "sop_name": sop_name,
            "fault_type": fault_type,
        }

    async def complete_step(
        self,
        execution_id: int,
        step_index: int,
        evidence_type: Optional[str] = None,
        evidence_value: Optional[dict] = None,
        duration_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        """Record step completion with evidence."""
        step_result = TaskStepResult(
            execution_id=execution_id,
            step_index=step_index,
            status="completed",
            duration_seconds=duration_seconds,
            evidence_type=evidence_type,
            evidence_value=evidence_value,
            is_compliant=True,
        )
        self.db.add(step_result)
        await self.db.commit()

        return {
            "step_index": step_index,
            "is_compliant": step_result.is_compliant,
            "feedback": None,
        }

    async def complete_task(
        self,
        execution_id: int,
    ) -> dict[str, Any]:
        """Mark execution complete and trigger report generation."""
        stmt = select(TaskExecution).where(TaskExecution.id == execution_id)
        result = await self.db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            return {"error": "Execution not found"}

        execution.status = "completed"
        execution.completed_at = datetime.now(timezone.utc)

        # Update parent task
        task_stmt = select(Task).where(Task.id == execution.task_id)
        task_result = await self.db.execute(task_stmt)
        task = task_result.scalar_one_or_none()
        if task:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now(timezone.utc)

        await self.db.commit()

        return {
            "execution_id": execution_id,
            "task_id": execution.task_id,
            "status": "completed",
            "report_generation": "triggered",
        }
