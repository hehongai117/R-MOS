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
from app.services.authz_guard import ActorContext, actor_has_role


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


async def ensure_teacher_scope_over_student(
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    student_id: int,
    *,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
) -> None:
    """教师职权写路径：**有管辖权的教师或管理员；对象所有者本人一律拒绝**。

    与 `ensure_write_owner` 的规则**方向相反**，不可互换（审计 M-01）：

    - `ensure_write_owner` 用于「本人的东西本人改」（暂停自己的训练会话）；
    - 本函数用于「**教师对学生行使职权**」（评分、审批）。此类操作
      **必须排除对象所有者本人**——否则「任意登录用户可给任意作业打分」
      会被"修"成「学生可以给自己打分」，只是把洞换了个位置。

    管辖权判定复用 `ClassMembershipService.teacher_has_student_scope`
    （Enrollment ⋈ TeachingClass），与 `force-submit` 同一口径。
    """
    from app.services.identity.class_membership import ClassMembershipService

    if "admin" in actor.roles or actor.account_role == "admin":
        return

    if actor.user_id == student_id:
        await raise_write_access_denied(
            db,
            request,
            action=action,
            resource_type=resource_type,
            resource_id=student_id if resource_id is None else resource_id,
            reason="owner_cannot_exercise_teacher_authority",
        )

    if actor.account_role == "teacher":
        membership = ClassMembershipService(db)
        if await membership.teacher_has_student_scope(
            teacher_id=actor.user_id, student_id=student_id
        ):
            return

    await raise_write_access_denied(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=student_id if resource_id is None else resource_id,
        reason="teacher_has_no_scope_for_student",
    )


async def ensure_role_for_write(
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    *allowed_roles: str,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
) -> None:
    """角色制写路径守卫：对**无归属字段**的对象按角色授权。

    董事会 2026-09-03 裁定的权限划分：
    **管理员拥有全部权限；教师负责教学内容与学生管理。**

    适用对象：数据库不记录创建者/拥有者、因而无法做对象级归属校验的写操作
    （`sops`、`fault_cases`、`robot_sop_drafts`、`external_assessments`、
    `assessment_providers` 五张表均无归属字段）。

    ⚠️ **这不是归属校验的等价物。** 它只能表达「哪类人可以操作这类对象」，
    不能表达「谁的东西谁能改」。因此：

    - 同角色用户之间**互相不隔离**（任意教师可改任意教学内容）；
    - 职责分离**无法实施**（无作者字段时无从判断「批准者是否即提交者」），
      故审批类动作收紧为仅管理员，使作者与批准者天然分属不同角色。

    归属字段补齐后，相关端点应改回 `ensure_write_owner` /
    `ensure_teacher_scope_over_student`，本函数仅作为过渡。
    """
    if actor_has_role(actor, *allowed_roles):
        return

    await raise_write_access_denied(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=f"role_not_allowed:{actor.account_role or 'unknown'}",
    )
