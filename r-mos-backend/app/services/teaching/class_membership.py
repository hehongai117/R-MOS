"""
UF-02-b-3: teacher/student class membership scope service.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teaching import Enrollment, TeachingClass


class ClassMembershipService:
    """Class membership access checks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def teacher_has_student_scope(
        self,
        teacher_id: int,
        student_id: int,
        class_id: int | None = None,
    ) -> bool:
        """教师是否对该学生有管辖权。

        `class_id` 为 None 时问的是「**任一**自有班级里有这个学生」——
        用于与班级无关的职权（如 `force-submit` 训练会话）。

        传入 `class_id` 时收紧为「**该班级**里有这个学生，且该班归这位教师**」
        （审计 F-AUTH-04）：评分这类操作依附于具体作业，
        「教过这个学生」不等于「有权评这一次尝试」——
        否则教师 A 只要在自己某个班教过学生 X，
        就能给 X 在教师 B 班级里的尝试打分。
        """
        stmt = (
            select(Enrollment.id)
            .join(TeachingClass, TeachingClass.id == Enrollment.class_id)
            .where(
                TeachingClass.teacher_id == teacher_id,
                Enrollment.student_id == student_id,
            )
        )
        if class_id is not None:
            stmt = stmt.where(TeachingClass.id == class_id)
        result = await self.db.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None
