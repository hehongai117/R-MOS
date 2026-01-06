"""
Task API端点（V2.3完整版）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.schemas.task import TaskCreate, TaskResponse, StepExecutionRequest, StepExecutionResponse
from app.schemas.report import TaskReport
from app.services.task_service import TaskService
from app.services.event_service import EventService
from app.services.scoring_service import ScoringService
from app.models.task import TaskStatus
from app.core.exceptions import BusinessRuleViolation

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, tags=["Tasks"])
async def create_task(
    request: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建Task"""
    try:
        service = TaskService(db)
        task = await service.create_task(request)
        return task
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/start", response_model=TaskResponse, tags=["Tasks"])
async def start_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """开始Task"""
    try:
        service = TaskService(db)
        task = await service.start_task(task_id)
        return task
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/step", response_model=StepExecutionResponse, tags=["Tasks"])
async def execute_step(
    task_id: int,
    request: StepExecutionRequest,
    db: AsyncSession = Depends(get_db)
):
    """执行步骤（核心API）"""
    try:
        service = TaskService(db)
        response = await service.execute_step(task_id, request)
        return response
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/pause", response_model=TaskResponse, tags=["Tasks"])
async def pause_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """暂停Task"""
    try:
        service = TaskService(db)
        task = await service.pause_task(task_id)
        return task
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse, tags=["Tasks"])
async def resume_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """恢复Task"""
    try:
        service = TaskService(db)
        task = await service.resume_task(task_id)
        return task
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """查询Task"""
    try:
        service = TaskService(db)
        task = await service.get_task(task_id)
        return task
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/report", response_model=TaskReport, tags=["Tasks"])
async def get_task_report(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取Task报告"""
    try:
        # 1. 加载Task
        service = TaskService(db)
        task = await service.get_task(task_id)
        
        # 2. 加载评分（如果已完成）
        if task.status == TaskStatus.COMPLETED:
            scoring_service = ScoringService(db)
            score_result = await scoring_service.calculate_score(task_id)
            
            # 3. 加载SOP（可能为NULL）
            sop_name = None
            if task.sop_id:
                sop = await service._get_sop(task.sop_id)
                sop_name = sop.name if sop else None
            
            # 4. 获取错误事件数量
            event_service = EventService(db)
            events = await event_service.get_task_events(task_id)
            error_count = sum(1 for e in events if e.is_error)

            # 5. 构造报告
            # V2.3.1 修复: 防御性检查 started_at 和 completed_at
            total_duration = 0
            if task.started_at and task.completed_at:
                total_duration = int((task.completed_at - task.started_at).total_seconds())

            return TaskReport(
                task_id=task.id,
                task_title=task.title,
                sop_name=sop_name,
                user_id=task.user_id,
                started_at=task.started_at,
                completed_at=task.completed_at,
                total_duration_seconds=total_duration,
                expected_duration_seconds=task.time_limit,
                final_score=score_result["final_score"],
                pass_score=float(task.pass_score),
                is_passed=task.is_passed,
                score_breakdown=score_result["breakdown"],
                step_scores=score_result["step_scores"],
                total_steps=len(score_result["step_scores"]),
                completed_steps=task.current_step_index,
                skipped_steps=sum(1 for s in score_result["step_scores"] if s.remarks == "已跳过"),
                error_count=error_count,
                recommendations=score_result["recommendations"],
                generated_at=datetime.utcnow()
            )
        else:
            raise BusinessRuleViolation(
                message="Task尚未完成，无法生成报告",
                code="TASK_NOT_COMPLETED",
                # V2.3.1 修复: 兼容字符串和枚举两种类型
                details={"task_status": task.status.value if hasattr(task.status, 'value') else task.status}
            )
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/events", tags=["Tasks"])
async def get_task_events(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取Task的所有事件（V2.4 新增 - 用于测试验证）"""
    try:
        # 验证Task存在
        service = TaskService(db)
        await service.get_task(task_id)  # 如果不存在会抛异常
        
        # 获取事件列表
        event_service = EventService(db)
        events = await event_service.get_task_events(task_id)
        
        # 返回事件列表（简化格式）
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "step_index": e.step_index,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "action": e.action,
                "result": e.result,
                "is_error": e.is_error,
                "error_message": e.error_message,
            }
            for e in events
        ]
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
