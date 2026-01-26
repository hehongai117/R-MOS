"""
教学演示数据导入脚本
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.sop import SOP, SOPStep
from app.models.task import Task
from app.models.teaching import GuidancePolicy, TeachingClass, Course, Assignment, AssignmentAttempt
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEMO_SOP_NAME = "教学演示SOP"
DEMO_POLICY_NAME = "Level 1 练习"
DEMO_CLASS_NAME = "教学演示班级"
DEMO_COURSE_NAME = "基础维保课程"
DEMO_ASSIGNMENT_TITLE = "示例作业"
DEMO_TASK_TITLE = "示例作业-教学任务"
DEMO_STUDENT_ID = 1001


async def get_or_create_sop(session: AsyncSession) -> SOP:
    result = await session.execute(select(SOP).where(SOP.name == DEMO_SOP_NAME))
    sop = result.scalar_one_or_none()
    if sop:
        return sop

    sop = SOP(
        name=DEMO_SOP_NAME,
        description="教学闭环演示用 SOP",
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
            title="定位目标部件",
            description="请确认目标部件位置",
            target_part="torso_link",
            expected_action="inspect",
            is_critical=True,
            timeout_seconds=60,
            allow_skip=False,
            hints=["点击模型高亮部件"],
            tools_required=["手电筒"],
        ),
        SOPStep(
            sop_id=sop.id,
            step_index=2,
            title="执行检查动作",
            description="完成基础检查动作",
            target_part="right_knee",
            expected_action="execute",
            is_critical=False,
            timeout_seconds=60,
            allow_skip=False,
            hints=["确认动作完成"],
            tools_required=["扳手"],
        ),
    ]
    session.add_all(steps)
    await session.commit()
    return sop


async def get_or_create_policy(session: AsyncSession) -> GuidancePolicy:
    result = await session.execute(select(GuidancePolicy).where(GuidancePolicy.name == DEMO_POLICY_NAME))
    policy = result.scalar_one_or_none()
    if policy:
        return policy

    policy = GuidancePolicy(
        name=DEMO_POLICY_NAME,
        base_mode="teaching",
        allow_ghost_hand=True,
        allow_hint_button=True,
        show_error_details=True,
        max_retry_count=-1,
        description="教学演示策略",
    )
    session.add(policy)
    await session.commit()
    return policy


async def get_or_create_class(session: AsyncSession) -> TeachingClass:
    result = await session.execute(select(TeachingClass).where(TeachingClass.name == DEMO_CLASS_NAME))
    teaching_class = result.scalar_one_or_none()
    if teaching_class:
        return teaching_class

    teaching_class = TeachingClass(
        name=DEMO_CLASS_NAME,
        term="2026 春季",
        teacher_id=1,
        metadata_json={"source": "seed_teaching_demo"},
    )
    session.add(teaching_class)
    await session.commit()
    return teaching_class


async def get_or_create_course(session: AsyncSession, class_id: int) -> Course:
    result = await session.execute(
        select(Course).where(Course.class_id == class_id, Course.name == DEMO_COURSE_NAME)
    )
    course = result.scalar_one_or_none()
    if course:
        return course

    course = Course(
        class_id=class_id,
        name=DEMO_COURSE_NAME,
        description="教学演示课程",
        schedule={"weekday": "周三", "time": "10:00"},
        metadata_json={"level": "基础"},
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
        select(Assignment).where(Assignment.class_id == class_id, Assignment.title == DEMO_ASSIGNMENT_TITLE)
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        return assignment

    assignment = Assignment(
        class_id=class_id,
        course_id=course_id,
        title=DEMO_ASSIGNMENT_TITLE,
        sop_id=sop_id,
        guidance_policy_id=guidance_policy_id,
        max_attempts=3,
        scoring_policy={"mode": "basic"},
        competition_mode=False,
        hidden_sop=False,
    )
    session.add(assignment)
    await session.commit()
    return assignment


async def get_or_create_task(session: AsyncSession, sop_id: int, assignment_id: int) -> Task:
    result = await session.execute(select(Task).where(Task.title == DEMO_TASK_TITLE))
    task = result.scalar_one_or_none()
    if task:
        if task.assignment_id != assignment_id:
            task.assignment_id = assignment_id
            await session.commit()
        return task

    service = TaskService(session)
    task = await service.create_task(
        TaskCreate(
            title=DEMO_TASK_TITLE,
            sop_id=sop_id,
            user_id=DEMO_STUDENT_ID,
            pass_score=70,
        )
    )
    task.assignment_id = assignment_id
    await session.commit()
    return task


async def get_or_create_attempt(
    session: AsyncSession,
    *,
    assignment_id: int,
    student_id: int,
    task_id: int,
) -> AssignmentAttempt:
    result = await session.execute(
        select(AssignmentAttempt).where(
            AssignmentAttempt.assignment_id == assignment_id,
            AssignmentAttempt.student_id == student_id,
            AssignmentAttempt.task_id == task_id,
        )
    )
    attempt = result.scalar_one_or_none()
    if attempt:
        return attempt

    attempt = AssignmentAttempt(
        assignment_id=assignment_id,
        student_id=student_id,
        task_id=task_id,
        attempt_index=1,
        status="in_progress",
    )
    session.add(attempt)
    await session.commit()
    return attempt


async def seed_database():
    async with AsyncSessionLocal() as session:
        sop = await get_or_create_sop(session)
        policy = await get_or_create_policy(session)
        teaching_class = await get_or_create_class(session)
        course = await get_or_create_course(session, teaching_class.id)
        assignment = await get_or_create_assignment(
            session,
            class_id=teaching_class.id,
            course_id=course.id,
            sop_id=sop.id,
            guidance_policy_id=policy.id,
        )
        task = await get_or_create_task(session, sop.id, assignment.id)
        await get_or_create_attempt(
            session,
            assignment_id=assignment.id,
            student_id=DEMO_STUDENT_ID,
            task_id=task.id,
        )

        print("✅ 教学演示数据已完成")
        print(f"- 班级：{teaching_class.name} ({teaching_class.id})")
        print(f"- 作业：{assignment.title} ({assignment.id})")
        print(f"- 任务：{task.title} ({task.id})")


if __name__ == "__main__":
    asyncio.run(seed_database())
