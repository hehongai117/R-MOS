"""Assembly builder — orchestrates URDF parsing, mesh conversion, and manifest generation."""
import json
import logging
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask
from app.models.robot_asset import RobotAsset, AssetType
from app.services.analysis.urdf_parser import URDFParser
from app.services.analysis.cad_converter import convert_single_cad_to_glb
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


class AssemblyBuilder:
    """Orchestrates: URDF discovery → parse → mesh conversion → manifest output."""

    def __init__(self):
        self.storage = get_storage()
        self.parser = URDFParser()

    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """Main entry point for pipeline integration."""
        robot_model_id = task.robot_model_id
        with self.storage.materialize_dir(robot_model_id) as robot_dir:
            return await self._process_in_dir(task, db, robot_model_id, robot_dir)

    async def _process_in_dir(
        self, task: AnalysisTask, db: AsyncSession, robot_model_id: int, robot_dir: Path
    ) -> dict:
        """Core assembly logic, called with the robot directory materialized on local disk."""
        # 1. Find URDF
        urdf_files = self._find_urdf_files(str(robot_dir))
        if not urdf_files:
            logger.info("robot_model_id=%d: no URDF found, skipping assembly build", robot_model_id)
            return {"assembly_built": False, "reason": "no URDF file found in uploads"}

        urdf_path = urdf_files[0]
        logger.info("robot_model_id=%d: found URDF at %s", robot_model_id, urdf_path)

        # 2. Parse URDF
        urdf_content = Path(urdf_path).read_text(encoding="utf-8", errors="replace")
        parse_result = self.parser.parse(urdf_content)
        logger.info(
            "robot_model_id=%d: parsed URDF '%s' — %d links, %d joints",
            robot_model_id, parse_result.robot_name,
            len(parse_result.links), len(parse_result.joints),
        )

        # 3. Resolve and convert meshes
        mesh_refs = [link.mesh_filename for link in parse_result.links if link.mesh_filename]
        resolved = self._resolve_mesh_files(mesh_refs, str(robot_dir))

        meshes_converted = 0
        for link in parse_result.links:
            if not link.mesh_filename:
                continue
            basename = Path(link.mesh_filename).name
            source_path = resolved.get(basename)
            if not source_path:
                logger.warning("robot_model_id=%d: mesh not found: %s", robot_model_id, basename)
                continue

            # 已存在则跳过（通过 storage.exists 检查，不依赖本地路径）
            if self.storage.exists(robot_model_id, f"models/{link.name}.glb"):
                meshes_converted += 1
                continue

            with tempfile.TemporaryDirectory() as tmp_dir:
                output_glb = Path(tmp_dir) / f"{link.name}.glb"
                result = await convert_single_cad_to_glb(source_path, str(output_glb))
                if result["success"]:
                    content = output_glb.read_bytes()
                    rel_path = self.storage.upload(
                        robot_model_id, f"{link.name}.glb", content, subdirectory="models"
                    )
                    meshes_converted += 1
                    existing = await db.execute(
                        select(RobotAsset).where(
                            RobotAsset.robot_model_id == robot_model_id,
                            RobotAsset.file_path == rel_path,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        db.add(RobotAsset(
                            robot_model_id=robot_model_id,
                            asset_type=AssetType.MODEL_GLB,
                            file_path=rel_path,
                            file_size=result["file_size"],
                            asset_metadata={"source": basename, "conversion": "urdf_assembly_build"},
                        ))
                else:
                    logger.warning(
                        "robot_model_id=%d: failed to convert %s: %s",
                        robot_model_id, basename, result["error"],
                    )

        # 4. Generate assembly manifest
        manifest = parse_result.to_assembly_manifest(robot_model_id)
        for link in parse_result.links:
            if link.mesh_filename:
                mesh_id = f"{link.name}_mesh"
                manifest["mesh_catalog"][mesh_id] = f"models/{link.name}.glb"

        # 5. Store manifest
        manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        manifest_rel_path = self.storage.upload(
            robot_model_id=robot_model_id,
            filename="assembly_manifest.json",
            content=manifest_json,
            subdirectory="manifests",
        )

        # 6. Register manifest asset
        existing_manifest = await db.execute(
            select(RobotAsset).where(
                RobotAsset.robot_model_id == robot_model_id,
                RobotAsset.file_path == manifest_rel_path,
            )
        )
        if not existing_manifest.scalar_one_or_none():
            db.add(RobotAsset(
                robot_model_id=robot_model_id,
                asset_type=AssetType.MANIFEST,
                file_path=manifest_rel_path,
                file_size=len(manifest_json),
                asset_metadata={
                    "type": "assembly_manifest",
                    "robot_name": parse_result.robot_name,
                    "links_count": len(parse_result.links),
                    "joints_count": len(parse_result.joints),
                },
            ))

        await db.flush()

        logger.info(
            "robot_model_id=%d: assembly built — %d meshes, manifest at %s",
            robot_model_id, meshes_converted, manifest_rel_path,
        )
        return {
            "assembly_built": True,
            "meshes_converted": meshes_converted,
            "manifest_path": manifest_rel_path,
            "links": len(parse_result.links),
            "joints": len(parse_result.joints),
        }

    def _find_urdf_files(self, robot_dir: str) -> list[str]:
        """Find all .urdf files recursively in robot's directory."""
        robot_path = Path(robot_dir)
        if not robot_path.exists():
            return []
        return [str(f) for f in robot_path.rglob("*.urdf")]

    def _resolve_mesh_files(
        self, mesh_refs: list[str], robot_dir: str
    ) -> dict[str, str]:
        """Resolve URDF mesh filename references to actual file paths.

        URDF often uses relative paths like '../meshes/base_link.STL'.
        We search the robot's upload directory for matching filenames (case-insensitive).
        """
        robot_path = Path(robot_dir)
        file_index: dict[str, str] = {}
        for f in robot_path.rglob("*"):
            if f.is_file():
                file_index[f.name.lower()] = str(f)

        resolved: dict[str, str] = {}
        for ref in mesh_refs:
            if not ref:
                continue
            basename = Path(ref).name
            if basename.lower() in file_index:
                resolved[basename] = file_index[basename.lower()]

        return resolved
