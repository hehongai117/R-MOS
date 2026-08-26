"""Read ownership checks shared by user-scoped and task-scoped endpoints."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User
from app.services.access_control import raise_read_access_denied
from app.services.authz_guard import ActorContext


async def ensure_user_scope(
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    target_user_id: int,
    *,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
) -> None:
    """Allow self, administrators, or a same-school teacher to read a user scope."""
    if actor.user_id == target_user_id:
        return
    if "admin" in actor.roles or actor.account_role == "admin":
        return

    if actor.account_role == "teacher" and actor.school_name is not None:
        result = await db.execute(select(User.school_name).where(User.id == target_user_id))
        target_school_name = result.scalar_one_or_none()
        if target_school_name is not None and target_school_name == actor.school_name:
            return

    await raise_read_access_denied(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=target_user_id if resource_id is None else resource_id,
        reason="cross_user_access",
    )


async def ensure_task_scope(
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    task: Task,
    *,
    action: str,
) -> None:
    """Apply user ownership rules to a task; only admins may read ownerless tasks."""
    if "admin" in actor.roles or actor.account_role == "admin":
        return
    if task.user_id is None:
        await raise_read_access_denied(
            db,
            request,
            action=action,
            resource_type="task",
            resource_id=task.id,
            reason="unowned_task",
        )

    await ensure_user_scope(
        db,
        request,
        actor,
        task.user_id,
        action=action,
        resource_type="task",
        resource_id=task.id,
    )
