# 会话交接：多机器人平台 Phase 5

> **日期:** 2026-05-10
> **用途:** 新对话开始时粘贴此文档，快速恢复上下文
> **前置:** Phase 0-4 已全部完成

## 当前状态

- **分支:** `main`（所有工作直接在 main 上）
- **已完成:**
  - Phase 0（数据模型+存储+迁移）✅
  - Phase 1（文件上传+完整API）✅
  - Phase 2（教师前端：知识库 + 机器人管理）✅
  - Phase 3（AI 分析管线）✅
  - Phase 4（学生前端：机器人选择 + 上下文切换）✅
- **下一步:** Phase 5（3D 查看器动态加载）

## Phase 4 产出确认

| Task | 文件 | 状态 |
|------|------|------|
| 4.1 | `app/api/v1/endpoints/students.py` — GET /students/{id}/robots | ✅ 4 tests |
| 4.2 | `src/store/robotContextStore.ts` — Zustand + localStorage 持久化 | ✅ |
| 4.3 | `src/components/RobotCards.tsx` — 机器人选择卡片组件 | ✅ |
| 4.4 | `src/pages/DashboardPage.tsx` — 集成机器人选择 | ✅ |
| 4.5 | 后端 SOP/场景 robot_model_id 过滤 + 前端联动 | ✅ |
| 4.6 | `AppLayout.tsx` 顶部机器人切换导航 | ✅ |

**学生上下文 Store 关键信息:**
- localStorage key: `rmos_current_robot_id`
- `useRobotContextStore()` 导出: `currentRobotId`, `currentRobot`, `availableRobots`, `setCurrentRobot`

## Phase 5 概要

> **目标:** 3D 查看器从 API 动态加载模型，替代硬编码 atom01 静态路径，最终删除 1.6GB 静态文件
> **前置:** Phase 1（资产 API）+ Phase 4（机器人上下文 Store）
> **预估 Task:** 5

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 5.1 | 动态 manifest 加载 | `config/robots.ts`, 3D 组件 | 从 API 获取 assembly_manifest 替代静态 import |
| 5.2 | GLB 模型动态加载 | 3D 查看器组件 | 从 `/robots/{id}/assets/` 加载 GLB 替代 `public/models/` |
| 5.3 | 加载状态与错误处理 | 3D 查看器组件 | 加载进度条、模型不存在兜底、加载失败提示 |
| 5.4 | 监控面板适配 | `pages/MonitorPage.tsx` | 关节配置 + 监控点位按 robot_model_id 动态加载 |
| 5.5 | 删除硬编码 atom01 静态文件 | `public/models/` | 迁移验证通过后删除 1.6GB 静态文件，项目瘦身 |

## 关键文件（Phase 5 需要了解）

### 前端 3D 查看器结构

```
r-mos-frontend/src/components/Viewer3D/
├── Atom01Viewer.tsx          — 主 3D 场景容器（Canvas + 灯光 + 控制器）
├── Atom01Model.tsx           — 加载 GLB 的 Three.js 组件
├── Atom01Interactive.tsx     — 交互模式（爆炸图、部件选择）
├── Atom01AssemblyRenderer.tsx — 装配渲染器
├── runtimeManifest.ts        — 运行时 manifest 适配器（现在从 API 项目资产加载）
├── assemblyManifest.ts       — 静态装配清单（现在硬编码 atom01）
└── constants.ts              — 机器人常量
```

### 静态资产现状

- `public/models/robots/atom01/` — 1.6GB GLB 静态文件（需最终删除）
- `src/config/robots.ts` — 已有 `getRobotModelBase()` 和 `getRobotManifestUrl()` 函数（Phase 0 产出），已支持动态 API URL 生成
- `src/pages/atom01Page.tsx`（或类似路由）— 3D 展示页面

### 后端资产 API

```
GET /api/v1/robots/{robot_id}/assets/{file_path:path}
```
此端点已在 Phase 1 实现，支持 GLB/JSON/PNG 文件服务。

### 机器人上下文

学生选中机器人后，`useRobotContextStore()` 的 `currentRobot.id` 是数字型 robot_model_id，传给 API 端点。`getRobotModelBase(String(robot.id))` 就能得到正确的 asset base URL。

### MonitorPage 现状

`MonitorPage.tsx` 中硬编码了 atom01 的关节映射 (`MONITOR_JOINT_MAP`, `ATOM01_JOINT_META`)，Phase 5.4 需要让这些配置从当前机器人的 manifest 动态读取，或至少提供空状态兜底。

## 后端资产 API 路径规则

- GLB 文件存储在: `data/robot-assets/{robot_model_id}/models/*.glb`
- Manifest JSON: `data/robot-assets/{robot_model_id}/manifests/*.json`
- API 访问: `GET /api/v1/robots/{id}/assets/models/model.glb`
- API 访问: `GET /api/v1/robots/{id}/assets/manifests/assembly.json`

## 用户偏好

- 所有反馈和过程输出使用中文
- 每完成一个 Phase 必须更新 CLAUDE.md + 总控计划 + 记忆文件
- commit message 保持英文
- **所有 Plan 编写使用 Opus 模型，Task 执行使用 Sonnet 模型**
- **所有 Phase 的 Task 使用 Subagent-Driven 执行方式**

## 执行方式

使用 `superpowers:writing-plans` 生成 Phase 5 详细计划（使用 Opus 模型），然后用 `superpowers:subagent-driven-development` 执行（Task 用 Sonnet 模型）。

## 会话恢复步骤

1. 读取 `CLAUDE.md` — 架构和技术规范
2. 读取 `docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md` — 总控计划确认进度
3. 读取本文件 — Phase 5 详细任务
4. 在 `/Users/xuhehong/Desktop/r-mos` 目录下开始编写 Phase 5 详细实施计划（先读前端 3D 组件代码）

## 重要风险提示

- Task 5.5（删除 1.6GB 静态文件）**必须在 5.1-5.4 全部验证通过后**再执行，不可提前删除
- atom01 现有用户（硬编码路由 `/atom01`）需要向后兼容，建议 5.4 之前保留静态 fallback
- 3D 查看器依赖 react-three-fiber + drei，加载大型 GLB 需要 Suspense 边界
