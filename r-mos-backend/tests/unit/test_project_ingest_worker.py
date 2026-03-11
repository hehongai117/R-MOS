from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy import select

from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.services.knowledge.project_ingest_worker import ProjectIngestWorker


@pytest.mark.asyncio
async def test_project_ingest_worker_creates_chunks_and_manifest(test_db) -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as zf:
        zf.writestr("docs/maintenance.md", "# 维护说明\n执行器弯曲维护步骤")
        zf.writestr("cad/robot.SLDASM", "assembly-placeholder")
        zf.writestr("cad/elbow.SLDPRT", "part-placeholder")
        zf.writestr("viewer/elbow.glb", b"glb-placeholder")
        zf.writestr("structure/N1.urdf", "<robot name='N1'></robot>")

    archive_path = "/tmp/rmos-test-ingest.zip"
    with open(archive_path, "wb") as fh:
        fh.write(archive_buffer.getvalue())

    project = RobotProject(
        robot_key="fourier-n1-ingest",
        brand="Fourier",
        model="N1",
        version="v1",
        status=RobotProjectStatus.UPLOADED,
        source_package_path=archive_path,
        ingest_summary_json={"files_total": 1, "classification_kind": "archive", "classification_strategy": "deferred"},
    )
    test_db.add(project)
    await test_db.flush()
    test_db.add(
        RobotProjectFile(
            project_id=project.id,
            filename="FourierN1.zip",
            relative_path="FourierN1.zip",
            file_kind="archive",
            storage_path=archive_path,
            classification_json={"strategy": "deferred"},
        )
    )
    await test_db.commit()

    await ProjectIngestWorker().ingest_project(test_db, project.id)

    chunks = (
        await test_db.execute(
            select(AIKnowledgeChunk).where(
                AIKnowledgeChunk.source_type == "robot_project",
                AIKnowledgeChunk.metadata_json["robot_project_id"].as_string() == project.id,
            )
        )
    ).scalars().all()
    manifest = (
        await test_db.execute(select(RobotPartManifest).where(RobotPartManifest.project_id == project.id))
    ).scalar_one()
    refreshed = (
        await test_db.execute(select(RobotProject).where(RobotProject.id == project.id))
    ).scalar_one()

    assert len(chunks) >= 3
    assert any(chunk.metadata_json.get("file_kind") == "document" for chunk in chunks)
    assert any(chunk.metadata_json.get("file_kind") == "assembly" for chunk in chunks)
    assert manifest.viewer_manifest_json["robotId"] == "fourier-n1-ingest"
    assert manifest.mapping_json["elbow"]["source_paths"] == ["cad/elbow.SLDPRT", "viewer/elbow.glb"]
    assert refreshed.status == RobotProjectStatus.READY
    assert refreshed.ingest_summary_json["files_total"] == 5
    assert refreshed.ingest_summary_json["chunks_total"] == len(chunks)


@pytest.mark.asyncio
async def test_project_ingest_worker_is_idempotent_on_reingest(test_db) -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as zf:
        zf.writestr("docs/maintenance.md", "# 维护说明\n执行器弯曲维护步骤")
        zf.writestr("cad/robot.SLDASM", "assembly-placeholder")
        zf.writestr("cad/elbow.SLDPRT", "part-placeholder")
        zf.writestr("viewer/elbow.glb", b"glb-placeholder")
        zf.writestr("structure/N1.urdf", "<robot name='N1'></robot>")

    archive_path = "/tmp/rmos-test-ingest-idempotent.zip"
    with open(archive_path, "wb") as fh:
        fh.write(archive_buffer.getvalue())

    project = RobotProject(
        robot_key="fourier-n1-idempotent",
        brand="Fourier",
        model="N1",
        version="v1",
        status=RobotProjectStatus.UPLOADED,
        source_package_path=archive_path,
        ingest_summary_json={"files_total": 1, "classification_kind": "archive", "classification_strategy": "deferred"},
    )
    test_db.add(project)
    await test_db.flush()
    test_db.add(
        RobotProjectFile(
            project_id=project.id,
            filename="FourierN1.zip",
            relative_path="FourierN1.zip",
            file_kind="archive",
            storage_path=archive_path,
            classification_json={"strategy": "deferred"},
        )
    )
    await test_db.commit()

    worker = ProjectIngestWorker()
    await worker.ingest_project(test_db, project.id)
    await worker.ingest_project(test_db, project.id)

    chunks = (
        await test_db.execute(
            select(AIKnowledgeChunk).where(
                AIKnowledgeChunk.source_type == "robot_project",
                AIKnowledgeChunk.metadata_json["robot_project_id"].as_string() == project.id,
            )
        )
    ).scalars().all()
    files = (
        await test_db.execute(select(RobotProjectFile).where(RobotProjectFile.project_id == project.id))
    ).scalars().all()
    refreshed = (
        await test_db.execute(select(RobotProject).where(RobotProject.id == project.id))
    ).scalar_one()

    assert len(chunks) == 5
    assert len(files) == 6
    assert refreshed.ingest_summary_json["files_total"] == 5
    assert refreshed.ingest_summary_json["chunks_total"] == 5


@pytest.mark.asyncio
async def test_project_ingest_worker_generates_embeddings_for_chunks(test_db, monkeypatch) -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as zf:
        zf.writestr("docs/maintenance.md", "# 维护说明\n执行器弯曲维护步骤")
        zf.writestr("viewer/elbow.glb", b"glb-placeholder")

    archive_path = "/tmp/rmos-test-ingest-embedding.zip"
    with open(archive_path, "wb") as fh:
        fh.write(archive_buffer.getvalue())

    project = RobotProject(
        robot_key="fourier-n1-embedding",
        brand="Fourier",
        model="N1",
        version="v1",
        status=RobotProjectStatus.UPLOADED,
        source_package_path=archive_path,
    )
    test_db.add(project)
    await test_db.flush()
    test_db.add(
        RobotProjectFile(
            project_id=project.id,
            filename="FourierN1.zip",
            relative_path="FourierN1.zip",
            file_kind="archive",
            storage_path=archive_path,
            classification_json={"strategy": "deferred"},
        )
    )
    await test_db.commit()

    async def fake_embed_batch(texts: list[str]):
        return [[float(index + 1), 0.0, 0.0] for index, _ in enumerate(texts)]

    monkeypatch.setattr(
        "app.services.knowledge.project_ingest_worker.embedding_service",
        type("_EmbeddingStub", (), {"embed_batch": staticmethod(fake_embed_batch)})(),
    )

    await ProjectIngestWorker().ingest_project(test_db, project.id)

    chunks = (
        await test_db.execute(
            select(AIKnowledgeChunk).where(
                AIKnowledgeChunk.source_type == "robot_project",
                AIKnowledgeChunk.metadata_json["robot_project_id"].as_string() == project.id,
            )
        )
    ).scalars().all()

    assert len(chunks) == 2
    assert all(isinstance(chunk.embedding, list) for chunk in chunks)
