# DEV_PLAN_001｜R-MOS v0.3（Jarvis）开发计划书

> 文档状态：Draft v1.0（阶段 1）
> 生成时间：2026-02-06
> 适用范围：`/Users/xuhehong/Desktop/r-mos`
> 约束来源：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`、`docs/design/DEV_TASK_BRIEFING_001.md`

---

## 1. 项目目标（引用 DEV_TASK_BRIEFING_001）

本计划以 `docs/design/DEV_TASK_BRIEFING_001.md` 为开发入口，目标为三项同时成立：

1. 落地“注册/登录 + RBAC + 对象级权限 + 审计”的权限地基。
2. 落地 Jarvis 最小可用链路（Command → Skill → Approval → Audit → 可回放证据）。
3. 落地“按验收矩阵可回归、按门禁可裁决”的工程节奏（证据可复现、可追溯）。

本计划严格遵守：

- `docs/testing/ACCEPTANCE_CHARTER.md`：验收裁决规则与 Gate 定义。
- `docs/specs/ACCEPTANCE_TEST_MATRIX.md`：测试点与 Test ID 清单。
- 冲突裁决优先级：`DEV_TASK_BRIEFING_001.md > ADR-AI-STACK-001.md > AUTHZ_RBAC_SPEC_FINAL.md > AI_AUTHZ_INTEGRATION_SPEC_REVISED.md > AI_TWIN_AGENT_SPEC_REVISED.md > ACCEPTANCE_TEST_MATRIX.md > HLD_JARVIS_V0_3.md > LLD_TASK_BREAKDOWN_V0_3.md > RUNBOOK.md > PROJECT_MANUAL.md`。

---

## 2. 门禁总览（引用 ACCEPTANCE_CHARTER）

### 2.1 Gate-1（AUTH 基线门禁）

通过判定（全部同时满足）：

1. 认证链路可用（注册/登录/刷新/登出）。
2. RBAC 生效（路由级权限正确）。
3. 对象级权限生效（Read 越权 404，Write 越权 403）。
4. deny 全量审计（含真实 `resource_id`）。
5. 证据可复现并入 `DEVELOPMENT_LOG.md`。

### 2.2 Gate-2（Skill 治理与审批门禁）

通过判定（全部同时满足）：

1. Skill 风险规则生效（RISK-001/002/003）。
2. 写工具审批门控生效（`side_effects` 非空不得绕过审批）。
3. 审计链闭环：`tool_call_pending -> approval_granted/rejected -> tool_call_success/failed`。
4. `trace_id` 在 Command/ToolCall/Approval/Audit 可串联。

### 2.3 Gate-3（Jarvis 最小链路门禁）

通过判定（全部同时满足）：

1. Command 统一入口可跑通教师与学生最小链路。
2. RAG 后过滤与 HTTP 响应码边界正确（RAG 空结果不等于 HTTP 404）。
3. Timeline/Replay 可定位引用并可回放。
4. E2E trace 链完整、指标达标（引用覆盖率、幻觉率、读工具成功率、红队通过率）。

### 2.4 环境硬约束引用（AGENTS / RUNBOOK）

本计划中的命令与环境口径必须与 `AGENTS.md`、`docs/ops/RUNBOOK.md` 保持一致，不使用“示例值”误导执行：

1. `DATABASE_URL` 固定：`postgresql+asyncpg://postgres@localhost:5432/postgres`。
2. CORS 固定允许：`http://127.0.0.1:55173`（不擅改）。
3. Python 仅在 `.venv` 内执行（如 `source .venv/bin/activate`）。
4. 本机 HTTP 调用必须使用 `curl --noproxy 127.0.0.1,localhost`。
5. 代理约束：V2rayN `10808`；如需暂时清理代理变量，仅按 RUNBOOK 指令在当前终端临时处理。

---

## 3. Gate-1 开发计划（M1）

