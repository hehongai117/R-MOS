"""
Incident API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentListResponse
from app.services.incident_service import IncidentService

router = APIRouter()


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List incidents."""
    service = IncidentService(db)
    return await service.list_incidents(page=page, size=size)


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    request: IncidentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an incident record."""
    service = IncidentService(db)
    return await service.create_incident(request)


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single incident record."""
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
