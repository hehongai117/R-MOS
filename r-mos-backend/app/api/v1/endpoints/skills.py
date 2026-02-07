"""
Skill 治理 API（Gate-2 / D-002）。
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError, WriteAccessDeniedError
from app.models.skill_registry import Skill, SkillRelease, SkillReview
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, require_permission


router = APIRouter()

RISK_LEVEL_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
CRITICAL_SIDE_EFFECT_KEYWORDS = (
    "assignments",
    "grades",
    "publishing",
    "bulk_dispatch",
    "faults",
    "delete",
)


class SkillCreateRequest(BaseModel):
    skill_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    risk_level: Literal["low", "medium", "high", "critical"]
    side_effects: list[str] = Field(default_factory=list)
    allowlist_resources: list[str] = Field(default_factory=list)
    description: str | None = None
    feature_flag: str | None = Field(default=None, max_length=128)
    rollback_strategy: dict[str, Any] | None = None


class SkillReviewRequest(BaseModel):
    review_notes: str | None = None


class SkillPublishRequest(BaseModel):
    release_notes: str | None = None


def _contains_critical_side_effects(side_effects: list[str]) -> bool:
    normalized = [item.lower() for item in side_effects]
    return any(
        any(keyword in effect for keyword in CRITICAL_SIDE_EFFECT_KEYWORDS)
        for effect in normalized
    )


def _validate_publish_risk(skill: Skill) -> str | None:
    """D-003 策略：风险规则仅在 publish 阶段强制校验。"""
    side_effects: list[str] = list(skill.side_effects or [])
    risk_level = (skill.risk_level or "").lower()

    if risk_level not in RISK_LEVEL_ORDER:
        return "violates_RISK_unknown_level"

    if side_effects and risk_level == "low":
        return "violates_RISK_001"

    if _contains_critical_side_effects(side_effects):
        current_level = RISK_LEVEL_ORDER.get(risk_level, 0)
        if current_level < RISK_LEVEL_ORDER["high"]:
            return "violates_RISK_002"

    if risk_level == "critical":
        if not skill.feature_flag:
            return "violates_RISK_003_missing_feature_flag"
        if not skill.rollback_strategy:
            return "violates_RISK_003_missing_rollback_strategy"

    return None


@router.post("/ai/skills", status_code=201)
async def create_skill(
    payload: SkillCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("skills:write", required_role="admin")),
):
    skill = Skill(
        skill_id=payload.skill_id,
        version=payload.version,
        name=payload.name,
        created_by_user_id=str(actor.user_id),
        risk_level=payload.risk_level,
        side_effects=payload.side_effects,
        allowlist_resources=payload.allowlist_resources,
        feature_flag=payload.feature_flag,
        rollback_strategy=payload.rollback_strategy,
        status="draft",
        description=payload.description,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    await log_allow_event(
        db,
        request,
        action="skill_created",
        actor_user_id=str(actor.user_id),
        resource_type="Skill",
        resource_id=skill.id,
        reason="create_success",
    )

    return {
        "id": skill.id,
        "skill_id": skill.skill_id,
        "version": skill.version,
        "status": skill.status,
        "risk_level": skill.risk_level,
    }


@router.post("/ai/skills/{id}/submit-review")
async def submit_skill_review(
    id: int,
    payload: SkillReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("skills:write")),
):
    skill_result = await db.execute(select(Skill).where(Skill.id == id))
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        raise ResourceNotFoundError("Skill", id)

    is_admin = "admin" in actor.roles
    is_creator = skill.created_by_user_id == str(actor.user_id)
    if not (is_admin or is_creator):
        reason = "not_creator_or_admin"
        await log_deny_event(
            db,
            request,
            action="permission_denied",
            resource_type="Skill",
            resource_id=id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise PermissionDeniedError(
            action="permission_denied",
            resource_type="Skill",
            resource_id=id,
            reason=reason,
            message="仅技能发布者或管理员可提交审核",
        )

    review = SkillReview(
        skill_id=skill.skill_id,
        version=skill.version,
        reviewer_user_id=str(actor.user_id),
        status="pending",
        review_notes=payload.review_notes,
    )
    skill.status = "in_review"
    db.add(review)
    await db.commit()
    await db.refresh(review)

    await log_allow_event(
        db,
        request,
        action="skill_review_submitted",
        actor_user_id=str(actor.user_id),
        resource_type="Skill",
        resource_id=id,
        reason="submit_review_success",
    )

    return {
        "skill_id": id,
        "review_id": review.id,
        "status": skill.status,
    }


@router.post("/ai/skills/{id}/publish")
async def publish_skill(
    id: int,
    payload: SkillPublishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("skills:publish", required_role="admin")),
):
    skill_result = await db.execute(select(Skill).where(Skill.id == id))
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        raise ResourceNotFoundError("Skill", id)

    risk_error = _validate_publish_risk(skill)
    if risk_error is not None:
        await log_deny_event(
            db,
            request,
            action="skill_publish_denied",
            resource_type="Skill",
            resource_id=id,
            reason=risk_error,
            actor_user_id=str(actor.user_id),
        )
        raise WriteAccessDeniedError(
            action="skill_publish_denied",
            resource_type="Skill",
            resource_id=id,
            reason=risk_error,
            message="技能发布风险校验未通过",
        )

    release = SkillRelease(
        skill_id=skill.skill_id,
        version=skill.version,
        status="published",
        released_by_user_id=str(actor.user_id),
        release_notes=payload.release_notes,
    )
    skill.status = "published"
    db.add(release)
    await db.commit()
    await db.refresh(release)

    await log_allow_event(
        db,
        request,
        action="skill_published",
        actor_user_id=str(actor.user_id),
        resource_type="Skill",
        resource_id=id,
        reason="publish_success",
    )

    return {
        "skill_id": id,
        "release_id": release.id,
        "status": skill.status,
    }
