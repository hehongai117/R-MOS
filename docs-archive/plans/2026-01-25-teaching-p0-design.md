# Teaching P0 (Ghost Hand + Scaffolding + Evidence + Teacher Console) Design

**Date:** 2026-01-25
**Strategy:** Phased Delivery (C view architecture, A execution)

## Phased Delivery Summary

### Phase 1 (Immediate Execution / 本次执行范围)
- Ghost Hand 基础引导（规则/目标点引导）
- 4 档放权（全引导→半引导→只判错→考试）
- 证据引擎基础版（步骤、用时、错误、提示依赖、完成证据包）
- 教师中控台 MVP（班级看板、作业分发/回收、基础评分报告）

### Phase 2 (Planned Iteration / Backlog)
- Root-cause 诊断解释（诊断链、因果说明）
- 易错点统计（零件/约束/步骤/班级聚合）
- 能力画像（工具/规范/诊断/安全/效率维度）

### Phase 3 (Future Expansion / Roadmap)
- 竞赛对齐（诊断证据提交、隐藏 SOP 模式）
- 诊断路径评分（效率/证据质量/误判成本）

## Goals & Non-goals

**Goals (Phase 1)**
- 教学闭环跑通：引导 → 执行 → 证据 → 中控 → 作业 → 基础评分
- 不侵入现有裁决内核，采用 EvidenceLink 方式解耦教学域与执行域
- 可扩展到 Phase 2/3，无需重构数据库

**Non-goals (Phase 1)**
- CAD/BOM 导入、MTDL、厂家 OTA、复杂故障链裁决
- 完整 Ghost Hand 轨迹回放（Phase 2 扩展）

## Architecture Overview

- **Execution Domain（现有）**：SOP / Task / Event / Snapshot / Score
- **Teaching Domain（新增）**：Class / Course / Enrollment / Assignment / Attempt / GuidancePolicy
- **Evidence Domain（已有+扩展）**：EvidenceBundle / EvidenceItem + EvidenceLink

核心原则：教学域通过 EvidenceLink 与 Task 解耦；裁决/执行域不感知学生与班级。

## Data Model (C View)

### New Entities

**GuidancePolicy**
- `id`, `name`, `base_mode` (teaching|exam)
- `allow_ghost_hand` (bool)
- `allow_hint_button` (bool)
- `show_error_details` (bool)
- `max_retry_count` (int, -1 = unlimited)
- `description`, `created_at`, `updated_at`

**Class**
- `id`, `name`, `term`, `teacher_id`, `metadata`

**Course**
- `id`, `name`, `class_id`, `description`, `schedule`, `metadata`

**Enrollment**
- `id`, `class_id`, `student_id`, `role` (student|assistant)

**Assignment**
- `id`, `class_id`, `course_id`, `title`, `sop_id`, `guidance_policy_id`
- `start_at`, `due_at`, `max_attempts`, `scoring_policy`
- `competition_mode` (bool, Phase 3)
- `hidden_sop` (bool, Phase 3)
- `blind_step_mask` (JSON, Phase 3)

**AssignmentAttempt**
- `id`, `assignment_id`, `student_id`, `task_id`, `evidence_bundle_id`
- `status` (in_progress|completed|graded|abandoned)
- `score` (float)
- `graded_at`, `abandoned_at`, `attempt_index`
- `diagnosis_code` (Phase 2)
- `path_score` (Phase 3)
- `evidence_quality_score` (Phase 3)

**EvidenceLink** (new join table)
- `id`, `bundle_id`, `task_id`, `attempt_id`, `student_id`, `class_id`, `created_at`

### Existing Entities (unchanged)
- `Task` / `Event` / `Snapshot`
- `EvidenceBundle` / `EvidenceItem`

### GuidancePolicy (API shape)
```ts
interface GuidancePolicy {
  id: string
  name: string
  baseMode: 'teaching' | 'exam'
  allowGhostHand: boolean
  allowHintButton: boolean
  showErrorDetails: boolean
  maxRetryCount: number // -1 = unlimited
}
```

### AssignmentAttempt State Machine
- `in_progress` → `completed` → `graded`
- `in_progress` → `abandoned`
- `completed` can be `graded` or remain `completed`

## Evidence Engine (Phase 1)

- Trigger: Task 完成/终止时生成 EvidenceBundle
- 证据内容：步骤时长、错误事件、跳步、提示使用次数、完成证据
- 通过 EvidenceLink 关联 `task_id` + `attempt_id` + `student_id`

## API Design (Phase 1)

- `/api/v1/guidance-policies` (list/get/create)
- `/api/v1/classes` (CRUD)
- `/api/v1/courses` (CRUD)
- `/api/v1/enrollments` (add/remove)
- `/api/v1/assignments` (CRUD)
- `/api/v1/assignments/{id}/attempts` (list/create)
- `/api/v1/attempts/{id}` (get/update status/grade)
- `/api/v1/attempts/{id}/evidence` (get evidence bundle summary)

## Frontend (Phase 1)

- **Student View**: 作业列表 → 启动作业 → 进入 Task 执行
- **Teacher Console**: 班级看板、作业管理、提交列表、基础评分
- **Ghost Hand**: 规则/目标点引导（高亮部件 + 箭头 + 文字提示）
- **Scaffolding**: GuidancePolicy 驱动 UI 行为（提示按钮/错误细节/引导显示）

## Phase 2/3 Backlog (Data Reserved)

- Root-cause 诊断字段、统计聚合、能力画像
- 竞赛模式字段、隐藏 SOP、诊断路径评分

## Risks & Mitigations

- **风险**：教学域与裁决域耦合过深 → **缓解**：EvidenceLink 解耦
- **风险**：Ghost Hand 过度复杂 → **缓解**：Phase 1 仅规则引导
- **风险**：评分一致性 → **缓解**：统一从 Task Report 派生 Attempt 评分