### 3.1 模块清单（对应 LLD A~J）

- A：认证与会话（A-001~A-003）
- B：RBAC + 对象级权限（B-001~B-003）
- C：审计基础（C-001~C-003）

### 3.1.1 Gate-1 进度（✅=证据闭环已完成）

- C-001 ✅
- B-001 ✅
- A-001 ✅
- A-002 ✅
- A-003 ✅
- B-002 ✅
- B-003 ✅
- C-002 ✅
- C-003 ✅

证据来源：`DEVELOPMENT_LOG.md` 对照表（见 `DEVELOPMENT_LOG.md` 的 Gate-1 对照段落）。
对应提交哈希：A-001（`86a988d`、`9a5946d`）、A-002（`d76f469`）、A-003（`545b8cb`、`d5d782a`）、B-001（`b5b9d04`、`d7dd307`）、B-002（`e74ba11`、`4b94e2f`）、B-003（`624482c`、`ac05aa6`）、C-001（`d46386b`、`1f60cad`）、C-002/C-003（`2c2b450`）。
备注：历史 Teaching 头部门控（`X-RMOS-Role/X-User-ID`）仅用于语义证明；本轮已补齐 Bearer + RBAC 路由守卫地基，不再以头部门控作为 B-001 完成依据。

### 3.2 API 清单（路由、权限键、对象级校验点、审计事件）

| 路由 | 权限键 | 对象级校验点 | 审计事件 |
|---|---|---|---|
| `POST /api/v1/auth/register` | 公共路由 | 无 | `register_success` / `register_failed` |
| `POST /api/v1/auth/login` | 公共路由 | 无 | `login_success` / `login_failed` |
| `POST /api/v1/auth/refresh` | 公共路由 | token 撤销/过期校验 | `token_refresh_success` / `token_refresh_failed` |
| `POST /api/v1/auth/logout` | 已登录用户 | refresh token 归属校验 | `logout_success` |
| `GET /api/v1/auth/me` | 已登录用户 | `user_id` 与 token 一致 | `profile_read` |
| `GET /api/v1/admin/users` | `users:read` + admin | 无 | `admin_users_read` / `access_denied` |
| `GET /api/v1/teaching/attempts/{id}` | `assignment_attempts:read` | Student 仅本人；Teacher 仅课程范围；Admin 全量 | `access_denied`（Read 越权对外 404） |
| `PATCH /api/v1/teaching/attempts/{id}` | `assignment_attempts:write` | 同上，写越权返回 403 | `modify_denied` / `attempt_updated` |
| `GET /api/v1/teaching/attempts/{id}/evidence` | `evidence_bundles:read` | 归属与课程范围校验 | `access_denied` |
| `GET /api/v1/audit/events` | `audit_events:read`（admin/auditor） | 仅允许可读角色 | `audit_query` |

### 3.3 数据库迁移清单（表/字段/索引/顺序）

迁移顺序（必须按序执行）：

