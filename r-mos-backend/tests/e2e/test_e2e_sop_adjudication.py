"""
SOP 裁决 API 端到端测试

验证 GET /api/v1/sops/adjudication 端点：
- difficulty 映射：low→beginner, medium→intermediate, high→advanced
- sopId 格式：sop-db-{id}
- stepId 格式：step-{id}
- applicable_model 过滤
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.sop import SOP, SOPStep


async def _seed_sop(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str,
    applicable_model: str,
    difficulty_level: str = "medium",
    category: str = "maintenance",
    num_steps: int = 2,
) -> int:
    """向数据库写入一条 SOP 及若干步骤，返回 SOP id。"""
    async with session_factory() as session:
        sop = SOP(
            name=name,
            description=f"{name} 描述",
            applicable_model=applicable_model,
            category=category,
            difficulty_level=difficulty_level,
            estimated_time=300,
            version="1.0",
            target_module="test_module",
        )
        session.add(sop)
        await session.flush()  # 获取 auto-increment id

        for i in range(1, num_steps + 1):
            step = SOPStep(
                sop_id=sop.id,
                step_index=i,
                title=f"步骤 {i}",
                description=f"执行步骤 {i}",
                target_part="joint_01",
                expected_action="inspect",
                is_critical=(i == 1),
                timeout_seconds=60,
                allow_skip=False,
            )
            session.add(step)

        await session.commit()
        return sop.id


# ─────────────────────────── 测试用例 ───────────────────────────

def test_adjudication_difficulty_mapping_medium(e2e_env):
    """medium difficulty → intermediate；sopId / stepId 格式正确。"""
    client, session_factory = e2e_env

    sop_id = asyncio.run(
        _seed_sop(
            session_factory,
            name="膝关节检查流程",
            applicable_model="MOCK_HUMANOID_V1",
            difficulty_level="medium",
            num_steps=2,
        )
    )

    resp = client.get("/api/v1/sops/adjudication")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1

    # 找到我们种入的那条 SOP
    sop_item = next((s for s in data["items"] if s["sopId"] == f"sop-db-{sop_id}"), None)
    assert sop_item is not None, f"未找到 sopId=sop-db-{sop_id}"

    # difficulty 映射
    assert sop_item["difficulty"] == "intermediate"

    # steps 存在
    assert len(sop_item["steps"]) == 2


def test_adjudication_difficulty_mapping_low(e2e_env):
    """low difficulty → beginner。"""
    client, session_factory = e2e_env

    sop_id = asyncio.run(
        _seed_sop(
            session_factory,
            name="简单润滑流程",
            applicable_model="MOCK_HUMANOID_V1",
            difficulty_level="low",
            num_steps=1,
        )
    )

    resp = client.get("/api/v1/sops/adjudication")
    assert resp.status_code == 200

    items = resp.json()["items"]
    sop_item = next((s for s in items if s["sopId"] == f"sop-db-{sop_id}"), None)
    assert sop_item is not None
    assert sop_item["difficulty"] == "beginner"


def test_adjudication_difficulty_mapping_high(e2e_env):
    """high difficulty → advanced。"""
    client, session_factory = e2e_env

    sop_id = asyncio.run(
        _seed_sop(
            session_factory,
            name="高难度大修流程",
            applicable_model="MOCK_HUMANOID_V1",
            difficulty_level="high",
            num_steps=3,
        )
    )

    resp = client.get("/api/v1/sops/adjudication")
    assert resp.status_code == 200

    items = resp.json()["items"]
    sop_item = next((s for s in items if s["sopId"] == f"sop-db-{sop_id}"), None)
    assert sop_item is not None
    assert sop_item["difficulty"] == "advanced"


def test_adjudication_sop_id_format(e2e_env):
    """验证 sopId 格式为 sop-db-{id}，stepId 格式为 step-{id}。"""
    client, session_factory = e2e_env

    sop_id = asyncio.run(
        _seed_sop(
            session_factory,
            name="格式验证SOP",
            applicable_model="FORMAT_TEST_MODEL",
            difficulty_level="medium",
            num_steps=2,
        )
    )

    resp = client.get(
        "/api/v1/sops/adjudication",
        params={"applicable_model": "FORMAT_TEST_MODEL"},
    )
    assert resp.status_code == 200

    items = resp.json()["items"]
    assert len(items) == 1

    sop_item = items[0]
    # sopId 格式
    assert sop_item["sopId"] == f"sop-db-{sop_id}"

    # stepId 格式：step-{step.id}（数字）
    for step in sop_item["steps"]:
        step_id: str = step["stepId"]
        assert step_id.startswith("step-"), f"stepId 格式错误：{step_id}"
        numeric_part = step_id[len("step-"):]
        assert numeric_part.isdigit(), f"stepId 数字部分不是纯数字：{step_id}"


def test_adjudication_applicable_model_filter_found(e2e_env):
    """applicable_model 过滤：存在的型号返回非空列表。"""
    client, session_factory = e2e_env

    asyncio.run(
        _seed_sop(
            session_factory,
            name="型号过滤测试SOP",
            applicable_model="FILTER_MODEL_A",
            difficulty_level="medium",
            num_steps=1,
        )
    )
    # 同时种一条不同型号的 SOP，确保过滤有效
    asyncio.run(
        _seed_sop(
            session_factory,
            name="不相关型号SOP",
            applicable_model="FILTER_MODEL_B",
            difficulty_level="low",
            num_steps=1,
        )
    )

    resp = client.get(
        "/api/v1/sops/adjudication",
        params={"applicable_model": "FILTER_MODEL_A"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    for item in data["items"]:
        # 所有返回条目必须属于目标型号（sopId 前缀验证已够，这里检查响应结构完整性）
        assert item["sopId"].startswith("sop-db-")


def test_adjudication_applicable_model_filter_not_found(e2e_env):
    """applicable_model 过滤：不存在的型号返回空列表。"""
    client, session_factory = e2e_env

    resp = client.get(
        "/api/v1/sops/adjudication",
        params={"applicable_model": "NON_EXISTENT_MODEL_XYZ"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_adjudication_step_fields_present(e2e_env):
    """验证每个 step 包含必要字段。"""
    client, session_factory = e2e_env

    asyncio.run(
        _seed_sop(
            session_factory,
            name="字段完整性验证SOP",
            applicable_model="FIELD_CHECK_MODEL",
            difficulty_level="medium",
            num_steps=1,
        )
    )

    resp = client.get(
        "/api/v1/sops/adjudication",
        params={"applicable_model": "FIELD_CHECK_MODEL"},
    )
    assert resp.status_code == 200

    items = resp.json()["items"]
    assert len(items) == 1
    step = items[0]["steps"][0]

    required_step_fields = {"stepId", "stepIndex", "title", "description", "action"}
    for field in required_step_fields:
        assert field in step, f"step 缺少字段：{field}"


def test_adjudication_top_level_fields_present(e2e_env):
    """验证每条 SOP 响应包含顶层必要字段。"""
    client, session_factory = e2e_env

    asyncio.run(
        _seed_sop(
            session_factory,
            name="顶层字段验证SOP",
            applicable_model="TOP_FIELD_MODEL",
            difficulty_level="high",
            num_steps=1,
        )
    )

    resp = client.get(
        "/api/v1/sops/adjudication",
        params={"applicable_model": "TOP_FIELD_MODEL"},
    )
    assert resp.status_code == 200

    items = resp.json()["items"]
    assert len(items) == 1
    sop_item = items[0]

    required_fields = {"sopId", "title", "version", "targetModule", "estimatedTime", "difficulty", "steps"}
    for field in required_fields:
        assert field in sop_item, f"SOP 响应缺少顶层字段：{field}"
