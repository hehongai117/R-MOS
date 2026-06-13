# 开源机器人批量导入实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将桌面 `github开源机器人` 文件夹中的 8 个开源机器人项目全量导入 R-MOS，去重后存储到 `data/robot-assets/`，并创建数据库记录。

**Architecture:** 编写一个 Python 播种脚本，定义每个机器人的元数据和源路径映射，应用去重规则后复制文件到目标目录，然后通过 SQLAlchemy 异步会话插入 RobotModel 和 RobotAsset 记录。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0+ (async), aiosqlite, shutil, pathlib

**Spec:** `docs/superpowers/specs/2026-06-13-opensource-robot-import-design.md`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `r-mos-backend/scripts/seed_opensource_robots.py` | 创建：主播种脚本 |

源目录（只读）：`/Users/xuhehong/Desktop/github开源机器人/`
目标目录：`r-mos-backend/data/robot-assets/{4..11}/uploads/`

---

### Task 1: 创建播种脚本 — 机器人清单与去重工具

**Files:**
- Create: `r-mos-backend/scripts/seed_opensource_robots.py`

- [ ] **Step 1: 创建脚本骨架和机器人清单定义**

```python
"""
开源机器人批量导入播种脚本。

用法:
    python scripts/seed_opensource_robots.py              # 执行导入
    python scripts/seed_opensource_robots.py --dry-run    # 预览模式，不执行

源: ~/Desktop/github开源机器人/
目标: data/robot-assets/{id}/uploads/
"""
import asyncio
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus
from app.models.robot_asset import RobotAsset, AssetType
from app.core.config import settings

# ── 源目录 ──────────────────────────────────────────────
SOURCE_ROOT = Path.home() / "Desktop" / "github开源机器人"

# ── 目标根 ──────────────────────────────────────────────
ASSET_ROOT = Path(__file__).resolve().parent.parent / "data" / "robot-assets"


@dataclass
class RobotSpec:
    """单个待导入机器人的元数据和路径映射。"""
    target_id: int
    brand: str
    model_name: str
    description: str
    # (源相对路径, 目标子目录) 列表。源相对于 SOURCE_ROOT。
    path_mappings: list[tuple[str, str]] = field(default_factory=list)


ROBOT_SPECS: list[RobotSpec] = [
    RobotSpec(
        target_id=4,
        brand="天工",
        model_name="Tiangong Pro",
        description="天工 Pro 人形机器人 — URDF + STEP 整机 + 用户手册",
        path_mappings=[
            ("天工/pro_urdf_publish/urdf", "urdf"),
            ("天工/pro_urdf_publish/meshes", "meshes"),
            ("天工/x_humanoid_0430_newfeet_newbody_publish/urdf", "urdf_v2"),
            ("天工/x_humanoid_0430_newfeet_newbody_publish/meshes", "meshes_v2"),
            ("天工/TG10-00_机器人总装体.STEP", "models"),
            ("天工/网站-pro天工用户手册_0508.pdf", "docs"),
        ],
    ),
    RobotSpec(
        target_id=5,
        brand="天工",
        model_name="Tiangong Lite",
        description="天工 Lite 人形机器人 — ROS workspace + STEP 整机 + 用户手册",
        path_mappings=[
            ("天工/lite", "ros_workspace"),
            ("天工/TG11-00_机器人总装体.STEP", "models"),
            ("天工/网站-lite天工用户手册_0508.pdf", "docs"),
            ("天工/lite_urdf_publish.zip", "urdf_zip"),
        ],
    ),
    RobotSpec(
        target_id=6,
        brand="智元",
        model_name="灵犀 X1",
        description="智元灵犀 X1 人形机器人 — 三版资料（2024.10 / 2025.01 / 2025.03）",
        path_mappings=[
            ("智元机器人灵犀X1开源资料/智元灵犀X1_20250307", "v20250307"),
            ("智元机器人灵犀X1开源资料/智元灵犀X1_20250108", "v20250108"),
            ("智元机器人灵犀X1开源资料/智元灵犀X1_20241024", "v20241024"),
        ],
    ),
    RobotSpec(
        target_id=7,
        brand="智元",
        model_name="OmniHand T2",
        description="智元 OmniHand 灵动款灵巧手 — STEP 模型 + 规格书 + 使用手册",
        path_mappings=[
            ("智元灵巧手", "."),
        ],
    ),
    RobotSpec(
        target_id=8,
        brand="ORCA",
        model_name="ORCA Hand v1",
        description="ORCA Hand 开源灵巧手 — 3MF/STL/STEP 模型 + PCB + 固件",
        path_mappings=[
            ("hands", "."),
        ],
    ),
    RobotSpec(
        target_id=9,
        brand="高擎动力",
        model_name="Mini π",
        description="高擎动力 Mini π 双足机器人 — CAD + URDF + SDK + PCB",
        path_mappings=[
            ("高擎动力/Mini_π_双足机器人", "."),
        ],
    ),
    RobotSpec(
        target_id=10,
        brand="高擎动力",
        model_name="6DOF-A-06",
        description="高擎动力六轴机械臂 — 硬件资料 + SDK",
        path_mappings=[
            ("高擎动力/六轴机械臂", "."),
        ],
    ),
    RobotSpec(
        target_id=11,
        brand="高擎动力",
        model_name="四足机器人",
        description="高擎动力四足机器人 — STEP + 硬件 + 软件 + 运动控制",
        path_mappings=[
            ("高擎动力/四足机器人", "."),
        ],
    ),
]
```

