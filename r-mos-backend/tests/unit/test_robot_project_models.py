from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.models.robot_sop_draft import RobotSOPDraft, RobotSOPDraftReviewStatus


@pytest.mark.asyncio
async def test_robot_project_asset_models_persist(test_db) -> None:
    project = RobotProject(
        robot_key="fourier-n1-v1",
        brand="Fourier",
        model="N1",
        version="v1",
        status=RobotProjectStatus.UPLOADED,
        source_package_path="storage/robot-projects/fourier-n1-v1.zip",
        ingest_summary_json={"files_total": 12},
    )
    test_db.add(project)
    await test_db.flush()

    test_db.add(
        RobotProjectFile(
            project_id=project.id,
            filename="总装.SLDASM",
            relative_path="FourierN1模型总装/总装.SLDASM",
            file_kind="assembly",
            mime_type="application/octet-stream",
            sha256="deadbeef",
            storage_path="storage/robot-projects/fourier-n1-v1/总装.SLDASM",
            classification_json={"strategy": "metadata_only"},
        )
    )
    test_db.add(
        RobotPartManifest(
            project_id=project.id,
            manifest_version="1.0",
            tree_json={"root": "torso"},
            mapping_json={"frame_torso": ["总装.SLDASM"]},
            viewer_manifest_json={"robotId": "fourier-n1-v1"},
        )
    )
    test_db.add(
        RobotSOPDraft(
            project_id=project.id,
            request_id="req-001",
            draft_json={"steps": [{"title": "安全断电"}]},
            citations_json=["chunk-1"],
            review_status=RobotSOPDraftReviewStatus.DRAFT_PENDING_REVIEW,
        )
    )
    await test_db.commit()

    stored = await test_db.scalar(
        select(RobotProject).where(RobotProject.robot_key == "fourier-n1-v1")
    )
    assert stored is not None
    assert stored.status == RobotProjectStatus.UPLOADED
    assert stored.ingest_summary_json == {"files_total": 12}


@pytest.mark.asyncio
async def test_robot_project_robot_key_must_be_unique(test_db) -> None:
    test_db.add(
        RobotProject(
            robot_key="duplicate-key",
            brand="Fourier",
            model="N1",
            version="v1",
            status=RobotProjectStatus.UPLOADED,
            source_package_path="storage/a.zip",
        )
    )
    await test_db.commit()

    test_db.add(
        RobotProject(
            robot_key="duplicate-key",
            brand="Fourier",
            model="N1",
            version="v1",
            status=RobotProjectStatus.INGESTING,
            source_package_path="storage/b.zip",
        )
    )
    with pytest.raises(IntegrityError):
        await test_db.commit()
