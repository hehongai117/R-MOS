"""
Observation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.observation import ObservationCreate, ObservationResponse, ObservationListResponse
from app.services.observation_service import ObservationService

router = APIRouter()


@router.get("/observations", response_model=ObservationListResponse)
async def list_observations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List observations."""
    service = ObservationService(db)
    return await service.list_observations(page=page, size=size)


@router.post("/observations", response_model=ObservationResponse, status_code=201)
async def create_observation(
    request: ObservationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an observation record."""
    service = ObservationService(db)
    return await service.create_observation(request)


@router.get("/observations/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single observation record."""
    service = ObservationService(db)
    observation = await service.get_observation(observation_id)
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    return observation