1. `G1-001`：新建认证基础表
   - 表：`users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `refresh_tokens`
   - 关键字段：`users.email`（唯一）、`refresh_tokens.is_revoked`
   - 索引：
     - `ux_users_email`
     - `ux_roles_name`
     - `ux_permissions_key`
     - `ix_user_roles_user_id`, `ix_user_roles_role_id`

2. `G1-002`：审计表补强
   - 表：`audit_events`（若已有则增量变更）
   - 字段：`decision`, `reason`, `request_meta`, `trace_id`（可空，Gate-2 后转强约束）
   - 索引：`ix_audit_events_actor_created_at`, `ix_audit_events_resource`

3. `G1-003`：对象级访问所需字段补齐（仅在缺失时）
   - 目标表：`assignment_attempts`, `tasks`, `evidence_links` 等
   - 字段：`owner_user_id` / `course_id` / `created_by`（按实际缺口补齐）
   - 索引：`ix_attempt_owner`, `ix_attempt_course`, `ix_task_created_by`

4. `G1-004`：权限种子
   - 初始化角色：`admin`, `teacher`, `student`, `auditor`
   - 初始化权限键：`users:*`, `roles:*`, `permissions:*`, `assignment_attempts:*`, `evidence_bundles:read`, `audit_events:read` 等

### 3.4 验收点映射（精确 Test ID）

- AUTH：`AUTH-T001`, `AUTH-T002`, `AUTH-T003`, `AUTH-T004`, `AUTH-T005`, `AUTH-T006`, `AUTH-T007`, `AUTH-T008`, `AUTH-T009`, `AUTH-T010`, `AUTH-T011`
- AUTHZ（API级）：`AUTHZ-T001`, `AUTHZ-T002`, `AUTHZ-T003`, `AUTHZ-T004`, `AUTHZ-T005`, `AUTHZ-T006`, `AUTHZ-T007`
- 对象级：`OBJ-T001`, `OBJ-T002`, `OBJ-T003`, `OBJ-T004`, `OBJ-T005`, `OBJ-T006`, `OBJ-T007`, `OBJ-T008`, `OBJ-T009`
- 审计关键：`AUDIT-T001`, `AUDIT-T006`

### 3.5 最小回归命令集（可复制）

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
alembic -c alembic.ini upgrade head
pytest tests/unit -q
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/health
```

对象级语义抽检（示例，实际按测试数据替换 token/id）：

```bash
curl --noproxy 127.0.0.1,localhost -H "Authorization: Bearer ${TOKEN_STUDENT_A}" \
  http://127.0.0.1:8000/api/v1/teaching/attempts/${ATTEMPT_B_ID}

curl --noproxy 127.0.0.1,localhost -X PATCH -H "Authorization: Bearer ${TOKEN_STUDENT_A}" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}' \
  http://127.0.0.1:8000/api/v1/teaching/attempts/${ATTEMPT_B_ID}
```

### 3.6 风险与回滚策略

- 风险 1：对象级规则只做路由层，服务层遗漏。
  - 回滚/缓解：保留旧逻辑开关；服务层加统一 `authorize_resource()`；未通过 `OBJ` 用例不合并。
- 风险 2：Read/Write 响应码实现混乱。
  - 回滚/缓解：统一异常映射中间件；失败时回滚到上一版本异常映射。
- 风险 3：迁移导致历史数据不可读。
  - 回滚/缓解：迁移前快照备份；字段增量迁移（先 nullable 再回填）；失败执行 `alembic downgrade -1`。
- 风险 4：权限误拒（合法请求被 403/404 拒绝）。
  - 回滚/缓解：启用“策略回退开关 + 审计比对”；按 `AUTHZ-T005/T006` 与 `OBJ-T001/T003` 复测，定位规则误判后再灰度恢复。

---

## 4. Gate-2 开发计划（M2）

### 4.1 模块清单（对应 LLD A~J）

- D：Skill Registry + Governance（D-001~D-003）
- E：Tool Executor（E-001~E-004）
- F：Approval Service（F-001~F-003）
- G（基础）：Command 状态骨架与 trace 串联（G-001）

### 4.1.x 回归入口扩展项（A-001~A-007）

说明：A-001~A-007 是 Gate-2 的 smoke 回归入口/门禁/证据固化计划项，用于保障 Gate-2 的交付与回归，不属于 D/E/F/G 业务模块清单。

### 4.1.1 Gate-2 进度（模块 D/E/F/G，✅=证据闭环已完成）

- D-001 ✅
- D-002 ✅
- D-003 ⏳
- E-001 ⏳
- E-002 ⏳
- E-003 ⏳
- E-004 ⏳
- F-001 ⏳
- F-002 ⏳
- F-003 ⏳
- G-001 ⏳

### 4.1.2 Gate-2 进度（回归入口/门禁 A-001~A-007，✅=证据闭环已完成）

