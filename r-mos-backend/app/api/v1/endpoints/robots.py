"""Robot model CRUD API endpoints."""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.storage.file_storage import LocalFileStorage
from app.services.authz_guard import ActorContext, get_current_actor
from app.services.robot_service import RobotService
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.schemas.robot_model import (
    RobotModelCreate,
    RobotModelUpdate,
    RobotModelResponse,
    RobotModelListResponse,
    RobotAssetResponse,
    FileUploadResponse,
    SharedRobotResponse,
    SharedRobotListResponse,
)
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
from app.schemas.analysis_task import AnalysisTaskResponse, AnalysisTaskListResponse

router = APIRouter(prefix="/robots", tags=["robots"])

# Initialize storage (will be replaced with DI later)
_storage = LocalFileStorage()


def _require_teacher_or_admin(actor: ActorContext):
    if "teacher" not in actor.roles and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="教师或管理员权限才能操作机器人")


@router.post("", response_model=RobotModelResponse, status_code=status.HTTP_201_CREATED)
async def create_robot(
    body: RobotModelCreate,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """创建新机器人型号。"""
    _require_teacher_or_admin(actor)
    robot = RobotModel(
        brand=body.brand,
        model_name=body.model_name,
        version=body.version,
        description=body.description,
        owner_teacher_id=actor.user_id,
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    db.add(robot)
    await db.flush()

    binding = TeacherRobotBinding(
        teacher_id=actor.user_id,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    db.add(binding)
    await db.commit()
    await db.refresh(robot)
    return robot


@router.get("", response_model=RobotModelListResponse)
async def list_robots(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """列出当前教师名下的机器人（自有 + 引用）。"""
    _require_teacher_or_admin(actor)
    stmt = (
        select(RobotModel, TeacherRobotBinding.binding_type)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(TeacherRobotBinding.teacher_id == actor.user_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    items = []
    for robot, binding_type in rows:
        resp = RobotModelResponse.model_validate(robot)
        resp.binding_type = binding_type
        items.append(resp)
    return RobotModelListResponse(items=items, total=len(items))


@router.get("/shared", response_model=SharedRobotListResponse)
async def list_shared_robots(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """浏览共享机器人库（任何已登录教师可访问）。"""
    _require_teacher_or_admin(actor)

    stmt = select(RobotModel).where(
        RobotModel.visibility == RobotVisibility.SHARED,
        RobotModel.status == RobotStatus.READY,
    )

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (RobotModel.brand.ilike(search_pattern)) | (RobotModel.model_name.ilike(search_pattern))
        )

    stmt = stmt.order_by(RobotModel.updated_at.desc())
    result = await db.execute(stmt)
    robots = list(result.scalars().all())

    binding_result = await db.execute(
        select(TeacherRobotBinding.robot_model_id).where(
            TeacherRobotBinding.teacher_id == actor.user_id,
        )
    )
    bound_ids = {row[0] for row in binding_result.all()}

    items = []
    for robot in robots:
        item = SharedRobotResponse(
            id=robot.id,
            brand=robot.brand,
            model_name=robot.model_name,
            version=robot.version,
            owner_teacher_id=robot.owner_teacher_id,
            owner_name=None,
            visibility=robot.visibility.value if hasattr(robot.visibility, 'value') else robot.visibility,
            status=robot.status.value if hasattr(robot.status, 'value') else robot.status,
            description=robot.description,
            thumbnail_path=robot.thumbnail_path,
            created_at=robot.created_at,
            updated_at=robot.updated_at,
            is_bound=robot.id in bound_ids,
        )
        items.append(item)

    return SharedRobotListResponse(items=items, total=len(items))


@router.get("/{robot_id}", response_model=RobotModelResponse)
async def get_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取机器人详情（需绑定关系或共享可见）。"""
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if "admin" in actor.roles:
        return robot
    if robot.visibility == RobotVisibility.SHARED:
        return robot
    binding_result = await db.execute(
        select(TeacherRobotBinding).where(
            TeacherRobotBinding.teacher_id == actor.user_id,
            TeacherRobotBinding.robot_model_id == robot_id,
        )
    )
    if not binding_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="无权访问该机器人")
    return robot


@router.put("/{robot_id}", response_model=RobotModelResponse)
async def update_robot(
    robot_id: int,
    body: RobotModelUpdate,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """更新机器人信息（仅 owner）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以编辑")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(robot, key, value)
    await db.commit()
    await db.refresh(robot)
    return robot


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """删除机器人（仅 owner）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以删除")
    await db.delete(robot)
    await db.commit()


@router.post("/{robot_id}/upload", response_model=FileUploadResponse)
async def upload_robot_files(
    robot_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """上传文件到机器人（支持批量）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以上传文件")

    uploaded = []
    failed = []

    for file in files:
        try:
            clean_name = RobotService.validate_filename(file.filename or "")
            content = await file.read()
            RobotService.validate_file_size(len(content))

            asset_type = RobotService.detect_asset_type(clean_name)
            subdirectory = RobotService.detect_subdirectory(asset_type)

            rel_path = _storage.upload(
                robot_model_id=robot_id,
                filename=clean_name,
                content=content,
                subdirectory=subdirectory,
            )

            asset = RobotAsset(
                robot_model_id=robot_id,
                asset_type=asset_type,
                file_path=rel_path,
                file_size=len(content),
            )
            db.add(asset)
            await db.flush()
            await db.refresh(asset)
            uploaded.append(asset)
        except ValueError as e:
            failed.append({"filename": file.filename or "", "error": str(e)})

    await db.commit()
    return FileUploadResponse(
        uploaded=[RobotAssetResponse.model_validate(a) for a in uploaded],
        failed=failed,
    )


@router.post("/{robot_id}/analyze", response_model=AnalysisTaskResponse, status_code=status.HTTP_201_CREATED)
async def trigger_analysis(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """手动触发 AI 分析（创建 AnalysisTask）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以触发分析")

    # 防止重复触发：检查是否有未完成的分析任务
    existing = await db.execute(
        select(AnalysisTask).where(
            AnalysisTask.robot_model_id == robot_id,
            AnalysisTask.status.in_([AnalysisTaskStatus.PENDING, AnalysisTaskStatus.RUNNING]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已有分析任务进行中，请等待完成后再触发")

    # 查询该机器人的上传文件 ID
    asset_result = await db.execute(
        select(RobotAsset.id).where(
            RobotAsset.robot_model_id == robot_id,
            RobotAsset.asset_type == AssetType.UPLOAD_ORIGINAL,
        )
    )
    doc_ids = [row[0] for row in asset_result.all()]

    task = AnalysisTask(
        robot_model_id=robot_id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.PENDING,
        input_document_ids=doc_ids,
    )
    db.add(task)

    # 更新机器人状态为 analyzing
    robot.status = RobotStatus.ANALYZING
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{robot_id}/analysis-tasks", response_model=AnalysisTaskListResponse)
async def list_analysis_tasks(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """查看机器人的分析任务列表。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以查看分析任务")

    task_result = await db.execute(
        select(AnalysisTask)
        .where(AnalysisTask.robot_model_id == robot_id)
        .order_by(AnalysisTask.created_at.desc())
    )
    tasks = list(task_result.scalars().all())
    return AnalysisTaskListResponse(items=tasks, total=len(tasks))


@router.put("/{robot_id}/publish", response_model=RobotModelResponse)
async def publish_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """发布机器人（status → ready）或取消发布（status → draft）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以发布")

    if robot.status == RobotStatus.READY:
        # 取消发布
        robot.status = RobotStatus.DRAFT
    else:
        if not RobotService.can_publish(robot.status):
            raise HTTPException(status_code=409, detail="当前状态不允许发布（分析进行中）")
        robot.status = RobotStatus.READY

    await db.commit()
    await db.refresh(robot)
    return robot


@router.put("/{robot_id}/visibility", response_model=RobotModelResponse)
async def set_visibility(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """切换机器人共享状态（private ↔ shared）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以修改共享状态")

    if robot.visibility == RobotVisibility.SHARED:
        robot.visibility = RobotVisibility.PRIVATE
        # 清理所有 shared_ref 绑定
        await db.execute(
            delete(TeacherRobotBinding).where(
                TeacherRobotBinding.robot_model_id == robot_id,
                TeacherRobotBinding.binding_type == "shared_ref",
            )
        )
    else:
        robot.visibility = RobotVisibility.SHARED

    await db.commit()
    await db.refresh(robot)
    return robot


@router.post("/{robot_id}/bind", status_code=status.HTTP_201_CREATED)
async def bind_shared_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """引用一个共享机器人到自己名下。"""
    _require_teacher_or_admin(actor)

    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.visibility != RobotVisibility.SHARED:
        raise HTTPException(status_code=400, detail="该机器人未设为共享，无法引用")

    if robot.owner_teacher_id == actor.user_id:
        raise HTTPException(status_code=400, detail="不能引用自己创建的机器人")

    existing = await db.execute(
        select(TeacherRobotBinding).where(
            TeacherRobotBinding.teacher_id == actor.user_id,
            TeacherRobotBinding.robot_model_id == robot_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已经引用过该机器人")

    binding = TeacherRobotBinding(
        teacher_id=actor.user_id,
        robot_model_id=robot_id,
        binding_type="shared_ref",
    )
    db.add(binding)
    await db.commit()
    return {"detail": "引用成功"}


@router.delete("/{robot_id}/bind", status_code=status.HTTP_204_NO_CONTENT)
async def unbind_shared_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """取消引用一个共享机器人。"""
    _require_teacher_or_admin(actor)

    result = await db.execute(
        select(TeacherRobotBinding).where(
            TeacherRobotBinding.teacher_id == actor.user_id,
            TeacherRobotBinding.robot_model_id == robot_id,
            TeacherRobotBinding.binding_type == "shared_ref",
        )
    )
    binding = result.scalar_one_or_none()
    if not binding:
        raise HTTPException(status_code=404, detail="未找到引用关系")

    await db.delete(binding)
    await db.commit()


@router.get("/{robot_id}/tools")
async def get_robot_tools(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取机器人工具列表（从 assembly_manifest.json 中读取）。"""
    import json
    from pathlib import Path

    manifest_path = Path("data/robot-assets") / str(robot_id) / "manifests" / "assembly_manifest.json"
    if not manifest_path.exists():
        return {"robot_id": robot_id, "tools": []}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"robot_id": robot_id, "tools": manifest.get("tools", [])}


@router.get("/{robot_id}/assets")
async def list_robot_assets(
    robot_id: int,
    asset_type: Optional[str] = Query(None, description="过滤资产类型: upload_original, model_glb, manifest, thumbnail"),
    db: AsyncSession = Depends(get_db),
):
    """列出机器人的资产文件，支持按 asset_type 过滤。"""
    query = select(RobotAsset).where(RobotAsset.robot_model_id == robot_id)
    if asset_type:
        query = query.where(RobotAsset.asset_type == asset_type)
    result = await db.execute(query)
    assets = result.scalars().all()
    return {
        "items": [
            {
                "id": a.id,
                "asset_type": a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
                "file_path": a.file_path,
                "file_name": a.file_path.split("/")[-1],
                "file_size": a.file_size,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ]
    }


@router.get("/{robot_id}/assets/{file_path:path}")
async def get_robot_asset(
    robot_id: int,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """获取机器人资产文件（3D 模型、manifest 等）。

    无需认证 — Three.js GLTFLoader 直接 fetch，无法附加 Authorization header。
    资产文件（GLB/JSON）为非敏感数据。
    """
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    try:
        full_path = _storage.get_full_path(robot_model_id=robot_id, rel_path=file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    content_types = {
        "glb": "model/gltf-binary",
        "gltf": "model/gltf+json",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
    }
    media_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(full_path, media_type=media_type)

