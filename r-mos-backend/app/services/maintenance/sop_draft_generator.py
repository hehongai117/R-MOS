from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject
from app.services.knowledge.hub import KnowledgeHub
from app.services.knowledge.query_embedding_service import query_embedding_service

logger = logging.getLogger(__name__)


class SOPDraftGenerator:
    def __init__(self) -> None:
        self.knowledge_hub = KnowledgeHub()

    async def generate(
        self,
        *,
        db: AsyncSession,
        project: RobotProject,
        maintenance_goal: str,
        focus_area: Optional[str] = None,
    ) -> dict[str, Any]:
        manifest = (
            await db.execute(select(RobotPartManifest).where(RobotPartManifest.project_id == project.id))
        ).scalar_one()
        knowledge_results = await self._retrieve_knowledge(
            db=db,
            project=project,
            maintenance_goal=maintenance_goal,
            focus_area=focus_area,
        )
        if not knowledge_results:
            raise ValueError("knowledge_missing")
        return self.build_draft(
            project=project,
            manifest=manifest,
            knowledge_results=knowledge_results,
            maintenance_goal=maintenance_goal,
            focus_area=focus_area,
        )

    async def _retrieve_knowledge(
        self,
        *,
        db: AsyncSession,
        project: RobotProject,
        maintenance_goal: str,
        focus_area: Optional[str],
    ) -> list[dict[str, Any]]:
        query = " ".join(
            part.strip()
            for part in [project.brand, project.model, maintenance_goal, focus_area or ""]
            if part and part.strip()
        )
        embedding: Optional[list[float]] = None
        try:
            embedding = await query_embedding_service.embed_query(query)
        except Exception as exc:
            logger.warning("[Maintenance] Query embedding generation failed: %s", exc)

        results = await self.knowledge_hub.search(
            db=db,
            query=query,
            embedding=embedding,
            top_k=6,
            filters={"robot_project_id": project.id},
            allow_degraded=True,
        )
        normalized: list[dict[str, Any]] = []
        for item in results:
            if isinstance(item, dict):
                normalized.append(item)
                continue
            normalized.append(
                {
                    "chunk_id": getattr(item, "chunk_id", None) or getattr(item, "id", None),
                    "title": getattr(item, "title", "chunk"),
                    "content": getattr(item, "content", ""),
                    "score": getattr(item, "score", 0),
                    "source": getattr(item, "source", "semantic"),
                    "metadata": getattr(item, "metadata", None),
                }
            )
        return normalized

    def build_draft(
        self,
        *,
        project: RobotProject,
        manifest: RobotPartManifest,
        knowledge_results: list[dict[str, Any]],
        maintenance_goal: str,
        focus_area: Optional[str],
    ) -> dict[str, Any]:
        citations = [
            {
                "chunk_id": item.get("chunk_id") or item.get("title") or f"citation-{idx}",
                "title": item.get("title") or f"citation-{idx}",
                "score": item.get("score", 0),
                "source": item.get("source", "semantic"),
            }
            for idx, item in enumerate(knowledge_results[:5], start=1)
        ]

        manifest_tree = getattr(manifest, "tree_json", None) or {}
        manifest_mapping = getattr(manifest, "mapping_json", None) or {}
        viewer_manifest = getattr(manifest, "viewer_manifest_json", None) or {}
        target_parts = self._pick_target_parts(manifest_mapping, focus_area)
        steps = self._build_steps(knowledge_results, target_parts, maintenance_goal)
        tools = sorted(
            {
                tool
                for step in steps
                for tool in step.get("required_tools", [])
            }
        )
        review_notes = [
            f"part mapping requires review: {node}"
            for node in viewer_manifest.get("needs_review_nodes", []) or []
        ]

        draft = {
            "title": f"{project.brand} {project.model} {maintenance_goal}".strip(),
            "maintenance_goal": maintenance_goal,
            "steps": steps,
            "tools": tools,
            "citations": citations,
            "model_targets": target_parts,
            "review_notes": review_notes,
            "manifest_tree": manifest_tree,
            "manifest_mapping": manifest_mapping,
        }
        return {
            "draft": draft,
            "citations": citations,
            "viewer_manifest": viewer_manifest,
            "manifest_tree": manifest_tree,
            "manifest_mapping": manifest_mapping,
        }

    def _pick_target_parts(
        self,
        mapping: dict[str, dict[str, Any]],
        focus_area: Optional[str],
    ) -> list[str]:
        parts = list(mapping.keys())
        if not parts:
            return []
        if focus_area:
            lowered = focus_area.lower()
            preferred = [part for part in parts if part.lower() in lowered or lowered in part.lower()]
            remainder = [part for part in parts if part not in preferred]
            ordered = preferred + remainder
        else:
            ordered = parts
        return ordered[: max(1, min(3, len(ordered)))]

    def _build_steps(
        self,
        knowledge_results: list[dict[str, Any]],
        target_parts: list[str],
        maintenance_goal: str,
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        selected_results = knowledge_results[: max(1, min(3, len(knowledge_results)))]
        for index, item in enumerate(selected_results, start=1):
            part = target_parts[min(index - 1, len(target_parts) - 1)] if target_parts else None
            tools = ["hex-key"] if "关节" in f"{item.get('title', '')}{maintenance_goal}" else ["inspection-kit"]
            steps.append(
                {
                    "step_id": f"step_{index:03d}",
                    "title": item.get("title") or f"维护步骤 {index}",
                    "description": item.get("content") or maintenance_goal,
                    "required_tools": tools,
                    "model_targets": [part] if part else [],
                    "preconditions": ["robot_power_off"],
                }
            )
        return steps
