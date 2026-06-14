"""
Seed script: bulk-import 8 opensource robots into R-MOS.

Robots seeded (IDs 4-11):
  4  天工 Tiangong Pro       humanoid
  5  天工 Tiangong Lite      humanoid
  6  智元 灵犀 X1             humanoid
  7  智元 OmniHand T2        dexterous hand
  8  ORCA ORCA Hand v1       dexterous hand
  9  高擎动力 Mini π           biped
  10 高擎动力 6DOF-A-06        arm
  11 高擎动力 四足机器人         quadruped

Idempotent: skips robots whose brand+model_name already exists.
Dedup: skips .DS_Store, __MACOSX, Thumbs.db, duplicate downloads
       (filenames with " (1)" etc.), Finder copies (ending in " 2" etc.),
       and zip files when the extracted directory already exists.

Run:
    cd r-mos-backend
    python -m scripts.seed_opensource_robots
    python -m scripts.seed_opensource_robots --dry-run
"""

import asyncio
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or r-mos-backend/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.robot_asset import AssetType, RobotAsset
from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SOURCE_ROOT = Path.home() / "Desktop" / "github开源机器人"
TARGET_ROOT = _BACKEND_DIR / "data" / "robot-assets"

# ---------------------------------------------------------------------------
# Robot specs
# ---------------------------------------------------------------------------


@dataclass
class RobotSpec:
    """Definition for one robot to be seeded."""

    robot_id: int
    brand: str
    model_name: str
    robot_type: str
    description: str
    # List of (source_rel_path, target_subdir) pairs.
    # source_rel_path: relative to SOURCE_ROOT (use "" for SOURCE_ROOT itself)
    # target_subdir:   subdirectory name under uploads/ (use "." for root)
    path_mappings: list[tuple[str, str]] = field(default_factory=list)


