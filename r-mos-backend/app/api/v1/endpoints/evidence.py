"""
Evidence API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.evidence import EvidenceBundleCreate, EvidenceBundleResponse, EvidenceBundleListResponse
from app.services.evidence_service import EvidenceService

router = APIRouter()


@router.get("/evidence-bundles", response_model=EvidenceBundleListResponse)
async def list_evidence_bundles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List evidence bundles."""
    service = EvidenceService(db)
    return await service.list_bundles(page=page, size=size)


@router.post("/evidence-bundles", response_model=EvidenceBundleResponse, status_code=201)
async def create_evidence_bundle(
    request: EvidenceBundleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an evidence bundle."""
    service = EvidenceService(db)
    return await service.create_bundle(request)


@router.get("/evidence-bundles/{bundle_id}", response_model=EvidenceBundleResponse)
async def get_evidence_bundle(
    bundle_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single evidence bundle."""
    service = EvidenceService(db)
    bundle = await service.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    return bundle
