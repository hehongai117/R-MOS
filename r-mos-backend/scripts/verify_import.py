"""
验证开源机器人导入完整性。

三层检查：
  1. 文件系统完整性 — 源文件 vs 导入文件（数量、大小、抽样 MD5）
  2. 数据库一致性 — robot_models 记录 + robot_assets 数量匹配
  3. API 可达性 — 启动后端后，抽样下载 asset 文件验证可用

用法:
    cd r-mos-backend
    python scripts/verify_import.py              # 文件 + 数据库检查
    python scripts/verify_import.py --with-api   # 额外测试 API 层（需后端运行中）
"""

import asyncio
import hashlib
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

from scripts.seed_opensource_robots import (
    ROBOT_SPECS,
    SOURCE_ROOT,
    TARGET_ROOT,
    _collect_files,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASS = "\033[32mPASS\033[0m"
_FAIL = "\033[31mFAIL\033[0m"
_WARN = "\033[33mWARN\033[0m"

_total_checks = 0
_passed_checks = 0
_failed_checks = 0
_failed_details: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    global _total_checks, _passed_checks, _failed_checks
    _total_checks += 1
    if condition:
        _passed_checks += 1
        print(f"  [{_PASS}] {name}")
    else:
        _failed_checks += 1
        msg = f"  [{_FAIL}] {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        _failed_details.append(f"{name}: {detail}")


def md5_file(path: Path, chunk_size: int = 8192) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 1. File system integrity
# ---------------------------------------------------------------------------


def verify_filesystem():
    print("\n" + "=" * 60)
    print("  [1/3] 文件系统完整性检查")
    print("=" * 60)

    if not SOURCE_ROOT.exists():
        print(f"\n  [{_WARN}] 源目录不存在: {SOURCE_ROOT}")
        print("  跳过源文件对比（源目录已删除？）")
        # Still check target files exist
        for spec in ROBOT_SPECS:
            target_dir = TARGET_ROOT / str(spec.robot_id) / "uploads"
            check(
                f"Robot {spec.robot_id} ({spec.brand} {spec.model_name}) 目标目录存在",
                target_dir.exists(),
                f"目录不存在: {target_dir}",
            )
            if target_dir.exists():
                file_count = sum(1 for _ in target_dir.rglob("*") if _.is_file())
                check(
                    f"Robot {spec.robot_id} 有文件",
                    file_count > 0,
                    f"目录为空",
                )
        return

    for spec in ROBOT_SPECS:
        print(f"\n  Robot {spec.robot_id}: {spec.brand} {spec.model_name}")

        # Collect expected files from source (reusing seed script logic)
        expected_files: list[tuple[Path, Path, int]] = []  # (src, tgt, size)
        for src_rel, tgt_subdir in spec.path_mappings:
            src = SOURCE_ROOT / src_rel if src_rel else SOURCE_ROOT
            files = _collect_files(src)
            for src_file in files:
                if src.is_file():
                    rel = Path(src_file.name)
                else:
                    rel = src_file.relative_to(src)
                if tgt_subdir == ".":
                    tgt = TARGET_ROOT / str(spec.robot_id) / "uploads" / rel
                else:
                    tgt = TARGET_ROOT / str(spec.robot_id) / "uploads" / tgt_subdir / rel
                expected_files.append((src_file, tgt, src_file.stat().st_size))

        # Check target directory exists
        target_dir = TARGET_ROOT / str(spec.robot_id) / "uploads"
        check(f"目标目录存在", target_dir.exists(), str(target_dir))
        if not target_dir.exists():
            continue

        # Count actual files in target
        actual_count = sum(1 for _ in target_dir.rglob("*") if _.is_file())
        expected_count = len(expected_files)
        check(
            f"文件数量匹配 (期望 {expected_count}, 实际 {actual_count})",
            actual_count == expected_count,
            f"差异 {actual_count - expected_count}",
        )

        # Check each expected file exists and size matches
        missing = 0
        size_mismatch = 0
        for src_file, tgt_file, expected_size in expected_files:
            if not tgt_file.exists():
                missing += 1
                continue
            actual_size = tgt_file.stat().st_size
            if actual_size != expected_size:
                size_mismatch += 1

        check(f"文件全部存在 (缺失 {missing}/{expected_count})", missing == 0)
        check(f"文件大小全部匹配 (不匹配 {size_mismatch}/{expected_count})", size_mismatch == 0)

        # Sample MD5 check: pick up to 3 files of different sizes
        sample_files = sorted(expected_files, key=lambda x: x[2])  # sort by size
        # Pick smallest, middle, and a medium-sized one (avoid huge files)
        medium_files = [f for f in sample_files if f[2] < 10_000_000]  # <10MB
        samples = []
        if medium_files:
            samples.append(medium_files[0])  # smallest
            samples.append(medium_files[len(medium_files) // 2])  # middle
            if len(medium_files) > 2:
                samples.append(medium_files[-1])  # largest under 10MB

        md5_ok = 0
        md5_total = len(samples)
        for src_file, tgt_file, _ in samples:
            if tgt_file.exists():
                src_hash = md5_file(src_file)
                tgt_hash = md5_file(tgt_file)
                if src_hash == tgt_hash:
                    md5_ok += 1

        if md5_total > 0:
            check(
                f"MD5 抽样校验 ({md5_ok}/{md5_total} 通过)",
                md5_ok == md5_total,
            )


# ---------------------------------------------------------------------------
# 2. Database consistency
# ---------------------------------------------------------------------------


async def verify_database():
    print("\n" + "=" * 60)
    print("  [2/3] 数据库一致性检查")
    print("=" * 60)

    from sqlalchemy import func, select

    from app.core.database import AsyncSessionLocal
    from app.models.robot_asset import RobotAsset
    from app.models.robot_model import RobotModel

    async with AsyncSessionLocal() as session:
        # Check all 8 robots exist
        for spec in ROBOT_SPECS:
            result = await session.execute(
                select(RobotModel).where(RobotModel.id == spec.robot_id)
            )
            robot = result.scalar_one_or_none()

            print(f"\n  Robot {spec.robot_id}: {spec.brand} {spec.model_name}")
            check("数据库记录存在", robot is not None)
            if robot is None:
                continue

            check(f"brand 正确 ('{robot.brand}')", robot.brand == spec.brand)
            check(f"model_name 正确 ('{robot.model_name}')", robot.model_name == spec.model_name)
            check(f"visibility = SHARED", str(robot.visibility) == "RobotVisibility.SHARED"
                  or robot.visibility.value == "shared")
            check(f"owner_teacher_id = None", robot.owner_teacher_id is None)

            # Check asset count matches files on disk
            asset_result = await session.execute(
                select(func.count()).where(RobotAsset.robot_model_id == spec.robot_id)
            )
            db_asset_count = asset_result.scalar()

            target_dir = TARGET_ROOT / str(spec.robot_id) / "uploads"
            if target_dir.exists():
                disk_count = sum(1 for _ in target_dir.rglob("*") if _.is_file())
            else:
                disk_count = 0

            check(
                f"资产记录数匹配 (DB: {db_asset_count}, 磁盘: {disk_count})",
                db_asset_count == disk_count,
                f"差异 {db_asset_count - disk_count}",
            )

            # Spot check: verify a few asset file_path records point to real files
            asset_result = await session.execute(
                select(RobotAsset)
                .where(RobotAsset.robot_model_id == spec.robot_id)
                .limit(5)
            )
            assets = asset_result.scalars().all()
            spot_ok = 0
            for asset in assets:
                full_path = _BACKEND_DIR / asset.file_path
                if full_path.exists():
                    spot_ok += 1
            check(
                f"资产路径抽检 ({spot_ok}/{len(assets)} 文件可达)",
                spot_ok == len(assets),
            )


# ---------------------------------------------------------------------------
# 3. API accessibility
# ---------------------------------------------------------------------------


async def verify_api():
    print("\n" + "=" * 60)
    print("  [3/3] API 可达性检查")
    print("=" * 60)

    try:
        import httpx
    except ImportError:
        print(f"\n  [{_WARN}] httpx 未安装，尝试 aiohttp...")
        try:
            import aiohttp
            await _verify_api_aiohttp()
            return
        except ImportError:
            print(f"  [{_FAIL}] 需要 httpx 或 aiohttp。安装: pip install httpx")
            return

    await _verify_api_httpx()


async def _verify_api_httpx():
    import httpx

    base = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=10) as client:
        # Check backend is running
        try:
            r = await client.get(f"{base}/health")
            check("后端健康检查", r.status_code == 200, f"status={r.status_code}")
        except httpx.ConnectError:
            print(f"\n  [{_FAIL}] 无法连接后端 (localhost:8000)。请先启动后端。")
            return

        for spec in ROBOT_SPECS:
            print(f"\n  Robot {spec.robot_id}: {spec.brand} {spec.model_name}")

            # Get robot detail (no auth for asset endpoint)
            # Pick a sample file to download
            from sqlalchemy import select as sa_select

            from app.core.database import AsyncSessionLocal
            from app.models.robot_asset import RobotAsset

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    sa_select(RobotAsset)
                    .where(RobotAsset.robot_model_id == spec.robot_id)
                    .limit(3)
                )
                assets = result.scalars().all()

            if not assets:
                check("有可测试的资产", False, "数据库无资产记录")
                continue

            for asset in assets:
                # file_path is like "data/robot-assets/4/uploads/pro_urdf/urdf/humanoid.urdf"
                # API expects: /robots/4/assets/uploads/pro_urdf/urdf/humanoid.urdf
                # Strip the "data/robot-assets/{id}/" prefix
                fp = asset.file_path
                prefix = f"data/robot-assets/{spec.robot_id}/"
                if fp.startswith(prefix):
                    rel = fp[len(prefix):]
                else:
                    rel = fp

                url = f"{base}/robots/{spec.robot_id}/assets/{rel}"
                try:
                    r = await client.get(url)
                    fname = Path(rel).name
                    if r.status_code == 200:
                        # Verify size matches
                        content_length = len(r.content)
                        size_ok = (asset.file_size is None
                                   or content_length == asset.file_size
                                   or asset.file_size == 2_147_483_647)  # capped large files
                        check(
                            f"下载 {fname} (HTTP 200, {content_length} bytes)",
                            size_ok,
                            f"大小不匹配: DB={asset.file_size}, 下载={content_length}" if not size_ok else "",
                        )
                    else:
                        check(f"下载 {fname}", False, f"HTTP {r.status_code}")
                except Exception as e:
                    check(f"下载 {Path(rel).name}", False, str(e))


async def _verify_api_aiohttp():
    import aiohttp

    base = "http://localhost:8000/api/v1"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as client:
        try:
            async with client.get(f"{base}/health") as r:
                check("后端健康检查", r.status == 200, f"status={r.status}")
        except aiohttp.ClientConnectorError:
            print(f"\n  [{_FAIL}] 无法连接后端 (localhost:8000)。请先启动后端。")
            return

        for spec in ROBOT_SPECS:
            print(f"\n  Robot {spec.robot_id}: {spec.brand} {spec.model_name}")

            from sqlalchemy import select as sa_select

            from app.core.database import AsyncSessionLocal
            from app.models.robot_asset import RobotAsset

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    sa_select(RobotAsset)
                    .where(RobotAsset.robot_model_id == spec.robot_id)
                    .limit(3)
                )
                assets = result.scalars().all()

            if not assets:
                check("有可测试的资产", False, "数据库无资产记录")
                continue

            for asset in assets:
                fp = asset.file_path
                prefix = f"data/robot-assets/{spec.robot_id}/"
                rel = fp[len(prefix):] if fp.startswith(prefix) else fp
                url = f"{base}/robots/{spec.robot_id}/assets/{rel}"
                try:
                    async with client.get(url) as r:
                        fname = Path(rel).name
                        if r.status == 200:
                            content = await r.read()
                            size_ok = (asset.file_size is None
                                       or len(content) == asset.file_size
                                       or asset.file_size == 2_147_483_647)
                            check(
                                f"下载 {fname} (HTTP 200, {len(content)} bytes)",
                                size_ok,
                            )
                        else:
                            check(f"下载 {fname}", False, f"HTTP {r.status}")
                except Exception as e:
                    check(f"下载 {Path(rel).name}", False, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    with_api = "--with-api" in sys.argv

    print("\n" + "=" * 60)
    print("  R-MOS 开源机器人导入验证")
    print("=" * 60)

    verify_filesystem()
    await verify_database()

    if with_api:
        await verify_api()
    else:
        print(f"\n  [跳过] API 检查（使用 --with-api 启用，需后端运行中）")

    # Summary
    print("\n" + "=" * 60)
    if _failed_checks == 0:
        print(f"  \033[32m全部通过: {_passed_checks}/{_total_checks} 检查项 PASS\033[0m")
    else:
        print(f"  \033[31m有失败: {_passed_checks} PASS / {_failed_checks} FAIL (共 {_total_checks})\033[0m")
        print(f"\n  失败项:")
        for d in _failed_details:
            print(f"    - {d}")
    print("=" * 60 + "\n")

    return _failed_checks == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
