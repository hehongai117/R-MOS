"""Ownership checks for user-scoped and task-scoped endpoints.

读路径与写路径的规则**故意不同**，见 `ensure_write_owner` 的文档。
"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User
from app.services.access_control import (
    raise_read_access_denied,
    raise_write_access_denied,
)
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


async def ensure_write_owner(
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    owner_user_id: int | None,
    *,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
) -> None:
    """写路径归属校验：**仅对象所有者本人或管理员**。

    与 `ensure_user_scope` 的关键差异——**同校教师不被放行**（审计 M-01）：

    - 读规则允许同校教师，是为了教师能查看本校学生的档案与进度；
    - 若把该规则平移到写路径，等于**悄悄新增**「教师可修改／放弃任意本校学生对象」
      这一能力。教师的合法介入应走各自的显式端点（如 `force-submit`）并各自校验管辖权，
      而不是从读规则里顺带获得。

    `owner_user_id` 为 None 表示对象无主：**只有管理员可写**，与 `ensure_task_scope`
    对无主任务的处置一致。

    拒绝时走 `raise_write_access_denied`（记审计事件后抛 403），
    与读路径的 404「不泄露存在性」区分开——写操作的目标对象已由调用方确认存在。
    """
    if "admin" in actor.roles or actor.account_role == "admin":
        return
    if owner_user_id is not None and actor.user_id == owner_user_id:
        return

    await raise_write_access_denied(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=owner_user_id if resource_id is None else resource_id,
        reason="not_object_owner" if owner_user_id is not None else "unowned_object",
    )
