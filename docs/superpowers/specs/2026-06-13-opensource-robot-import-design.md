# 开源机器人批量导入设计

> 日期: 2026-06-13
> 状态: Draft

## 目标

将桌面 `github开源机器人` 文件夹中的 8 个开源机器人项目全量导入 R-MOS 多机器人平台，去除重复副本，创建数据库记录和文件资产，导入后可选删除源文件夹释放 ~25GB 磁盘空间。

## 现有机器人（不变）

| R-MOS ID | 品牌 | 型号 | 状态 |
|----------|------|------|------|
| 1 | RoboParty | ATOM-01 | ready（完整 manifest + GLB） |
| 2 | Fourier | N1 | ready（URDF + STL + manifest） |
| 3 | 未知 | 未知 | draft（PDF/STEP 零件图纸） |

## 新增机器人（ID 4-11）

| 新 ID | 品牌 | 型号 | 源文件夹 | 类型 | 去重后估算 |
|-------|------|------|---------|------|-----------|
| 4 | 天工 | Tiangong Pro | `天工/pro_urdf_publish` + STEP + 手册 | 人形 | ~800MB |
| 5 | 天工 | Tiangong Lite | `天工/lite` + 手册 | 人形 | ~500MB |
| 6 | 智元 | 灵犀 X1 | `智元机器人灵犀X1开源资料`（最新版） | 人形 | ~5GB |
| 7 | 智元 | OmniHand T2 | `智元灵巧手` | 灵巧手 | ~400MB |
| 8 | ORCA | ORCA Hand v1 | `hands` | 灵巧手 | ~150MB |
| 9 | 高擎动力 | Mini π | `高擎动力/Mini_π_双足机器人` | 双足 | ~1.5GB |
| 10 | 高擎动力 | 6DOF-A-06 | `高擎动力/六轴机械臂` | 机械臂 | ~50MB |
| 11 | 高擎动力 | 四足机器人 | `高擎动力/四足机器人` | 四足 | ~150MB |

## 去重规则

1. **重复下载副本** — 文件名含 `(1)`, `(2)`, `(3)` 后缀的跳过，只保留无后缀的原始文件
2. **Finder 副本** — 文件/目录名以 ` 2`, ` 3` 结尾的跳过（macOS 复制产生）
3. **zip + 解压共存** — 当 `xxx.zip` 和 `xxx/` 目录同时存在时，只保留解压目录，跳过 zip
4. **split zip** — `xxx.zip.001`, `.002` 等分卷文件，保留（可能需要合并才能解压）
5. **.git 目录** — 跳过，不导入 Git 历史
6. **.DS_Store** — 跳过

## 数据模型映射

### RobotModel 记录

```python
RobotModel(
    brand="天工",
    model_name="Tiangong Pro",
    version="1.0",
    owner_teacher_id=None,      # 系统内置
    visibility="shared",         # 所有教师可见
    status="draft",              # 待 AI 分析
    description="天工 Pro 人形机器人开源资料",
    thumbnail_path=None,
)
```

### RobotAsset 记录

每个上传文件创建一条记录：

```python
RobotAsset(
    robot_model_id=4,
    asset_type="upload_original",
    file_path="uploads/meshes/base_link.stl",   # 相对于 robot-assets/{id}/
    file_size=123456,
    asset_metadata=None,
)
```

### TeacherRobotBinding

系统内置机器人不创建 binding，所有教师通过 `visibility=shared` 可见。

## 文件存储结构

```
data/robot-assets/
├── 1/   (ATOM-01, 已有)
├── 2/   (N1, 已有)
├── 3/   (已有)
├── 4/   (天工 Pro)
│   └── uploads/
│       ├── meshes/          # URDF mesh 文件
│       ├── urdf/            # URDF 描述文件
│       ├── docs/            # PDF 手册
│       └── models/          # STEP 3D 模型
├── 5/   (天工 Lite)
│   └── uploads/...
├── 6/   (智元灵犀 X1)
│   └── uploads/...
├── 7/   (智元 OmniHand)
│   └── uploads/...
├── 8/   (ORCA Hand)
│   └── uploads/...
├── 9/   (高擎 Mini π)
│   └── uploads/...
├── 10/  (高擎 6DOF 机械臂)
│   └── uploads/...
└── 11/  (高擎四足机器人)
    └── uploads/...
```

## 源文件夹映射详细

### Robot 4: 天工 Pro

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `天工/pro_urdf_publish/urdf/` | `uploads/urdf/` | URDF 文件 |
| `天工/pro_urdf_publish/meshes/` | `uploads/meshes/` | mesh 文件 |
| `天工/TG10-00_机器人总装体.STEP` | `uploads/models/` | 整机 STEP |
| `天工/网站-pro天工用户手册_0508.pdf` | `uploads/docs/` | 用户手册 |

### Robot 5: 天工 Lite

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `天工/lite/` 目录 | `uploads/` | 完整 Lite 资料 |
| `天工/网站-lite天工用户手册_0508.pdf` | `uploads/docs/` | 用户手册 |

