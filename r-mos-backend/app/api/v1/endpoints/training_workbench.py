"""
Training workbench sub-router.
Routes and helpers extracted verbatim from training.py (Phase 3 refactor).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from app.core.database import get_db
from app.services.training.session_service import SessionService
from app.services.authz_guard import ActorContext, get_current_actor
from app.schemas.training_workbench import (
    ProjectGenerateRequest,
    ProjectGenerateResponse,
    WorkbenchDraftRequest,
    WorkbenchDraftResponse,
    WorkbenchEvidenceUploadResponse,
    WorkbenchStepSubmitRequest,
    WorkbenchStepSubmitResponse,
    WorkbenchAskRequest,
    WorkbenchAssistantMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_workbench_project_snapshot(payload: dict) -> dict:
    project = payload.get("project") or {}
    steps = payload.get("steps") or []
    return {
        "title": project.get("title", "训练工作台"),
        "summary": project.get("summary", ""),
        "estimated_time": max(len(steps) * 10, 15),
        "steps": [
            {
                "id": step.get("id"),
                "step_index": step.get("step_index", index),
                "title": step.get("title"),
                "instruction": step.get("instruction"),
                "evidence_hint": step.get("evidence_hint"),
                "model_targets": step.get("model_targets", []),
                "tools": step.get("tools", []),
            }
            for index, step in enumerate(steps)
        ],
        "seed_messages": payload.get("messages", []),
        "viewer_manifest": {
            "highlight_mode": "step_targets",
        },
        "verdict_config": {"time_limit": max(len(steps) * 10, 15)},
    }


# ============ UF-04: Training Project Routes ============

@router.post(
    "/training/projects/generate",
    response_model=ProjectGenerateResponse,
    tags=["Training"]
)
async def generate_training_project(
    request: ProjectGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """UF-04-b-2: 生成训练项目

    使用 SSE 流式返回项目配置
    """
    async def sse_stream():
        try:
            from app.services.training.project_generator import ProjectGenerator

            generator = ProjectGenerator(db)

            # 构建 intent 对象
            class IntentPlaceholder:
                category = None
                brand = request.robot_id
                model = None
                difficulty = request.difficulty
                focus_areas = request.focus_areas

            intent = IntentPlaceholder()

            # 流式生成项目
            async for chunk in generator.generate(intent, request.user_id):
                if "error" in chunk:
                    yield f"data: {json.dumps(chunk)}\n\n"
                    break

                if chunk.get("status") == "completed":
                    project = chunk.get("project")
                    if project:
                        yield f"data: {json.dumps({
                            "status": "completed",
                            "project_id": project.project_id,
                            "project": {
                                "project_id": project.project_id,
                                "title": project.title,
                                "description": project.description,
                                "estimated_time": project.estimated_time,
                                "difficulty_cap": project.difficulty_cap,
                            }
                        })}\n\n"
                    break

                yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"[UF-04] Project generation error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


@router.post(
    "/training/workbench/draft",
    response_model=WorkbenchDraftResponse,
    tags=["Training"],
)
async def generate_training_workbench_draft(
    request: WorkbenchDraftRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """为训练工作台空态生成 AI 草案。"""
    try:
        from app.services.training.workbench_draft_generator import TrainingWorkbenchDraftGenerator

        payload = await TrainingWorkbenchDraftGenerator(db).generate(
            user_id=actor.user_id,
            robot_model=request.robot_model,
            robot_id=request.robot_id,
            task_summary=request.task_summary,
            focus_prompt=request.focus_prompt,
        )
        session_service = SessionService(db)
        session_id = await session_service.create_session(
            user_id=actor.user_id,
            project_id=payload["project"]["project_id"],
            project_snapshot=_build_workbench_project_snapshot(payload),
        )
        await session_service.initialize_steps(session_id, payload["steps"])
        payload["project"]["session_id"] = session_id
    except json.JSONDecodeError as exc:
        # JSONDecodeError 是 ValueError 的子类，必须放在 except ValueError 之前，
        # 否则 AI 结果解析失败会被错误归为 400 输入错误，502 分支成为死代码。
        raise HTTPException(status_code=502, detail="AI 返回结果无法解析为训练草案") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"[training-workbench] draft generation failed: {exc}")
        raise HTTPException(status_code=502, detail="训练草案生成失败，请稍后重试") from exc

    return WorkbenchDraftResponse(**payload)


@router.post(
    "/training/workbench/evidence",
    response_model=WorkbenchEvidenceUploadResponse,
    status_code=201,
    tags=["Training"],
)
async def upload_training_workbench_evidence(
    session_id: str = Form(...),
    step_id: str = Form(...),
    note: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    from app.services.training.workbench_execution_service import TrainingWorkbenchExecutionService

    payload = await TrainingWorkbenchExecutionService(db).upload_evidence(
        user_id=actor.user_id,
        session_id=session_id,
        step_id=step_id,
        note=note,
        file=file,
    )
    return WorkbenchEvidenceUploadResponse(**payload)


@router.post(
    "/training/workbench/sessions/{session_id}/steps/{step_id}/submit",
    response_model=WorkbenchStepSubmitResponse,
    tags=["Training"],
)
async def submit_training_workbench_step(
    session_id: str,
    step_id: str,
    request: WorkbenchStepSubmitRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    from app.services.training.workbench_execution_service import TrainingWorkbenchExecutionService

    payload = await TrainingWorkbenchExecutionService(db).submit_step(
        user_id=actor.user_id,
        session_id=session_id,
        step_id=step_id,
        step_index=request.step_index,
        note=request.note,
        evidence_bundle_id=request.evidence_bundle_id,
        tools_confirmed=[tool.model_dump() for tool in request.tools_confirmed],
    )
    return WorkbenchStepSubmitResponse(**payload)


@router.post(
    "/training/workbench/ask",
    response_model=WorkbenchAssistantMessageResponse,
    tags=["Training"],
)
async def ask_training_workbench_assistant(
    request: WorkbenchAskRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    from app.services.training.workbench_execution_service import TrainingWorkbenchExecutionService

    payload = await TrainingWorkbenchExecutionService(db).ask_follow_up(
        user_id=actor.user_id,
        session_id=request.session_id,
        step_id=request.step_id,
        question=request.question,
        messages=request.messages,
    )
    return WorkbenchAssistantMessageResponse(**payload)
