# AGENTS｜R-MOS Codex 开发强约束（Read-first）
> 权威源：本文件是 Codex 开发规则的唯一真相源（Single Source of Truth）。  
> 镜像：docs/ops/CODEX_RULES.md 必须与本文件一致，但不作为权威源。  
> 适用范围：所有对 r-mos 仓库的开发/测试/文档修改。  
> 生效优先级：AGENTS.md > docs/plans/2026-03-05-review-test-cleanup-execution.md > R-MOS_Review_Test_Cleanup_Plan.md > docs/review/review-checklist.md > docs/testing/backend-test-report.md > docs/testing/TEST_REPORT.md > docs/testing/TEST_PLAN.md > docs/ops/RUNBOOK.md > docs/adr/* > DEVELOPMENT_LOG.md
> “任何任务必须对齐 docs/testing/ACCEPTANCE_CHARTER.md 的门禁与证据要求。”

---

## 0) 当前项目状态快照（2026-03-05）

- 专项执行计划：`docs/plans/2026-03-05-review-test-cleanup-execution.md`
- 源计划文件：`R-MOS_Review_Test_Cleanup_Plan.md`
- 已完成并打标：
  - `R-04-3`（阻塞项修复）
  - `T-01` / `T-02` / `T-03` / `T-04` / `T-05`
- 当前测试基线（最近一次可追溯证据）：
  - 后端基线：`collected 239`，`236 passed, 3 skipped, 0 failed, 0 error`
  - 后端核心 14 服务覆盖率门禁：`378 passed, 1 skipped, 0 failed`，覆盖率 `74.63%`（`>= 70%`）
  - 前端：`npm test`（Vitest）`8 passed`；`npm run build` PASS
- 当前下一步：进入 `T-06`（前端核心组件测试补全）
- 专项批次闭环（每批必须同步）：
  1. 更新 `R-MOS_Review_Test_Cleanup_Plan.md` 勾选状态
  2. 更新 `docs/review/review-checklist.md`
  3. 追加 `DEVELOPMENT_LOG.md`（命令、结果、失败处理）
  4. 输出可复现最小验证命令与结果摘要

---

## 1) Read-first Checkpoint（每次任务开始必须输出并逐条确认）
Codex 每次开始任务前，必须在回复中逐条输出并确认（✅/❌）：

1. ✅ 当前仓库目录：`/Users/xuhehong/Desktop/r-mos`
2. ✅ Python 环境：仅在 `.venv` 内执行（不得用系统 Python）
3. ✅ 代理/网络：
   - 代理：V2rayN `10808`
   - 本机 HTTP 调用：必须 `curl --noproxy 127.0.0.1,localhost`
4. ✅ 服务启动约束：
   - 若任务需要访问前端/后端/API/联调：先说明“需要启动服务”，并给出启动命令与端口
5. ✅ 固定配置（不得擅改）：
   - `DATABASE_URL` 固定
   - CORS 允许 `http://127.0.0.1:55173`
6. ✅ Git 规则：
   - 允许 commit
   - **git push 必须事先获得用户许可（严禁擅自 push）**
7. ✅ 事实源优先级（冲突时按此为准）：
   - docs/plans/2026-03-05-review-test-cleanup-execution.md
   - R-MOS_Review_Test_Cleanup_Plan.md
   - docs/review/review-checklist.md
   - docs/review/service-test-gap-2026-03-05.md
   - docs/testing/backend-test-report.md
   - docs/testing/TEST_REPORT.md
   - docs/testing/TEST_PLAN.md
   - docs/ops/RUNBOOK.md
   - docs/adr/ADR.md
   - DEVELOPMENT_LOG.md

---

## 2) 可以做 / 必须做 / 不能做（硬约束）

### 2.1 可以做
- 改代码、补测试、补文档、跑本地测试、提交 commit（不 push）
- 维护 specs/adr/runbook/test plan/report
- 修复 lint/type/check（若项目已有）

### 2.2 必须做（每个任务都必须满足）
- 变更最小化：只改与任务直接相关的文件
- 变更前后必须给出：
  - `git diff --name-only`
  - 关键差异片段（只截关键段落/关键函数）
- 必须给出可复现命令（可复制）
- 必须跑与变更相关的“最小测试集”，并记录结果（见第 4 节）
- 必须更新 `DEVELOPMENT_LOG.md`（见第 5 节）
- 若属于 Review/Test Cleanup 专项批次：每完成一组必须同步更新计划勾选、review-checklist、DEVELOPMENT_LOG，并输出最小验证命令摘要
- 若变更影响验收：必须同步更新 `docs/testing/TEST_PLAN.md` 或 `TEST_REPORT.md`

### 2.3 不能做（出现即判失败）
- 不能编造测试结果；不能“假设通过”
- 不能跳过鉴权/审批/审计等安全门控（AI/权限相关尤其严格）
- 不能引入新外部依赖/服务而不写 ADR（见第 6 节）
- 不能擅改 DATABASE_URL / CORS 等固定约束
- 不能未经许可执行 `git push`

---

## 3) 标准开发流程（强制步骤）

### 3.1 任务开始（必做）
1. 输出 Read-first Checkpoint（第 1 节）
2. 任务目标（1 句话）
3. 改动边界预测（预计改哪些文件）
4. 验收标准（对应哪些 tests/spec）

### 3.2 实施中（必做）
1. 小步提交：每个 commit 只做一件事
2. 新增/调整 API 或表结构：同步更新相关 spec/adr
3. 涉及前后端联调：明确需要启动哪些服务与端口

### 3.3 任务结束（必做）
1. 输出 `git diff --name-only`
2. 跑测试并输出结果（第 4 节）
3. 更新 `DEVELOPMENT_LOG.md`（第 5 节）
4. 允许 commit，输出 commit hash
5. **停止在 push 前：询问用户是否允许 push**

---

## 4) 测试与证据记录标准（每次任务必须达标）

### 4.1 最小测试集（按变更类型）
- 仅文档变更：不要求代码测试，但必须自检一致性（链接/编号/口径）
- 后端逻辑变更：至少跑相关单测/集成脚本（若存在），提供命令与输出摘要
- 前端变更：至少执行 `npm test`（Vitest）或 `npm run build`，提供命令与输出摘要
- 回归变更：跑对应回归脚本（如 scripts/run_phase3_regression.sh 等）

### 4.2 测试证据格式（必须写进 DEVELOPMENT_LOG）
- Commands Run（可复制）
- Output 摘要（失败时贴关键错误栈）
- Result：PASS/FAIL
- Failure Handling：失败原因 + 下一步动作

> 严禁写“看起来没问题”“应该通过”。

---

## 5) 开发记录标准（DEVELOPMENT_LOG.md）
每次任务结束必须新增一条记录，格式必须一致：

- DateTime:
- Task:
- Scope (files changed):
- Commands Run:
- Tests:
- Result:
- Risks/Notes:
- Next Step:

记录粒度：另一位工程师仅凭日志即可复现你的改动与测试。

---

## 6) ADR 触发条件（满足任一必须新增 ADR）
新增 `docs/adr/ADR-*.md` 的触发条件：
- 新增依赖（Python/Node 包）
- 新增外部服务（队列/向量库/对象存储）
- 更改权限/审批/审计模型
- 更改数据表结构且影响多个模块

ADR 最小内容：背景、决策、备选、影响、迁移策略、回滚策略。

---

## 7) AI/权限/审批（v0.3 强制规则）
- 任意 write tool：必须 `risk_level >= medium` 且走审批（teacher confirm 起）
- 任意 deny：必须写审计；对外 404 也必须记录真实 `resource_id`
- RAG：对象级后过滤“返回空”属于检索层；HTTP GET 越权仍返回 404
- trace_id 必须贯穿：Command → ToolCall → Approval → Audit
- 引用（citations/evidence_refs）必须服务端校验存在且可访问

---

## 8) Codex 输出格式（每次回复必须包含）
1. 答案总结
2. 最终结论
