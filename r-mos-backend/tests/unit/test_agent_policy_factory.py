"""
UF-02-b: AgentPolicyFactory tests.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.user import User
from app.services.identity.agent_policy_factory import AgentPolicyFactory


@pytest.mark.asyncio
async def test_agent_policy_factory_student_mapping(test_db):
    student = User(
        email=f"student_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Student",
        role="student",
        hint_level=4,
    )
    test_db.add(student)
    await test_db.commit()
    await test_db.refresh(student)

    config = await AgentPolicyFactory.build(
        db=test_db,
        user_id=student.id,
        memory={"skill_level": 3},
    )

    assert config.guidance_mode is True
    assert config.hint_level == 4
    assert config.difficulty_cap == 4
    assert config.show_answers is False


@pytest.mark.asyncio
async def test_agent_policy_factory_teacher_and_admin(test_db):
    teacher = User(
        email=f"teacher_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Teacher",
        role="teacher",
        hint_level=3,
    )
    admin = User(
        email=f"admin_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Admin",
        role="admin",
        hint_level=3,
    )
    test_db.add_all([teacher, admin])
    await test_db.commit()
    await test_db.refresh(teacher)
    await test_db.refresh(admin)

    teacher_cfg = await AgentPolicyFactory.build(db=test_db, user_id=teacher.id)
    admin_cfg = await AgentPolicyFactory.build(db=test_db, user_id=admin.id)

    assert teacher_cfg.observe_mode is True
    assert teacher_cfg.can_override_verdict is True
    assert teacher_cfg.show_full_analysis is True

    assert admin_cfg.management_mode is True
    assert admin_cfg.audit_access is True


def test_agent_policy_factory_hint_level_prompt_mapping():
    assert AgentPolicyFactory.get_hint_level_prompt(1).startswith("只确认")
    assert AgentPolicyFactory.get_hint_level_prompt(5).startswith("提供逐步骤")
    assert "引导学生思考" in AgentPolicyFactory.get_hint_level_prompt(99)
