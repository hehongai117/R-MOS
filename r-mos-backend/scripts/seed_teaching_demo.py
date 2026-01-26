"""
教学演示数据导入脚本
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, delete, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.migration_contract import assert_migration_contract
from app.models import Base
from app.models.sop import SOP, SOPStep
from app.models.task import Task
from app.models.teaching import (
    GuidancePolicy,
    TeachingClass,
    Course,
    Enrollment,
    Assignment,
    AssignmentAttempt,
    EvidenceLink,
)
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEFAULT_CLASS_NAME = "教学演示班级"
DEFAULT_COURSE_NAME = "基础维保课程"
DEFAULT_POLICY_NAME = "默认教学策略"
DEFAULT_SOP_NAME = "教学演示SOP"
DEFAULT_ASSIGNMENT_TITLE = "示例作业"
DEFAULT_ASSIGNMENT_DESC = "教学闭环演示作业"


def parse_student_id(raw: str) -> int:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits:
        return int(digits)
    raise ValueError(f"学生编号无法解析为数字，请检查 --student-id：{raw}")


async def has_table(session: AsyncSession, table_name: str) -> bool:
    def _has(sync_session) -> bool:
        return inspect(sync_session.get_bind()).has_table(table_name)

    return await session.run_sync(_has)


async def reset_teaching_domain(session: AsyncSession) -> None:
    delete_targets = [
        (EvidenceLink, "evidence_links"),
        (AssignmentAttempt, "assignment_attempts"),
        (Assignment, "assignments"),
        (Enrollment, "enrollments"),
        (Course, "courses"),
        (TeachingClass, "classes"),
        (GuidancePolicy, "guidance_policies"),
    ]
    for model, table_name in delete_targets:
        if await has_table(session, table_name):
            await session.execute(delete(model))
    await session.commit()


async def ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_sop(session: AsyncSession) -> SOP:
    result = await session.execute(select(SOP).where(SOP.name == DEFAULT_SOP_NAME))
    sop = result.scalar_one_or_none()
    if sop:
        return sop

    sop = SOP(
        name=DEFAULT_SOP_NAME,
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
    result = await session.execute(select(GuidancePolicy).where(GuidancePolicy.name == DEFAULT_POLICY_NAME))
    policy = result.scalar_one_or_none()
    if policy:
        return policy

    policy = GuidancePolicy(
        name=DEFAULT_POLICY_NAME,
        base_mode="teaching",
        allow_ghost_hand=True,
        allow_hint_button=True,
        show_error_details=True,
        max_retry_count=-1,
        description="教学演示默认策略",
    )
    session.add(policy)
    await session.commit()
    return policy


async def get_or_create_class(session: AsyncSession) -> TeachingClass:
    result = await session.execute(select(TeachingClass).where(TeachingClass.name == DEFAULT_CLASS_NAME))
    teaching_class = result.scalar_one_or_none()
    if teaching_class:
        return teaching_class

    teaching_class = TeachingClass(
        name=DEFAULT_CLASS_NAME,
        term="2026 春季",
        teacher_id=1,
        metadata_json={"source": "教学演示脚本"},
    )
    session.add(teaching_class)
    await session.commit()
    return teaching_class


async def get_or_create_course(session: AsyncSession, *, class_id: int) -> Course:
    result = await session.execute(select(Course).where(Course.class_id == class_id, Course.name == DEFAULT_COURSE_NAME))
    course = result.scalar_one_or_none()
    if course:
        return course

    course = Course(
        class_id=class_id,
        name=DEFAULT_COURSE_NAME,
        description="教学演示课程",
        schedule={"weekday": "周三", "time": "10:00"},
        metadata_json={"level": "基础"},
    )
    session.add(course)
    await session.commit()
    return course


async def get_or_create_enrollment(session: AsyncSession, *, class_id: int, student_id: int) -> Enrollment:
    result = await session.execute(
        select(Enrollment).where(Enrollment.class_id == class_id, Enrollment.student_id == student_id)
    )
    enrollment = result.scalar_one_or_none()
    if enrollment:
        return enrollment

    enrollment = Enrollment(
        class_id=class_id,
        student_id=student_id,
        role="student",
    )
    session.add(enrollment)
    await session.commit()
    return enrollment


async def get_or_create_assignment(
    session: AsyncSession,
    *,
    class_id: int,
    course_id: int | None,
    sop_id: int,
    guidance_policy_id: int,
) -> Assignment:
    result = await session.execute(
        select(Assignment).where(Assignment.class_id == class_id, Assignment.title == DEFAULT_ASSIGNMENT_TITLE)
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        return assignment

    assignment = Assignment(
        class_id=class_id,
        course_id=course_id,
        title=DEFAULT_ASSIGNMENT_TITLE,
        sop_id=sop_id,
        guidance_policy_id=guidance_policy_id,
        max_attempts=3,
        scoring_policy={"description": DEFAULT_ASSIGNMENT_DESC, "sop_ref": sop_id},
        competition_mode=False,
        hidden_sop=False,
    )
    session.add(assignment)
    await session.commit()
    return assignment


async def get_or_create_task(
    session: AsyncSession,
    *,
    sop_id: int,
    assignment_id: int,
    guidance_policy_id: int,
    student_id: int,
) -> Task:
    result = await session.execute(select(Task).where(Task.title == DEFAULT_ASSIGNMENT_TITLE))
    task = result.scalar_one_or_none()
    if task:
        if task.assignment_id != assignment_id:
            task.assignment_id = assignment_id
        if task.guidance_policy_id != guidance_policy_id:
            task.guidance_policy_id = guidance_policy_id
        await session.commit()
        return task

    service = TaskService(session)
    task = await service.create_task(
        TaskCreate(
            title=DEFAULT_ASSIGNMENT_TITLE,
            sop_id=sop_id,
            user_id=student_id,
            pass_score=70,
        )
    )
    task.assignment_id = assignment_id
    task.guidance_policy_id = guidance_policy_id
    await session.commit()
    return task


async def seed_database(args: argparse.Namespace) -> None:
    student_id = parse_student_id(args.student_id)
    bootstrap_enabled = args.bootstrap or os.getenv("ALLOW_BOOTSTRAP") == "1"
    if bootstrap_enabled:
        await ensure_tables()
    async with AsyncSessionLocal() as session:
        if not bootstrap_enabled:
            await assert_migration_contract(session)
        if args.reset:
            await reset_teaching_domain(session)

        sop = await get_or_create_sop(session)
        policy = await get_or_create_policy(session)
        teaching_class = await get_or_create_class(session)
        course = await get_or_create_course(session, class_id=teaching_class.id)
        await get_or_create_enrollment(session, class_id=teaching_class.id, student_id=student_id)
        assignment = await get_or_create_assignment(
            session,
            class_id=teaching_class.id,
            course_id=course.id,
            sop_id=sop.id,
            guidance_policy_id=policy.id,
        )
        task = await get_or_create_task(
            session,
            sop_id=sop.id,
            assignment_id=assignment.id,
            guidance_policy_id=policy.id,
            student_id=student_id,
        )

        print("✅ 教学演示数据已完成")
        print(f"- 班级：{teaching_class.name} ({teaching_class.id})")
        print(f"- 课程：{course.name} ({course.id})")
        print(f"- 作业：{assignment.title} ({assignment.id})")
        print(f"- 任务：{task.title} ({task.id})")
        print(f"- 学生：{args.student_id}（内部编号 {student_id}）")
        print("\n后端健康检查：")
        print("curl http://localhost:8000/api/v1/health")
        print("\n尝试创建示例：")
        print(
            "curl -X POST http://localhost:8000/api/v1/assignments/"
            f"{assignment.id}/attempts -H \"Content-Type: application/json\" "
            f"-d '{{\"studentId\": {student_id}}}'"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="教学演示数据初始化")
    parser.add_argument("--student-id", default="S001", help="学生编号")
    parser.add_argument("--reset", action="store_true", help="清理教学域数据")
    parser.add_argument("--bootstrap", action="store_true", help="仅用于本地临时库的建表兜底")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(seed_database(parse_args()))