- A-001 ✅
- A-002 ✅
- A-003 ✅
- A-004 ✅
- A-005 ✅
- A-006 ✅
- A-007 ✅

### 4.2 API 清单（路由、权限键、对象级校验点、审计事件）

| 路由 | 权限键 | 对象级校验点 | 审计事件 |
|---|---|---|---|
| `POST /api/v1/ai/skills` | `skills:write`（建议仅 admin） | 审核前不可执行 | `skill_created` |
| `POST /api/v1/ai/skills/{id}/submit-review` | `skills:write` | 仅发布者/管理员可提交 | `skill_review_submitted` |
| `POST /api/v1/ai/skills/{id}/publish` | `skills:publish`（admin） | 强制校验 RISK-001/002/003 | `skill_published` / `skill_publish_denied` |
| `POST /api/v1/ai/commands` | 已登录 + intent 对应权限 | 写工具进入审批前不可执行 side_effects | `command_created`, `tool_call_pending` |
| `GET /api/v1/ai/approvals` | `approvals:read` | teacher 仅课程范围；auditor 只读 | `approval_query` |
| `POST /api/v1/ai/approvals/{id}/confirm` | `approvals:approve` | auditor 仅可 critical；teacher 仅课程范围 | `approval_granted` / `approval_denied` |
| `POST /api/v1/ai/approvals/{id}/reject` | `approvals:reject` | 同上 | `approval_rejected` |
| `GET /api/v1/audit/events?trace_id=...` | `audit_events:read` | trace 可见性与角色限制 | `audit_query` |

### 4.3 数据库迁移清单（表/字段/索引/顺序）

迁移顺序（必须按序执行）：

1. `G2-001`：Skill 治理数据
   - 表：`skills`, `skill_reviews`, `skill_releases`
   - 关键字段：`skill_id`, `version`, `risk_level`, `side_effects`, `allowlist_resources`, `status`
   - 索引：
     - `ux_skills_skill_version(skill_id, version)`
     - `ix_skills_status_risk(status, risk_level)`

2. `G2-002`：审批数据
   - 表：`approvals`, `approval_policies`
   - 关键字段：`risk_level`, `required_approvers`, `approvals_received`, `status`, `expires_at`, `trace_id`
   - 索引：`ix_approvals_status_expires`, `ix_approvals_trace`, `ix_approvals_resource`

3. `G2-003`：Command/ToolCall 最小闭环
   - 表：`commands`, `command_results`, `ai_tool_calls`
   - 关键字段：`trace_id`, `actor_user_id`, `intent`, `status`, `approval_id`
   - 索引：`ux_commands_trace_id`, `ix_tool_calls_trace_skill`

4. `G2-004`：审计扩展字段
   - 表：`audit_events` 增量字段：`skill_id`, `skill_version`, `tool_call_args`, `side_effects_applied`, `approval_id`
   - 索引：`ix_audit_trace_created(trace_id, created_at)`

5. `G2-005`：策略与约束
   - 数据约束：
     - `side_effects != []` 时 `risk_level != 'low'`
     - critical skill 必须 `feature_flag` 与 `rollback_strategy`

### 4.4 验收点映射（精确 Test ID）

- SKILL：`SKILL-T001`, `SKILL-T002`, `SKILL-T003`, `SKILL-T004`, `SKILL-T005`, `SKILL-T006`, `SKILL-T007`, `SKILL-T008`, `SKILL-T009`, `SKILL-T010`
- APPROVAL：`APPR-T001`, `APPR-T002`, `APPR-T003`, `APPR-T004`, `APPR-T005`, `APPR-T006`, `APPR-T007`, `APPR-T008`, `APPR-T009`, `APPR-T010`, `APPR-T011`, `APPR-T012`
- AGENT（写工具门控相关）：`AGENT-T006`, `AGENT-T007`, `AGENT-T008`, `AGENT-T009`, `AGENT-T010`
- 审计链：`AUDIT-T007`, `AUDIT-T008`