- [ ] **Step 2: 实现去重过滤函数**

在同一文件中继续添加：

```python
# ── 去重规则 ─────────────────────────────────────────────

# 匹配 "(1)", "(2)", "(1)(1)" 等下载副本后缀（文件名或目录名中）
_DUP_DOWNLOAD_RE = re.compile(r'\(\d+\)(?:\(\d+\))*(?=\.\w+$|$)')

# 匹配 macOS Finder 复制产生的 " 2", " 3" 后缀
_DUP_FINDER_RE = re.compile(r' \d+$')

SKIP_NAMES = {'.DS_Store', '.git', '__MACOSX', 'Thumbs.db'}


def should_skip(path: Path, all_siblings: set[str] | None = None) -> bool:
    """判断某路径是否应跳过（去重/垃圾文件）。"""
    name = path.name

    # 1) 系统垃圾 / git
    if name in SKIP_NAMES:
        return True

    # 2) 下载副本: xxx(1).zip, xxx(2)/ 等
    stem = path.stem if path.is_file() else name
    if _DUP_DOWNLOAD_RE.search(stem):
        return True

    # 3) Finder 副本: "xxx 2", "xxx 3"
    if _DUP_FINDER_RE.search(stem if path.is_file() else name):
        return True

    # 4) zip + 解压目录共存 → 跳过 zip
    if path.is_file() and path.suffix == '.zip' and all_siblings:
        dir_name = path.stem
        if dir_name in all_siblings:
            return True

    return False


def collect_siblings(parent: Path) -> set[str]:
    """收集目录下所有直接子项的名字，用于 zip/目录共存检测。"""
    if not parent.is_dir():
        return set()
    return {p.name for p in parent.iterdir()}
```

- [ ] **Step 3: 实现文件复制逻辑**

