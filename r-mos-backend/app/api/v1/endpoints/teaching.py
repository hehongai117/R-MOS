"""
Teaching domain API endpoints.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError
from app.schemas.teaching import (
    GuidancePolicyCreate,
    GuidancePolicyResponse,
)
from app.services.teaching_service import TeachingService
from app.api.v1.endpoints.teaching_common import (
    _raise_business_error,
    _raise_not_found,
)
from app.api.v1.endpoints import teaching_roster


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/guidance-policies",
    response_model=List[GuidancePolicyResponse],
    response_model_by_alias=True,
)
async def list_guidance_policies(db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    return await service.list_guidance_policies()


@router.post(
    "/guidance-policies",
    response_model=GuidancePolicyResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_guidance_policy(
    request: GuidancePolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.create_guidance_policy(**request.model_dump())
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)


@router.get(
    "/guidance-policies/{policy_id}",
    response_model=GuidancePolicyResponse,
    response_model_by_alias=True,
)
async def get_guidance_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.get_guidance_policy(policy_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


router.include_router(teaching_roster.router)
