# R-MOS 多机器人可插拔平台设计

> **日期:** 2026-05-07
> **状态:** 已确认
> **目标:** 将 R-MOS 从单机器人硬编码项目改造为多机器人可插拔平台，支持教师上传机器人资料、AI 自动分析、教师间授权共享

---

## 1. 背景与动机

当前 R-MOS 围绕 ATOM-01 单一机器人硬编码：
- 1.6GB 零件模型在前端 `public/models/` 目录
- 3D 查看器、SOP、知识库、故障映射全部绑定 atom01
- 不同学校采购的机器人品牌型号不同，无法复用同一套系统

**目标状态：** 教师上传机器人原始资料（PDF、CAD），AI 自动解析生成结构化数据（SOP、知识文档、故障码、装配清单），教师校准后发布。教师间可授权共享，学生看到的是绑定教师配置好的机器人环境。

## 2. 核心架构：知识库驱动 + 机器人目录

以现有知识库为核心，新增轻量 `RobotModel` 目录表作为索引。知识库是教师操作的主入口，所有资料通过 `robot_model_id` 关联。

### 2.1 系统流程

```
教师上传文件（PDF/CAD）
    → 存入知识库（knowledge_document）
    → AI 分析管线（异步后台任务）
    → 生成结构化数据：SOP / 故障码 / 装配清单 / 3D 模型资产
    → 教师校准审核（所有 AI 生成内容均为 draft 状态）
    → 发布上线（学生可见）
    → 可选：设为"共享"供其他教师引用
```

### 2.2 方案选型理由

对比过「RobotPackage 中心化」方案（所有资料打包为一个独立包），选择「知识库驱动」方案，原因：
- 复用现有 `knowledge_document` + `SOP` 表，加 `robot_model_id` 外键即可关联
- 教师操作入口就是知识库页面，上传 → 分析 → 校准流程自然
- 改动最小，能最快跑起来

## 3. 数据模型

### 3.1 新增表

```
RobotModel（机器人目录）
├── id: UUID
├── brand: str                      # 品牌（如 "优必选"、"宇树"、"R-MOS"）
├── model_name: str                 # 型号（如 "Walker X"、"H1"、"ATOM-01"）
├── version: str                    # 版本号
├── owner_teacher_id: FK → User     # 创建者教师（null 表示系统内置）
├── visibility: enum                # private | shared
├── status: enum                    # draft | analyzing | ready
├── description: text               # 机器人描述
├── thumbnail_path: str             # 缩略图路径
├── created_at, updated_at
```

```
TeacherRobotBinding（教师选配表）
├── id: UUID
├── teacher_id: FK → User
├── robot_model_id: FK → RobotModel
├── binding_type: enum              # owner | shared_ref
├── created_at
├── UNIQUE(teacher_id, robot_model_id)
```

```
RobotAsset（机器人资产文件）
├── id: UUID
├── robot_model_id: FK → RobotModel
├── asset_type: enum                # model_glb | manifest | thumbnail | upload_original
├── file_path: str                  # 相对存储路径
├── file_size: int                  # 字节
├── metadata: JSONB                 # 格式、顶点数、节点数等
├── created_at
```

```
AnalysisTask（AI 分析任务）
├── id: UUID
├── robot_model_id: FK → RobotModel
├── task_type: enum                 # pdf_extract | cad_parse | sop_generate | full
├── status: enum                    # pending | running | completed | failed
├── input_document_ids: ARRAY       # 输入文档 ID 列表
├── output_summary: JSONB           # 分析结果摘要
├── error_message: text             # 失败原因
├── created_at, completed_at
```

### 3.2 现有表扩展

| 表 | 新增字段 | 说明 |
|----|---------|------|
| `knowledge_document` | `robot_model_id: FK → RobotModel (nullable)` | 关联到机器人 |
| `SOP` | `robot_model_id: FK → RobotModel (nullable)` | 关联到机器人 |
| `fault_sop_mapping` | `robot_model_id: FK → RobotModel (nullable)` | 关联到机器人 |
| `knowledge_document` | `generation_status: enum (manual \| ai_draft \| published)` | 区分 AI 生成与人工上传 |
| `SOP` | `generation_status: enum (manual \| ai_draft \| published)` | 同上 |

所有新增 `robot_model_id` 字段允许 null，向后兼容旧数据。

## 4. AI 分析管线

### 4.1 文本类分析（PDF/Word → 结构化数据）

```
上传 PDF/Word 手册
├── 步骤1: 文档切片 → 存入 knowledge_document（generation_status = ai_draft）
├── 步骤2: 提取故障码和症状 → 生成 fault_sop_mapping
└── 步骤3: 提取维保步骤 → 生成 SOP 草稿（generation_status = ai_draft）
```

