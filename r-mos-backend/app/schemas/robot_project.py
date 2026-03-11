from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RobotProjectUploadJobResponse(BaseModel):
    job_id: str
    project_id: str
    status: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    brand: str | None = None
    model: str | None = None
    version: str | None = None


class RobotProjectSummaryResponse(BaseModel):
    project_id: str
    robot_key: str
    brand: str
    model: str
    version: str | None = None
    status: str
    ingest_summary: dict[str, Any] | None = None


class RobotProjectListResponse(BaseModel):
    projects: list[RobotProjectSummaryResponse]


class RobotProjectManifestResponse(BaseModel):
    project_id: str
    robot_key: str
    brand: str
    model: str
    version: str | None = None
    status: str
    ingest_summary: dict[str, Any] | None = None
    tree: dict[str, Any]
    mapping: dict[str, Any]
    viewer_manifest: dict[str, Any]
