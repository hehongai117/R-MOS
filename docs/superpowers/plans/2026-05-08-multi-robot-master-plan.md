# R-MOS 多机器人可插拔平台 — 总控计划

> **设计文档:** `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md`
> **创建日期:** 2026-05-08
> **最后更新:** 2026-05-08

---

## Phase 总览

| Phase | 名称 | Task 数 | 依赖 | 状态 |
|-------|------|---------|------|------|
| 0 | 数据模型 + 存储 + 迁移基础 | 10 | 无 | ✅ 已完成 |
| 1 | 文件上传 + 机器人完整 API | 6 | Phase 0 | ⬚ 未开始 |
| 2 | 教师前端（知识库 + 机器人管理） | 8 | Phase 1 | ⬚ 未开始 |
| 3 | AI 分析管线 | 7 | Phase 1 | ⬚ 未开始 |
| 4 | 学生前端（机器人选择 + 上下文切换） | 6 | Phase 2 | ⬚ 未开始 |
| 5 | 3D 查看器动态加载 | 5 | Phase 1, Phase 4 | ⬚ 未开始 |
| 6 | 共享市场（授权引用 + 同步） | 5 | Phase 2 | ⬚ 未开始 |

**总计:** 47 Tasks（Phase 0 已完成 10，剩余 37）

---

## 依赖关系图

```
Phase 0 (✅ 已完成)
  │
  ├──→ Phase 1（文件上传 + 完整 API）
  │       │
  │       ├──→ Phase 2（教师前端）
  │       │       │
  │       │       ├──→ Phase 4（学生前端）
  │       │       └──→ Phase 6（共享市场）
  │       │
  │       ├──→ Phase 3（AI 分析管线）
  │       │
  │       └──→ Phase 5（3D 查看器）← 也依赖 Phase 4
```

**关键路径:** Phase 0 → 1 → 2 → 4（学生能用的最短路径）

**可并行:** Phase 2 完成后，Phase 3/4/6 可以并行推进；Phase 5 需要 Phase 1+4 都完成

---

## Phase 0: 数据模型 + 存储 + 迁移基础 ✅

> 详细计划: `docs/superpowers/plans/2026-05-07-multi-robot-phase0.md`

| # | Task | 状态 |
|---|------|------|
| 0.1 | RobotModel + TeacherRobotBinding ORM 模型 | ✅ |
| 0.2 | RobotAsset + AnalysisTask ORM 模型 | ✅ |
| 0.3 | 扩展现有模型（SOP/KnowledgeDocument/FaultSOPMapping 加 robot_model_id） | ✅ |
| 0.4 | Alembic 迁移脚本 | ✅ |
| 0.5 | FileStorageService 抽象 + LocalFileStorage 实现 | ✅ |
| 0.6 | RobotModel Pydantic Schemas | ✅ |
| 0.7 | 基础 Robot CRUD API（创建/列表/详情/更新/删除） | ✅ |
| 0.8 | atom01 数据迁移脚本 | ✅ |
| 0.9 | 资产文件 API 端点（路径遍历防护 + 鉴权） | ✅ |
| 0.10 | 前端 robots.ts 支持动态加载 | ✅ |

**产出文件:**
- `r-mos-backend/app/models/robot_model.py`, `robot_asset.py`, `analysis_task.py`
- `r-mos-backend/app/schemas/robot_model.py`
- `r-mos-backend/app/api/v1/endpoints/robots.py`
- `r-mos-backend/app/services/storage/file_storage.py`
- `r-mos-backend/scripts/migrate_atom01.py`
- `r-mos-frontend/src/config/robots.ts`

---

## Phase 1: 文件上传 + 机器人完整 API

