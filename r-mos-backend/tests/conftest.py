from datetime import datetime
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
# Import models to register tables with SQLAlchemy metadata
import app.models as app_models  # noqa: F401
from app.models import skill_profile, training, training_submission  # noqa: F401
from app.models.sop import SOP, SOPStep
from app.models.training import TrainingSession
from app.models.user import User
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def test_engine() -> AsyncEngine:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_db(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncSession:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def db_session(test_db: AsyncSession) -> AsyncSession:
    """Backward-compatible alias for legacy tests."""
    yield test_db


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    user = User(
        email=f"student_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Fixture Student",
        role="student",
        hint_level=3,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_session(
    test_db: AsyncSession,
    test_user: User,
) -> TrainingSession:
    training_session = TrainingSession(
        session_id=f"sess-{uuid4()}",
        project_id=f"project-{uuid4()}",
        user_id=test_user.id,
        status="active",
        current_step=0,
        project_snapshot={"estimated_time": 60},
        total_duration=0,
        started_at=datetime.utcnow(),
    )
    test_db.add(training_session)
    await test_db.commit()
    await test_db.refresh(training_session)
    return training_session


async def _create_sop(db_session, *, allow_skip_first_step: bool = False) -> SOP:
    sop_record = SOP(
        name="测试SOP",
        description="用于单元测试",
        applicable_model="MOCK_HUMANOID_V1",
        category="unit-test",
        difficulty_level="low",
        estimated_time=120,
    )
    db_session.add(sop_record)
    await db_session.flush()

    steps = [
        SOPStep(
            sop_id=sop_record.id,
            step_index=1,
            title="步骤一",
            description="第一个步骤",
            target_part="knee_right",
            expected_action="inspect",
            is_critical=True,
            allow_skip=allow_skip_first_step,
            timeout_seconds=60,
        ),
        SOPStep(
            sop_id=sop_record.id,
            step_index=2,
            title="步骤二",
            description="第二个步骤",
            target_part="knee_right",
            expected_action="execute",
            is_critical=False,
            allow_skip=False,
            timeout_seconds=60,
        ),
    ]
    db_session.add_all(steps)
    await db_session.commit()
    return sop_record


@pytest_asyncio.fixture
async def sample_sop(db_session):
    return await _create_sop(db_session, allow_skip_first_step=False)


@pytest_asyncio.fixture
async def sample_task(db_session, sample_sop):
    service = TaskService(db_session)
    task = await service.create_task(
        TaskCreate(
            title="测试任务",
            sop_id=sample_sop.id,
            user_id=1,
            pass_score=70,
        )
    )
    return task


@pytest_asyncio.fixture
async def sample_task_with_skippable_step(db_session):
    sop_record = await _create_sop(db_session, allow_skip_first_step=True)
    service = TaskService(db_session)
    task = await service.create_task(
        TaskCreate(
            title="可跳过步骤任务",
            sop_id=sop_record.id,
            user_id=1,
            pass_score=70,
        )
    )
    return task
