"""
Gate-2 G-001：审计查询索引加固门禁测试。

目标：
- 校验 audit_events 高频查询组合索引存在
- 在小数据集下验证 trace 查询路径可命中索引执行计划
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("未设置 DATABASE_URL，跳过 G-001 审计索引门禁测试。")
    return database_url


@pytest.mark.asyncio
async def test_audit_query_indexes_exist() -> None:
    database_url = _require_database_url()
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.begin() as conn:
            index_names = await conn.run_sync(
                lambda sync_conn: {
                    idx["name"] for idx in sa.inspect(sync_conn).get_indexes("audit_events")
                }
            )
            assert "ix_audit_trace_created" in index_names, "缺少索引 ix_audit_trace_created。"
            assert "ix_audit_action_created" in index_names, "缺少索引 ix_audit_action_created。"
            assert "ix_audit_actor_created" in index_names, "缺少索引 ix_audit_actor_created。"
            assert "ix_audit_resource_created" in index_names, "缺少索引 ix_audit_resource_created。"
            assert "ix_audit_approval_created" in index_names, "缺少索引 ix_audit_approval_created。"
            assert "ix_audit_skill_created" in index_names, "缺少索引 ix_audit_skill_created。"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audit_trace_query_explain_uses_trace_index() -> None:
    database_url = _require_database_url()
    engine = create_async_engine(database_url, future=True)
    trace_id = f"g001-trace-{uuid4().hex[:12]}"

    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO audit_events (
                        actor_user_id,
                        action,
                        resource_type,
                        resource_id,
                        decision,
                        reason,
                        request_meta,
                        trace_id,
                        skill_id,
                        skill_version,
                        tool_call_args,
                        side_effects_applied
                    ) VALUES (
                        :actor_user_id,
                        :action,
                        :resource_type,
                        :resource_id,
                        :decision,
                        :reason,
                        CAST(:request_meta AS JSON),
                        :trace_id,
                        :skill_id,
                        :skill_version,
                        CAST(:tool_call_args AS JSON),
                        CAST(:side_effects_applied AS JSON)
                    )
                    """
                ),
                {
                    "actor_user_id": "2001",
                    "action": "tool_call_pending",
                    "resource_type": "AIToolCall",
                    "resource_id": "901",
                    "decision": "allow",
                    "reason": "g001_index_probe",
                    "request_meta": '{"path":"/api/v1/audit/events","method":"GET"}',
                    "trace_id": trace_id,
                    "skill_id": "skill.g001",
                    "skill_version": "1.0.0",
                    "tool_call_args": '{"query":"trace"}',
                    "side_effects_applied": '[]',
                },
            )

            await conn.execute(sa.text("SET LOCAL enable_seqscan = off"))
            await conn.execute(sa.text("SET LOCAL enable_bitmapscan = off"))
            await conn.execute(sa.text("SET LOCAL enable_sort = off"))
            plan_rows = await conn.execute(
                sa.text(
                    """
                    EXPLAIN (COSTS OFF)
                    SELECT id
                    FROM audit_events
                    WHERE trace_id = :trace_id
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                ),
                {"trace_id": trace_id},
            )
            plan_text = "\n".join(row[0] for row in plan_rows)
            assert "ix_audit_trace_created" in plan_text, (
                "trace 查询计划未命中 ix_audit_trace_created，无法满足 G-001 索引门槛。"
            )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("DELETE FROM audit_events WHERE trace_id = :trace_id"),
                {"trace_id": trace_id},
            )
        await engine.dispose()
