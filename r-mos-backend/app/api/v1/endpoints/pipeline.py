"""Pipeline API — diagnosis-to-task-to-report flow."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
    student_id: int


class CreateTaskFromDiagnosisResponse(BaseModel):
    task_id: int
    execution_id: int
    sop_id: Optional[int]
    sop_name: str
    fault_type: str


class StepCompleteRequest(BaseModel):
    step_index: int
    evidence_type: Optional[str] = None
    evidence_value: Optional[dict] = None
    duration_seconds: Optional[int] = None


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
):
    """Create maintenance task from diagnosis result."""
    service = TaskPipelineService(db)
    result = await service.create_task_from_diagnosis(
        diagnosis_trace_id=request.diagnosis_trace_id,
        fault_type=request.fault_type,
        student_id=request.student_id,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CreateTaskFromDiagnosisResponse(**result)


@router.post("/executions/{execution_id}/steps/complete", response_model=StepCompleteResponse)
async def complete_step(
    execution_id: int,
    request: StepCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record step completion with evidence."""
    service = TaskPipelineService(db)
    result = await service.complete_step(
        execution_id=execution_id,
        step_index=request.step_index,
        evidence_type=request.evidence_type,
        evidence_value=request.evidence_value,
        duration_seconds=request.duration_seconds,
    )
    return StepCompleteResponse(**result)


@router.post("/executions/{execution_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark task execution complete, trigger report generation."""
    service = TaskPipelineService(db)
    result = await service.complete_task(execution_id=execution_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TaskCompleteResponse(**result)
