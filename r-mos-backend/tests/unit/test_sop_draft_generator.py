from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.maintenance.sop_draft_generator import SOPDraftGenerator


@pytest.mark.asyncio
async def test_sop_draft_generator_returns_citations_and_review_notes() -> None:
    generator = SOPDraftGenerator()
    project = SimpleNamespace(id="project-1", robot_key="fourier-n1", brand="Fourier", model="N1")
    manifest = SimpleNamespace(
        mapping_json={
            "elbow": {"source_paths": ["cad/elbow.SLDPRT", "viewer/elbow.glb"]},
            "wrist": {"source_paths": ["viewer/wrist.glb"]},
        },
        viewer_manifest_json={
            "robotId": "fourier-n1",
            "parts": ["viewer/elbow.glb", "viewer/wrist.glb"],
            "needs_review_nodes": ["wrist"],
        },
    )
    knowledge_results = [
        {
            "chunk_id": "chunk-1",
            "title": "肘关节维护说明",
            "content": "执行器弯曲维护要求先断电并检查肘关节总成。",
            "score": 0.92,
            "source": "semantic",
        },
        {
            "chunk_id": "chunk-2",
            "title": "腕关节复核",
            "content": "复核腕关节连接和紧固状态。",
            "score": 0.88,
            "source": "semantic",
        },
    ]

    payload = generator.build_draft(
        project=project,
        manifest=manifest,
        knowledge_results=knowledge_results,
        maintenance_goal="执行器弯曲维护",
        focus_area="肘关节",
    )

    draft = payload["draft"]
    assert draft["maintenance_goal"] == "执行器弯曲维护"
    assert draft["citations"][0]["chunk_id"] == "chunk-1"
    assert "wrist" in draft["review_notes"][0]
    assert draft["steps"][0]["model_targets"] == ["elbow"]
    assert payload["viewer_manifest"]["robotId"] == "fourier-n1"
