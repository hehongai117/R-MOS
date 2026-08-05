"""统一导入：一次上传同时喂 RobotModel 与 RobotProject 两条管线。

背景：知识库过去有两个上传入口 —— 「文件上传」只产出 RobotModel/GLB（喂 3D 展示、
实时监控），「机器人项目」只产出 RobotProject（喂 SOP 维保练习页、知识检索）。
两者互不相识，用户无从判断该用哪个。现在统一为一个入口，后台双写。
"""
import pytest

from app.models.robot_project import RobotProject
from app.models.robot_project_file import RobotProjectFile
from app.services.knowledge.project_ingest_service import ProjectIngestService


@pytest.mark.asyncio
async def test_sync_creates_project_bound_to_robot_model(test_db, tmp_path):
    service = ProjectIngestService(storage_root=tmp_path)

    project = await service.sync_project_for_robot_model(
        test_db,
        robot_model_id=42,
        brand="W2",
        model="W2V1",
        version="1.0",
        files=[
            ("w2v1.urdf", b"<robot name='w2v1'/>", "application/xml"),
            ("base_link.stl", b"solid\nendsolid", None),
        ],
    )

    assert project.robot_key == "robot-model-42"
    assert project.brand == "W2"
    assert project.model == "W2V1"

    files = (
        await test_db.execute(
            RobotProjectFile.__table__.select().where(
                RobotProjectFile.project_id == project.id
            )
        )
    ).fetchall()
    assert len(files) == 2


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_appends_new_files(test_db, tmp_path):
    """同一机型多次上传应复用同一个 project，而不是每次新建。"""
    service = ProjectIngestService(storage_root=tmp_path)

    first = await service.sync_project_for_robot_model(
        test_db,
        robot_model_id=7,
        brand="CASBOT",
        model="MINI",
        version=None,
        files=[("a.urdf", b"<robot/>", None)],
    )
    second = await service.sync_project_for_robot_model(
        test_db,
        robot_model_id=7,
        brand="CASBOT",
        model="MINI",
        version=None,
        files=[("b.stl", b"solid", None)],
    )

    assert first.id == second.id

    projects = (
        await test_db.execute(
            RobotProject.__table__.select().where(RobotProject.robot_key == "robot-model-7")
        )
    ).fetchall()
    assert len(projects) == 1

    files = (
        await test_db.execute(
            RobotProjectFile.__table__.select().where(
                RobotProjectFile.project_id == first.id
            )
        )
    ).fetchall()
    assert len(files) == 2


@pytest.mark.asyncio
async def test_sync_does_not_duplicate_same_filename(test_db, tmp_path):
    service = ProjectIngestService(storage_root=tmp_path)

    await service.sync_project_for_robot_model(
        test_db,
        robot_model_id=9,
        brand="B",
        model="M",
        version=None,
        files=[("same.urdf", b"v1", None)],
    )
    project = await service.sync_project_for_robot_model(
        test_db,
        robot_model_id=9,
        brand="B",
        model="M",
        version=None,
        files=[("same.urdf", b"v2", None)],
    )

    files = (
        await test_db.execute(
            RobotProjectFile.__table__.select().where(
                RobotProjectFile.project_id == project.id
            )
        )
    ).fetchall()
    assert len(files) == 1, "同名文件应覆盖而不是新增一条记录"


def test_upload_endpoint_wires_knowledge_sync():
    """上传端点必须同时喂知识管线，否则统一入口就名不副实。"""
    import inspect

    from app.api.v1.endpoints import robots

    source = inspect.getsource(robots.upload_robot_files)
    assert "sync_project_for_robot_model" in source, "上传端点应双写知识管线"
    # 知识管线失败不能阻断 3D 资产上传
    assert "except Exception" in source
