"""
UF-02-a: SessionInitializer tests.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.models.teaching import TeachingClass
from app.models.training import TrainingSession
from app.models.user import User
from app.services.identity.session_initializer import SessionInitializer


class _FakeMemoryHub:
    async def get_student_profile(self, _user_id: int):
        return {
            "last_training": "轴承检查",
            "weak_steps": ["step_002", "step_005"],
            "skill_level": 2,
        }


@pytest.mark.asyncio
async def test_session_initializer_student_path_with_unfinished_session(test_db, test_user):
    unfinished = TrainingSession(
        session_id=f"sess-{uuid4()}",
        project_id=f"project-{uuid4()}",
        user_id=test_user.id,
        status="active",
        current_step=2,
        project_snapshot={"title": "训练项目A", "steps": [1, 2, 3]},
        total_duration=120,
        started_at=datetime.utcnow(),
    )
    test_db.add(unfinished)
    await test_db.commit()

    initializer = SessionInitializer(test_db)
    initializer.memory_hub = _FakeMemoryHub()

    context = await initializer.initialize_session(test_user.id)
    assert context.role == "student"
    assert context.agent_config["guidance_mode"] is True
    assert context.agent_config["hint_level"] == 3
    assert "薄弱环节" in context.welcome_summary
    assert context.unfinished_session is not None
    assert context.unfinished_session["session_id"] == unfinished.session_id


@pytest.mark.asyncio
async def test_session_initializer_teacher_path(test_db):
    teacher = User(
        email=f"teacher_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Teacher",
        role="teacher",
        hint_level=3,
    )
    test_db.add(teacher)
    await test_db.commit()
    await test_db.refresh(teacher)

    cls = TeachingClass(name="Class A", teacher_id=teacher.id)
    test_db.add(cls)
    await test_db.commit()

    initializer = SessionInitializer(test_db)
    context = await initializer.initialize_session(teacher.id)

    assert context.role == "teacher"
    assert context.agent_config["observe_mode"] is True
    assert context.agent_config["can_override_verdict"] is True
    assert "您负责" in context.welcome_summary


@pytest.mark.asyncio
async def test_session_initializer_admin_path(test_db):
    admin = User(
        email=f"admin_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Admin",
        role="admin",
        hint_level=3,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)

    initializer = SessionInitializer(test_db)
    context = await initializer.initialize_session(admin.id)

    assert context.role == "admin"
    assert context.agent_config["management_mode"] is True
    assert context.agent_config["audit_access"] is True
    assert "active_sessions" in context.stats
