"""
验收矩阵标准账号种子脚本。

用途：
- 对齐 docs/specs/ACCEPTANCE_TEST_MATRIX.md 中的标准登录账号
- 补齐 teacher/class/course/enrollment 最小关系，确保登录后会话初始化可用
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.migration_contract import assert_migration_contract
from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.teaching import Course, Enrollment, TeachingClass
from app.models.user import User


engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@dataclass(frozen=True)
class SeedUser:
    key: str
    email: str
    password: str
    full_name: str
    role: str


STANDARD_USERS = (
    SeedUser("admin", "admin@rmos.test", "Admin@123", "Acceptance Admin", "admin"),
    SeedUser("teacher1", "teacher1@rmos.test", "Teacher@123", "Acceptance Teacher One", "teacher"),
    SeedUser("teacher2", "teacher2@rmos.test", "Teacher@123", "Acceptance Teacher Two", "teacher"),
    SeedUser("student_a", "student_a@rmos.test", "Student@123", "Acceptance Student A", "student"),
    SeedUser("student_b", "student_b@rmos.test", "Student@123", "Acceptance Student B", "student"),
)

CLASS_SPECS = (
    {
        "class_name": "Acceptance Class 1",
        "term": "2026 Spring",
        "course_name": "course-1",
        "teacher_key": "teacher1",
        "student_keys": ("student_a", "student_b"),
    },
    {
        "class_name": "Acceptance Class 2",
        "term": "2026 Spring",
        "course_name": "course-2",
        "teacher_key": "teacher2",
        "student_keys": (),
    },
)

ROLE_SPECS = {
    "admin": "系统管理员",
    "teacher": "教师",
    "student": "学生",
    "auditor": "审计员",
}

PERMISSION_SPECS = {
    "agent:read": ("读取智能体知识与项目资产", "agent", "read"),
    "agent:execute": ("执行智能体知识与项目操作", "agent", "execute"),
    "users:read": ("读取用户列表", "users", "read"),
    "users:write": ("管理用户角色", "users", "write"),
    "teaching:read": ("读取教学域基础数据", "teaching", "read"),
    "assignment_attempts:read": ("读取作业尝试", "assignment_attempts", "read"),
    "audit_events:read": ("读取审计事件", "audit_events", "read"),
}

ROLE_PERMISSION_KEYS = {
    "admin": {
        "agent:read",
        "agent:execute",
        "users:read",
        "users:write",
        "teaching:read",
        "assignment_attempts:read",
        "audit_events:read",
    },
    "teacher": {"agent:read", "agent:execute", "teaching:read", "assignment_attempts:read"},
    "student": {"agent:read", "teaching:read", "assignment_attempts:read"},
    "auditor": {"audit_events:read"},
}


async def get_or_create_user(session: AsyncSession, spec: SeedUser) -> User:
    result = await session.execute(select(User).where(User.email == spec.email))
    user = result.scalar_one_or_none()
    password_hash = hash_password(spec.password)
    if user is None:
        user = User(
            email=spec.email,
            password_hash=password_hash,
            full_name=spec.full_name,
            role=spec.role,
            is_active=True,
            is_verified=True,
            hint_level=3,
        )
        session.add(user)
        await session.flush()
        return user

    user.password_hash = password_hash
    user.full_name = spec.full_name
    user.role = spec.role
    user.is_active = True
    user.is_verified = True
    if spec.role != "student":
        user.teacher_id = None
        user.class_id = None
    return user


async def get_or_create_role(session: AsyncSession, *, name: str, description: str) -> Role:
    result = await session.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(name=name, description=description)
        session.add(role)
        await session.flush()
        return role

    role.description = description
    return role


async def get_or_create_permission(
    session: AsyncSession,
    *,
    key: str,
    description: str,
    resource_type: str,
    action: str,
) -> Permission:
    result = await session.execute(select(Permission).where(Permission.key == key))
    permission = result.scalar_one_or_none()
    if permission is None:
        permission = Permission(
            key=key,
            description=description,
            resource_type=resource_type,
            action=action,
        )
        session.add(permission)
        await session.flush()
        return permission

    permission.description = description
    permission.resource_type = resource_type
    permission.action = action
    return permission


async def ensure_role_permission(
    session: AsyncSession,
    *,
    role_id: int,
    permission_id: int,
) -> RolePermission:
    result = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    role_permission = result.scalar_one_or_none()
    if role_permission is None:
        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        session.add(role_permission)
        await session.flush()
    return role_permission


async def sync_user_role(
    session: AsyncSession,
    *,
    user_id: int,
    role_id: int,
) -> None:
    await session.execute(
        delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id != role_id,
        )
    )
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
    )
    user_role = result.scalar_one_or_none()
    if user_role is None:
        session.add(UserRole(user_id=user_id, role_id=role_id))
        await session.flush()


async def get_or_create_class(
    session: AsyncSession,
    *,
    name: str,
    teacher_id: int,
    term: str,
) -> TeachingClass:
    result = await session.execute(select(TeachingClass).where(TeachingClass.name == name))
    teaching_class = result.scalar_one_or_none()
    if teaching_class is None:
        teaching_class = TeachingClass(
            name=name,
            term=term,
            teacher_id=teacher_id,
            metadata_json={"seed": "acceptance_users"},
        )
        session.add(teaching_class)
        await session.flush()
        return teaching_class

    teaching_class.teacher_id = teacher_id
    teaching_class.term = term
    teaching_class.metadata_json = {"seed": "acceptance_users"}
    return teaching_class


async def get_or_create_course(
    session: AsyncSession,
    *,
    class_id: int,
    course_name: str,
) -> Course:
    result = await session.execute(
        select(Course).where(Course.class_id == class_id, Course.name == course_name)
    )
    course = result.scalar_one_or_none()
    if course is None:
        course = Course(
            class_id=class_id,
            name=course_name,
            description=f"Acceptance seeded course {course_name}",
            schedule={"seed": "acceptance_users"},
            metadata_json={"seed": "acceptance_users"},
        )
        session.add(course)
        await session.flush()
        return course

    course.description = f"Acceptance seeded course {course_name}"
    course.schedule = {"seed": "acceptance_users"}
    course.metadata_json = {"seed": "acceptance_users"}
    return course


async def ensure_enrollment(
    session: AsyncSession,
    *,
    class_id: int,
    student_id: int,
) -> Enrollment:
    result = await session.execute(
        select(Enrollment).where(
            Enrollment.class_id == class_id,
            Enrollment.student_id == student_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        enrollment = Enrollment(
            class_id=class_id,
            student_id=student_id,
            role="student",
        )
        session.add(enrollment)
        await session.flush()
        return enrollment

    enrollment.role = "student"
    return enrollment


async def seed_acceptance_users() -> None:
    async with AsyncSessionLocal() as session:
        await assert_migration_contract(session)

        roles: dict[str, Role] = {}
        for role_name, description in ROLE_SPECS.items():
            roles[role_name] = await get_or_create_role(
                session,
                name=role_name,
                description=description,
            )

        permissions: dict[str, Permission] = {}
        for key, spec in PERMISSION_SPECS.items():
            description, resource_type, action = spec
            permissions[key] = await get_or_create_permission(
                session,
                key=key,
                description=description,
                resource_type=resource_type,
                action=action,
            )

        for role_name, permission_keys in ROLE_PERMISSION_KEYS.items():
            for permission_key in permission_keys:
                await ensure_role_permission(
                    session,
                    role_id=roles[role_name].id,
                    permission_id=permissions[permission_key].id,
                )

        users: dict[str, User] = {}
        for spec in STANDARD_USERS:
            user = await get_or_create_user(session, spec)
            users[spec.key] = user
            await sync_user_role(
                session,
                user_id=user.id,
                role_id=roles[spec.role].id,
            )

        await session.flush()

        for spec in CLASS_SPECS:
            teacher = users[spec["teacher_key"]]
            teaching_class = await get_or_create_class(
                session,
                name=spec["class_name"],
                teacher_id=teacher.id,
                term=spec["term"],
            )
            await get_or_create_course(
                session,
                class_id=teaching_class.id,
                course_name=spec["course_name"],
            )
            for student_key in spec["student_keys"]:
                student = users[student_key]
                student.teacher_id = teacher.id
                student.class_id = teaching_class.id
                await ensure_enrollment(
                    session,
                    class_id=teaching_class.id,
                    student_id=student.id,
                )

        await session.commit()

        print("✅ 验收矩阵账号已同步")
        for spec in STANDARD_USERS:
            user = users[spec.key]
            print(f"- {spec.key}: id={user.id} email={user.email} role={user.role}")
        for spec in CLASS_SPECS:
            print(
                f"- class={spec['class_name']} teacher={spec['teacher_key']} "
                f"course={spec['course_name']} students={','.join(spec['student_keys']) or '-'}"
            )


if __name__ == "__main__":
    asyncio.run(seed_acceptance_users())
