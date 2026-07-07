"""Assembly manifest generator — parses GLB node tree into structured JSON."""
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask
from app.models.robot_asset import RobotAsset, AssetType
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """解析 GLB 文件节点树，生成装配清单 JSON 并存储为 MANIFEST 资产。"""

    def __init__(self):
        self.storage = get_storage()

    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """处理分析任务，为所有 GLB 资产生成装配清单。

        Returns:
            {"manifests_created": N} 或 {"manifests_created": 0, "reason": "no GLB assets"}
        """
        # 1. 查询 robot_model_id 关联的 MODEL_GLB 类型资产
        stmt = select(RobotAsset).where(
            RobotAsset.robot_model_id == task.robot_model_id,
            RobotAsset.asset_type == AssetType.MODEL_GLB,
        )
        result = await db.execute(stmt)
        glb_assets = result.scalars().all()

        # 2. 无 GLB 资产时提前返回
        if not glb_assets:
            logger.info("robot_model_id=%d 无 GLB 资产，跳过清单生成", task.robot_model_id)
            return {"manifests_created": 0, "reason": "no GLB assets"}

        manifests_created = 0

        # 3. 对每个 GLB 资产生成装配清单
        for asset in glb_assets:
            try:
                # a. 解析节点树
                tree = self._parse_glb_nodes(asset)

                # b. 存储 JSON 文件
                manifest_path = self._store_manifest(asset.robot_model_id, asset, tree)

                # c. 计算节点数
                node_count = self._count_nodes(tree)

                # d. 创建 MANIFEST 资产记录
                manifest_asset = RobotAsset(
                    robot_model_id=asset.robot_model_id,
                    asset_type=AssetType.MANIFEST,
                    file_path=manifest_path,
                    file_size=len(json.dumps(tree).encode("utf-8")),
                    asset_metadata={
                        "source_glb": asset.file_path,
                        "source_glb_id": asset.id,
                        "node_count": node_count,
                    },
                )
                db.add(manifest_asset)
                manifests_created += 1
                logger.info(
                    "robot_model_id=%d 生成装配清单：%s（%d 节点）",
                    asset.robot_model_id, manifest_path, node_count,
                )

            except Exception as exc:
                logger.error(
                    "GLB 资产 id=%d path=%s 生成清单失败：%s",
                    asset.id, asset.file_path, exc,
                    exc_info=True,
                )

        # 4. flush 让数据库分配 ID
        await db.flush()

        # 5. 返回结果
        return {"manifests_created": manifests_created}

    def _parse_glb_nodes(self, asset: RobotAsset) -> dict:
        """用 trimesh 加载 GLB 文件并构建节点树。"""
        try:
            import trimesh
        except ImportError as exc:
            raise RuntimeError("trimesh 未安装，无法解析 GLB 文件") from exc

        # materialize 文件（trimesh 需要真实本地路径）
        rel = asset.file_path.split("/", 1)[-1]  # e.g. "models/robot.glb"
        with self.storage.materialize(asset.robot_model_id, rel) as full_path:
            loaded = trimesh.load(str(full_path))
        return self._build_node_tree(loaded)

    def _build_node_tree(self, scene) -> dict:
        """从 trimesh Scene 或 Mesh 构建节点树结构。"""
        try:
            import trimesh
        except ImportError:
            trimesh = None

        # 判断是否为 Scene（有 geometry 属性且包含多个几何体）
        if hasattr(scene, "geometry") and isinstance(scene.geometry, dict):
            children = []
            for geom_name, geom in scene.geometry.items():
                try:
                    vertices = geom.vertices.shape[0]
                    faces = geom.faces.shape[0]
                except Exception:
                    vertices = 0
                    faces = 0
                children.append({
                    "name": geom_name,
                    "type": "mesh",
                    "vertices": vertices,
                    "faces": faces,
                    "children": [],
                })
            return {"name": "root", "children": children}

        # 单个 Mesh 直接包装
        try:
            vertices = scene.vertices.shape[0]
            faces = scene.faces.shape[0]
        except Exception:
            vertices = 0
            faces = 0

        return {
            "name": "root",
            "type": "mesh",
            "vertices": vertices,
            "faces": faces,
            "children": [],
        }

    def _store_manifest(self, robot_model_id: int, asset: RobotAsset, tree: dict) -> str:
        """将节点树序列化为 JSON 并存储到 manifests/ 子目录。

        Returns:
            存储后的相对路径，格式如 "10/manifests/robot_manifest.json"
        """
        # 从 GLB 文件路径提取文件名（无扩展名）
        glb_stem = Path(asset.file_path).stem  # e.g. "robot"
        filename = f"{glb_stem}_manifest.json"

        content = json.dumps(tree, ensure_ascii=False, indent=2).encode("utf-8")
        rel_path = self.storage.upload(
            robot_model_id=robot_model_id,
            filename=filename,
            content=content,
            subdirectory="manifests",
        )
        return rel_path

    def _count_nodes(self, tree: dict) -> int:
        """递归计算节点总数（包括 root）。"""
        count = 1
        for child in tree.get("children", []):
            count += self._count_nodes(child)
        return count
