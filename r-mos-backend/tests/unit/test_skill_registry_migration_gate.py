"""
Gate-2 D-001（G2-001）迁移门禁测试。

目标：
- 校验 skills / skill_reviews / skill_releases 三表存在
- 校验 skills(skill_id, version) 唯一约束有效
- 校验 status + risk_level 复合索引存在
"""

from __future__ import annotations

from datetime import datetime
import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("未设置 DATABASE_URL，跳过 G2-001 迁移门禁测试。")
    return database_url


def _insert_skill_sql() -> sa.TextClause:
    return sa.text(
        """
        INSERT INTO skills (
            skill_id, version, name, risk_level, side_effects, allowlist_resources, status, created_at, updated_at
        ) VALUES (
            :skill_id, :version, :name, :risk_level,
            CAST(:side_effects AS JSON), CAST(:allowlist_resources AS JSON), :status, :created_at, :updated_at
        )
        """
    )


def _utc_naive_now() -> datetime:
    return datetime.utcnow()


@pytest.mark.asyncio
async def test_skill_registry_migration_gate() -> None:
    database_url = _require_database_url()
    engine = create_async_engine(database_url, future=True)
    unique_skill_id = f"gate-skill-{uuid4().hex[:12]}"

    try:
        async with engine.begin() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(sa.inspect(sync_conn).get_table_names())
            )
            assert {"skills", "skill_reviews", "skill_releases"}.issubset(table_names), (
                "缺少 G2-001 目标表：skills/skill_reviews/skill_releases。"
            )

            skill_columns = await conn.run_sync(
                lambda sync_conn: {
                    column["name"] for column in sa.inspect(sync_conn).get_columns("skills")
                }
            )
            for required_column in (
                "skill_id",
                "version",
                "risk_level",
                "side_effects",
                "allowlist_resources",
                "status",
            ):
                assert required_column in skill_columns, f"skills 缺少关键字段：{required_column}"

            unique_constraints = await conn.run_sync(
                lambda sync_conn: sa.inspect(sync_conn).get_unique_constraints("skills")
            )
            unique_constraint_names = {
                constraint["name"] for constraint in unique_constraints if constraint.get("name")
            }
            assert "ux_skills_skill_version" in unique_constraint_names, (
                "缺少唯一约束 ux_skills_skill_version(skill_id, version)。"
            )

            indexes = await conn.run_sync(
                lambda sync_conn: sa.inspect(sync_conn).get_indexes("skills")
            )
            index_names = {index["name"] for index in indexes}
            assert "ix_skills_status_risk" in index_names, (
                "缺少复合索引 ix_skills_status_risk(status, risk_level)。"
            )

            await conn.execute(
                sa.text("DELETE FROM skill_releases WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )
            await conn.execute(
                sa.text("DELETE FROM skill_reviews WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )
            await conn.execute(
                sa.text("DELETE FROM skills WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )

            await conn.execute(
                _insert_skill_sql(),
                {
                    "created_at": _utc_naive_now(),
                    "updated_at": _utc_naive_now(),
                    "skill_id": unique_skill_id,
                    "version": "1.0.0",
                    "name": "G2-001 迁移门禁技能",
                    "risk_level": "medium",
                    "side_effects": '["assignment.write"]',
                    "allowlist_resources": '["Assignment:1001"]',
                    "status": "draft",
                },
            )

        with pytest.raises(IntegrityError):
            async with engine.begin() as conn:
                await conn.execute(
                    _insert_skill_sql(),
                    {
                        "created_at": _utc_naive_now(),
                        "updated_at": _utc_naive_now(),
                        "skill_id": unique_skill_id,
                        "version": "1.0.0",
                        "name": "G2-001 重复版本",
                        "risk_level": "medium",
                        "side_effects": '["assignment.write"]',
                        "allowlist_resources": '["Assignment:1001"]',
                        "status": "draft",
                    },
                )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("DELETE FROM skill_releases WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )
            await conn.execute(
                sa.text("DELETE FROM skill_reviews WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )
            await conn.execute(
                sa.text("DELETE FROM skills WHERE skill_id = :skill_id"),
                {"skill_id": unique_skill_id},
            )
        await engine.dispose()
