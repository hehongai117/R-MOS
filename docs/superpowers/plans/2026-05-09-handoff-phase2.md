# 会话交接：多机器人平台 Phase 2

> **日期:** 2026-05-09
> **用途:** 新对话开始时粘贴此文档，快速恢复上下文

## 当前状态

- **分支:** `main`（所有工作直接在 main 上）
- **已完成:** Phase 0（数据模型+存储+迁移） + Phase 1（文件上传+完整API）
- **下一步:** Phase 2（教师前端：知识库 + 机器人管理）

## 关键文件（按重要性排序）

1. `CLAUDE.md` — 项目架构 + Phase 状态速查表 + 会话恢复指引
2. `docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md` — 总控计划（7 Phase / 47 Tasks）
3. `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md` — 设计文档（10 节）
4. `docs/superpowers/plans/2026-05-08-multi-robot-phase1.md` — Phase 1 计划（已完成，供参考）

## Phase 2 概要（总控计划中的定义）

> **目标:** 教师在前端完成：添加机器人 → 上传资料 → 查看分析状态 → 发布
> **前置:** Phase 1 ✅
> **预估 Task:** 8

| # | Task | 说明 |
|---|------|------|
| 2.1 | 机器人 API 客户端 | `api/robots.ts` Axios 封装 |
| 2.2 | 机器人管理 Store | Zustand store |
| 2.3 | 机器人列表侧边栏 | 左侧栏组件 |
| 2.4 | 添加机器人对话框 | 表单组件 |
| 2.5 | 文件上传组件 | 拖拽上传 + 进度 |
| 2.6 | 知识库页面改造 | 整合侧边栏 + 按 robot_model_id 过滤 |
| 2.7 | 分析状态面板 | AnalysisTask 状态展示 |
| 2.8 | 发布控制 UI | 发布/共享按钮 + 状态徽标 |

## 后端 API（Phase 1 已实现，前端可直接调用）

```
GET    /api/v1/robots                        — 列出教师名下机器人
POST   /api/v1/robots                        — 创建机器人
GET    /api/v1/robots/{id}                   — 机器人详情
PUT    /api/v1/robots/{id}                   — 更新（品牌/型号/版本/描述）
DELETE /api/v1/robots/{id}                   — 删除
POST   /api/v1/robots/{id}/upload            — 批量文件上传
POST   /api/v1/robots/{id}/analyze           — 触发 AI 分析
GET    /api/v1/robots/{id}/analysis-tasks    — 分析任务列表
PUT    /api/v1/robots/{id}/publish           — 发布/取消发布（toggle）
PUT    /api/v1/robots/{id}/visibility        — 共享/私有切换（toggle）
GET    /api/v1/robots/{id}/assets/{path}     — 资产文件
```

## 执行方式

使用 `superpowers:writing-plans` 生成 Phase 2 详细计划，然后用 `superpowers:subagent-driven-development` 执行。

## 用户偏好

- 所有反馈和过程输出使用中文
- 每完成一个 Phase 必须更新 CLAUDE.md + 总控计划 + 记忆文件
- commit message 保持英文
