# Training Workbench Execution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将学生端训练工作台从 AI 草案展示页补成可执行页面，打通正式步骤提交、证据上传入库、裁决、AI 追问与步骤联动 3D 高亮。

**Architecture:** 继续复用现有 `training session / submission / evidence bundle / Atom01 viewer` 能力，不额外引入服务。后端新增面向训练工作台的执行接口，前端把草案会话改成真实训练会话，并以步骤级状态驱动裁决、追问与 3D 高亮。裁决先采用“规则校验 + 用户级 LLM 解释”的轻量组合，避免一次性重做整套评估系统。

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, Pydantic, React, Zustand, Vitest, existing Viewer3D components

### Task 1: 训练工作台真实会话化

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py`
- Modify: `r-mos-backend/app/services/training/workbench_draft_generator.py`
- Modify: `r-mos-backend/app/services/training/session_service.py`
- Test: `r-mos-backend/tests/unit/test_training_workbench_draft_api.py`
- Modify: `r-mos-frontend/src/api/training.ts`

**Step 1: Write the failing test**

为草案接口补断言，要求返回真实 `session_id`、步骤索引、`model_targets`。

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit/test_training_workbench_draft_api.py -q`

Expected: FAIL，因为当前草案接口只返回虚拟 draft session，且无 3D 目标。

**Step 3: Write minimal implementation**

- 在草案生成器中补 `model_targets`。
- 草案接口生成后调用 `SessionService.create_session(...)` 创建真实训练会话。
- 在 `project_snapshot` 中写入步骤、工具、证据提示与 3D 目标，供后续提交/恢复使用。

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: persist training workbench drafts as sessions"`

### Task 2: 步骤提交、证据入库与裁决接口

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py`
- Create: `r-mos-backend/app/services/training/workbench_execution_service.py`
- Modify: `r-mos-backend/app/services/evidence_service.py`
- Modify: `r-mos-backend/app/schemas/evidence.py`
- Test: `r-mos-backend/tests/unit/test_training_workbench_execution_api.py`

**Step 1: Write the failing test**

新增接口测试，覆盖：
- 上传证据后生成 `evidence_bundle_id`
- 步骤提交写入 `SessionStepRecord`
- 裁决返回 `PASS/FAIL` 与 `llm_explanation`

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit/test_training_workbench_execution_api.py -q`

Expected: FAIL，因为接口尚不存在。

**Step 3: Write minimal implementation**

- 新增训练工作台证据上传接口，接收 `UploadFile`，保存到本地 `storage/training-evidence/`。
- 基于文件内容计算 hash，调用 `EvidenceService` 入库，返回 `bundle_id`。
- 新增步骤提交接口：校验关键工具、证据是否存在；生成规则裁决；调用用户级 LLM 生成解释；回写 `SessionStepRecord`。

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: add executable training workbench submission flow"`

### Task 3: AI 追问接口

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py`
- Modify: `r-mos-backend/app/services/training/workbench_execution_service.py`
- Test: `r-mos-backend/tests/unit/test_training_workbench_execution_api.py`
- Modify: `r-mos-frontend/src/api/training.ts`

**Step 1: Write the failing test**

新增 `ask` 接口测试，要求传入用户问题、当前步骤上下文后返回 assistant message。

**Step 2: Run test to verify it fails**

Run: 同 Task 2  
Expected: FAIL

**Step 3: Write minimal implementation**

- 新增 `POST /training/workbench/ask`
- 读取用户 LLM 配置
- 拼入当前步骤说明、工具状态、证据摘要与最近消息
- 返回结构化 assistant message

**Step 4: Run test to verify it passes**

Run: 同 Task 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: add training workbench follow-up assistant"`

### Task 4: 前端执行态与 3D 步骤高亮

**Files:**
- Modify: `r-mos-frontend/src/pages/TrainingWorkbenchPage.tsx`
- Modify: `r-mos-frontend/src/store/workbenchStore.ts`
- Modify: `r-mos-frontend/src/api/training.ts`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Viewer.tsx`
- Test: `r-mos-frontend/src/pages/__tests__/TrainingWorkbenchPage.test.tsx`

**Step 1: Write the failing test**

补页面测试，覆盖：
- 草案生成后持有真实 session
- 上传证据并提交步骤
- 调用 AI 追问
- 当前步骤切换时把 `modelTargets` 传给 3D viewer

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/pages/__tests__/TrainingWorkbenchPage.test.tsx`

Expected: FAIL，因为当前页面只有本地假提交和本地消息追加。

**Step 3: Write minimal implementation**

- store 增加 `evidenceBundleId / evidenceItems / submitting / asking / modelTargets`
- 页面接入真实上传、真实提交、真实 AI 追问
- 3D viewer 支持 `highlightLinks`，按当前步骤目标高亮

**Step 4: Run test to verify it passes**

Run: 同 Step 2  
Expected: PASS

**Step 5: Commit**

`git commit -m "feat: execute training workbench steps end to end"`

### Task 5: 回归验证与文档

**Files:**
- Modify: `DEVELOPMENT_LOG.md`
- Optional: `docs/testing/TEST_REPORT.md`

**Step 1: Run backend verification**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit/test_training_workbench_draft_api.py tests/unit/test_training_workbench_execution_api.py -q`

Expected: PASS

**Step 2: Run frontend verification**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/pages/__tests__/TrainingWorkbenchPage.test.tsx src/pages/__tests__/UserSettingsPage.test.tsx && npm run build`

Expected: PASS

**Step 3: Browser verification**

刷新 `/workbench/training`，验证：
- 空态生成真实会话
- 上传证据后可正式提交
- 返回裁决
- 输入问题后得到 AI 追问回复
- 切换步骤时 3D 高亮同步变化

**Step 4: Update logs**

- 追加 `DEVELOPMENT_LOG.md`
- 输出 `git diff --name-only`

**Step 5: Commit**

`git commit -m "test: verify executable training workbench flow"`
