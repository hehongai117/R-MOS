"""
Task API端点（V2.3完整版）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.services.authz_guard import (
    ActorContext,
    actor_has_role,
    get_current_actor,
    resolve_actor_identity,
)
from app.services.ownership import ensure_task_scope, ensure_write_owner
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskListResponse,
    StepExecutionRequest,
    StepExecutionResponse,
)
from app.schemas.report import ChecklistEvidence, TaskReport
from app.services.task_service import TaskService
from app.services.event_service import EventService
from app.services.scoring_service import ScoringService
from app.services.preflight_check import preflight_check_service
from app.models.task import TaskStatus
from app.models.task_execution import TaskExecution, TaskStepResult
from app.core.exceptions import BusinessRuleViolation

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, tags=["Tasks"])
async def create_task(
    request: TaskCreate,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """创建Task（带执行前检查）"""
    # 审计 M-02 残留：此前无身份注入，执行人取自请求体 `user_id`，
    # 任意登录用户可为他人建任务；且省略该字段即可整段跳过 P0-4-3 执行前检查。
    # 收敛到认证身份后 `user_id` 恒有值，执行前检查不再可绕过。
    request.user_id = resolve_actor_identity(
        actor,
        request.user_id,
        action="create_task",
        resource_type="Task",
    )

    # P0-4-3: 执行前检查
    # 将 user_id 转换为字符串（preflight check 使用字符串）
    user_id_str = str(request.user_id)

    # 获取 SOP 中的 robot_id（如果有）
    robot_id = None

    can_proceed, reason = await preflight_check_service.can_proceed(
        user_id=user_id_str,
        sop_id=request.sop_id,
        robot_id=robot_id,
        db=db,
        available_tools=request.available_tools,
    )

    if not can_proceed:
        raise HTTPException(
            status_code=400,
            detail={
                "error_type": "PreflightCheckFailed",
                "message": "执行前检查未通过",
                "reason": reason
            }
        )

    service = TaskService(db)
    task = await service.create_task(request)
    return task


@router.post("/tasks/{task_id}/start", response_model=TaskResponse, tags=["Tasks"])
async def start_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """开始Task"""
    # 审计 M-01：同文件的三个读端点均调 ensure_task_scope，
    # 四个写端点此前一个都没有——「读有写没有」的典型。
    service = TaskService(db)
    existing = await service.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await ensure_write_owner(
        db, request, actor, existing.user_id,
        action="start_task", resource_type="task", resource_id=task_id,
    )
    task = await service.start_task(task_id)
    return task


@router.post("/tasks/{task_id}/step", response_model=StepExecutionResponse, tags=["Tasks"])
async def execute_step(
    task_id: int,
    request: StepExecutionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """执行步骤（核心API）"""
    # 审计 M-01：此前无身份、无归属校验。
    service = TaskService(db)
    existing = await service.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await ensure_write_owner(
        db, http_request, actor, existing.user_id,
        action="execute_task_step", resource_type="task", resource_id=task_id,
    )
    response = await service.execute_step(task_id, request)
    return response


@router.post("/tasks/{task_id}/pause", response_model=TaskResponse, tags=["Tasks"])
async def pause_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """暂停Task"""
    # 审计 M-01：同文件的三个读端点均调 ensure_task_scope，
    # 四个写端点此前一个都没有——「读有写没有」的典型。
    service = TaskService(db)
    existing = await service.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await ensure_write_owner(
        db, request, actor, existing.user_id,
        action="pause_task", resource_type="task", resource_id=task_id,
    )
    task = await service.pause_task(task_id)
    return task


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse, tags=["Tasks"])
async def resume_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """恢复Task"""
    # 审计 M-01：同文件的三个读端点均调 ensure_task_scope，
    # 四个写端点此前一个都没有——「读有写没有」的典型。
    service = TaskService(db)
    existing = await service.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await ensure_write_owner(
        db, request, actor, existing.user_id,
        action="resume_task", resource_type="task", resource_id=task_id,
    )
    task = await service.resume_task(task_id)
    return task


@router.get("/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
    user_id: Optional[int] = Query(None, description="按执行用户过滤（仅教师/管理员可用）"),
    status: Optional[TaskStatus] = Query(None, description="按任务状态过滤"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """查询 Task 列表（维保报告列表页数据源）。

    可见范围按角色收敛：学生只能看到本人的任务，教师/管理员可查看全部或指定用户。
    入参 user_id 对学生无效——权限不能依赖前端传参，否则可被直接绕过。
    """
    # 与 robots/onboarding 同一缺陷：`actor.roles` 对正常注册用户为空集，
    # 只查它会使注册教师永远不被视为特权方。改用同时认两套来源的 actor_has_role。
    is_privileged = actor_has_role(actor, "teacher", "admin")
    effective_user_id = user_id if is_privileged else actor.user_id

    service = TaskService(db)
    items, total = await service.list_tasks(
        user_id=effective_user_id, status=status, limit=limit, offset=offset
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """查询Task"""
    service = TaskService(db)
    task = await service.get_task(task_id)
    await ensure_task_scope(
        db, request, actor, task.user_id, action="read_task", resource_id=task.id
    )
    return task


@router.get("/tasks/{task_id}/report", response_model=TaskReport, tags=["Tasks"])
async def get_task_report(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取Task报告"""
    # 1. 加载Task
    service = TaskService(db)
    task = await service.get_task(task_id)
    await ensure_task_scope(
        db,
        request,
        actor,
        task.user_id,
        action="read_task_report",
        resource_id=task.id,
    )

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

        evidence_result = await db.execute(
            select(TaskStepResult)
            .join(TaskExecution, TaskExecution.id == TaskStepResult.execution_id)
            .where(
                TaskExecution.task_id == task_id,
                TaskStepResult.evidence_type.in_(("kit_checklist", "verify_checklist")),
            )
            .order_by(TaskStepResult.step_index)
        )
        checklist_evidence = [
            ChecklistEvidence(
                step_index=item.step_index,
                evidence_type=item.evidence_type,
                evidence_value=item.evidence_value,
                is_compliant=item.is_compliant,
            )
            for item in evidence_result.scalars().all()
        ]

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
            generated_at=datetime.now(timezone.utc),
            checklist_evidence=checklist_evidence or None,
        )
    else:
        raise BusinessRuleViolation(
            message="Task尚未完成，无法生成报告",
            code="TASK_NOT_COMPLETED",
            # V2.3.1 修复: 兼容字符串和枚举两种类型
            details={"task_status": task.status.value if hasattr(task.status, 'value') else task.status}
        )


@router.get("/tasks/{task_id}/events", tags=["Tasks"])
async def get_task_events(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取Task的所有事件（V2.4 新增 - 用于测试验证）"""
    # 验证Task存在
    service = TaskService(db)
    task = await service.get_task(task_id)  # 如果不存在会抛异常
    await ensure_task_scope(
        db,
        request,
        actor,
        task.user_id,
        action="read_task_events",
        resource_id=task.id,
    )

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
