"""
Observation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.observation import Observation
from app.schemas.observation import ObservationCreate, ObservationResponse, ObservationListResponse
from app.services.authz_guard import ActorContext, actor_has_role, get_current_actor
from app.services.observation_service import ObservationService
from app.services.ownership import ensure_role_for_write, ensure_user_scope

router = APIRouter()


@router.get("/observations", response_model=ObservationListResponse)
async def list_observations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """List observations."""
    service = ObservationService(db)
    return await service.list_observations(
        page=page,
        size=size,
        owner_user_id=actor.user_id,
        school_name=actor.school_name if actor_has_role(actor, "teacher") else None,
        include_all=actor_has_role(actor, "admin"),
    )


@router.post("/observations", response_model=ObservationResponse, status_code=201)
async def create_observation(
    request: ObservationCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Create an observation record."""
    await ensure_role_for_write(
        db,
        http_request,
        actor,
        "teacher",
        "admin",
        action="create_observation",
        resource_type="Observation",
    )
    service = ObservationService(db)
    return await service.create_observation(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )


@router.get("/observations/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Get a single observation record."""
    observation_row = await db.get(Observation, observation_id)
    if observation_row is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    await ensure_user_scope(
        db,
        http_request,
        actor,
        observation_row.created_by_user_id or 0,
        action="read_observation",
        resource_type="Observation",
        resource_id=observation_id,
    )
    service = ObservationService(db)
    observation = await service.get_observation(observation_id)
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    return observation