```python
def copy_with_dedup(src: Path, dst_dir: Path, *, dry_run: bool = False) -> list[tuple[str, int]]:
    """
    递归复制 src 到 dst_dir，应用去重规则。
    返回 [(相对路径, 文件大小), ...] 列表。
    """
    copied: list[tuple[str, int]] = []

    if src.is_file():
        if should_skip(src):
            return copied
        dst_file = dst_dir / src.name
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_file)
        size = src.stat().st_size
        copied.append((str(dst_file.relative_to(dst_dir.parent)), size))
        return copied

    if not src.is_dir():
        return copied

    siblings = collect_siblings(src)

    for child in sorted(src.iterdir()):
        if should_skip(child, siblings):
            continue
        if child.is_file():
            rel = child.name
            dst_file = dst_dir / rel
            if not dry_run:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(child, dst_file)
            size = child.stat().st_size
            copied.append((str(dst_file.relative_to(dst_dir.parent)), size))
        elif child.is_dir():
            sub_dst = dst_dir / child.name
            copied.extend(copy_with_dedup(child, sub_dst, dry_run=dry_run))

    return copied
```

- [ ] **Step 4: 保存文件**

保存到 `r-mos-backend/scripts/seed_opensource_robots.py`。

---

### Task 2: 实现数据库播种与主入口

**Files:**
- Modify: `r-mos-backend/scripts/seed_opensource_robots.py`

- [ ] **Step 1: 添加数据库播种函数**

在脚本末尾添加：

```python
# ── 数据库 ───────────────────────────────────────────────

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_one_robot(
    session: AsyncSession,
    spec: RobotSpec,
    copied_files: list[tuple[str, int]],
    *,
    dry_run: bool = False,
) -> None:
    """为一个机器人创建 RobotModel + RobotAsset 记录。"""
    # 幂等检查
    result = await session.execute(
        select(RobotModel).where(
            RobotModel.brand == spec.brand,
            RobotModel.model_name == spec.model_name,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  ⏭  Robot {spec.brand} {spec.model_name} 已存在 (id={existing.id})，跳过")
        return

    if dry_run:
        print(f"  📝 [DRY-RUN] 将创建 RobotModel(brand={spec.brand}, model={spec.model_name})")
        print(f"     将创建 {len(copied_files)} 条 RobotAsset 记录")
        return

    robot = RobotModel(
        brand=spec.brand,
        model_name=spec.model_name,
        version="1.0",
        owner_teacher_id=None,
        visibility=RobotVisibility.SHARED,
        status=RobotStatus.DRAFT,
        description=spec.description,
    )
    session.add(robot)
    await session.flush()  # 获取自增 ID

    for rel_path, file_size in copied_files:
        asset = RobotAsset(
            robot_model_id=robot.id,
            asset_type=AssetType.UPLOAD_ORIGINAL,
            file_path=f"uploads/{rel_path}",
            file_size=file_size,
        )
        session.add(asset)

    print(f"  ✅ Robot {spec.brand} {spec.model_name} (id={robot.id}): {len(copied_files)} assets")
```

- [ ] **Step 2: 添加主函数**

```python
async def main(dry_run: bool = False) -> None:
    """主入口：遍历机器人清单，复制文件 + 播种数据库。"""
    if not SOURCE_ROOT.is_dir():
        print(f"❌ 源目录不存在: {SOURCE_ROOT}")
        sys.exit(1)

    print(f"{'[DRY-RUN] ' if dry_run else ''}开源机器人批量导入")
    print(f"  源: {SOURCE_ROOT}")
    print(f"  目标: {ASSET_ROOT}")
    print()

    total_files = 0
    total_bytes = 0

    async with AsyncSessionLocal() as session:
        for spec in ROBOT_SPECS:
            print(f"── Robot {spec.target_id}: {spec.brand} {spec.model_name} ──")

            uploads_dir = ASSET_ROOT / str(spec.target_id) / "uploads"
            all_copied: list[tuple[str, int]] = []

            for src_rel, dst_sub in spec.path_mappings:
                src_path = SOURCE_ROOT / src_rel
                if not src_path.exists():
                    print(f"  ⚠️  源路径不存在，跳过: {src_rel}")
                    continue

                if dst_sub == ".":
                    target = uploads_dir
                else:
                    target = uploads_dir / dst_sub

                copied = copy_with_dedup(src_path, target, dry_run=dry_run)
                all_copied.extend(copied)

            file_count = len(all_copied)
            byte_count = sum(s for _, s in all_copied)
            total_files += file_count
            total_bytes += byte_count
            print(f"  文件: {file_count}, 大小: {byte_count / 1024 / 1024:.1f} MB")

            await seed_one_robot(session, spec, all_copied, dry_run=dry_run)
            print()

        if not dry_run:
            await session.commit()
            print("💾 数据库已提交")

    print(f"{'[DRY-RUN] ' if dry_run else ''}汇总: {total_files} 文件, {total_bytes / 1024 / 1024 / 1024:.2f} GB")


if __name__ == "__main__":
    is_dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=is_dry_run))
```

