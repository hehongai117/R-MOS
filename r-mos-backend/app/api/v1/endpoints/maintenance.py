from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_sop_draft import RobotSOPDraft, RobotSOPDraftReviewStatus
from app.schemas.maintenance import (
    DraftRejectRequest,
    MaintenanceDraftCreateRequest,
    MaintenanceDraftResponse,
    MaintenanceDraftUpdateRequest,
)
from app.services.maintenance.sop_draft_generator import SOPDraftGenerator
from app.services.maintenance.verdict_step_generator import VerdictStepGenerator

router = APIRouter()


def _approved_status_tokens() -> tuple[str, str]:
    return (
        RobotSOPDraftReviewStatus.APPROVED.value,
        RobotSOPDraftReviewStatus.APPROVED.name,
    )


def _serialize_draft(record: RobotSOPDraft) -> MaintenanceDraftResponse:
    draft = dict(record.draft_json or {})
    return MaintenanceDraftResponse(
        draft_id=record.id,
        project_id=record.project_id,
        request_id=record.request_id,
        review_status=record.review_status.value if hasattr(record.review_status, "value") else str(record.review_status),
        draft=draft,
        verdict_steps=list(draft.get("verdict_steps", [])),
        viewer_manifest=dict(draft.get("viewer_manifest", {})),
        manifest_tree=dict(draft.get("manifest_tree", {})),
        manifest_mapping=dict(draft.get("manifest_mapping", {})),
        citations=list(record.citations_json or []),
    )


async def _get_project(
    db: AsyncSession,
    *,
    project_id: str | None,
    robot_key: str | None,
) -> RobotProject:
    stmt = select(RobotProject)
    if project_id:
        stmt = stmt.where(RobotProject.id == project_id)
    elif robot_key:
        stmt = stmt.where(RobotProject.robot_key == robot_key)
    else:
        raise HTTPException(status_code=422, detail="project_id or robot_key is required")

    project = (await db.execute(stmt)).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="robot project not found")
    if project.status != RobotProjectStatus.READY:
        raise HTTPException(status_code=409, detail="robot project is not ready")
    return project


async def _get_draft(db: AsyncSession, draft_id: str) -> RobotSOPDraft:
    record = (await db.execute(select(RobotSOPDraft).where(RobotSOPDraft.id == draft_id))).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return record


@router.post("/maintenance/drafts", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def create_maintenance_draft(
    request: MaintenanceDraftCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    project = await _get_project(db, project_id=request.project_id, robot_key=request.robot_key)
    draft_payload = await SOPDraftGenerator().generate(
        db=db,
        project=project,
        maintenance_goal=request.maintenance_goal,
        focus_area=request.focus_area,
    )
    verdict_steps = VerdictStepGenerator().generate(draft_payload["draft"]["steps"])
    draft_json = {
        **draft_payload["draft"],
        "verdict_steps": verdict_steps,
        "viewer_manifest": draft_payload["viewer_manifest"],
        "manifest_tree": draft_payload["manifest_tree"],
        "manifest_mapping": draft_payload["manifest_mapping"],
    }
    record = RobotSOPDraft(
        project_id=project.id,
        request_id=request.request_id or str(uuid4()),
        draft_json=draft_json,
        citations_json=draft_payload["citations"],
        review_status=RobotSOPDraftReviewStatus.DRAFT_PENDING_REVIEW,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _serialize_draft(record)


@router.get("/maintenance/drafts/{draft_id}", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def get_maintenance_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    return _serialize_draft(await _get_draft(db, draft_id))


@router.patch("/maintenance/drafts/{draft_id}", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def update_maintenance_draft(
    draft_id: str,
    request: MaintenanceDraftUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    record = await _get_draft(db, draft_id)
    draft_json = dict(record.draft_json or {})
    for field in ("title", "maintenance_goal", "steps", "tools", "review_notes"):
        value = getattr(request, field)
        if value is not None:
            draft_json[field] = value
    if request.steps is not None:
        draft_json["model_targets"] = sorted(
            {
                target
                for step in request.steps
                for target in step.get("model_targets", [])
            }
        )
    draft_json["verdict_steps"] = VerdictStepGenerator().generate(list(draft_json.get("steps", [])))
    record.draft_json = draft_json
    await db.commit()
    await db.refresh(record)
    return _serialize_draft(record)


@router.post("/maintenance/drafts/{draft_id}/submit-review", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def submit_maintenance_draft_for_review(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    record = await _get_draft(db, draft_id)
    record.review_status = RobotSOPDraftReviewStatus.DRAFT_PENDING_REVIEW
    await db.commit()
    await db.refresh(record)
    return _serialize_draft(record)


@router.post("/maintenance/drafts/{draft_id}/approve", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def approve_maintenance_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    record = await _get_draft(db, draft_id)
    approved_rows = (
        await db.execute(
            select(RobotSOPDraft).where(
                RobotSOPDraft.project_id == record.project_id,
                RobotSOPDraft.id != record.id,
                cast(RobotSOPDraft.review_status, String).in_(_approved_status_tokens()),
            )
        )
    ).scalars().all()
    for row in approved_rows:
        row.review_status = RobotSOPDraftReviewStatus.REJECTED
    record.review_status = RobotSOPDraftReviewStatus.APPROVED
    await db.commit()
    await db.refresh(record)
    return _serialize_draft(record)


@router.post("/maintenance/drafts/{draft_id}/reject", response_model=MaintenanceDraftResponse, tags=["Maintenance"])
async def reject_maintenance_draft(
    draft_id: str,
    request: DraftRejectRequest,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    record = await _get_draft(db, draft_id)
    draft_json = dict(record.draft_json or {})
    review_notes = list(draft_json.get("review_notes", []))
    review_notes.append(f"rejected: {request.reason}")
    draft_json["review_notes"] = review_notes
    record.draft_json = draft_json
    record.review_status = RobotSOPDraftReviewStatus.REJECTED
    await db.commit()
    await db.refresh(record)
    return _serialize_draft(record)


@router.get(
    "/maintenance/projects/{project_id}/executable-draft",
    response_model=MaintenanceDraftResponse,
    tags=["Maintenance"],
)
async def get_executable_draft(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDraftResponse:
    record = (
        await db.execute(
            select(RobotSOPDraft)
            .where(
                RobotSOPDraft.project_id == project_id,
                cast(RobotSOPDraft.review_status, String).in_(_approved_status_tokens()),
            )
            .order_by(RobotSOPDraft.updated_at.desc())
        )
    ).scalars().first()
    if record is None:
        raise HTTPException(status_code=404, detail="no approved draft available")
    return _serialize_draft(record)
