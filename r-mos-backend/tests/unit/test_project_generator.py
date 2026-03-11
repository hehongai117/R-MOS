"""
UF-04: ProjectGenerator tests.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.services.training.project_generator import ProjectGenerator, ProjectStatus


class _Intent:
    def __init__(self):
        self.brand = "ABB"
        self.model = "IRB1200"
        self.category = "工业机器人"
        self.focus_areas = ["执行器弯曲维护"]
        self.intent_type = SimpleNamespace(value="training_new")


@pytest.mark.asyncio
async def test_project_generator_generate_success(monkeypatch, test_db):
    generator = ProjectGenerator(test_db)
    intent = _Intent()

    async def fake_retrieve(_intent):
        return [{"title": f"doc-{i}", "content": "ok"} for i in range(6)]

    async def fake_chat(**_kwargs):
        return SimpleNamespace(
            content=json.dumps(
                {
                    "project_id": "proj-001",
                    "title": "轴承维护训练",
                    "description": "标准流程",
                    "steps": [
                        {
                            "step_id": "step_001",
                            "title": "安全检查",
                            "description": "佩戴防护装备",
                            "model_highlight": ["arm"],
                            "required_tools": ["multimeter"],
                            "ref_ids": ["ref-1"],
                            "required_level": 1,
                        }
                    ],
                    "tools_checklist": [
                        {
                            "tool_id": "tool-1",
                            "name": "multimeter",
                            "spec": "standard",
                            "is_critical": True,
                        }
                    ],
                    "verdict_config": {"mode": "normal", "time_limit": 60, "max_attempts": 3},
                    "robot": {"asset_id": "rb-1", "brand": "ABB", "model": "IRB1200"},
                    "estimated_time": 60,
                    "difficulty_cap": 3,
                }
            )
        )

    monkeypatch.setattr(generator, "_retrieve_knowledge", fake_retrieve)
    monkeypatch.setattr("app.services.training.project_generator.llm_router.chat", fake_chat)

    events = [item async for item in generator.generate(intent=intent, user_id=1)]

    assert [item["status"] for item in events] == [
        ProjectStatus.RETRIEVING_KNOWLEDGE,
        ProjectStatus.ANALYZING_HISTORY,
        ProjectStatus.GENERATING_PROJECT,
        ProjectStatus.COMPLETED,
    ]
    project = events[-1]["project"]
    assert project.project_id == "proj-001"
    assert project.title == "轴承维护训练"
    assert len(project.steps) >= 1


@pytest.mark.asyncio
async def test_project_generator_generate_knowledge_missing(monkeypatch, test_db):
    generator = ProjectGenerator(test_db)
    intent = _Intent()

    async def fake_retrieve(_intent):
        return [{"title": "only-one", "content": "tiny"}]

    monkeypatch.setattr(generator, "_retrieve_knowledge", fake_retrieve)

    events = [item async for item in generator.generate(intent=intent, user_id=1)]

    assert [item["status"] for item in events] == [
        ProjectStatus.RETRIEVING_KNOWLEDGE,
        ProjectStatus.ERROR,
    ]
    assert events[-1]["error"] == "knowledge_missing"


@pytest.mark.asyncio
async def test_project_generator_generate_fallback_when_llm_timeout(monkeypatch, test_db):
    generator = ProjectGenerator(test_db)
    intent = _Intent()

    async def fake_retrieve(_intent):
        return [{"title": f"doc-{i}", "content": "ok"} for i in range(6)]

    async def fake_chat(**_kwargs):
        raise TimeoutError("llm timeout")

    monkeypatch.setattr(generator, "_retrieve_knowledge", fake_retrieve)
    monkeypatch.setattr("app.services.training.project_generator.llm_router.chat", fake_chat)

    events = [item async for item in generator.generate(intent=intent, user_id=1)]
    assert events[-1]["status"] == ProjectStatus.COMPLETED
    project = events[-1]["project"]
    assert project.project_id.startswith("fallback_")
    assert project.title == "标准训练项目"


@pytest.mark.asyncio
async def test_project_generator_retrieve_knowledge_passes_query_embedding(monkeypatch, test_db):
    generator = ProjectGenerator(test_db)
    intent = _Intent()
    captured: dict[str, object] = {}

    async def fake_embed_query(text: str):
        captured["query_text"] = text
        return [0.1, 0.2, 0.3]

    async def fake_search(**kwargs):
        captured["search_kwargs"] = kwargs
        return []

    monkeypatch.setattr(
        "app.services.training.project_generator.query_embedding_service.embed_query",
        fake_embed_query,
    )
    monkeypatch.setattr(generator.knowledge_hub, "search", fake_search)

    await generator._retrieve_knowledge(intent)

    assert "ABB" in str(captured["query_text"])
    assert "执行器弯曲维护" in str(captured["query_text"])
    assert captured["search_kwargs"]["embedding"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_project_generator_retrieve_knowledge_falls_back_when_embedding_fails(monkeypatch, test_db):
    generator = ProjectGenerator(test_db)
    intent = _Intent()
    captured: dict[str, object] = {}

    async def fake_embed_query(_text: str):
        raise RuntimeError("embedding unavailable")

    async def fake_search(**kwargs):
        captured["search_kwargs"] = kwargs
        return []

    monkeypatch.setattr(
        "app.services.training.project_generator.query_embedding_service.embed_query",
        fake_embed_query,
    )
    monkeypatch.setattr(generator.knowledge_hub, "search", fake_search)

    await generator._retrieve_knowledge(intent)

    assert captured["search_kwargs"]["embedding"] is None