- 走现有 DeepSeek/MiniMax LLM 链路
- 所有生成内容为 `ai_draft` 状态，教师确认后改为 `published`

### 4.2 3D 模型分析（CAD → GLB + 装配清单）

```
上传 CAD 文件
├── 步骤1: 格式检测 + 校验（文件是否损坏、格式是否支持）
├── 步骤2: 转换为 GLB（OpenCascade / trimesh）
├── 步骤3: 自动质量检查
│     ├── 顶点数/面数是否在合理范围
│     ├── 模型尺寸是否合理（非零、非异常大）
│     ├── 节点树是否解析成功（节点数 > 0）
│     └── 纹理/材质是否丢失
├── 步骤4: 生成缩略图预览
└── 步骤5: 解析节点树 → 生成 assembly_manifest 草稿
```

- CAD 格式转换用 OpenCascade 等开源工具，不走大模型
- 采用**半自动 + 人工校准**模式：AI 先生成草稿，教师在界面上修正（重命名零件、调整层级、标注关键关节）

### 4.3 3D 模型上传要求

| 项目 | 要求 |
|------|------|
| 推荐格式 | GLTF/GLB（直接可用，无需转换） |
| 支持转换 | STEP/STP（通用 CAD 交换格式，转换可靠） |
| 有条件支持 | STL（仅几何，无层级信息，需人工补充装配关系） |
| 不支持 | SLDPRT/SLDASM（SolidWorks 私有格式，需用户先导出为 STEP） |
| 文件大小限制 | 单文件 ≤ 200MB，单个机器人总资产 ≤ 2GB |
| 命名规范建议 | 节点/零件用有意义的名称，避免 Part1、Body2 等无意义命名 |

### 4.4 兜底策略

| 场景 | 处理 |
|------|------|
| 转换失败 | 标记 `conversion_failed`，提示教师导出为 GLTF 后重新上传 |
| 转换成功但质量差 | 标记 `needs_review`，教师在 3D 预览界面确认 |
| LLM 提取结果不理想 | 教师在校准界面手动修改，或重新触发分析 |

### 4.5 触发机制

- 上传完成后自动创建 `AnalysisTask`（status = pending）
- 后台 worker 异步执行，完成后通知教师
- 教师可离开页面，回来后查看分析结果

## 5. 教师操作流程

### 5.1 流程一：创建新机器人

```
① 知识库页面点击"添加机器人" → 填写品牌、型号
② 上传资料 → 拖拽 PDF/CAD 文件，支持批量上传
③ AI 分析中 → 进度条 + 状态提示，可离开页面
④ 校准审核 → 审核 SOP 草稿、校准 3D 模型节点树
⑤ 发布上线 → 学生可见，可选设为"共享"
```

### 5.2 流程二：从共享库选配

```
① 浏览共享机器人库 → 按品牌/型号搜索
② 查看详情 → 3D 预览、SOP 列表、知识文档
③ 一键添加 → 引用关联（非复制），源头更新自动同步
```

### 5.3 教师知识库页面布局

- **左侧栏：** 机器人列表，区分自有（✅）、分析中（⏳）、引用（🔗）
- **右侧内容区：** Tab 切换 — 知识文档 / SOP / 故障码 / 3D 模型 / 原始文件
- **状态标记：** 已发布（绿色）、待审核/AI 草稿（黄色）、分析中（蓝色）

### 5.4 共享机制

- 授权共享：教师可将自有机器人设为 `visibility = shared`
- 引用关系：其他教师通过 `TeacherRobotBinding(binding_type = shared_ref)` 关联
- 数据不复制：引用方看到的就是源头数据，源头更新自动可见
- 权限控制：只有 owner 可以编辑资料、修改共享状态

## 6. 学生端体验

### 6.1 变化原则

学生不需要感知"多机器人"复杂性，只看到教师配置好的结果。

### 6.2 具体变化

| 场景 | 行为 |
|------|------|
| 教师只配 1 个机器人 | 学生无感知，体验与现在完全一致 |
| 教师配了多个机器人 | Dashboard 显示机器人卡片列表，点击选择后进入 |
| 选择机器人后 | 全局上下文切换：SOP、故障场景、3D 模型、AI 助手知识库全部跟着变 |

### 6.3 上下文切换影响范围

- 3D 查看器 → 加载对应 RobotModel 的 GLB 模型
- SOP 列表 → 只显示 `robot_model_id` 匹配的 SOP
- 故障场景 → 只显示对应故障码
- AI 助手 → 检索范围限定在对应机器人的知识库
- 实时监控 → 加载对应机器人的关节配置和监控点位

