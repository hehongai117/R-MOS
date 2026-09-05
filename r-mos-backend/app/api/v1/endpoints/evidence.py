"""
Evidence API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.evidence import EvidenceBundle
from app.schemas.evidence import EvidenceBundleCreate, EvidenceBundleResponse, EvidenceBundleListResponse
from app.services.authz_guard import ActorContext, actor_has_role, get_current_actor
from app.services.evidence_service import EvidenceService
from app.services.ownership import ensure_role_for_write, ensure_user_scope

router = APIRouter()


@router.get("/evidence-bundles", response_model=EvidenceBundleListResponse)
async def list_evidence_bundles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """List evidence bundles."""
    service = EvidenceService(db)
    return await service.list_bundles(
        page=page,
        size=size,
        owner_user_id=actor.user_id,
        school_name=actor.school_name if actor_has_role(actor, "teacher") else None,
        include_all=actor_has_role(actor, "admin"),
    )


@router.post("/evidence-bundles", response_model=EvidenceBundleResponse, status_code=201)
async def create_evidence_bundle(
    request: EvidenceBundleCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Create an evidence bundle."""
    await ensure_role_for_write(
        db,
        http_request,
        actor,
        "teacher",
        "admin",
        action="create_evidence_bundle",
        resource_type="EvidenceBundle",
    )
    service = EvidenceService(db)
    return await service.create_bundle(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )


@router.get("/evidence-bundles/{bundle_id}", response_model=EvidenceBundleResponse)
async def get_evidence_bundle(
    bundle_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Get a single evidence bundle."""
    bundle_row = await db.get(EvidenceBundle, bundle_id)
    if bundle_row is None:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    await ensure_user_scope(
        db,
        http_request,
        actor,
        bundle_row.created_by_user_id or 0,
        action="read_evidence_bundle",
        resource_type="EvidenceBundle",
        resource_id=bundle_id,
    )
    service = EvidenceService(db)
    bundle = await service.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    return bundle
