from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MaintenanceDraftCreateRequest(BaseModel):
    project_id: Optional[str] = None
    robot_key: Optional[str] = None
    maintenance_goal: str
    focus_area: Optional[str] = None
    request_id: Optional[str] = None


class MaintenanceDraftUpdateRequest(BaseModel):
    title: Optional[str] = None
    maintenance_goal: Optional[str] = None
    steps: Optional[list[dict[str, Any]]] = None
    tools: Optional[list[str]] = None
    review_notes: Optional[list[str]] = None


class DraftRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class MaintenanceDraftResponse(BaseModel):
    draft_id: str
    project_id: str
    request_id: str
    review_status: str
    draft: dict[str, Any]
    verdict_steps: list[dict[str, Any]]
    viewer_manifest: dict[str, Any]
    manifest_tree: dict[str, Any]
    manifest_mapping: dict[str, Any]
    citations: list[dict[str, Any]]