## 7. 存储与文件管理

### 7.1 目录结构

```
/data/robot-assets/
  └── {robot_model_id}/
        ├── uploads/          # 原始上传文件（PDF、CAD）
        ├── models/           # 转换后的 GLB 模型
        ├── manifests/        # 装配清单等 JSON
        └── thumbnails/       # 缩略图预览
```

### 7.2 接口设计

新增 `FileStorageService`：
- `upload(robot_model_id, file, asset_type) → RobotAsset`
- `download(robot_model_id, asset_path) → FileResponse`
- `delete(robot_model_id, asset_id) → void`
- `list(robot_model_id, asset_type?) → [RobotAsset]`

内部实现先用本地磁盘（`LocalFileStorage`），接口兼容未来切换 OSS（`OSSFileStorage`）。

### 7.3 前端资产加载

- 现在：`/public/models/robots/atom01/base_link.glb`（硬编码静态路径）
- 改后：`GET /api/v1/robots/{robot_model_id}/assets/models/base_link.glb`（API 动态路由）

### 7.4 与 git 的关系

- `/data/robot-assets/` 加入 `.gitignore`
- 现有 `public/models/` 下 1.6GB 文件在迁移后删除
- 项目体积从 ~1.7GB 降到几十 MB

## 8. atom01 迁移策略

现有 ATOM-01 作为"第一个 RobotModel"无损迁入新架构。

### 8.1 迁移步骤

```
1. 创建 RobotModel 记录
   brand: "R-MOS", model_name: "ATOM-01", status: "ready"
   owner_teacher_id: null（系统内置）

2. 迁移文件
   public/models/robots/atom01/*.glb     →  /data/robot-assets/{id}/models/
   public/models/parts/*                 →  /data/robot-assets/{id}/models/parts/
   assembly_manifest.json                →  /data/robot-assets/{id}/manifests/

3. 迁移数据库记录
   现有 SOP             → 补上 robot_model_id
   现有 knowledge_document → 补上 robot_model_id
   现有 fault_sop_mapping  → 补上 robot_model_id

4. 前端适配
   Viewer3D 组件从硬编码路径 → 读取 API 返回的资产 URL
   partsManifest.ts 从静态导入 → 从 API 动态获取

5. 兼容保障
   数据库迁移脚本自动执行步骤 1-3
   robot_model_id 字段允许 null（向后兼容）
   ATOM-01 作为默认 fallback RobotModel
```

### 8.2 迁移原则

迁移完成后，现有功能的表现和现在完全一样，只是底层从硬编码变成了数据驱动。

## 9. 角色与权限

不引入新角色，在现有三级角色基础上扩展：

| 操作 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 创建 RobotModel | ✅ | ✅ | ❌ |
| 上传资料 | ✅ | ✅（自有机器人） | ❌ |
| 校准审核 AI 结果 | ✅ | ✅（自有机器人） | ❌ |
| 发布/取消发布 | ✅ | ✅（自有机器人） | ❌ |
| 设置共享 | ✅ | ✅（自有机器人） | ❌ |
| 引用共享机器人 | ✅ | ✅ | ❌ |
| 选择/切换机器人 | — | — | ✅ |
| 查看机器人资料 | ✅ | ✅（自有+引用） | ✅（教师已发布的） |

教师即空间：学生绑定教师，看到教师名下所有已发布的 RobotModel。后续可平滑升级为组织模式（加 `org_id` 字段）。

## 10. 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/robots` | 列出当前教师名下的机器人 |
| POST | `/api/v1/robots` | 创建新 RobotModel |
| GET | `/api/v1/robots/{id}` | 获取机器人详情 |
| PUT | `/api/v1/robots/{id}` | 更新机器人信息 |
| DELETE | `/api/v1/robots/{id}` | 删除机器人（仅 owner） |
| POST | `/api/v1/robots/{id}/upload` | 上传资料文件 |
| GET | `/api/v1/robots/{id}/assets/{path}` | 获取资产文件（3D 模型等） |
| POST | `/api/v1/robots/{id}/analyze` | 手动触发 AI 分析 |
| GET | `/api/v1/robots/{id}/analysis-tasks` | 查看分析任务状态 |
| PUT | `/api/v1/robots/{id}/publish` | 发布/取消发布 |
| PUT | `/api/v1/robots/{id}/visibility` | 设置共享状态 |
| GET | `/api/v1/robots/shared` | 浏览共享机器人库 |
| POST | `/api/v1/robots/{id}/bind` | 引用共享机器人 |
| DELETE | `/api/v1/robots/{id}/bind` | 取消引用 |
| GET | `/api/v1/students/{id}/robots` | 学生获取可用机器人列表 |
