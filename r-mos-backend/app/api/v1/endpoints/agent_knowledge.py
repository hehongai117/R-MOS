"""
Agent Knowledge Sub-Router
/knowledge/... routes extracted from agent.py (Phase 3 refactor).
Aggregated by agent.py via router.include_router(agent_knowledge.router).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pathlib import PurePosixPath
import re
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.authz_guard import ActorContext, actor_has_role, require_permission
from app.services.knowledge_governance import knowledge_governance
from app.services.knowledge.project_ingest_worker import ProjectIngestWorker
from app.services.knowledge.project_ingest_service import project_ingest_service
from app.services.knowledge.file_classifier import FileClassification, classify_file
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

# This endpoint buffers one file in memory before ingest. 10 MiB bounds request
# memory while keeping ordinary manuals and small robot assets usable.
MAX_KNOWLEDGE_UPLOAD_BYTES = 10 * 1024 * 1024
_SAFE_UPLOAD_BASENAME = re.compile(r"^[\w.-]+$")


async def _run_project_ingest(project_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await ProjectIngestWorker().ingest_project(session, project_id)


def _should_use_request_session_for_ingest(db: AsyncSession) -> bool:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        return False
    database = getattr(bind.engine.url, "database", None)
    return database in (None, "", ":memory:")



async def _same_school_user_ids(db: AsyncSession, actor: ActorContext) -> Optional[set[str]]:
    """返回与调用者同校的用户编号集合；`None` 表示不限制（管理员）。

    审计 C-AUTH-01／03／04：知识与机器人项目此前**不按学校过滤**，
    他校用户可读、可提交他人草稿。口径与模块 F 一致
    （见 `ownership.py` 的 `ensure_user_scope` 文档）：
    **同校可读是既定设计，跨校不是**——学校是租户边界。

    知识条目由内存服务持有、不带学校字段，因此过滤只能在端点层做：
    条目的 `created_by` → `User.school_name`。内存服务不该知道租户模型。
    """
    from app.models.user import User

    if actor_has_role(actor, "admin"):
        return None
    if not actor.school_name:
        return {str(actor.user_id)}
    rows = await db.execute(select(User.id).where(User.school_name == actor.school_name))
    return {str(uid) for uid in rows.scalars()}



async def _assert_project_visible(db: AsyncSession, actor: ActorContext, project_id: str) -> None:
    """机器人项目的跨校可见性校验（审计 C-AUTH-03）。

    单个资源用**端点层校验**、列表用 service 层过滤——两者形态不同：
    列表要静默排除，单个要明确拒绝。

    越权一律 404 而非 403：这是**读**路径，403 会泄露「该项目存在」
    （口径见 `services/robot/visibility.py` 与 `ownership.py`）。
    """
    from app.models.robot_project import RobotProject

    if actor_has_role(actor, "admin"):
        return
    project = (
        await db.execute(select(RobotProject).where(RobotProject.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        return  # 不存在由各端点自身的 404 处理，此处不抢先报错
    if project.school_name != actor.school_name:
        raise HTTPException(status_code=404, detail="robot project not found")


# ============ Knowledge Governance Endpoints ============

@router.post("/knowledge/search")
async def search_knowledge(
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("agent:read")),
):
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

    visible = await _same_school_user_ids(db, actor)
    if visible is not None:
        results = [m for m in results if not m.entry.created_by or m.entry.created_by in visible]

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
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Upload a knowledge file and create an ingest job record."""
    raw_filename = file.filename or "upload.bin"
    filename = PurePosixPath(raw_filename.replace("\\", "/")).name
    if filename in {"", ".", ".."} or _SAFE_UPLOAD_BASENAME.fullmatch(filename) is None:
        raise HTTPException(status_code=400, detail="Invalid knowledge filename")
    if classify_file(filename).kind is FileClassification.DEFERRED:
        raise HTTPException(status_code=415, detail="Unsupported knowledge file type")

    content = await file.read(MAX_KNOWLEDGE_UPLOAD_BYTES + 1)
    if len(content) > MAX_KNOWLEDGE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Knowledge file exceeds 10 MiB limit")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    job = await project_ingest_service.create_upload_job(
        db,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
        filename=filename,
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
    actor: ActorContext = Depends(require_permission("agent:read")),
):
    """Query upload ingest job status."""
    await _assert_project_visible(db, actor, job_id)
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
    actor: ActorContext = Depends(require_permission("agent:read")),
):
    # 审计 C-AUTH-03：列表静默排除他校项目（单资源端点则明确 404，见 _assert_project_visible）
    if actor_has_role(actor, "admin"):
        return await project_ingest_service.list_projects(db)
    return await project_ingest_service.list_projects(db, school_name=actor.school_name)


@router.get("/knowledge/projects/{project_id}/manifest", response_model=RobotProjectManifestResponse)
async def get_robot_project_manifest(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("agent:read")),
):
    await _assert_project_visible(db, actor, project_id)
    manifest = await project_ingest_service.get_project_manifest(db, project_id=project_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="robot project manifest not found")
    return manifest


@router.get("/knowledge/projects/{project_id}/assets/{asset_path:path}")
async def get_robot_project_asset(
    project_id: str,
    asset_path: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("agent:read")),
):
    await _assert_project_visible(db, actor, project_id)
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
async def submit_knowledge(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Submit knowledge for review"""
    # 审计 C-AUTH-04：此前无任何归属校验，他校用户可提交他人草稿送审。
    entry = knowledge_governance.get_knowledge(entry_id)
    if entry is not None:
        visible = await _same_school_user_ids(db, actor)
        if visible is not None and entry.created_by and entry.created_by not in visible:
            # 写路径用 403，不用 404——口径见 `ownership.py`：
            # 读路径 404 是为了不泄露存在性；写操作的目标对象已由调用方确认存在。
            raise HTTPException(status_code=403, detail="cross-school knowledge submit denied")
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
