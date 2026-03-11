from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.knowledge_chunk import AIKnowledgeChunk
from tests.e2e.helpers import parse_sse_events, register_and_login


@pytest.mark.e2e
def test_e2e_robot_project_semantic_flow(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = e2e_env

    async def _seed_chunks() -> None:
        async with session_factory() as session:
            for idx in range(6):
                session.add(
                    AIKnowledgeChunk(
                        id=f"semantic-{idx}",
                        source_type="robot_project",
                        source_id=f"fourier-n1-doc-{idx}",
                        content=f"maintenance semantic document {idx}",
                        embedding=[0.91, 0.08, 0.01],
                        metadata_json={
                            "brand": "semantic-regression",
                            "robot_project_id": "robot-project-001",
                            "part_name": f"joint-{idx}",
                        },
                    )
                )
            await session.commit()

    async def _fake_embed_query(text: str) -> list[float]:
        assert "semantic-regression" in text
        assert "执行器弯曲维护" in text
        return [0.91, 0.08, 0.01]

    async def _fake_chat(**_kwargs):
        return SimpleNamespace(
            content=json.dumps(
                {
                    "project_id": "semantic-flow-001",
                    "title": "执行器维护训练",
                    "description": "基于语义检索知识生成",
                    "steps": [
                        {
                            "step_id": "step_001",
                            "title": "确认执行器总成",
                            "description": "根据知识库定位弯曲维护相关部件",
                            "model_highlight": ["joint-1"],
                            "required_tools": ["hex-key"],
                            "ref_ids": ["semantic-0"],
                            "required_level": 1,
                        }
                    ],
                    "tools_checklist": [
                        {
                            "tool_id": "tool-1",
                            "name": "hex-key",
                            "spec": "4mm",
                            "is_critical": True,
                        }
                    ],
                    "verdict_config": {"mode": "guided", "time_limit": 45, "max_attempts": 2},
                    "robot": {
                        "asset_id": "semantic-regression",
                        "brand": "semantic-regression",
                        "model": "N1",
                    },
                    "estimated_time": 45,
                    "difficulty_cap": 3,
                }
            )
        )

    asyncio.run(_seed_chunks())
    monkeypatch.setattr(
        "app.services.training.project_generator.query_embedding_service.embed_query",
        _fake_embed_query,
    )
    monkeypatch.setattr("app.services.training.project_generator.llm_router.chat", _fake_chat)

    user_id, _email, _login_payload = register_and_login(client, email_prefix="e2e_semantic_flow")

    resp = client.post(
        "/api/v1/training/projects/generate",
        json={
            "user_id": user_id,
            "robot_id": "semantic-regression",
            "difficulty": "medium",
            "focus_areas": ["执行器弯曲维护"],
        },
    )
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    assert events
    assert events[0]["status"] == "retrieving_knowledge"
    assert events[-1]["status"] == "completed"
    assert events[-1]["project_id"] == "semantic-flow-001"
    assert events[-1]["project"]["title"] == "执行器维护训练"
