# 会话交接：多机器人平台 Phase 4

> **日期:** 2026-05-09
> **用途:** 新对话开始时粘贴此文档，快速恢复上下文
> **前置:** Phase 0-3 已全部完成

## 当前状态

- **分支:** `main`（所有工作直接在 main 上）
- **已完成:**
  - Phase 0（数据模型+存储+迁移）✅
  - Phase 1（文件上传+完整API）✅
  - Phase 2（教师前端：知识库 + 机器人管理）✅
  - Phase 3（AI 分析管线）✅
- **下一步:** Phase 4（学生前端：机器人选择 + 上下文切换）

## Phase 3 产出确认

| Task | 文件 | 状态 |
|------|------|------|
| 3.1 | `app/services/analysis/scheduler.py` | ✅ 4 tests |
| 3.2 | `app/services/analysis/pdf_extractor.py` | ✅ 3 tests |
| 3.3 | `app/services/analysis/sop_extractor.py` | ✅ 3 tests |
| 3.4 | `app/services/analysis/fault_extractor.py` | ✅ 3 tests |
| 3.5 | `app/services/analysis/cad_converter.py` | ✅ 8 tests |
| 3.6 | `app/services/analysis/manifest_generator.py` | ✅ 7 tests |
| 3.7 | `app/services/analysis/worker.py` + main.py | ✅ 3 tests |

**后端测试基线:** Phase 3 新增 31 passed

**Phase 3 重要设计决策（影响 Phase 4）:**
- `robot_asset.py` 中字段名是 `asset_metadata`（不是 `metadata`，已重命名避免 SQLAlchemy 2.0 保留字冲突）
- 故障码提取只存入 `AnalysisTask.output_summary`，不创建 FaultSOPMapping（因 sop_id 外键约束）

## Phase 4 概要

> **目标:** 学生能看到教师配置的机器人列表，选择后全局上下文切换（SOP/故障场景/AI助手全部跟着变）
> **前置:** Phase 2（教师已发布机器人可用）
> **预估 Task:** 6

| # | Task | 涉及文件 | 说明 |
|---|------|---------|------|
| 4.1 | 学生机器人列表 API | `r-mos-backend/app/api/v1/endpoints/robots.py` | `GET /students/{id}/robots` 返回绑定教师名下已发布的机器人 |
| 4.2 | 机器人上下文 Store | `r-mos-frontend/src/store/robotContextStore.ts`(新) | 全局当前机器人上下文，持久化到 localStorage |
| 4.3 | 机器人选择卡片 | `r-mos-frontend/src/components/RobotCards.tsx`(新) | Dashboard 上的机器人卡片列表（品牌、型号、状态） |
| 4.4 | Dashboard 页面改造 | `r-mos-frontend/src/pages/DashboardPage.tsx` | 多机器人时显示选择卡片，单机器人时自动选中 |
| 4.5 | SOP/故障场景过滤 | 多个前端页面 | SOP 列表、故障场景按 robot_model_id 过滤，传递给 API |
| 4.6 | 上下文切换导航 | `r-mos-frontend/src/components/Layout/` | 顶部导航显示当前机器人名称，支持切换 |

## 关键文件（Phase 4 需要了解）

### 后端

- `r-mos-backend/app/api/v1/endpoints/robots.py` — 现有 Robot CRUD + analyze 端点（Phase 1 产出）
- `r-mos-backend/app/models/robot_model.py` — RobotModel(brand/model_name/status/visibility) + TeacherRobotBinding
- `r-mos-backend/app/models/sop.py` — SOP 有 robot_model_id 字段（nullable）
- `r-mos-backend/app/services/authz_guard.py` — ActorContext 含 user_id/roles/permissions

### 前端（已有）

- `r-mos-frontend/src/types/robotModel.ts` — RobotModel TypeScript 类型定义
- `r-mos-frontend/src/api/robots.ts` — 已有教师用机器人 API 客户端（listRobots/createRobot 等）
- `r-mos-frontend/src/store/robotStore.ts` — 已有教师用机器人 Store（Zustand）
- `r-mos-frontend/src/pages/DashboardPage.tsx` — 当前只显示学习进度统计，需要加机器人选择
- `r-mos-frontend/src/components/Layout/` — 顶部导航组件（需要加机器人切换 UI）
- `r-mos-frontend/src/pages/SOPListPage.tsx` — SOP 列表页（Task 4.5 需要加 robot_model_id 过滤）
- `r-mos-frontend/src/pages/ScenarioPickerPage.tsx` — 故障场景选择页（Task 4.5 需要加过滤）

## 后端 API 现状

```
GET  /api/v1/robots              — 列出当前教师的机器人（教师用）
GET  /api/v1/robots/{id}         — 机器人详情（owner 或已发布的共享机器人可见）
POST /api/v1/robots/{id}/analyze — 触发 AI 分析
GET  /api/v1/robots/{id}/analysis-tasks — 查分析任务
```

**Task 4.1 需要新增：**
```
GET  /api/v1/students/{id}/robots  — 学生查看绑定教师名下已发布的机器人
```

查询逻辑：通过 `TeacherRobotBinding` 找到该学生绑定的教师，再找教师名下 `status=READY` 的机器人。

## 前端现有 Store 结构

```typescript
// robotStore.ts（教师用，Phase 2 产出）
interface RobotState {
  robots: RobotModel[]
  selectedRobotId: number | null
  fetchRobots: () => Promise<void>
  ...
}

// 需要新建 robotContextStore.ts（学生用）
interface RobotContextState {
  currentRobotId: number | null        // 当前选中的机器人
  currentRobot: RobotModel | null      // 当前机器人详情
  availableRobots: RobotModel[]        // 可用的机器人列表
  setCurrentRobot: (robot: RobotModel) => void
  fetchAvailableRobots: (studentId: number) => Promise<void>
  // 持久化到 localStorage（key: "rmos_current_robot_id"）
}
```

## 用户偏好

- 所有反馈和过程输出使用中文
- 每完成一个 Phase 必须更新 CLAUDE.md + 总控计划 + 记忆文件
- commit message 保持英文
- **所有 Plan 编写使用 Opus 模型，Task 执行使用 Sonnet 模型，复杂 Task 可用 Opus**
- **所有 Phase 的 Task 使用 Subagent-Driven 执行方式**

## 执行方式

使用 `superpowers:writing-plans` 生成 Phase 4 详细计划（使用 Opus 模型），然后用 `superpowers:subagent-driven-development` 执行（Task 用 Sonnet 模型）。

## 会话恢复步骤

1. 读取 `CLAUDE.md` — 架构和技术规范
2. 读取 `docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md` — 总控计划确认进度
3. 读取本文件 — Phase 4 详细任务
4. 开始编写 Phase 4 详细实施计划