### Robot 6: 智元灵犀 X1

仅导入最新版本 `智元灵犀X1_20250307/`，跳过旧版本 `_20241024` 和 `_20250108`。
去重规则特别适用于此文件夹（大量重复下载）。

### Robot 7: 智元 OmniHand

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `智元灵巧手/*.STEP` | `uploads/models/` | 左右手 STEP |
| `智元灵巧手/*.pdf` | `uploads/docs/` | 规格书、说明书、维护手册 |
| `智元灵巧手/OmniHandBox-2-5/` | `uploads/hardware/` | 硬件资料 |
| `智元灵巧手/omnihand_description-*/` | `uploads/description/` | 描述文件 |

跳过：`.bin` 固件文件、重复 zip

### Robot 8: ORCA Hand

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `hands/*.3mf` | `uploads/models/` | 3D 打印模型 |
| `hands/*.stl` | `uploads/models/` | STL 模型 |
| `hands/*.step` | `uploads/models/` | STEP 整机 |
| `hands/ORCA_Fingers/` | `uploads/fingers/` | 手指组件 |
| `hands/ORCA_Molds/` | `uploads/molds/` | 模具 |
| `hands/ORCA_Tower/` | `uploads/tower/` | Tower 组件 |
| `hands/orca_core/` | `uploads/firmware/` | 核心固件/代码 |
| `hands/orcahand_description/` | `uploads/description/` | 描述文件 |
| `hands/*.xls, *.csv` | `uploads/bom/` | BOM 和元件表 |
| `hands/ORCA_Motor_Connectors_Gerber/` | `uploads/pcb/` | PCB Gerber 文件 |

### Robot 9: 高擎 Mini π

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `Mini_π_双足机器人/CAD模型/` | `uploads/models/cad/` | CAD 模型目录 |
| `Mini_π_双足机器人/双足机器人CAD模型.STEP` | `uploads/models/` | 整机 STEP |
| `Mini_π_双足机器人/URDF完整版/` | `uploads/urdf/full/` | 完整 URDF |
| `Mini_π_双足机器人/URDF简化版/` | `uploads/urdf/simplified/` | 简化 URDF |
| `Mini_π_双足机器人/PAI-urdf/` | `uploads/urdf/pai/` | PAI URDF |
| `Mini_π_双足机器人/*.pdf` | `uploads/docs/` | 手册和原理图 |
| `Mini_π_双足机器人/主控板PCB.png` | `uploads/pcb/` | PCB 图 |

跳过：`libtorch*` SDK 包、重复副本 `PAI-urdf 2`、zip 文件（已有解压目录）

### Robot 10: 高擎 6DOF 机械臂

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `六轴机械臂/6DOF-A-06/` | `uploads/hardware/` | 硬件资料 |
| `六轴机械臂/livelybot_arm-main/` | `uploads/software/` | 软件/SDK |

跳过：`livelybot_arm-main 2`（Finder 副本）、`.7z` zip

### Robot 11: 高擎四足机器人

| 源路径 | 目标子目录 | 说明 |
|--------|-----------|------|
| `四足机器人/四足机器人结构/` | `uploads/structure/` | 结构资料 |
| `四足机器人/四足狗-5046-02.STEP` | `uploads/models/` | 整机 STEP |
| `四足机器人/硬件/` | `uploads/hardware/` | 硬件资料 |
| `四足机器人/软件/` | `uploads/software/` | 软件 |
| `四足机器人/运动控制/` | `uploads/control/` | 运动控制 |

跳过：所有 ` 2` 后缀的副本目录、zip 文件

## 实现方式

编写 Python 播种脚本 `scripts/seed_opensource_robots.py`：

1. 定义机器人清单（brand, model_name, description, 源路径映射）
2. 遍历清单，为每个机器人：
   a. 创建 `data/robot-assets/{id}/uploads/` 目录结构
   b. 按映射规则复制文件（应用去重过滤）
   c. 插入 `RobotModel` 数据库记录
   d. 为每个文件插入 `RobotAsset` 记录
3. 打印汇总报告（每个机器人的文件数、总大小）

脚本特性：
- 幂等：重跑不会重复创建（按 brand + model_name 判断是否已存在）
- dry-run 模式：`--dry-run` 只打印计划，不执行
- 使用 `shutil.copytree` / `shutil.copy2` 保留文件元数据

## 不做的事

- 不触发 AI 分析管线（导入后手动触发）
- 不删除源文件夹（用户手动确认后删除）
- 不修改已有 Robot 1/2/3 的数据
- 不创建 TeacherRobotBinding（系统内置用 shared 可见性）

## 验收标准

1. `data/robot-assets/` 下新增 4-11 共 8 个目录
2. 数据库 `robot_models` 表新增 8 条记录
3. 数据库 `robot_assets` 表为每个上传文件创建记录
4. 去重生效：无 `(1)`, `(2)`, ` 2` 副本，无冗余 zip
5. 脚本可重跑（幂等）
