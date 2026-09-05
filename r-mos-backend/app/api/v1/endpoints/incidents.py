"""
Incident API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentListResponse
from app.services.authz_guard import ActorContext, actor_has_role, get_current_actor
from app.services.incident_service import IncidentService
from app.services.ownership import ensure_role_for_write, ensure_user_scope

router = APIRouter()


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """List incidents."""
    service = IncidentService(db)
    return await service.list_incidents(
        page=page,
        size=size,
        owner_user_id=actor.user_id,
        school_name=actor.school_name if actor_has_role(actor, "teacher") else None,
        include_all=actor_has_role(actor, "admin"),
    )


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    request: IncidentCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Create an incident record."""
    await ensure_role_for_write(
        db,
        http_request,
        actor,
        "teacher",
        "admin",
        action="create_incident",
        resource_type="Incident",
    )
    service = IncidentService(db)
    return await service.create_incident(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Get a single incident record."""
    incident_row = await db.get(Incident, incident_id)
    if incident_row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    await ensure_user_scope(
        db,
        http_request,
        actor,
        incident_row.created_by_user_id or 0,
        action="read_incident",
        resource_type="Incident",
        resource_id=incident_id,
    )
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
