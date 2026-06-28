"""
Agent Knowledge Sub-Router
/knowledge/... routes extracted from agent.py (Phase 3 refactor).
Aggregated by agent.py via router.include_router(agent_knowledge.router).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.authz_guard import ActorContext, require_permission
from app.services.knowledge_governance import knowledge_governance
from app.services.knowledge.project_ingest_worker import ProjectIngestWorker
from app.services.knowledge.project_ingest_service import project_ingest_service
from app.schemas.robot_project import (
    RobotProjectListResponse,
    RobotProjectManifestResponse,
    RobotProjectUploadJobResponse,
)
from app.schemas.agent import (
    KnowledgeSearchRequest,
    KnowledgeCreateRequest,
    KnowledgeApproveRequest,
)

router = APIRouter()
knowledge_upload_jobs: dict[str, dict[str, Any]] = {}


async def _run_project_ingest(project_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await ProjectIngestWorker().ingest_project(session, project_id)


def _should_use_request_session_for_ingest(db: AsyncSession) -> bool:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        return False
    database = getattr(bind.engine.url, "database", None)
    return database in (None, "", ":memory:")


# ============ Knowledge Governance Endpoints ============

@router.post("/knowledge/search")
async def search_knowledge(request: KnowledgeSearchRequest, _: None = Depends(require_permission("agent:read"))):
    """Search knowledge entries"""
    from app.services.knowledge_governance import KnowledgeSearchQuery, KnowledgeStatus

    status = KnowledgeStatus.APPROVED if request.status == "APPROVED" else KnowledgeStatus.PENDING

    results = knowledge_governance.search_knowledge(
        KnowledgeSearchQuery(
            query=request.query,
            device_model=request.device_model,
            part_type=request.part_type,
            status=status,
        )
    )

    return {
        "results": [
            {
                "id": m.entry.id,
                "type": m.entry.type.value,
                "status": m.entry.status.value,
                "title": m.entry.title,
                "content": m.entry.content,
                "scope": m.entry.scope.model_dump(),
                "contraindications": m.entry.contraindications.model_dump(),
                "risk_level": m.entry.risk_level.value,
                "confidence": m.entry.confidence.model_dump(),
                "relevance_score": m.relevance_score,
                "match_reasons": m.match_reasons,
            }
            for m in results
        ]
    }


@router.post("/knowledge")
async def create_knowledge(
    request: KnowledgeCreateRequest,
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Create new knowledge entry"""
    from app.services.knowledge_governance import KnowledgeType, RiskLevel, Scope

    entry = knowledge_governance.create_knowledge(
        title=request.title,
        content=request.content,
        entry_type=KnowledgeType(request.type),
        creator_id=str(actor.user_id),
        scope=Scope(**request.scope) if request.scope else None,
        risk_level=RiskLevel(request.risk_level),
    )

    return {
        "id": entry.id,
        "status": entry.status.value,
        "title": entry.title,
    }


@router.post("/knowledge/upload")
async def upload_knowledge_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand: Optional[str] = None,
    model: Optional[str] = None,
    version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:execute")),
):
    """Upload a knowledge file and create an ingest job record."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    job = await project_ingest_service.create_upload_job(
        db,
        filename=file.filename or "upload.bin",
        content=content,
        content_type=file.content_type,
        brand=brand,
        model=model,
        version=version,
    )
    if _should_use_request_session_for_ingest(db):
        background_tasks.add_task(ProjectIngestWorker().ingest_project, db, job.project_id)
    else:
        background_tasks.add_task(_run_project_ingest, job.project_id)
    return job.model_dump()


@router.get("/knowledge/upload/{job_id}")
async def get_knowledge_upload_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:read")),
):
    """Query upload ingest job status."""
    job: RobotProjectUploadJobResponse | dict[str, Any] | None = await project_ingest_service.get_upload_job(
        db,
        job_id=job_id,
    )
    if isinstance(job, RobotProjectUploadJobResponse):
        return job.model_dump()

    if job is None:
        job = knowledge_upload_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Knowledge upload job not found")
    return job


@router.get("/knowledge/projects", response_model=RobotProjectListResponse)
async def list_robot_projects(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:read")),
):
    return await project_ingest_service.list_projects(db)


@router.get("/knowledge/projects/{project_id}/manifest", response_model=RobotProjectManifestResponse)
async def get_robot_project_manifest(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:read")),
):
    manifest = await project_ingest_service.get_project_manifest(db, project_id=project_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="robot project manifest not found")
    return manifest


@router.get("/knowledge/projects/{project_id}/assets/{asset_path:path}")
async def get_robot_project_asset(
    project_id: str,
    asset_path: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:read")),
):
    try:
        content, media_type = await project_ingest_service.get_project_asset(
            db,
            project_id=project_id,
            asset_path=asset_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="robot project asset not found") from exc
    return Response(content=content, media_type=media_type)


@router.post("/knowledge/{entry_id}/submit")
async def submit_knowledge(entry_id: str, _: None = Depends(require_permission("agent:execute"))):
    """Submit knowledge for review"""
    success, message = knowledge_governance.submit_for_review(entry_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "submitted"}


@router.post("/knowledge/{entry_id}/approve")
async def approve_knowledge(
    entry_id: str,
    request: KnowledgeApproveRequest,
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Approve or reject knowledge"""
    from app.services.knowledge_governance import ApprovalRequest

    success, message = knowledge_governance.approve_knowledge(
        ApprovalRequest(
            entry_id=entry_id,
            reviewer_id=str(actor.user_id),
            decision=request.decision,
            feedback=request.feedback,
            rating=request.rating,
        )
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": request.decision}
