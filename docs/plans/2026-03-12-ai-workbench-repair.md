# AI Workbench Repair Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复学生端 AI 工作台的主链路，让页面可真实发送、获得响应、查看轨迹，并把诊断面板动作接成可执行后端流程。

**Architecture:** 不放大学生的命令执行权限，保留 `command` 模式继续要求 `agent:execute`；只把 AI 工作台使用的 `message` 模式放开到 `agent:read`，并在 `OrchestratorV2` 中补齐 `general / execution / knowledge / coach` 的真实响应生成。诊断面板动作通过新增轻量后端接口写入 trace 事件，前端读取结果更新消息流，不引入新依赖。

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, existing RBAC/authz guard, React, Vitest, pytest

### Task 1: 安全拆分消息模式与命令模式权限

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`
- Test: `r-mos-backend/tests/e2e/test_agent_execute.py`

**Step 1: Write the failing test**

补 `/agent/execute` 权限测试：
- 学生 `message` 模式允许访问
- 学生 `command` 模式仍返回 `403`

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/e2e/test_agent_execute.py -q`

Expected: FAIL，因为当前统一依赖 `agent:execute`

**Step 3: Write minimal implementation**

- 去掉路由级固定 `agent:execute` 依赖
- 在 `execute_agent` 内按 `_detect_mode(request)` 分支：
  - `message` 仅要求当前 actor 具备 `agent:read`
  - `command` 继续要求 `agent:execute`
- 缺权时沿用现有审计与 `403` 返回

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "fix: allow student message mode in ai workbench"`

### Task 2: 补齐 AI 工作台消息模式后端响应

**Files:**
- Modify: `r-mos-backend/app/services/orchestrator_v2.py`
- Test: `r-mos-backend/tests/unit/test_orchestrator_v2.py`

**Step 1: Write the failing test**

新增 orchestrator 用例，覆盖：
- `general` 返回任务摘要/审批待办/日报类文本
- `execute-task` 返回维保派单建议和步骤
- `delegate-coach` 返回训练指导建议
- `read-kb` / `write-kb` 返回知识查询/记录建议

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit/test_orchestrator_v2.py -q`

Expected: FAIL，因为当前大多仍是 placeholder，且 `general` 模块未注册

**Step 3: Write minimal implementation**

- 注册 `general` 模块
- 用轻量规则+模板生成 AI 工作台需要的真实结果结构
- 保持诊断分支不动
- 为 trace/replay 保留统一响应字段

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: add ai workbench message handlers"`

### Task 3: 打通诊断面板动作

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`
- Test: `r-mos-backend/tests/e2e/test_agent_execute.py`
- Modify: `r-mos-frontend/src/api/agent-v2.ts`
- Modify: `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`
- Test: `r-mos-frontend/src/pages/agent/__tests__/AgentWorkbenchPage.test.tsx`

**Step 1: Write the failing test**

补前端测试和后端接口测试，覆盖：
- 点击“确认执行方案”会调用后端并回填成功消息
- 点击“上报教师审核”会调用后端并回填审批消息

**Step 2: Run test to verify it fails**

Run backend: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/e2e/test_agent_execute.py -q`

Run frontend: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/pages/agent/__tests__/AgentWorkbenchPage.test.tsx`

Expected: FAIL，因为当前仅弹 toast

**Step 3: Write minimal implementation**

- 新增 AI 工作台诊断动作接口
- 将动作写入 trace 事件并返回提示文本
- 前端收到成功后追加 assistant 消息，而不是只弹 toast

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: wire ai workbench diagnosis actions"`

### Task 4: 回归验证与记录

**Files:**
- Modify: `DEVELOPMENT_LOG.md`
- Optional: `docs/testing/TEST_REPORT.md`

**Step 1: Run backend verification**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit/test_orchestrator_v2.py tests/e2e/test_agent_execute.py -q`

Expected: PASS

**Step 2: Run frontend verification**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/pages/agent/__tests__/AgentWorkbenchPage.test.tsx && npm run build`

Expected: PASS

**Step 3: Browser verification**

刷新 `/agent/workbench`，用学生账号验证：
- 快捷按钮和发送可返回响应
- 诊断问题仍要求有遥测数据
- trace 可打开
- 诊断动作按钮真实生效

**Step 4: Update logs**

- 追加 `DEVELOPMENT_LOG.md`
- 输出 `git diff --name-only`

**Step 5: Commit**

`git commit -m "fix: restore ai workbench student flow"`
