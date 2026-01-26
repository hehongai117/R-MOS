from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

REQUIRED_TABLES = [
    "tasks",
    "guidance_policies",
    "classes",
    "courses",
    "enrollments",
    "assignments",
    "assignment_attempts",
    "evidence_links",
]

REQUIRED_TASK_COLUMNS = [
    "assignment_id",
    "guidance_policy_id",
]


def _format_missing(missing_tables: list[str], missing_columns: list[str]) -> str:
    parts: list[str] = []
    if missing_tables:
        parts.append("缺少表: " + ", ".join(missing_tables))
    if missing_columns:
        parts.append("缺少字段: " + ", ".join(missing_columns))
    detail = "；".join(parts)
    return f"检测到迁移未完成，{detail}。请先运行 alembic upgrade head"


async def check_migration_contract(session: AsyncSession) -> tuple[list[str], list[str]]:
    def _inspect(sync_session) -> tuple[list[str], list[str]]:
        inspector = inspect(sync_session.get_bind())
        missing_tables = [table for table in REQUIRED_TABLES if not inspector.has_table(table)]
        missing_columns: list[str] = []
        if inspector.has_table("tasks"):
            columns = {column["name"] for column in inspector.get_columns("tasks")}
            for column_name in REQUIRED_TASK_COLUMNS:
                if column_name not in columns:
                    missing_columns.append(f"tasks.{column_name}")
        else:
            missing_columns.extend([f"tasks.{column_name}" for column_name in REQUIRED_TASK_COLUMNS])
        return missing_tables, missing_columns

    return await session.run_sync(_inspect)


async def assert_migration_contract(session: AsyncSession) -> None:
    missing_tables, missing_columns = await check_migration_contract(session)
    if missing_tables or missing_columns:
        raise RuntimeError(_format_missing(missing_tables, missing_columns))
