from __future__ import annotations

import hashlib
import mimetypes
import re
import tempfile
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.schemas.robot_project import (
    RobotProjectListResponse,
    RobotProjectManifestResponse,
    RobotProjectSummaryResponse,
    RobotProjectUploadJobResponse,
)
from app.services.knowledge.file_classifier import classify_file


def _slug(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


class ProjectIngestService:
    def __init__(self, storage_root: Path | None = None) -> None:
        default_root = Path(tempfile.gettempdir()) / "rmos-robot-projects"
        self.storage_root = storage_root or default_root

    async def create_upload_job(
        self,
        db: AsyncSession,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        brand: str | None,
        model: str | None,
        version: str | None,
    ) -> RobotProjectUploadJobResponse:
        project_id = str(uuid.uuid4())
        robot_key = f"{_slug(brand)}-{_slug(model)}-{_slug(version)}-{project_id[:8]}"
        target_dir = self.storage_root / project_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(content)

        classified = classify_file(filename)
        project = RobotProject(
            id=project_id,
            robot_key=robot_key,
            brand=brand or "unknown",
            model=model or "unknown",
            version=version,
            status=RobotProjectStatus.UPLOADED,
            source_package_path=str(target_path),
            ingest_summary_json={
                "files_total": 1,
                "classification_kind": classified.kind.value,
                "classification_strategy": classified.strategy.value,
            },
        )
        project_file = RobotProjectFile(
            project_id=project_id,
            filename=filename,
            relative_path=filename,
            file_kind=classified.kind.value,
            mime_type=content_type,
            sha256=hashlib.sha256(content).hexdigest(),
            storage_path=str(target_path),
            classification_json={
                "strategy": classified.strategy.value,
                "extension": classified.extension,
            },
        )
        db.add(project)
        db.add(project_file)
        await db.commit()

        return RobotProjectUploadJobResponse(
            job_id=project.id,
            project_id=project.id,
            status=project.status.value,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            brand=project.brand,
            model=project.model,
            version=project.version,
        )

    async def get_upload_job(
        self,
        db: AsyncSession,
        *,
        job_id: str,
    ) -> RobotProjectUploadJobResponse | None:
        project = (
            await db.execute(select(RobotProject).where(RobotProject.id == job_id))
        ).scalar_one_or_none()
        if project is None:
            return None

        project_file = (
            await db.execute(
                select(RobotProjectFile).where(RobotProjectFile.project_id == project.id)
            )
        ).scalars().first()

        return RobotProjectUploadJobResponse(
            job_id=project.id,
            project_id=project.id,
            status=project.status.value,
            filename=project_file.filename if project_file else None,
            content_type=project_file.mime_type if project_file else None,
            size_bytes=None,
            brand=project.brand,
            model=project.model,
            version=project.version,
        )

    async def list_projects(self, db: AsyncSession) -> RobotProjectListResponse:
        projects = (
            await db.execute(select(RobotProject).order_by(RobotProject.updated_at.desc()))
        ).scalars().all()
        return RobotProjectListResponse(
            projects=[
                RobotProjectSummaryResponse(
                    project_id=project.id,
                    robot_key=project.robot_key,
                    brand=project.brand,
                    model=project.model,
                    version=project.version,
                    status=project.status.value if hasattr(project.status, "value") else str(project.status),
                    ingest_summary=dict(project.ingest_summary_json or {}),
                )
                for project in projects
            ]
        )

    async def get_project_manifest(
        self,
        db: AsyncSession,
        *,
        project_id: str,
    ) -> RobotProjectManifestResponse | None:
        project = (
            await db.execute(select(RobotProject).where(RobotProject.id == project_id))
        ).scalar_one_or_none()
        if project is None:
            return None
        manifest = (
            await db.execute(select(RobotPartManifest).where(RobotPartManifest.project_id == project.id))
        ).scalar_one_or_none()
        if manifest is None:
            return None
        return RobotProjectManifestResponse(
            project_id=project.id,
            robot_key=project.robot_key,
            brand=project.brand,
            model=project.model,
            version=project.version,
            status=project.status.value if hasattr(project.status, "value") else str(project.status),
            ingest_summary=dict(project.ingest_summary_json or {}),
            tree=dict(manifest.tree_json or {}),
            mapping=dict(manifest.mapping_json or {}),
            viewer_manifest=dict(manifest.viewer_manifest_json or {}),
        )

    async def get_project_asset(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        asset_path: str,
    ) -> tuple[bytes, str]:
        project_file = (
            await db.execute(
                select(RobotProjectFile).where(
                    RobotProjectFile.project_id == project_id,
                    RobotProjectFile.relative_path == asset_path,
                )
            )
        ).scalars().first()
        if project_file is None:
            raise FileNotFoundError(asset_path)

        media_type = project_file.mime_type or mimetypes.guess_type(project_file.filename)[0] or "application/octet-stream"
        return self._read_storage_bytes(project_file.storage_path), media_type

    def _read_storage_bytes(self, storage_path: str) -> bytes:
        if "::" in storage_path:
            archive_path_str, member_name = storage_path.split("::", 1)
            with zipfile.ZipFile(archive_path_str) as archive:
                return archive.read(member_name)
        return Path(storage_path).read_bytes()

project_ingest_service = ProjectIngestService()