### 4.5 最小回归命令集（可复制）

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
alembic -c alembic.ini upgrade head
pytest tests/unit -q
curl --noproxy 127.0.0.1,localhost "http://127.0.0.1:8000/api/v1/audit/events?trace_id=${TRACE_ID}"
```

审批链路抽检（示例）：

```bash
curl --noproxy 127.0.0.1,localhost -X POST \
  -H "Authorization: Bearer ${TOKEN_TEACHER}" \
  -H "Content-Type: application/json" \
  -d '{"intent":"dispatch","input_text":"创建中级电机故障作业","scope":{"course_id":"'"${COURSE_ID}"'"}}' \
  http://127.0.0.1:8000/api/v1/ai/commands

curl --noproxy 127.0.0.1,localhost -X POST \
  -H "Authorization: Bearer ${TOKEN_TEACHER}" \
  http://127.0.0.1:8000/api/v1/ai/approvals/${APPROVAL_ID}/confirm
```

### 4.6 风险与回滚策略

- 风险 1：写工具绕过审批直接落库。
  - 回滚/缓解：执行器前置硬校验（`approval.status=approved` 才可写）；紧急时全局关闭写技能 feature flag。
- 风险 2：critical 审批组合口径冲突导致验收失败。
  - 回滚/缓解：以 `approval_policies` 配置为准；P0 至少支持 `teacher+auditor`（满足矩阵 `APPR-T005`），并预留可扩展组合。
- 风险 3：Skill 元数据升级破坏兼容。
  - 回滚/缓解：版本不可变，发布失败回滚到上一个 published 版本；新版本灰度启用。
- 风险 4：迁移后索引过慢。
  - 回滚/缓解：高成本索引分批创建；失败先禁用新链路，保留旧读路径。
- 风险 5：审批链断（长期停留 `waiting_approval` 或 trace 断链）。
  - 回滚/缓解：执行“审批补偿任务 + 状态修复脚本”；将命令降级为只读建议模式，待 `APPR-T001/T007/T008` 与 `AUDIT-T008` 通过后恢复写链路。

---

## 5. Gate-3 开发计划（M3）

### 5.1 模块清单（对应 LLD A~J）

- G（完整）：Command 入口与意图编排（G-002~G-003）
- H：RAG 检索与后过滤（H-001~H-004）
- I：Timeline 与引用回放（I-001~I-003）
- J：Eval/Replay/Regression（J-001~J-003）

### 5.2 API 清单（路由、权限键、对象级校验点、审计事件）

| 路由 | 权限键 | 对象级校验点 | 审计事件 |
|---|---|---|---|
| `POST /api/v1/ai/commands`（`explain/replay/highlight/adjust_difficulty/critique`） | 按 intent 映射（如 `tasks:read`, `assignments:write`） | scope 中 `attempt/task/course` 必须做对象级校验 | `command_created`, `tool_call_*` |
| `POST /api/v1/ai/rag/query`（或经 commands 间接调用） | 读权限集合 | 向量候选后过滤，越权仅过滤不泄露 ID | `rag_filter_applied` |
| `GET /api/v1/teaching/attempts/{id}/replay` | `assignment_attempts:read` | Student 仅本人，Teacher 仅课程范围 | `replay_requested` / `access_denied` |
| `POST /api/v1/timelines/generate` | `timelines:write`（建议 teacher/admin） | scope 归属校验 | `timeline_generated` |
| `GET /api/v1/timelines/{id}/alignment` | `timelines:read` | timeline 归属与课程范围 | `timeline_alignment_read` |
| `GET /api/v1/timelines/{id}/locate?ref_id=` | `timelines:read` | `ref_id` 可见性校验 | `timeline_ref_located` / `reference_validation_failed` |
| `POST /api/v1/evidence_cards` | `evidence_bundles:write`（建议 teacher） | attempt 访问范围校验 | `evidence_card_created` |
| `GET /api/v1/ai/replay/{trace_id}` | `audit_events:read` | trace 可见性控制 | `trace_replay_read` |

### 5.3 数据库迁移清单（表/字段/索引/顺序）

迁移顺序（必须按序执行）：

1. `G3-001`：RAG 索引基础（PostgreSQL + pgvector）
   - 扩展：`CREATE EXTENSION IF NOT EXISTS vector`
   - 表：`ai_knowledge_chunks`（`source_type`, `source_id`, `content`, `embedding`, `owner_user_id`, `course_id`, `attempt_id`, `metadata`）
   - 索引：
     - `ivfflat` / `hnsw`（按环境） on `embedding`
     - `ix_chunks_owner_course(owner_user_id, course_id)`

2. `G3-002`：时间轴与对齐
   - 表：`multimodal_timelines`, `timeline_segments`, `alignment_map`, `evidence_cards`
   - 索引：`ix_timeline_scope(scope_type, scope_id)`, `ix_segments_timeline_start`, `ix_alignment_anchor`

3. `G3-003`：多模态原始片段
   - 表：`video_segments`, `audio_segments`, `sensor_streams`, `text_logs`
   - 索引：`ix_video_attempt_ts`, `ix_audio_attempt_ts`, `ix_sensor_channel_ts`, `ix_text_logs_scope_ts`

4. `G3-004`：评估与回放
   - 表：`ai_eval_cases`, `ai_eval_runs`, `ai_eval_metrics`
   - 索引：`ix_eval_runs_timestamp`, `ix_eval_metrics_run_id`

5. `G3-005`：审计与回放收口
   - 确保 AI 路径 `trace_id` 非空（可通过约束/应用层保证）
   - 强制引用可访问性校验失败记录 `reference_validation_failed`

### 5.4 验收点映射（精确 Test ID）

- RAG：`RAG-T001`, `RAG-T002`, `RAG-T003`, `RAG-T004`, `RAG-T005`, `RAG-T006`, `RAG-T007`, `RAG-T008`
- AGENT（读编排与稳定性）：`AGENT-T001`, `AGENT-T002`, `AGENT-T003`, `AGENT-T004`, `AGENT-T005`, `AGENT-T011`, `AGENT-T012`
- TEACHER：`TEACHER-T001`, `TEACHER-T002`, `TEACHER-T003`, `TEACHER-T004`, `TEACHER-T005`, `TEACHER-T006`, `TEACHER-T007`
- STUDENT：`STUDENT-T001`, `STUDENT-T002`, `STUDENT-T003`, `STUDENT-T004`, `STUDENT-T005`, `STUDENT-T006`, `STUDENT-T007`, `STUDENT-T008`, `STUDENT-T009`, `STUDENT-T010`, `STUDENT-T011`
- TIMELINE：`TIMELINE-T001`, `TIMELINE-T002`, `TIMELINE-T003`, `TIMELINE-T004`, `TIMELINE-T005`, `TIMELINE-T006`, `TIMELINE-T007`, `TIMELINE-T008`
- SEC：`SEC-T001`, `SEC-T002`, `SEC-T003`, `SEC-T004`, `SEC-T005`, `SEC-T006`, `SEC-T007`, `SEC-T008`
- EVAL：`EVAL-T001`, `EVAL-T002`, `EVAL-T003`, `EVAL-T004`, `EVAL-T005`, `EVAL-T006`, `EVAL-T007`, `EVAL-T008`, `EVAL-T009`
- E2E：`E2E-T001`, `E2E-T002`, `E2E-T003`, `E2E-T004`, `E2E-T005`, `E2E-T006`, `E2E-T007`, `E2E-T008`

### 5.5 最小回归命令集（可复制）

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
alembic -c alembic.ini upgrade head
bash scripts/run_phase3_regression.sh
curl --noproxy 127.0.0.1,localhost "http://127.0.0.1:8000/api/v1/audit/events?trace_id=${TRACE_ID}"
```

