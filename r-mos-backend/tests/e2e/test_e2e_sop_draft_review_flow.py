from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus


async def _seed_robot_project_flow(session_factory: async_sessionmaker[AsyncSession], project_id: str) -> None:
    async with session_factory() as session:
        session.add(
            RobotProject(
                id=project_id,
                robot_key="semantic-regression",
                brand="semantic-regression",
                model="N1",
                version="v1",
                status=RobotProjectStatus.READY,
                source_package_path="/tmp/semantic-regression.zip",
            )
        )
        session.add(
            RobotPartManifest(
                project_id=project_id,
                manifest_version="1.0",
                tree_json={"nodes": [{"id": "elbow"}, {"id": "wrist"}]},
                mapping_json={
                    "elbow": {"source_paths": ["viewer/elbow.glb"]},
                    "wrist": {"source_paths": ["viewer/wrist.glb"]},
                },
                viewer_manifest_json={
                    "robotId": "semantic-regression",
                    "parts": ["viewer/elbow.glb", "viewer/wrist.glb"],
                    "needs_review_nodes": ["wrist"],
                },
            )
        )
        for idx in range(6):
            session.add(
                AIKnowledgeChunk(
                    id=f"draft-flow-{idx}",
                    source_type="robot_project",
                    source_id=f"semantic-doc-{idx}",
                    content=f"semantic maintenance knowledge {idx}",
                    embedding=[0.91, 0.08, 0.01],
                    metadata_json={
                        "robot_project_id": project_id,
                        "brand": "semantic-regression",
                        "part_name": "elbow" if idx < 3 else "wrist",
                    },
                )
            )
        await session.commit()


@pytest.mark.e2e
def test_e2e_sop_draft_review_flow(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = e2e_env
    asyncio.run(_seed_robot_project_flow(session_factory, "sop-flow-project"))

    async def _fake_embed_query(text: str) -> list[float]:
        assert "semantic-regression" in text
        assert "执行器弯曲维护" in text
        return [0.91, 0.08, 0.01]

    monkeypatch.setattr(
        "app.services.maintenance.sop_draft_generator.query_embedding_service.embed_query",
        _fake_embed_query,
    )

    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={
            "project_id": "sop-flow-project",
            "maintenance_goal": "执行器弯曲维护",
            "focus_area": "肘关节",
        },
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()
    assert payload["review_status"] == "draft_pending_review"
    assert payload["viewer_manifest"]["robotId"] == "semantic-regression"
    assert payload["manifest_tree"]["nodes"][0]["id"] == "elbow"
    assert payload["manifest_mapping"]["elbow"]["source_paths"] == ["viewer/elbow.glb"]
    assert payload["draft"]["citations"]
    assert payload["verdict_steps"]

    draft_id = payload["draft_id"]
    edit_resp = client.patch(
        f"/api/v1/maintenance/drafts/{draft_id}",
        json={"review_notes": ["人工确认 wrist 映射"], "title": "执行器维护人工修订版"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["draft"]["title"] == "执行器维护人工修订版"

    approve_resp = client.post(f"/api/v1/maintenance/drafts/{draft_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["review_status"] == "approved"

    executable_resp = client.get("/api/v1/maintenance/projects/sop-flow-project/executable-draft")
    assert executable_resp.status_code == 200
    assert executable_resp.json()["draft_id"] == draft_id
