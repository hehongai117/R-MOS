"""
Migrate ATOM-01 from hardcoded assets to RobotModel data-driven architecture.

This script:
1. Creates a RobotModel record for ATOM-01 (system built-in)
2. Updates existing SOPs with robot_model_id
3. Updates existing KnowledgeDocuments with robot_model_id
4. Updates existing FaultSOPMappings with robot_model_id
5. Copies 3D model files from public/models/ to data/robot-assets/{id}/

Usage:
    cd r-mos-backend
    source venv/bin/activate
    python scripts/migrate_atom01.py
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal as async_session
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus
from app.models.sop import SOP
from app.models.knowledge_document import KnowledgeDocument
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.robot_asset import RobotAsset, AssetType

PROJECT_ROOT = Path(__file__).parent.parent.parent  # r-mos/
FRONTEND_MODELS = PROJECT_ROOT / "r-mos-frontend" / "public" / "models"
ASSETS_BASE = PROJECT_ROOT / "data" / "robot-assets"


async def main():
    async with async_session() as db:
        # 1. Check if ATOM-01 already exists
        result = await db.execute(
            select(RobotModel).where(
                RobotModel.brand == "R-MOS",
                RobotModel.model_name == "ATOM-01",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"ATOM-01 already migrated (id={existing.id}). Skipping DB migration.")
            robot_id = existing.id
        else:
            # 2. Create RobotModel
            robot = RobotModel(
                brand="R-MOS",
                model_name="ATOM-01",
                version="1.0",
                owner_teacher_id=None,
                visibility=RobotVisibility.SHARED,
                status=RobotStatus.READY,
                description="R-MOS 原型人形机器人",
            )
            db.add(robot)
            await db.flush()
            robot_id = robot.id
            print(f"Created RobotModel ATOM-01 (id={robot_id})")

            # 3. Update existing records
            sop_result = await db.execute(
                update(SOP).where(SOP.robot_model_id.is_(None)).values(robot_model_id=robot_id)
            )
            print(f"Updated {sop_result.rowcount} SOPs")

            kd_result = await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.robot_model_id.is_(None))
                .values(robot_model_id=robot_id, generation_status="published")
            )
            print(f"Updated {kd_result.rowcount} KnowledgeDocuments")

            fsm_result = await db.execute(
                update(FaultSOPMapping)
                .where(FaultSOPMapping.robot_model_id.is_(None))
                .values(robot_model_id=robot_id)
            )
            print(f"Updated {fsm_result.rowcount} FaultSOPMappings")

            await db.commit()

        # 4. Copy model files
        dest_dir = ASSETS_BASE / str(robot_id)
        src_robot = FRONTEND_MODELS / "robots" / "atom01"
        src_parts = FRONTEND_MODELS / "parts"

        if src_robot.exists() and not (dest_dir / "models").exists():
            dest_models = dest_dir / "models"
            print(f"Copying robot models: {src_robot} -> {dest_models}")
            shutil.copytree(src_robot, dest_models)

            manifest_dest = dest_dir / "manifests"
            manifest_dest.mkdir(parents=True, exist_ok=True)
            for manifest_name in ["assembly_manifest.json", "explode_manifest.json"]:
                manifest_src = src_robot / manifest_name
                if manifest_src.exists():
                    shutil.copy2(manifest_src, manifest_dest / manifest_name)
                    print(f"Copied {manifest_name}")
        else:
            print(f"Robot models already migrated or source not found: {src_robot}")

        # Note: public/models/parts/ (1.6GB shared parts catalog) is NOT
        # robot-specific. It stays in public/ and is served as static assets.
        # Only atom01's robot GLBs + manifests are migrated here.

        # 5. Register assets in DB
        async with async_session() as db2:
            existing_assets = await db2.execute(
                select(RobotAsset).where(RobotAsset.robot_model_id == robot_id)
            )
            if not existing_assets.scalars().first():
                models_dir = dest_dir / "models"
                if models_dir.exists():
                    for glb_file in models_dir.glob("*.glb"):
                        asset = RobotAsset(
                            robot_model_id=robot_id,
                            asset_type=AssetType.MODEL_GLB,
                            file_path=f"models/{glb_file.name}",
                            file_size=glb_file.stat().st_size,
                        )
                        db2.add(asset)
                    await db2.commit()
                    print("Registered GLB assets in database")

        print("\n=== Migration complete ===")
        print(f"RobotModel ID: {robot_id}")
        print(f"Assets directory: {dest_dir}")
        print(f"\nNext steps:")
        print(f"  1. Verify: ls {dest_dir}/models/")
        print(f"  2. After verification, delete: rm -rf {FRONTEND_MODELS}/robots/atom01")
        print(f"  3. The parts/ directory (1.6GB) stays in public/ as shared assets")


if __name__ == "__main__":
    asyncio.run(main())