前端最小回归（与 Gate-3 联动）：

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm run build
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm test
```

### 5.6 风险与回滚策略

- 风险 1：RAG 泄露越权信息。
  - 回滚/缓解：强制后过滤与 `deny_count` 审计；一旦出现泄露立即关闭 RAG 对外入口，回退到规则诊断只读路径。
- 风险 2：引用不可回放导致结论不可证。
  - 回滚/缓解：输出前强制引用校验；失败返回 `insufficient_data` 模板。
- 风险 3：时间轴表膨胀与性能下降。
  - 回滚/缓解：冷热分层、按 scope 分区、索引降级策略；必要时停用非关键多模态写入。
- 风险 4：评估指标不达标仍发布。
  - 回滚/缓解：将 `EVAL-T001~T003/T005~T007` 设为发布阻断条件，未达标直接禁止发布。

---

## 6. 执行纪律（强制）

1. 每次只做 1 个最小可验收任务（例如 A-001、B-001、C-001）。
2. 每次任务结束必须更新 `DEVELOPMENT_LOG.md`（命令、输出摘要、PASS/FAIL、风险、下一步）。
3. 每次任务输出必须包含：
   - Read-first Checkpoint
   - Plan（≤5）
   - Executed Commands
   - Diff Summary（`git diff --name-only` + 关键片段）
   - Tests（命令 + 结果）
   - DoD Checklist（绑定 Test ID）
   - Push Gate
4. 不得擅自 `git push`；如需 push，必须先获得用户明确许可。
5. 不得编造测试结果；失败必须给出错误栈与处置动作。
6. 不得绕过审批直接执行 AI 写工具。

---

## 7. 里程碑时间盒与交付物

- M1（Gate-1）：Auth + RBAC + Object-level + Audit 基线
  - 交付：A/B/C 模块可运行、对应 P0 用例证据
- M2（Gate-2）：Skill 治理 + Approval + Tool Executor
  - 交付：D/E/F + G-001、审批链可追溯证据
- M3（Gate-3）：Jarvis 最小链路（RAG + Replay + Timeline + Eval）
  - 交付：G-002~G-003 + H/I/J、E2E 证据与指标达标报告

每个里程碑都必须附带：

1. `git diff --name-only`。
2. 对应 Test ID 的命令与结果摘要。
3. `DEVELOPMENT_LOG.md` 记录。
4. 若涉及验收口径变化，联动更新 `docs/testing/TEST_PLAN.md` 或 `docs/testing/TEST_REPORT.md`。

---

## 8. 证据格式（写入 DEVELOPMENT_LOG.md）

每条记录必须包含：

- `DateTime`
- `Task`
- `Scope (files changed)`
- `Commands Run`
- `Tests`
- `Result`（PASS/FAIL）
- `Risks/Notes`
- `Next Step`

禁止使用“看起来没问题”“应该通过”等非证据化结论。

---

## 9. 计划执行入口

从 Gate-1 的最小任务开始，推荐顺序：

1. C-001（统一审计写入，先落地 deny/allow 统一审计接口）
2. B-001（鉴权/RBAC 守卫与错误映射地基：Read 越权 404，Write 越权 403）
3. A-001（注册接口）
4. A-002（登录接口）
5. A-003（刷新/登出）
6. B-002（对象级权限校验）
7. B-003（auditor 约束）
8. C-002/C-003（审计查询与审批审计闭环）

每完成一个任务即跑最小回归并记录证据，不跨 Gate 并行开发。

---

## 10. Gate-2 A-001 回归入口

新增脚本：`/Users/xuhehong/Desktop/r-mos/r-mos-backend/scripts/run_gate2_smoke.sh`

默认执行（仅 smoke，不依赖服务已启动）：

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && ./scripts/run_gate2_smoke.sh
```

