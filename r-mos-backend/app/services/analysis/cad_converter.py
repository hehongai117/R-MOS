"""CAD → GLB converter with quality checks."""
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask
from app.models.robot_asset import RobotAsset, AssetType
from app.services.storage.file_storage import LocalFileStorage

logger = logging.getLogger(__name__)

CAD_EXTENSIONS = {".step", ".stp", ".stl"}
GLB_EXTENSIONS = {".glb", ".gltf"}
MIN_VERTICES = 10
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


class CadConverter:
    """检测 CAD/GLB 文件并转换为 GLB 格式，创建 MODEL_GLB 资产记录。"""

    def __init__(self):
        self.storage = LocalFileStorage()

    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """处理分析任务中的 CAD/GLB 文件。

        Returns:
            {"skipped": True, "reason": str} — 无 CAD/GLB 文件时
            {"models_converted": int, "glb_copied": int, "errors": list | None} — 处理完成时
        """
        # 1. 查询该机器人的所有 UPLOAD_ORIGINAL 资产
        result = await db.execute(
            select(RobotAsset).where(
                RobotAsset.robot_model_id == task.robot_model_id,
                RobotAsset.asset_type == AssetType.UPLOAD_ORIGINAL,
            )
        )
        all_assets = result.scalars().all()

        # 2. 按扩展名分类
        cad_assets = []
        glb_assets = []
        for asset in all_assets:
            suffix = Path(asset.file_path).suffix.lower()
            if suffix in CAD_EXTENSIONS:
                cad_assets.append(asset)
            elif suffix in GLB_EXTENSIONS:
                glb_assets.append(asset)

        # 3. 无任何 CAD/GLB 文件时跳过
        if not cad_assets and not glb_assets:
            return {"skipped": True, "reason": "no CAD/GLB files found"}

        models_converted = 0
        glb_copied = 0
        errors = []

        # 4. GLB 文件：直接复制到 models/ 目录
        for asset in glb_assets:
            try:
                info = self._copy_glb_asset(asset)
                new_asset = RobotAsset(
                    robot_model_id=asset.robot_model_id,
                    asset_type=AssetType.MODEL_GLB,
                    file_path=info["file_path"],
                    file_size=info["file_size"],
                    asset_metadata={"source_asset_id": asset.id, "conversion": "direct_copy"},
                )
                db.add(new_asset)
                glb_copied += 1
                logger.info("GLB 复制成功: %s → %s", asset.file_path, info["file_path"])
            except Exception as exc:
                msg = f"GLB 复制失败 [{asset.file_path}]: {exc}"
                logger.error(msg)
                errors.append(msg)

        # 5. CAD 文件：转换为 GLB
        for asset in cad_assets:
            try:
                info = self._convert_cad_to_glb(asset)
                if info is None:
                    msg = f"CAD 转换返回 None [{asset.file_path}]"
                    logger.warning(msg)
                    errors.append(msg)
                    continue
                new_asset = RobotAsset(
                    robot_model_id=asset.robot_model_id,
                    asset_type=AssetType.MODEL_GLB,
                    file_path=info["file_path"],
                    file_size=info["file_size"],
                    asset_metadata={
                        "source_asset_id": asset.id,
                        "conversion": "cad_to_glb",
                        "quality": info.get("quality"),
                    },
                )
                db.add(new_asset)
                models_converted += 1
                logger.info("CAD 转换成功: %s → %s", asset.file_path, info["file_path"])
            except Exception as exc:
                msg = f"CAD 转换异常 [{asset.file_path}]: {exc}"
                logger.error(msg)
                errors.append(msg)

        # 6. 刷新到数据库
        await db.flush()

        return {
            "models_converted": models_converted,
            "glb_copied": glb_copied,
            "errors": errors if errors else None,
        }

    def _copy_glb_asset(self, asset: RobotAsset) -> dict:
        """将 GLB 文件复制到 models/ 子目录，返回新的存储信息。"""
        rel = asset.file_path.split("/", 1)[-1]  # "uploads/robot.glb"
        src_path = self.storage.get_full_path(asset.robot_model_id, rel)
        filename = Path(src_path).name
        content = Path(src_path).read_bytes()
        rel_path = self.storage.upload(asset.robot_model_id, filename, content, subdirectory="models")
        return {"file_path": rel_path, "file_size": len(content)}

    def _convert_cad_to_glb(self, asset: RobotAsset) -> Optional[dict]:
        """将 STEP/STP/STL 文件转换为 GLB 格式。

        Returns:
            {"file_path": str, "file_size": int, "quality": dict} — 成功
            None — 失败（trimesh 不可用或转换出错）
        """
        # 1. 尝试导入 trimesh
        try:
            import trimesh
        except ImportError:
            logger.error("trimesh 未安装，无法执行 CAD 转换。请运行: pip install trimesh")
            return None

        # 2. 获取源文件绝对路径
        rel = asset.file_path.split("/", 1)[-1]
        try:
            src_path = self.storage.get_full_path(asset.robot_model_id, rel)
        except ValueError as exc:
            logger.error("路径遍历检测: %s", exc)
            return None

        if not Path(src_path).exists():
            logger.error("源文件不存在: %s", src_path)
            return None

        # 3. 加载模型
        try:
            scene = trimesh.load(src_path, force="scene")
        except Exception as exc:
            logger.error("trimesh 加载失败 [%s]: %s", src_path, exc)
            return None

        # 4. 导出为 GLB bytes
        try:
            glb_bytes = scene.export(file_type="glb")
        except Exception as exc:
            logger.error("GLB 导出失败 [%s]: %s", src_path, exc)
            return None

        # 5. 统计顶点/面数用于质量检查
        vertices = 0
        faces = 0
        if hasattr(scene, "geometry"):
            for geom in scene.geometry.values():
                if hasattr(geom, "vertices"):
                    vertices += len(geom.vertices)
                if hasattr(geom, "faces"):
                    faces += len(geom.faces)
        elif hasattr(scene, "vertices"):
            vertices = len(scene.vertices)
            faces = len(scene.faces) if hasattr(scene, "faces") else 0

        quality = self._quality_check(vertices=vertices, faces=faces, file_size=len(glb_bytes))

        # 6. 存储 GLB 文件（同名替换扩展名）
        stem = Path(src_path).stem
        glb_filename = f"{stem}.glb"
        rel_path = self.storage.upload(
            asset.robot_model_id, glb_filename, glb_bytes, subdirectory="models"
        )

        return {
            "file_path": rel_path,
            "file_size": len(glb_bytes),
            "quality": quality,
        }

    def _quality_check(self, vertices: int, faces: int, file_size: int) -> dict:
        """对转换结果做质量检查。

        Returns:
            {"passed": bool, "issues": list | None}
        """
        issues = []

        if vertices < MIN_VERTICES:
            issues.append(
                f"顶点数不足: {vertices} < {MIN_VERTICES}，模型可能为空或损坏"
            )

        if file_size > MAX_FILE_SIZE:
            issues.append(
                f"文件过大: {file_size / 1024 / 1024:.1f} MB > {MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
            )

        if issues:
            return {"passed": False, "issues": issues}
        return {"passed": True, "issues": None}