ROBOT_SPECS: list[RobotSpec] = [
    RobotSpec(
        robot_id=4,
        brand="天工",
        model_name="Tiangong Pro",
        robot_type="人形",
        description="天工 Pro 人形机器人，双足直立行走，包含 URDF、STEP 模型及用户手册。",
        path_mappings=[
            ("天工/pro_urdf_publish", "pro_urdf"),
            ("天工/x_humanoid_0430_newfeet_newbody_publish", "x_humanoid"),
            ("天工/TG10-00_机器人总装体.STEP", "."),
            ("天工/网站-pro天工用户手册_0508.pdf", "."),
        ],
    ),
    RobotSpec(
        robot_id=5,
        brand="天工",
        model_name="Tiangong Lite",
        robot_type="人形",
        description="天工 Lite 人形机器人，轻量版双足，包含 URDF、STEP 模型及用户手册。",
        path_mappings=[
            ("天工/lite", "lite"),
            ("天工/TG11-00_机器人总装体.STEP", "."),
            ("天工/lite_urdf_publish.zip", "."),
            ("天工/网站-lite天工用户手册_0508.pdf", "."),
        ],
    ),
    RobotSpec(
        robot_id=6,
        brand="智元",
        model_name="灵犀 X1",
        robot_type="人形",
        description="智元灵犀 X1 人形机器人开源资料，包含三个版本（20241024 / 20250108 / 20250307）。",
        path_mappings=[
            ("智元机器人灵犀X1开源资料", "."),
        ],
    ),
    RobotSpec(
        robot_id=7,
        brand="智元",
        model_name="OmniHand T2",
        robot_type="灵巧手",
        description="智元 OmniHand 灵动款 T2 灵巧手，包含 URDF、STEP、规格书及维护手册。",
        path_mappings=[
            ("智元灵巧手", "."),
        ],
    ),
    RobotSpec(
        robot_id=8,
        brand="ORCA",
        model_name="ORCA Hand v1",
        robot_type="灵巧手",
        description="ORCA 开源灵巧手 v1，包含 3MF 打印文件、STEP 模型及 BOM/电路资料。",
        path_mappings=[
            ("hands", "."),
        ],
    ),
    RobotSpec(
        robot_id=9,
        brand="高擎动力",
        model_name="Mini π",
        robot_type="双足",
        description="高擎动力 Mini π 双足机器人开源资料。",
        path_mappings=[
            ("高擎动力/Mini_π_双足机器人", "."),
        ],
    ),
    RobotSpec(
        robot_id=10,
        brand="高擎动力",
        model_name="6DOF-A-06",
        robot_type="机械臂",
        description="高擎动力 6DOF-A-06 六轴机械臂开源资料。",
        path_mappings=[
            ("高擎动力/六轴机械臂", "."),
        ],
    ),
    RobotSpec(
        robot_id=11,
        brand="高擎动力",
        model_name="四足机器人",
        robot_type="四足",
        description="高擎动力四足机器人开源资料。",
        path_mappings=[
            ("高擎动力/四足机器人", "."),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------

# Patterns for filenames that should always be skipped
_SKIP_NAMES: set[str] = {".DS_Store", "Thumbs.db", ".git"}
_SKIP_PREFIXES: tuple[str, ...] = ("__MACOSX",)

# Regex: " (1)", " (2)", " (1)(1)", " (2)(3)" etc.
_DL_DUP_RE = re.compile(r" \(\d+\)(\(\d+\))*$")

# Regex: Finder copies — stem ending with a space + single digit 2-9 (Finder starts at 2)
_FINDER_COPY_RE = re.compile(r" [2-9]$")


def _should_skip_name(name: str) -> bool:
    """Return True if this filename (without parent path) should be excluded."""
    if name in _SKIP_NAMES:
        return True
    for prefix in _SKIP_PREFIXES:
        if name.startswith(prefix):
            return True
    stem = Path(name).stem
    if _DL_DUP_RE.search(stem):
        return True
    if _FINDER_COPY_RE.search(stem):
        return True
    return False


def _collect_files(src: Path) -> list[Path]:
    """
    Recursively collect files under *src*, applying dedup filters.

    Dedup rules applied at directory level:
    - Skip entries matching _should_skip_name()
    - Skip a .zip file if a directory with the same stem exists in the same
      parent (zip+directory coexistence rule), UNLESS the zip is a split
      archive (.zip.001 etc. — actually these have extension ".001" so normal
      .zip dedup still applies correctly here).
    """
    if not src.exists():
        return []

    # If src is a single file, just return it (no dedup needed for single file)
    if src.is_file():
        return [src] if not _should_skip_name(src.name) else []

    results: list[Path] = []

    def _walk(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return

        # Build set of directory stems at this level for zip dedup
        dir_stems: set[str] = {
            e.stem for e in entries if e.is_dir() and not _should_skip_name(e.name)
        }

        for entry in entries:
            name = entry.name
            if _should_skip_name(name):
                continue

            if entry.is_symlink():
                continue

            if entry.is_dir():
                _walk(entry)
            elif entry.is_file():
                # zip+directory coexistence: skip .zip if same-stem dir exists
                if entry.suffix.lower() == ".zip" and entry.stem in dir_stems:
                    continue
                results.append(entry)

    _walk(src)
    return results


# ---------------------------------------------------------------------------
# Copy logic
# ---------------------------------------------------------------------------


def _copy_files(
    spec: RobotSpec,
    dry_run: bool,
) -> list[tuple[Path, int]]:
    """
    Copy all files for *spec* to the target directory.

    Returns list of (absolute_target_path, file_size) for successfully copied
    (or would-be-copied in dry-run) files.
    """
    copied: list[tuple[Path, int]] = []

    for src_rel, tgt_subdir in spec.path_mappings:
        src = SOURCE_ROOT / src_rel if src_rel else SOURCE_ROOT
        files = _collect_files(src)

        for src_file in files:
            # Build relative path within this source mapping
            if src.is_file():
                rel = Path(src_file.name)
            else:
                rel = src_file.relative_to(src)

            # Target path
            if tgt_subdir == ".":
                tgt_file = TARGET_ROOT / str(spec.robot_id) / "uploads" / rel
            else:
                tgt_file = TARGET_ROOT / str(spec.robot_id) / "uploads" / tgt_subdir / rel

            file_size = src_file.stat().st_size

            if not dry_run:
                tgt_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src_file), str(tgt_file))

            copied.append((tgt_file, file_size))

    return copied


# ---------------------------------------------------------------------------
# Database seeding
# ---------------------------------------------------------------------------


async def _seed_robot(
    spec: RobotSpec,
    copied_files: list[tuple[Path, int]],
    dry_run: bool,
) -> Optional[RobotModel]:
    """
    Insert RobotModel + RobotAsset records for *spec*.
    Returns None if already exists (idempotent).
    """
    async with AsyncSessionLocal() as session:
        # Check idempotency
        existing = await session.execute(
            select(RobotModel).where(
                RobotModel.brand == spec.brand,
                RobotModel.model_name == spec.model_name,
            )
        )
        robot = existing.scalar_one_or_none()
        if robot is not None:
            print(f"  [skip] {spec.brand} {spec.model_name} already in DB (id={robot.id})")
            return None

        if dry_run:
            print(f"  [dry-run] Would insert RobotModel: {spec.brand} {spec.model_name}")
            return None

        # Create RobotModel
        robot = RobotModel(
            id=spec.robot_id,
            brand=spec.brand,
            model_name=spec.model_name,
            version="1.0",
            owner_teacher_id=None,
            visibility=RobotVisibility.SHARED,
            status=RobotStatus.DRAFT,
            description=spec.description,
        )
        session.add(robot)
        await session.flush()  # get robot.id

        # Create RobotAsset records
        for tgt_file, file_size in copied_files:
            # Store path relative to r-mos-backend root
            try:
                rel_path = tgt_file.relative_to(_BACKEND_DIR)
            except ValueError:
                rel_path = tgt_file

            asset = RobotAsset(
                robot_model_id=robot.id,
                asset_type=AssetType.UPLOAD_ORIGINAL,
                file_path=str(rel_path),
                file_size=min(file_size, 2_147_483_647),  # cap to int32 max
                asset_metadata={"source": "opensource_seed"},
            )
            session.add(asset)

        await session.commit()
        return robot


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _fmt_size(total_bytes: int) -> str:
    if total_bytes >= 1024 ** 3:
        return f"{total_bytes / 1024**3:.2f} GB"
    if total_bytes >= 1024 ** 2:
        return f"{total_bytes / 1024**2:.2f} MB"
    return f"{total_bytes / 1024:.2f} KB"


async def main(dry_run: bool) -> None:
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{'='*60}")
    print(f"  {mode}R-MOS Opensource Robot Seed Script")
    print(f"  Source: {SOURCE_ROOT}")
    print(f"  Target: {TARGET_ROOT}")
    print(f"{'='*60}\n")

    if not SOURCE_ROOT.exists():
        print(f"ERROR: Source directory not found: {SOURCE_ROOT}")
        sys.exit(1)

    grand_total_files = 0
    grand_total_bytes = 0

    for spec in ROBOT_SPECS:
        print(f"Robot {spec.robot_id}: {spec.brand} {spec.model_name} ({spec.robot_type})")

        # Collect / copy files
        copied = _copy_files(spec, dry_run=dry_run)

        total_bytes = sum(sz for _, sz in copied)
        grand_total_files += len(copied)
        grand_total_bytes += total_bytes

        action = "Would copy" if dry_run else "Copied"
        print(f"  {action} {len(copied)} files  ({_fmt_size(total_bytes)})")

        # Seed DB
        robot = await _seed_robot(spec, copied, dry_run=dry_run)
        if robot:
            print(f"  Inserted RobotModel id={robot.id}, {len(copied)} assets")

        print()

    print(f"{'='*60}")
    print(f"  TOTAL: {grand_total_files} files, {_fmt_size(grand_total_bytes)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
