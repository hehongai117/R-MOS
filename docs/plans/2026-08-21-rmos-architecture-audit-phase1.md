# R-MOS Architecture Audit Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在固定提交上完成 R-MOS 六条关键链路的证据化审查，形成可复查的问题清单、当前软件测试基线和后续修复顺序。

**Architecture:** 审查以 `AGENTS.md` 和 `docs/testing/ACCEPTANCE_CHARTER.md` 为上位规则，在隔离分支先建立当前提交测试基线，再按六条链路从路由、服务、模型、配置和测试反向追踪。静态证据、自动测试、预生产、真机和课堂证据分开裁决；本阶段只修改计划、审查、测试报告与开发记录，不修改应用行为。

**Tech Stack:** FastAPI、SQLAlchemy、PostgreSQL/SQLite 测试夹具、React、TypeScript、Vitest、Vite、Claude Code 只读复核、Git worktree

- 版本：0.1.0
- 日期：2026-08-21
- 基线提交：`cd9422d6fa6d3fc818ade1c45cb932197b95f0dc`
- 审查分支：`codex/architecture-audit-phase1`
- 隔离工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/architecture-audit-phase1`

## 总体边界

- 只允许修改本计划、`docs/audit/*`、`docs/testing/TEST_PLAN.md`、`docs/testing/TEST_REPORT.md` 和 `docs-archive/DEVELOPMENT_LOG.md`。
- 不修改应用代码、测试代码、依赖版本、数据库结构、固定数据库地址或 CORS 配置。
- 数据库门禁测试只允许使用唯一临时编号，并由测试自身清理；不得写入真实业务记录。
- Claude Code 只允许 `Read`、`Glob`、`Grep`，不得修改文件或执行 shell。
- E1 自动测试通过不能替代 E2 预生产、E3 真机、E4 课堂或生产启用结论。
- 发现需要改变权限、审批、审计或数据结构的问题，只记录最小修复方向和复验方法，等待用户另行确认修复阶段。

### Task 1: 固定环境与当前提交测试基线

**Files:**
- Modify: `docs/testing/TEST_REPORT.md`
- Create: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 核对隔离工作区与解释器**

Run:

```bash
git status --short --branch
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python --version
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest --version
```

Expected: 分支为 `codex/architecture-audit-phase1`，工作区干净，解释器和 pytest 可用。

**Step 2: 运行后端全量测试**

Run from `r-mos-backend`:

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m dotenv \
  -f /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env run -- \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest
```

Expected: 当前完整收集范围 0 failed、0 error；若本机数据库被隔离限制阻断，先确认门禁测试清理行为，再在获批范围内复跑。

**Step 3: 运行前端全量测试与构建**

Run from `r-mos-frontend`:

```bash
npm test
npm run build
```

Expected: 测试 0 failed，构建退出码 0；警告单独记录，不改写成失败或忽略。

**Step 4: 记录首次失败与复验链**

把原始失败、根因、处理方式和最终复验结果写入审查报告及当前测试报告；不得只保留最终绿色数字。

### Task 2: 审查身份、角色与对象归属链

**Files:**
- Inspect: `r-mos-backend/app/services/authz_guard.py`
- Inspect: `r-mos-backend/app/services/access_control.py`
- Inspect: `r-mos-backend/app/api/v1/endpoints/{tasks,teaching,robots,students,schools,onboarding,training,training_workbench}.py`
- Inspect: `r-mos-backend/tests/unit/{test_auth_boundary,test_authz_guard_api,test_teaching_api,test_attempt_replay_api}.py`
- Inspect: `r-mos-backend/tests/e2e/test_e2e_cross_role_access.py`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 建立受保护接口清单**

逐路由记录认证依赖、角色/权限依赖、对象归属校验、拒绝状态码和拒绝审计；未看到证据的字段写“未知”，不得推断为已保护。

**Step 2: 反查对象归属实现**

从任务、课堂、学生、学校和机器人读取/写入入口反向追踪到服务层，检查跨学生、跨教师、跨学校、跨机器人访问是否都在服务端拒绝。

**Step 3: 运行定向测试**

Run from `r-mos-backend` with the Task 1 dotenv wrapper:

```bash
python -m pytest \
  tests/unit/test_auth_boundary.py \
  tests/unit/test_authz_guard_api.py \
  tests/unit/test_teaching_api.py \
  tests/unit/test_attempt_replay_api.py \
  tests/e2e/test_e2e_cross_role_access.py -q
```

Expected: 0 failed、0 error；测试未覆盖的对象归属路径仍保持“未验证”。

### Task 3: 审查任务与机器人控制链

**Files:**
- Inspect: `r-mos-backend/app/api/v1/endpoints/{tasks,adapter,robots,student_tasks}.py`
- Inspect: `r-mos-backend/app/services/{task_service,robot_service,preflight_check,snapshot_service}.py`
- Inspect: `r-mos-backend/app/adapters/{base,factory,mock}.py`
- Inspect: `r-mos-backend/tests/{unit/test_task_service,unit/test_task_list_api,unit/test_preflight_check,test_robot_service,unit/test_mock_adapter}.py`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 映射任务状态与机器人绑定**

记录任务创建、分配、执行、停止、完成和报告入口如何绑定用户、SOP、机器人及快照；检查状态变化是否由服务端约束。

**Step 2: 映射动作安全边界**

检查当前适配器类型、预定义动作、现场检查、审批、停止、超时、重复命令和自动重试行为；真实适配器缺失必须写成能力边界。

**Step 3: 运行定向测试**

Run with the Task 1 dotenv wrapper:

```bash
python -m pytest \
  tests/unit/test_task_service.py \
  tests/unit/test_task_list_api.py \
  tests/unit/test_preflight_check.py \
  tests/test_robot_service.py \
  tests/unit/test_mock_adapter.py -q
```

Expected: 0 failed、0 error；模拟适配器测试不得外推成真机通过。

### Task 4: 审查 SOP、裁决、证据与报告链

**Files:**
- Inspect: `r-mos-backend/app/api/v1/endpoints/{sops,tasks,evidence,training,training_workbench,teaching}.py`
- Inspect: `r-mos-backend/app/services/{sop_service,evidence_engine,evidence_enforcement,evidence_service,scoring_service,snapshot_service}.py`
- Inspect: `r-mos-backend/app/models/{sop,task,task_execution,evidence,teaching,training}.py`
- Inspect: `r-mos-backend/tests/{e2e/test_e2e_task_report_evidence,unit/test_evidence_cards_api,unit/test_training_workbench_execution_api,test_sop_three_phase}.py`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 追踪同一对象的一致性**

从步骤提交追踪到证据、步骤结果、评分、快照和报告，核对它们是否绑定同一任务/训练/尝试对象，并检查跨会话和共享对象污染风险。

**Step 2: 检查缺失、损坏与越权证据**

记录服务端对存在性、完整性、访问权限和发布后稳定性的实际校验；前端隐藏不算服务端门禁。

**Step 3: 运行定向测试**

Run with the Task 1 dotenv wrapper:

```bash
python -m pytest \
  tests/e2e/test_e2e_task_report_evidence.py \
  tests/unit/test_evidence_cards_api.py \
  tests/unit/test_training_workbench_execution_api.py \
  tests/test_sop_three_phase.py -q
```

Expected: 0 failed、0 error；报告一致性只对实际覆盖的数据路径作结论。

### Task 5: 审查 AI、审批与审计链

**Files:**
- Inspect: `r-mos-backend/app/api/v1/endpoints/{agent,agent_v2,ai_commands,approvals,audit,skills}.py`
- Inspect: `r-mos-backend/app/services/{approval_service,approval_queue,tool_executor,audit_event_service,policy_matrix}.py`
- Inspect: `r-mos-backend/app/services/policy/risk_scorer.py`
- Inspect: `r-mos-backend/tests/unit/{test_agent_authz,test_audit_events_api,test_deny_audit_entrypoint_gate,test_skill_governance_api,test_tool_executor_service}.py`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 追踪写操作门禁**

从 AI 请求追踪到风险分级、审批创建、批准/拒绝、工具执行和副作用，核对 `risk_level >= medium`、教师确认、过期/变更状态和学生自批拒绝。

**Step 2: 追踪审计与引用**

核对命令、工具调用、审批和结果是否由同一 `trace_id` 串联；拒绝是否记录真实资源编号；引用是否由服务端验证存在和可访问。

**Step 3: 运行定向测试**

Run with the Task 1 dotenv wrapper:

```bash
python -m pytest \
  tests/unit/test_agent_authz.py \
  tests/unit/test_audit_events_api.py \
  tests/unit/test_deny_audit_entrypoint_gate.py \
  tests/unit/test_skill_governance_api.py \
  tests/unit/test_tool_executor_service.py -q
```

Expected: 0 failed、0 error；AI 直接真机动作和绕过审批写入允许次数均为 0。

### Task 6: 审查遥测与实时通道链

**Files:**
- Inspect: `r-mos-backend/app/api/v1/endpoints/websocket.py`
- Inspect: `r-mos-backend/app/services/websocket_manager.py`
- Inspect: `r-mos-backend/app/services/llm/telemetry_context_builder.py`
- Inspect: `r-mos-frontend/src/hooks/useWebSocket.ts`
- Inspect: `r-mos-backend/tests/e2e/test_agent_diagnosis_flow.py`
- Inspect: `r-mos-backend/tests/unit/test_telemetry_context_builder.py`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 映射连接与订阅授权**

记录连接认证、机器人编号来源、订阅权限、广播目标、断线和重连行为，检查跨机器人消息是否有服务端隔离。

**Step 2: 运行现有定向测试**

Run with the Task 1 dotenv wrapper:

```bash
python -m pytest \
  tests/e2e/test_agent_diagnosis_flow.py::test_websocket_telemetry_protocol_is_consistent \
  tests/unit/test_telemetry_context_builder.py -q
```

Expected: 0 failed、0 error；若没有认证与跨机器人隔离测试，链路状态不得写 PASS。

### Task 7: 审查部署、恢复与交付链

**Files:**
- Inspect: `r-mos-backend/app/core/config.py`
- Inspect: `r-mos-backend/main.py`
- Inspect: `docker-compose.yml`
- Inspect: `r-mos-backend/Dockerfile`
- Inspect: `r-mos-frontend/Dockerfile`
- Inspect: `r-mos-frontend/nginx.conf`
- Inspect: `r-mos-backend/scripts/{run_dev,run_gate2_smoke,run_phase3_regression}.sh`
- Inspect: `docs/plans/2026-08-10-rmos-single-school-five-robot-deployment-rollback-v0.1.0.md`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 核对配置、镜像和运行入口**

记录生产校验、密钥、调试开关、镜像固定方式、资产持久化、备份恢复、离线能力和依赖健康检查。

**Step 2: 读取依赖风险结果**

Run from `r-mos-frontend`:

```bash
npm audit --omit=dev
npm audit
```

Expected: 只记录实际结果；不得执行 `npm audit fix` 或修改依赖。

**Step 3: 裁决高等级证据**

没有当前预生产恢复、断网、性能、真机或课堂证据时，E2 至 E4 和生产启用保持 BLOCKED，`REL-BLOCK-01` 不得清零。

### Task 8: Claude Code 独立只读复核

**Files:**
- Create: `docs/audit/2026-08-21-phase1-claude-code-readonly-evidence-v0.1.0.md`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`

**Step 1: 固定只读边界**

只允许 Claude Code 使用 `Read`、`Glob`、`Grep`；禁止 Bash、写文件和会话保存。调用前后都执行 Git 状态检查。

**Step 2: 分两轮复核**

第一轮检查六条链路是否遗漏 P0/P1/P2；第二轮给出已记录发现，让 Claude 只找证据错误、等级错误和遗漏。每条反馈必须由 Codex 回到代码独立核对。

**Step 3: 保存证据**

记录程序版本、模型、预算、退出码、费用、结构化结果、采纳/拒绝理由和调用前后零改动检查。

### Task 9: 收口报告、验证与提交

**Files:**
- Modify: `docs/audit/README.md`
- Modify: `docs/testing/TEST_PLAN.md`
- Modify: `docs/testing/TEST_REPORT.md`
- Modify: `docs-archive/DEVELOPMENT_LOG.md`
- Modify: `docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`
- Modify: `docs/audit/2026-08-21-phase1-claude-code-readonly-evidence-v0.1.0.md`

**Step 1: 完成发现清单**

每条发现包含编号、链路、事实/推断/未知、P0-P3、证据等级、代码位置、影响、最小处理方向、复验方法和 Claude 独立复核状态。

**Step 2: 同步验收状态**

只把实际完成的 E1 子范围写成 PASS/FAIL；六条链路存在强制缺口时总体状态写 FAIL，缺少外部环境时写 BLOCKED。E2 至 E4 和生产启用保持真实状态。

**Step 3: 执行文档验证**

Run:

```bash
test -f <本计划和两份 Phase 1 审查证据文件>
rg -n <六链路、发现编号、状态、证据等级、基线提交和 REL-BLOCK-01>
git diff --check
git diff --name-only
```

Expected: 链接和必备字段齐全，差异检查退出码 0，变更范围仅包含允许的文档。

**Step 4: 本地提交并停止在推送前**

分别提交计划和最终审查文档；输出提交号。不得执行 `git push`。