> **目标:** 教师能通过 API 上传文件、触发分析、管理机器人发布状态
> **前置:** Phase 0
> **预估 Task:** 6

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 1.1 | 文件上传端点 | `robots.py`, `file_storage.py`, `robot_asset.py` | `POST /robots/{id}/upload` 支持 PDF/CAD/GLB 批量上传，存入 `data/robot-assets/`，创建 RobotAsset 记录 |
| 1.2 | 上传校验与限制 | `robots.py`, `schemas/robot_model.py` | 文件类型白名单、单文件 ≤200MB、总资产 ≤2GB、文件名清理 |
| 1.3 | 分析任务 API | `robots.py`, `schemas/analysis_task.py`(新) | `POST /robots/{id}/analyze` 创建 AnalysisTask，`GET /robots/{id}/analysis-tasks` 查询状态 |
| 1.4 | 发布/取消发布 API | `robots.py` | `PUT /robots/{id}/publish`，校验 status 状态机（draft→ready），只有 owner/admin 可操作 |
| 1.5 | 共享状态 API | `robots.py` | `PUT /robots/{id}/visibility`，切换 private/shared，只有 owner/admin 可操作 |
| 1.6 | 完善 API 测试 | `tests/test_api_robots.py` | 补全 CRUD + 上传 + 发布 + 权限隔离的集成测试 |

---

## Phase 2: 教师前端（知识库 + 机器人管理）

> **目标:** 教师在前端完成：添加机器人 → 上传资料 → 查看分析状态 → 发布
> **前置:** Phase 1
> **预估 Task:** 8

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 2.1 | 机器人 API 客户端 | `api/robots.ts`(新) | Axios 封装所有 `/robots` 端点 |
| 2.2 | 机器人管理 Store | `store/robotStore.ts`(新) | Zustand store：机器人列表、当前选中、CRUD 操作 |
| 2.3 | 机器人列表侧边栏 | `components/RobotSidebar.tsx`(新) | 左侧栏展示自有/引用/分析中机器人，点击切换 |
| 2.4 | 添加机器人对话框 | `components/AddRobotDialog.tsx`(新) | 表单：品牌、型号、版本、描述 |
| 2.5 | 文件上传组件 | `components/FileUploader.tsx`(新) | 拖拽上传 PDF/CAD/GLB，进度条，文件类型校验 |
| 2.6 | 知识库页面改造 | `pages/KnowledgePage.tsx` | 整合机器人侧边栏 + 按 robot_model_id 过滤内容 |
| 2.7 | 分析状态面板 | `components/AnalysisStatusPanel.tsx`(新) | 展示 AnalysisTask 状态，轮询/WebSocket 更新 |
| 2.8 | 发布控制 UI | 集成到知识库页面 | 发布/取消发布按钮、共享开关、状态徽标 |

---

## Phase 3: AI 分析管线

> **目标:** 上传 PDF 后自动提取 SOP/故障码/知识文档；CAD 文件转 GLB
> **前置:** Phase 1（上传接口 + AnalysisTask 记录）
> **可与 Phase 2 并行**
> **预估 Task:** 7

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 3.1 | 分析任务调度器 | `services/analysis/scheduler.py`(新) | 从 pending 队列取任务，按类型分发到不同处理器 |
| 3.2 | PDF 文档切片器 | `services/analysis/pdf_extractor.py`(新) | PDF → 文本切片 → knowledge_document (generation_status=ai_draft) |
| 3.3 | SOP 提取器 | `services/analysis/sop_extractor.py`(新) | 从文本中提取维保步骤 → SOP 草稿 (generation_status=ai_draft) |
| 3.4 | 故障码提取器 | `services/analysis/fault_extractor.py`(新) | 从文本中提取故障码/症状 → fault_sop_mapping 记录 |
| 3.5 | CAD → GLB 转换器 | `services/analysis/cad_converter.py`(新) | STEP/STP → GLB 转换 (OpenCascade/trimesh)，质量检查 |
| 3.6 | 装配清单生成器 | `services/analysis/manifest_generator.py`(新) | 解析 GLB 节点树 → assembly_manifest JSON 草稿 |
| 3.7 | 后台 Worker 启动 | `services/analysis/worker.py`(新), `main.py` | 后台异步任务执行器，状态更新 + 错误处理 |

---

## Phase 4: 学生前端（机器人选择 + 上下文切换）