端到端证据模式（可选，需先启动后端）：

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
uvicorn main:app --host 127.0.0.1 --port 18080
```

另开终端：

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && ./scripts/run_gate2_smoke.sh --e2e
```

`--e2e` 模式自动校验 READ/WRITE 越权语义：READ 必须 `404 + ReadAccessDeniedError/READ_ACCESS_DENIED`，WRITE 必须 `403 + WriteAccessDeniedError/WRITE_ACCESS_DENIED`，失败即非零退出。
若提示服务不可达，需先按计划命令启动 `uvicorn main:app --host 127.0.0.1 --port 18080` 后再执行 `--e2e`。
可选参数 `--audit`（需与 `--e2e` 同用）会按 `DATABASE_URL` 连接 Postgres，校验 `audit_events` 至少命中 `read_access_denied` 与 `permission_denied` 两条 deny（AUDIT-T006）。
示例：
`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
`cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && ./scripts/run_gate2_smoke.sh --e2e --audit`
查看帮助：`cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && ./scripts/run_gate2_smoke.sh --help`
帮助输出包含参数说明、前置条件与退出码表。
退出码含义见：`./scripts/run_gate2_smoke.sh --help`

执行约束：
- 脚本内 curl 全部使用 `--noproxy 127.0.0.1,localhost`
- 脚本失败即非零退出码
- 严禁在未获许可时执行 `git push`

回归入口扩展项映射表（A-001~A-007）：

| 编号 | 状态 | 目的 | 命令 | 对应 commit | 证据落点（DEVELOPMENT_LOG 行号范围） |
| --- | --- | --- | --- | --- | --- |
| A-001 | ✅ | 新增 smoke 脚本入口 | `./scripts/run_gate2_smoke.sh` | `d943fff` | `DEVELOPMENT_LOG.md:345-372` |
| A-002 | ✅ | `--e2e` 响应语义自动断言 | `./scripts/run_gate2_smoke.sh --e2e` | `820fddb` | `DEVELOPMENT_LOG.md:373-391` |
| A-003 | ✅ | `--audit` 审计落库断言 | `./scripts/run_gate2_smoke.sh --e2e --audit` | `0814c33` | `DEVELOPMENT_LOG.md:392-410` |
| A-004 | ✅ | 提供 `--help/-h` 帮助入口 | `./scripts/run_gate2_smoke.sh --help` | `ac278dc` | `DEVELOPMENT_LOG.md:411-426` |
| A-005 | ✅ | 退出码“码→含义”说明 | `./scripts/run_gate2_smoke.sh --help` | `4f565dd` | `DEVELOPMENT_LOG.md:427-441` |
| A-006 | ✅ | 补齐 21 并核对 20/21/22/23/24 | `./scripts/run_gate2_smoke.sh --help` | `ec1a31d` | `DEVELOPMENT_LOG.md:442-454` |
| A-007 | ✅ | `--help` 一致性 pytest 门禁并纳入默认 smoke | `pytest -q tests/unit/test_smoke_help_gate.py` | `5a64b4e` | `DEVELOPMENT_LOG.md:455-484` |

Gate-2 后续计划任务（A-007 之后）：

- D-001 ✅：Skill 治理数据迁移 + ORM + 门禁测试（`a743fe5`，证据见 `DEVELOPMENT_LOG.md:485-504`）
- D-002 ✅：Skill 治理 API（技能注册/提审/发布最小闭环）（本次提交，证据见 `DEVELOPMENT_LOG.md:789-808`）
- D-003 ⏳：Skill 风险规则执行与发布门禁加固
- E-001 ⏳：Tool Executor 最小读链路（无副作用工具）
- F-001 ⏳：Approval Service 最小审批流（pending→granted/rejected）
