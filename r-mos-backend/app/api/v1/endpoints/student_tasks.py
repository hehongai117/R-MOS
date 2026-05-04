"""学生任务列表端点 — 聚合 task_executions + training_sessions"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.task_execution import TaskExecution
from app.models.task import Task
from app.models.sop import SOP

router = APIRouter()


class StudentTaskItem(BaseModel):
    id: int
    task_id: int
    task_name: str
    sop_name: Optional[str] = None
    fault_type: Optional[str] = None
    status: str  # in_progress / completed / abandoned
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentTaskListResponse(BaseModel):
    items: List[StudentTaskItem]
    total: int
    pending_count: int
    in_progress_count: int
    completed_count: int


@router.get("/student/tasks", response_model=StudentTaskListResponse, tags=["student"])
async def list_student_tasks(
    student_id: int = Query(..., description="学生 user ID"),
    status: Optional[str] = Query(None, description="筛选状态: in_progress/completed/abandoned"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取学生的任务执行列表"""
    # Note: Task.title is the field name (not Task.name); SOP.name is the field name (not SOP.title)
    base_query = (
        select(TaskExecution, Task.title.label("task_name"), SOP.name.label("sop_name"))
        .join(Task, TaskExecution.task_id == Task.id, isouter=True)
        .join(SOP, TaskExecution.sop_id == SOP.id, isouter=True)
        .where(TaskExecution.student_id == student_id)
        .order_by(TaskExecution.started_at.desc())
    )

    if status:
        base_query = base_query.where(TaskExecution.status == status)

    # Count query
    count_query = (
        select(
            func.count(TaskExecution.id).label("total"),
            func.sum(case((TaskExecution.status == "in_progress", 1), else_=0)).label("in_progress_count"),
            func.sum(case((TaskExecution.status == "completed", 1), else_=0)).label("completed_count"),
        )
        .where(TaskExecution.student_id == student_id)
    )
    counts = (await db.execute(count_query)).one()

    # Paginated results
    result = await db.execute(base_query.limit(limit).offset(offset))
    rows = result.all()

    items = [
        StudentTaskItem(
            id=row.TaskExecution.id,
            task_id=row.TaskExecution.task_id,
            task_name=row.task_name or f"任务 #{row.TaskExecution.task_id}",
            sop_name=row.sop_name,
            fault_type=row.TaskExecution.fault_type,
            status=row.TaskExecution.status,
            started_at=row.TaskExecution.started_at,
            completed_at=row.TaskExecution.completed_at,
        )
        for row in rows
    ]

    return StudentTaskListResponse(
        items=items,
        total=counts.total or 0,
        pending_count=0,
        in_progress_count=counts.in_progress_count or 0,
        completed_count=counts.completed_count or 0,
    )
