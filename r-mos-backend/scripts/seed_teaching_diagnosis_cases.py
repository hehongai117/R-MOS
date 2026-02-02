"""
Phase3 Step 1: 诊断规则触发样本生成脚本
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Iterable, List

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base
from app.models.event import Event, EventType
from app.models.snapshot import Snapshot
from app.models.sop import SOP, SOPStep
from app.models.task import Task, TaskStatus
from app.models.teaching import (
    Assignment,
    AssignmentAttempt,
    Course,
    EvidenceLink,
    GuidancePolicy,
    TeachingClass,
)
from app.models.evidence import EvidenceBundle
from app.services.evidence_engine import EvidenceEngine

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

CASE_CLASS_NAME = "诊断规则样本班级"
CASE_COURSE_NAME = "诊断规则样本课程"
CASE_POLICY_NAME = "诊断规则样本策略"
CASE_SOP_NAME = "诊断规则样本SOP"
CASE_ASSIGNMENT_TITLE = "诊断规则样本作业"
CASE_TASK_PREFIX = "诊断规则样本"


async def ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_sop(session: AsyncSession) -> SOP:
    result = await session.execute(select(SOP).where(SOP.name == CASE_SOP_NAME))
    sop = result.scalar_one_or_none()
    if sop:
        return sop

    sop = SOP(
        name=CASE_SOP_NAME,
        description="诊断规则样本 SOP",
        applicable_model="MOCK_HUMANOID_V1",
        category="教学",
        difficulty_level="low",
        estimated_time=300,
    )
    session.add(sop)
    await session.flush()

    steps = [
        SOPStep(
            sop_id=sop.id,
            step_index=1,
            title="步骤 1",
            description="样本步骤 1",
            target_part="torso_link",
            expected_action="inspect",
            is_critical=False,
            timeout_seconds=60,
            allow_skip=True,
            hints=["样本提示"],
            tools_required=["工具"],
        ),
        SOPStep(
            sop_id=sop.id,
            step_index=2,
            title="步骤 2",
            description="样本步骤 2",
            target_part="right_knee",
            expected_action="execute",
            is_critical=False,
            timeout_seconds=60,
            allow_skip=True,
            hints=["样本提示"],
            tools_required=["工具"],
        ),
    ]
    session.add_all(steps)
    await session.commit()
    return sop


async def get_or_create_policy(session: AsyncSession) -> GuidancePolicy:
    result = await session.execute(select(GuidancePolicy).where(GuidancePolicy.name == CASE_POLICY_NAME))
    policy = result.scalar_one_or_none()
    if policy:
        return policy

    policy = GuidancePolicy(
        name=CASE_POLICY_NAME,
        base_mode="teaching",
        allow_ghost_hand=True,
        allow_hint_button=True,
        show_error_details=True,
        max_retry_count=-1,
        description="诊断规则样本策略",
    )
    session.add(policy)
    await session.commit()
    return policy


async def get_or_create_class(session: AsyncSession) -> TeachingClass:
    result = await session.execute(select(TeachingClass).where(TeachingClass.name == CASE_CLASS_NAME))
    teaching_class = result.scalar_one_or_none()
    if teaching_class:
        return teaching_class

    teaching_class = TeachingClass(
        name=CASE_CLASS_NAME,
        term="2026 春季",
        teacher_id=1,
        metadata_json={"source": "diagnosis-case-script"},
    )
    session.add(teaching_class)
    await session.commit()
    return teaching_class


async def get_or_create_course(session: AsyncSession, *, class_id: int) -> Course:
    result = await session.execute(
        select(Course).where(Course.class_id == class_id, Course.name == CASE_COURSE_NAME)
    )
    course = result.scalar_one_or_none()
    if course:
        return course

    course = Course(
        class_id=class_id,
        name=CASE_COURSE_NAME,
        description="诊断规则样本课程",
        schedule={"weekday": "周四", "time": "10:00"},
        metadata_json={"source": "diagnosis-case-script"},
    )
    session.add(course)
    await session.commit()
    return course


async def get_or_create_assignment(
    session: AsyncSession,
    *,
    class_id: int,
    course_id: int | None,
    sop_id: int,
    guidance_policy_id: int,
) -> Assignment:
    result = await session.execute(
        select(Assignment).where(Assignment.class_id == class_id, Assignment.title == CASE_ASSIGNMENT_TITLE)
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        return assignment

    assignment = Assignment(
        class_id=class_id,
        course_id=course_id,
        title=CASE_ASSIGNMENT_TITLE,
        sop_id=sop_id,
        guidance_policy_id=guidance_policy_id,
        max_attempts=3,
        scoring_policy={"mode": "diagnosis-case"},
        competition_mode=False,
        hidden_sop=False,
        blind_step_mask=None,
    )
    session.add(assignment)
    await session.commit()
    return assignment


async def reset_cases(session: AsyncSession) -> None:
    task_rows = await session.execute(select(Task).where(Task.title.like(f"{CASE_TASK_PREFIX}%")))
    tasks = task_rows.scalars().all()
    task_ids = [task.id for task in tasks]

    if not task_ids:
        return

    link_rows = await session.execute(select(EvidenceLink).where(EvidenceLink.task_id.in_(task_ids)))
    links = link_rows.scalars().all()
    bundle_ids = [link.bundle_id for link in links]

    await session.execute(delete(Event).where(Event.task_id.in_(task_ids)))
    await session.execute(delete(Snapshot).where(Snapshot.task_id.in_(task_ids)))
    await session.execute(delete(EvidenceLink).where(EvidenceLink.task_id.in_(task_ids)))
    if bundle_ids:
        await session.execute(delete(EvidenceBundle).where(EvidenceBundle.id.in_(bundle_ids)))

    await session.execute(delete(AssignmentAttempt).where(AssignmentAttempt.task_id.in_(task_ids)))
    await session.execute(delete(Task).where(Task.id.in_(task_ids)))
    await session.commit()


def _case_list(case: str) -> List[str]:
    if case == "all":
        return ["error", "skip", "slow"]
    return [case]


async def create_case(session: AsyncSession, *, case: str, assignment: Assignment, sop: SOP, policy: GuidancePolicy) -> int:
    now = datetime.utcnow()
    if case == "slow":
        started_at = now - timedelta(seconds=10)
        completed_at = now
    else:
        started_at = now - timedelta(seconds=1)
        completed_at = now

    task = Task(
        title=f"{CASE_TASK_PREFIX}-{case}",
        sop_id=sop.id,
        assignment_id=assignment.id,
        guidance_policy_id=policy.id,
        status=TaskStatus.COMPLETED.value,
        current_step_index=2,
        started_at=started_at,
        completed_at=completed_at,
        final_score=100,
        is_passed=True,
    )
    session.add(task)
    await session.flush()

    attempt = AssignmentAttempt(
        assignment_id=assignment.id,
        student_id=1,
        task_id=task.id,
        attempt_index=1,
        status="completed",
    )
    session.add(attempt)
    await session.flush()

    events = []
    error_flag = case == "error"
    events.append(
        Event(
            task_id=task.id,
            event_type=EventType.STEP_EXECUTED.value,
            step_index=1,
            action="execute",
            result="success",
            is_error=error_flag,
            error_message="诊断样本错误" if error_flag else None,
            timestamp=started_at + timedelta(milliseconds=100),
            duration_ms=120,
        )
    )
    if case == "skip":
        events.append(
            Event(
                task_id=task.id,
                event_type=EventType.STEP_SKIPPED.value,
                step_index=1,
                action="skip",
                result="skipped",
                is_error=False,
                timestamp=started_at + timedelta(milliseconds=150),
            )
        )
    events.append(
        Event(
            task_id=task.id,
            event_type=EventType.STEP_EXECUTED.value,
            step_index=2,
            action="execute",
            result="success",
            is_error=False,
            timestamp=started_at + timedelta(milliseconds=300),
            duration_ms=140,
        )
    )

    session.add_all(events)
    await session.commit()

    engine = EvidenceEngine(session)
    await engine.generate_bundle_for_task(task.id, preferred_attempt_id=attempt.id)

    await session.refresh(attempt)
    return attempt.id


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed diagnosis rule cases")
    parser.add_argument("--reset", action="store_true", help="清理已有样本任务")
    parser.add_argument("--case", choices=["error", "skip", "slow", "all"], default="all")
    args = parser.parse_args()

    await ensure_tables()

    async with AsyncSessionLocal() as session:
        if args.reset:
            await reset_cases(session)

        sop = await get_or_create_sop(session)
        policy = await get_or_create_policy(session)
        teaching_class = await get_or_create_class(session)
        course = await get_or_create_course(session, class_id=teaching_class.id)
        assignment = await get_or_create_assignment(
            session,
            class_id=teaching_class.id,
            course_id=course.id,
            sop_id=sop.id,
            guidance_policy_id=policy.id,
        )

        for case in _case_list(args.case):
            attempt_id = await create_case(
                session,
                case=case,
                assignment=assignment,
                sop=sop,
                policy=policy,
            )
            print(f"case={case} attempt_id={attempt_id}")


if __name__ == "__main__":
    asyncio.run(main())
