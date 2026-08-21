# AGENTS｜R-MOS Codex 开发强约束（Read-first）
> 权威源：本文件是 Codex 开发规则的唯一真相源（Single Source of Truth）。  
> 镜像：docs/ops/CODEX_RULES.md 必须与本文件一致，但不作为权威源。  
> 适用范围：所有对 r-mos 仓库的开发/测试/文档修改。  
> 生效优先级：AGENTS.md > docs/testing/ACCEPTANCE_CHARTER.md > 已批准且适用的 docs/adr/* > 当前任务明确指定的 docs/superpowers/plans/* 或 docs/plans/* > docs/testing/2026-08-10-rmos-single-school-five-robot-acceptance-matrix-v0.1.0.md > docs/plans/2026-08-10-rmos-single-school-five-robot-deployment-rollback-v0.1.0.md > docs/testing/TEST_PLAN.md > docs/testing/TEST_REPORT.md > docs/audit/* > docs-archive/DEVELOPMENT_LOG.md > docs-archive/* 与 Git 历史
> “任何任务必须对齐 docs/testing/ACCEPTANCE_CHARTER.md 的门禁与证据要求。”

---

## 0) 当前项目状态快照（2026-08-21）

- 当前规则与记录：
  - 验收总纲：`docs/testing/ACCEPTANCE_CHARTER.md`
  - 当前测试报告：`docs/testing/TEST_REPORT.md`
  - 开发记录：`docs-archive/DEVELOPMENT_LOG.md`
  - 架构审查基线：`docs/audit/README.md`
- 最近完成的功能专项：`docs/superpowers/plans/2026-08-17-sop-three-phase-guided-flow.md` 记录 14/14 Task 完成；其中 Task 5.1 仍为有条件通过，完整 22 步 E2E 未稳定跑通。
- 最近一次记录的测试快照为 2026-08-21：后端 `822 passed, 3 skipped`，前端 `511 passed, 2 skipped`，前端构建 PASS。该数字属于对应提交的历史证据，本规则修复批次未重新执行，不得自动视为当前提交验收结果。
- 单校五台真机验收矩阵中的 E1 至 E4 正式执行尚未在本批完成；`REL-BLOCK-01` 继续阻断 D0 与任何生产启用。
- 当前下一步：规则事实源已修复；进入 Phase 1 六条链路审查前仍须获得用户确认。
- 每批闭环必须同步：
  1. 若当前任务有明确计划和状态表，更新对应状态；
  2. 影响验收时更新 `docs/testing/TEST_PLAN.md` 与/或 `docs/testing/TEST_REPORT.md`；
  3. 追加 `docs-archive/DEVELOPMENT_LOG.md`（命令、结果、失败处理）；
  4. 输出可复现最小验证命令与结果摘要。

---

## 1) Read-first Checkpoint（每次任务开始必须输出并逐条确认）
Codex 每次开始任务前，必须在回复中逐条输出并确认（✅/❌）：

1. ✅ 当前仓库目录：`/Users/xuhehong/Desktop/r-mos`
2. ✅/❌ Python 环境（每次任务现场检查，不得预填为已就绪）：
   - 标准后端环境：`/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv`
   - 主工作区使用 `r-mos-backend/venv/bin/python -m pytest ...`
   - 隔离 worktree 若没有本地 `venv`，可调用上述绝对路径解释器，但工作目录必须是该 worktree 的 `r-mos-backend`，并先核对解释器与依赖
   - 不得使用系统 Python
   - 只有解释器路径和当前任务所需依赖实际核对通过后才能输出 ✅；否则输出 ❌ 并停止 Python 相关执行
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
   - `AGENTS.md`
   - `docs/testing/ACCEPTANCE_CHARTER.md`
   - 已批准且适用的 `docs/adr/*`
   - 当前任务明确指定的 `docs/superpowers/plans/*` 或 `docs/plans/*`
   - `docs/testing/2026-08-10-rmos-single-school-five-robot-acceptance-matrix-v0.1.0.md`
   - `docs/plans/2026-08-10-rmos-single-school-five-robot-deployment-rollback-v0.1.0.md`
   - `docs/testing/TEST_PLAN.md`
   - `docs/testing/TEST_REPORT.md`
   - `docs/audit/*`
   - `docs-archive/DEVELOPMENT_LOG.md`
   - `docs-archive/*` 与 Git 历史仅作历史证据

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
- 必须更新 `docs-archive/DEVELOPMENT_LOG.md`（见第 5 节）
- 若当前任务有明确计划和状态表：每完成一组必须同步更新计划状态、开发记录，并输出最小验证命令摘要
- 若变更影响验收：必须同步更新 `docs/testing/TEST_PLAN.md` 与/或 `docs/testing/TEST_REPORT.md`

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
3. 更新 `docs-archive/DEVELOPMENT_LOG.md`（第 5 节）
4. 允许 commit，输出 commit hash
5. **停止在 push 前：询问用户是否允许 push**

---

## 4) 测试与证据记录标准（每次任务必须达标）

### 4.1 最小测试集（按变更类型）
- 仅文档变更：不要求代码测试，但必须自检一致性（链接/编号/口径）
- 后端逻辑变更：至少跑相关单测/集成脚本（若存在），提供命令与输出摘要
- 前端变更：至少执行 `npm test`（Vitest）或 `npm run build`，提供命令与输出摘要
- 回归变更：跑对应回归脚本（如 scripts/run_phase3_regression.sh 等）

### 4.2 测试证据格式（必须写进 `docs-archive/DEVELOPMENT_LOG.md`；影响验收时同步写入当前测试报告）
- Commands Run（可复制）
- Output 摘要（失败时贴关键错误栈）
- Result：PASS/FAIL
- Failure Handling：失败原因 + 下一步动作

> 严禁写“看起来没问题”“应该通过”。

---

## 5) 开发记录标准（`docs-archive/DEVELOPMENT_LOG.md`）
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

## 7) AI/权限/审批（强制规则）
- 任意 write tool：必须 `risk_level >= medium` 且走审批（teacher confirm 起）
- 任意 deny：必须写审计；对外 404 也必须记录真实 `resource_id`
- RAG：对象级后过滤“返回空”属于检索层；HTTP GET 越权仍返回 404
- trace_id 必须贯穿：Command → ToolCall → Approval → Audit
- 引用（citations/evidence_refs）必须服务端校验存在且可访问

---

## 8) Codex 输出格式（每次回复必须包含）
1. 答案总结
2. 最终结论