> **目标:** 学生能看到教师配置的机器人列表，选择后全局上下文切换
> **前置:** Phase 2（教师已发布机器人可用）
> **预估 Task:** 6

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 4.1 | 学生机器人列表 API | `robots.py` | `GET /students/{id}/robots` 返回绑定教师名下已发布的机器人 |
| 4.2 | 机器人上下文 Store | `store/robotContextStore.ts`(新) | 全局当前机器人上下文，持久化到 localStorage |
| 4.3 | 机器人选择卡片 | `components/RobotCards.tsx`(新) | Dashboard 上的机器人卡片列表（品牌、型号、缩略图） |
| 4.4 | Dashboard 页面改造 | `pages/DashboardPage.tsx` | 多机器人时显示选择卡片，单机器人时自动进入 |
| 4.5 | SOP/故障场景过滤 | 多个页面 | SOP 列表、故障场景、AI 助手检索范围按 robot_model_id 过滤 |
| 4.6 | 上下文切换导航 | `components/Layout/` | 顶部导航显示当前机器人名称，支持切换 |

---

## Phase 5: 3D 查看器动态加载

> **目标:** 3D 查看器从 API 动态加载模型，替代硬编码 atom01 路径
> **前置:** Phase 1（资产 API）+ Phase 4（机器人上下文）
> **预估 Task:** 5

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 5.1 | 动态 manifest 加载 | `config/robots.ts`, 3D 组件 | 从 API 获取 assembly_manifest 替代静态 import |
| 5.2 | GLB 模型动态加载 | 3D 查看器组件 | 从 `/robots/{id}/assets/` 加载 GLB 替代 `public/models/` |
| 5.3 | 加载状态与错误处理 | 3D 查看器组件 | 加载进度条、模型不存在兜底、加载失败提示 |
| 5.4 | 监控面板适配 | `pages/MonitorPage.tsx` | 关节配置 + 监控点位按 robot_model_id 动态加载 |
| 5.5 | 删除硬编码 atom01 静态文件 | `public/models/` | 迁移验证通过后删除 1.6GB 静态文件，项目瘦身 |

---

## Phase 6: 共享市场（授权引用 + 同步）

> **目标:** 教师浏览共享库、一键引用其他教师的机器人、源头更新自动同步
> **前置:** Phase 2（教师前端 + 共享状态 API）
> **可与 Phase 4/5 并行**
> **预估 Task:** 5

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 6.1 | 共享库 API | `robots.py` | `GET /robots/shared` 浏览共享库，支持品牌/型号搜索 |
| 6.2 | 引用绑定 API | `robots.py` | `POST /robots/{id}/bind` 创建 shared_ref 绑定，`DELETE` 取消 |
| 6.3 | 共享库浏览页面 | `pages/SharedRobotsPage.tsx`(新) | 卡片式浏览共享机器人，3D 预览、SOP 列表 |
| 6.4 | 引用管理 UI | 集成到知识库页面 | 引用标记 (🔗)、取消引用、同步状态显示 |
| 6.5 | 同步与权限保障 | 服务层 | 引用方只读、源头更新自动可见、owner 删除时级联处理 |

---

## 推荐执行顺序

```
Week 1:  Phase 1（文件上传 + 完整 API）
Week 2:  Phase 2（教师前端）+ Phase 3 前半（PDF 提取）并行
Week 3:  Phase 3 后半（CAD 转换）+ Phase 4（学生前端）
Week 4:  Phase 5（3D 动态加载）+ Phase 6（共享市场）
```

**里程碑检查点:**
- Phase 1 完成后：API 可用，可以 Postman/curl 验证全流程
- Phase 2 完成后：教师可在前端完成添加机器人 → 上传 → 发布
- Phase 4 完成后：学生可选择机器人并使用
- Phase 5 完成后：删除 1.6GB 静态文件，项目瘦身

---

## 会话恢复指引

新对话开始时，按以下顺序获取上下文：

1. 读 `CLAUDE.md` — 项目架构和技术规范
2. 读本文件 — Phase 总览表确认当前进度
3. 读当前 Phase 的详细计划文件 — 具体 Task 和步骤
4. 读设计文档 `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md` — 如需确认设计决策

**每完成一个 Phase，更新本文件的状态列。**
