"""
UF-02-b-3: class membership scope tests.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.teaching import Enrollment, TeachingClass
from app.models.user import User
from app.services.identity.class_membership import ClassMembershipService


@pytest.mark.asyncio
async def test_class_membership_teacher_scope_allow_and_deny(test_db):
    teacher_a = User(
        email=f"teacher_a_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Teacher A",
        role="teacher",
        hint_level=3,
    )
    teacher_b = User(
        email=f"teacher_b_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Teacher B",
        role="teacher",
        hint_level=3,
    )
    student = User(
        email=f"student_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Student",
        role="student",
        hint_level=3,
    )
    test_db.add_all([teacher_a, teacher_b, student])
    await test_db.commit()
    await test_db.refresh(teacher_a)
    await test_db.refresh(teacher_b)
    await test_db.refresh(student)

    cls = TeachingClass(name="Class A", teacher_id=teacher_a.id)
    test_db.add(cls)
    await test_db.commit()
    await test_db.refresh(cls)

    test_db.add(Enrollment(class_id=cls.id, student_id=student.id, role="student"))
    await test_db.commit()

    service = ClassMembershipService(test_db)

    assert await service.teacher_has_student_scope(teacher_id=teacher_a.id, student_id=student.id) is True
    assert await service.teacher_has_student_scope(teacher_id=teacher_b.id, student_id=student.id) is False
