from __future__ import annotations

import zipfile
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.services.knowledge import embedding_service
from app.services.knowledge.document_chunker import DocumentChunker
from app.services.knowledge.fallback_embedding import fallback_embedding_service
from app.services.knowledge.file_classifier import classify_file
from app.services.knowledge.robot_manifest_builder import RobotManifestBuilder


class ProjectIngestWorker:
    def __init__(self) -> None:
        self.chunker = DocumentChunker()
        self.manifest_builder = RobotManifestBuilder()

    async def ingest_project(self, db: AsyncSession, project_id: str) -> None:
        project = (
            await db.execute(select(RobotProject).where(RobotProject.id == project_id))
        ).scalar_one()
        existing_files = (
            await db.execute(select(RobotProjectFile).where(RobotProjectFile.project_id == project.id))
        ).scalars().all()

        materialized_files = await self._expand_archives(db, project, existing_files)
        chunk_count = 0

        await db.execute(
            delete(AIKnowledgeChunk).where(
                AIKnowledgeChunk.source_type == "robot_project",
                AIKnowledgeChunk.metadata_json["robot_project_id"].as_string() == project.id,
            )
        )

        for file in materialized_files:
            content = self._read_file_content(file)
            classified = classify_file(file.relative_path)
            chunk_drafts = self.chunker.chunk(
                project=project,
                relative_path=file.relative_path,
                classified=classified,
                content=content,
            )
            embeddings = await self._generate_embeddings(chunk_drafts)
            for chunk, embedding in zip(chunk_drafts, embeddings):
                chunk_count += 1
                record = AIKnowledgeChunk(
                    source_type="robot_project",
                    source_id=chunk.source_id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata_json=chunk.metadata,
                )
                db.add(record)
                await db.flush()

        manifest_payload = self.manifest_builder.build(project, materialized_files)
        existing_manifest = (
            await db.execute(select(RobotPartManifest).where(RobotPartManifest.project_id == project.id))
        ).scalar_one_or_none()
        if existing_manifest is None:
            db.add(
                RobotPartManifest(
                    project_id=project.id,
                    manifest_version="1.0",
                    tree_json=manifest_payload["tree"],
                    mapping_json=manifest_payload["mapping"],
                    viewer_manifest_json=manifest_payload["viewer_manifest"],
                )
            )
        else:
            existing_manifest.tree_json = manifest_payload["tree"]
            existing_manifest.mapping_json = manifest_payload["mapping"]
            existing_manifest.viewer_manifest_json = manifest_payload["viewer_manifest"]

        project.status = RobotProjectStatus.READY
        summary = dict(project.ingest_summary_json or {})
        summary["files_total"] = len(materialized_files)
        summary["chunks_total"] = chunk_count
        project.ingest_summary_json = summary
        await self._sync_pgvector_vectors_for_project(db, project.id)
        await db.commit()

    async def _generate_embeddings(self, chunk_drafts) -> list[list[float] | None]:
        if not chunk_drafts:
            return []
        if embedding_service is None:
            return fallback_embedding_service.embed_batch([chunk.content for chunk in chunk_drafts])

        try:
            embedded = await embedding_service.embed_batch([chunk.content for chunk in chunk_drafts])
        except Exception:
            return fallback_embedding_service.embed_batch([chunk.content for chunk in chunk_drafts])

        normalized = list(embedded[: len(chunk_drafts)])
        if len(normalized) < len(chunk_drafts):
            normalized.extend([None] * (len(chunk_drafts) - len(normalized)))
        return normalized

    async def _sync_pgvector_vectors_for_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> None:
        bind = db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return
        await db.execute(
            text(
                """
                UPDATE ai_knowledge_chunks
                SET embedding_vec = CAST(embedding::text AS vector)
                WHERE source_type = 'robot_project'
                  AND metadata->>'robot_project_id' = :project_id
                  AND embedding IS NOT NULL
                  AND json_typeof(embedding) = 'array'
                  AND embedding_vec IS NULL
                """
            ),
            {"project_id": project_id},
        )

    async def _expand_archives(
        self,
        db: AsyncSession,
        project: RobotProject,
        existing_files: list[RobotProjectFile],
    ) -> list[RobotProjectFile]:
        existing_by_path = {
            file.relative_path: file
            for file in existing_files
            if file.file_kind != "archive"
        }
        materialized: list[RobotProjectFile] = list(existing_by_path.values())
        for file in existing_files:
            if file.file_kind != "archive":
                continue

            archive_path = Path(file.storage_path)
            if not archive_path.exists():
                continue

            with zipfile.ZipFile(archive_path) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    if member.filename in existing_by_path:
                        continue
                    classified = classify_file(member.filename)
                    child = RobotProjectFile(
                        project_id=project.id,
                        filename=Path(member.filename).name,
                        relative_path=member.filename,
                        file_kind=classified.kind.value,
                        mime_type=None,
                        sha256=None,
                        storage_path=f"{archive_path}::{member.filename}",
                        classification_json={
                            "strategy": classified.strategy.value,
                            "extension": classified.extension,
                            "archive_member": True,
                        },
                    )
                    db.add(child)
                    existing_by_path[member.filename] = child
                    materialized.append(child)

            await db.flush()
        return materialized

    def _read_file_content(self, file: RobotProjectFile) -> bytes:
        storage_path = file.storage_path
        if "::" in storage_path:
            archive_path_str, member_name = storage_path.split("::", 1)
            with zipfile.ZipFile(archive_path_str) as zf:
                return zf.read(member_name)
        return Path(storage_path).read_bytes()
