import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
# Import models to register tables with SQLAlchemy metadata
from app.models import sop, task, event, snapshot, fault, incident, observation, evidence, assessment  # noqa: F401
from app.models.sop import SOP, SOPStep
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


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
