from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.task import Task, TaskStatus
from app.models.task_execution import TaskExecution, TaskStepResult


def test_completed_task_report_includes_checklist_evidence(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = e2e_env

    async def seed_report() -> int:
        async with session_factory() as session:
            now = datetime.now(timezone.utc)
            task = Task(
                title="膝关节轴承更换",
                status=TaskStatus.COMPLETED.value,
                started_at=now,
                completed_at=now,
                current_step_index=2,
                is_passed=True,
            )
            session.add(task)
            await session.flush()

            execution = TaskExecution(task_id=task.id, student_id=7, status="completed")
            session.add(execution)
            await session.flush()
            session.add_all(
                [
                    TaskStepResult(
                        execution_id=execution.id,
                        step_index=1,
                        evidence_type="kit_checklist",
                        evidence_value={
                            "required_items": ["6205 轴承", "拉拔器"],
                            "confirmed_items": ["6205 轴承", "拉拔器"],
                        },
                        is_compliant=True,
                    ),
                    TaskStepResult(
                        execution_id=execution.id,
                        step_index=2,
                        evidence_type="verify_checklist",
                        evidence_value={
                            "required_items": ["轴承转动顺畅"],
                            "confirmed_items": ["轴承转动顺畅"],
                        },
                        is_compliant=True,
                    ),
                    TaskStepResult(
                        execution_id=execution.id,
                        step_index=3,
                        evidence_type="photo",
                        evidence_value={"url": "existing-photo.jpg"},
                        is_compliant=True,
                    ),
                ]
            )
            await session.commit()
            return task.id

    task_id = asyncio.run(seed_report())
    response = client.get(f"/api/v1/tasks/{task_id}/report")

    assert response.status_code == 200
    assert response.json()["checklist_evidence"] == [
        {
            "step_index": 1,
            "evidence_type": "kit_checklist",
            "evidence_value": {
                "required_items": ["6205 轴承", "拉拔器"],
                "confirmed_items": ["6205 轴承", "拉拔器"],
            },
            "is_compliant": True,
        },
        {
            "step_index": 2,
            "evidence_type": "verify_checklist",
            "evidence_value": {
                "required_items": ["轴承转动顺畅"],
                "confirmed_items": ["轴承转动顺畅"],
            },
            "is_compliant": True,
        },
    ]


def test_task_report_schema_keeps_checklist_evidence_optional() -> None:
    from app.schemas.report import TaskReport

    assert TaskReport.model_fields["checklist_evidence"].default is None
