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

    async def teacher_has_student_scope(self, teacher_id: int, student_id: int) -> bool:
        result = await self.db.execute(
            select(Enrollment.id)
            .join(TeachingClass, TeachingClass.id == Enrollment.class_id)
            .where(
                TeachingClass.teacher_id == teacher_id,
                Enrollment.student_id == student_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
