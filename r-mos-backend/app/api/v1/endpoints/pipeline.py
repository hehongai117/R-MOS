"""Pipeline API — diagnosis-to-task-to-report flow."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.task_execution import TaskExecution
from app.services.ownership import ensure_write_owner
from app.services.authz_guard import (
    ActorContext,
    get_current_actor,
    resolve_actor_identity,
)
from app.services.pipeline.fault_diagnosis_service import FaultDiagnosisService
from app.services.pipeline.task_pipeline_service import TaskPipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class DiagnoseRequest(BaseModel):
    telemetry: dict[str, Any]
    fault_type_hint: Optional[str] = None


class DiagnoseResponse(BaseModel):
    success: bool
    fault_type: Optional[str]
    confidence: float
    affected_joints: list[str]
    reasoning: str
    recommended_sop: Optional[str]
    is_compound: bool
    llm_enhanced: bool = False


class CreateTaskFromDiagnosisRequest(BaseModel):
    diagnosis_trace_id: str
    fault_type: str
    # 归属取自认证上下文；该字段仅为兼容旧客户端保留，
    # 声称与令牌不一致的身份会被 `resolve_actor_identity` 拒绝。
    student_id: int | None = None
    available_tools: list[str] | None = None


class CreateTaskFromDiagnosisResponse(BaseModel):
    task_id: int
    execution_id: int
    sop_id: Optional[int]
    sop_name: str
    fault_type: str


class StepCompleteRequest(BaseModel):
    step_index: int = Field(..., ge=1)
    evidence_type: Optional[str] = None
    evidence_value: Optional[dict] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    is_compliant: bool = True


class StepCompleteResponse(BaseModel):
    step_index: int
    is_compliant: bool
    feedback: Optional[str] = None


class TaskCompleteResponse(BaseModel):
    execution_id: int
    task_id: int
    status: str
    report_generation: str


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose_fault(request: DiagnoseRequest):
    """Analyze telemetry and diagnose fault."""
    service = FaultDiagnosisService()
    result = await service.diagnose(request.telemetry)
    return DiagnoseResponse(**result)


@router.post("/tasks/from-diagnosis", response_model=CreateTaskFromDiagnosisResponse)
async def create_task_from_diagnosis(
    request: CreateTaskFromDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Create maintenance task from diagnosis result."""
    # 审计 M-02 残留：此前无身份注入，`student_id` 取自请求体并直接落为
    # `TaskExecution.student_id`，任意登录用户可为他人创建维保任务。
    # 与同文件 `complete_step` 保持同一归属口径：执行记录归调用者本人。
    student_id = resolve_actor_identity(
        actor,
        request.student_id,
        action="create_task_from_diagnosis",
        resource_type="TaskExecution",
    )
    service = TaskPipelineService(db)
    result = await service.create_task_from_diagnosis(
        diagnosis_trace_id=request.diagnosis_trace_id,
        fault_type=request.fault_type,
        student_id=student_id,
        available_tools=request.available_tools,
    )
    if result.get("error_type") == "PreflightCheckFailed":
        raise HTTPException(
            status_code=400,
            detail={
                "error_type": "PreflightCheckFailed",
                "message": "执行前检查未通过",
                "reason": result["reason"],
            },
        )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CreateTaskFromDiagnosisResponse(**result)


@router.post("/executions/{execution_id}/steps/complete", response_model=StepCompleteResponse)
async def complete_step(
    execution_id: int,
    request: StepCompleteRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Record step completion with evidence."""
    # 审计 M-01：此前无身份、无归属校验，任意登录用户可完成他人执行记录。
    execution = await db.get(TaskExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await ensure_write_owner(
        db, http_request, actor, execution.student_id,
        action="complete_execution_step", resource_type="TaskExecution", resource_id=execution_id,
    )
    service = TaskPipelineService(db)
    result = await service.complete_step(
        execution_id=execution_id,
        step_index=request.step_index,
        evidence_type=request.evidence_type,
        evidence_value=request.evidence_value,
        duration_seconds=request.duration_seconds,
        is_compliant=request.is_compliant,
    )
    return StepCompleteResponse(**result)


@router.post("/executions/{execution_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    execution_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Mark task execution complete, trigger report generation."""
    # 审计 M-01：此前无身份、无归属校验，任意登录用户可完成他人执行记录。
    execution = await db.get(TaskExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await ensure_write_owner(
        db, http_request, actor, execution.student_id,
        action="complete_task_execution", resource_type="TaskExecution", resource_id=execution_id,
    )
    service = TaskPipelineService(db)
    result = await service.complete_task(execution_id=execution_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TaskCompleteResponse(**result)