- [ ] **Step 3: 保存文件**

保存到 `r-mos-backend/scripts/seed_opensource_robots.py`。

---

### Task 3: Dry-Run 验证

**Files:**
- Run: `r-mos-backend/scripts/seed_opensource_robots.py`

- [ ] **Step 1: 运行 dry-run**

```bash
cd r-mos-backend
source venv/bin/activate
python scripts/seed_opensource_robots.py --dry-run
```

期望输出：
- 8 个机器人逐一打印文件数和大小
- 无 `(1)`, `(2)`, ` 2` 后缀的文件
- 无 `.DS_Store`, `.git`
- zip 和解压目录共存时只有目录没有 zip
- 总计大小应显著小于源文件夹的 25.7GB

- [ ] **Step 2: 检查去重效果**

对比一下 dry-run 输出的智元 X1 文件数。源目录有大量重复，去重后应大幅减少。
如果发现去重不充分或过度，调整 `should_skip()` 规则后重跑。

---

### Task 4: 执行导入

**Files:**
- Run: `r-mos-backend/scripts/seed_opensource_robots.py`
- Verify: `r-mos-backend/data/robot-assets/`

- [ ] **Step 1: 执行实际导入**

```bash
cd r-mos-backend
source venv/bin/activate
python scripts/seed_opensource_robots.py
```

期望输出：每个机器人显示 `✅` 并打印 asset 数量。

- [ ] **Step 2: 验证文件系统**

```bash
# 检查新目录是否创建
ls -la data/robot-assets/

# 检查每个机器人的文件数和大小
for d in 4 5 6 7 8 9 10 11; do
  echo "=== Robot $d ==="
  find data/robot-assets/$d -type f | wc -l
  du -sh data/robot-assets/$d
done
```

期望：8 个新目录，每个都有 uploads/ 子目录。

- [ ] **Step 3: 验证数据库**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('rmos_dev.db')
print('=== robot_models ===')
for row in conn.execute('SELECT id, brand, model_name, status, visibility FROM robot_models ORDER BY id'):
    print(row)
print()
print('=== robot_assets count per robot ===')
for row in conn.execute('SELECT robot_model_id, COUNT(*) FROM robot_assets GROUP BY robot_model_id ORDER BY robot_model_id'):
    print(f'Robot {row[0]}: {row[1]} assets')
conn.close()
"
```

期望：robot_models 表有 11 条记录（3 已有 + 8 新增），robot_assets 表每个新机器人都有对应记录。

- [ ] **Step 4: 验证幂等性**

```bash
python scripts/seed_opensource_robots.py
```

期望：8 个机器人全部显示 `⏭ 已存在，跳过`。

---

### Task 5: 提交

- [ ] **Step 1: 提交脚本**

```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-backend/scripts/seed_opensource_robots.py
git commit -m "feat: add bulk import script for 8 opensource robots

Imports Tiangong Pro/Lite, Agibot X1, OmniHand, ORCA Hand,
GaoQing Mini-pi/6DOF-arm/Quadruped from ~/Desktop/github开源机器人/.
Includes dedup logic (download copies, Finder copies, zip+dir coexist)
and idempotent database seeding.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

注意：`data/robot-assets/` 在 `.gitignore` 中，不会提交大文件。
