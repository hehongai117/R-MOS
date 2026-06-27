# Phase 2：测试安全网（重构前置）— 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐）逐 Task 实施。步骤用 checkbox（`- [ ]`）跟踪。
>
> 设计 Spec：`docs/superpowers/specs/2026-06-22-quality-hardening-upgrade-design.md`
> 总控计划：`docs/superpowers/plans/2026-06-22-quality-hardening-master-plan.md`

**Goal:** 为 Phase 3 待重构的 6 个巨型文件建立**特征测试（characterization tests）**安全网，并纳入 CI 覆盖率门禁，使 Phase 3 重构（行为等价）可被绿测验证。

**Architecture:** 特征测试锁定文件当前**对外可观测行为**（后端=HTTP 路由的请求/响应与副作用；前端=渲染 DOM + 关键交互回调），不依赖内部实现，从而在重构后仍然有效。复用本项目既有测试基建：后端 `_build_client`（SQLite 内存库 + 预置 School + override get_db）+ `_register_and_login`（role/school_name）；前端 `render` + `MemoryRouter` + mock（api/store/@react-three-fiber/@/adjudication）。

**Tech Stack:** 后端 pytest + pytest-cov + FastAPI TestClient + SQLite(aiosqlite)；前端 vitest + @testing-library/react + jsdom。

## Global Constraints

- **不改动被测产品代码**：本 Phase 只新增/修改测试与 CI 配置，**不动** `r-mos-backend/app/**` 与 `r-mos-frontend/src/**` 的产品逻辑（除非发现测试暴露的真实 bug，此时停下来上报，不擅自改）。
- **特征测试 = 锁定现状**：测试断言**当前真实行为**。写完应**立即通过**；若不通过，说明对行为的假设错了 → 调整断言去匹配真实行为（而非改产品代码）。这不是 TDD（不先红后绿）。
- **以当前最新状态为准**：遇到针对已移除/废弃实现的旧断言，对齐现状（skip/删并注明），不复活旧物。
- 覆盖率目标（行覆盖，line coverage）：后端三端点各 **≥80%**；`SOPMaintenancePage`、`SOPPlayerAdjudicated` 各 **≥70%**；`Atom01Interactive`（3D 重，jsdom 下渲染路径难测）**≥55%**，聚焦非 3D 的逻辑/回调/控制面板。
- 所有测试必须可重复、与真实 DB/网络隔离（SQLite + mock）。
- 提交信息中文，结尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 分支：`quality-hardening-phase2`（从当前 `quality-hardening-phase1` HEAD 创建）。

## 现状事实（执行前已核实，2026-06-25）

- 巨型文件与现有测试：
  | 文件 | 行数 | 路由/规模 | 现有测试 |
  |------|------|-----------|----------|
  | `app/api/v1/endpoints/agent.py` | 1214 | 36 路由 | test_agent_authz / test_agent_workbench_api / test_agent_policy_factory（部分） |
  | `app/api/v1/endpoints/training.py` | 1038 | 20 路由 | test_api_training_flow / test_training_phase2_api / test_training_workbench_*（部分） |
  | `app/api/v1/endpoints/teaching.py` | 901 | 24 路由 | test_teaching_api / test_api_teaching / test_teaching_service（部分） |
  | `src/pages/SOPMaintenancePage.tsx` | 1615 | — | SOPMaintenancePage.test.tsx / .dynamic.test.tsx（部分） |
  | `src/components/Viewer3D/Atom01Interactive.tsx` | 1207 | — | **无直接测试** |
  | `src/components/Maintenance/SOPPlayerAdjudicated.tsx` | 895 | — | **无直接测试** |
- CI 覆盖率门禁：后端 `backend-ci.yml` 对 14 个核心 service `--cov-fail-under=70`（**不含上述端点**）；另有 `--cov=app` 仅生成 xml 参考、无门禁。前端 `frontend-ci.yml` **无覆盖率门禁**。
- `pytest-cov` 已在本地 venv 安装，但需确认是否在 `requirements.txt`（CI 依赖它）。
- 后端测试基建样板：`tests/unit/test_skill_governance_api.py` 的 `_build_client()` + `_register_and_login()` + `_grant_role_permissions()`（含 School 白名单预置 `TEST_SCHOOL_NAME = "测试学校"`）。
- 前端 mock 样板：`src/pages/__tests__/SOPMaintenancePage.test.tsx`（mock `react-router-dom` 的 useNavigate、`@react-three/fiber` 的 Canvas、`@/adjudication`（含 `injectManifestPartRegistry`/`clearManifestPartRegistry`））。

---

### Task 1：覆盖率工具与基线

**Files:**
- Modify: `r-mos-backend/requirements.txt`（确保含 `pytest-cov`）
- Create: `r-mos-backend/scripts/coverage_godfiles.sh`（一键测 6 文件中后端部分的覆盖率）
- Create: `docs/superpowers/plans/phase2-coverage-baseline.md`（记录基线数字）

**Interfaces:**
- Produces: 可重复的覆盖率测量命令；6 个文件的基线行覆盖率数字（供后续 Task 验证增量与门禁阈值设定）。

- [ ] **Step 1：确认/补充 pytest-cov 依赖**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
grep -iE 'pytest-cov' requirements.txt || echo "MISSING"
```
若 `MISSING`，在 `requirements.txt` 末尾追加一行 `pytest-cov>=5.0`（与本地已装版本兼容即可），保证 CI 也装得到。

- [ ] **Step 2：创建后端覆盖率脚本**

Create `r-mos-backend/scripts/coverage_godfiles.sh`：
```bash
#!/usr/bin/env bash
# 测量 Phase 3 待重构后端端点的行覆盖率
set -euo pipefail
cd "$(dirname "$0")/.."
venv/bin/python -m pytest tests/ -q -o addopts='' -p no:warnings \
  --cov=app.api.v1.endpoints.agent \
  --cov=app.api.v1.endpoints.training \
  --cov=app.api.v1.endpoints.teaching \
  --cov-report=term-missing:skip-covered \
  "$@"
```
`chmod +x r-mos-backend/scripts/coverage_godfiles.sh`

- [ ] **Step 3：测量后端基线**

Run: `bash r-mos-backend/scripts/coverage_godfiles.sh 2>&1 | grep -E 'endpoints/(agent|training|teaching)\.py'`
Expected: 打印三行，形如 `app/api/v1/endpoints/agent.py   <stmts>   <miss>   <cover>%`。
记录三个百分比。若覆盖率报告打印不出（"No data"），改用：先 `venv/bin/python -m pytest tests/ -o addopts='' -p no:warnings --cov=app/api/v1/endpoints --cov-report=html:/tmp/cov_html -q` 再读 `/tmp/cov_html/index.html`，或 `venv/bin/coverage report --include='*/endpoints/agent.py,*/endpoints/training.py,*/endpoints/teaching.py'`。

- [ ] **Step 4：测量前端基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npx vitest run --coverage --coverage.include='src/pages/SOPMaintenancePage.tsx' --coverage.include='src/components/Viewer3D/Atom01Interactive.tsx' --coverage.include='src/components/Maintenance/SOPPlayerAdjudicated.tsx' 2>&1 | grep -E 'SOPMaintenancePage|Atom01Interactive|SOPPlayerAdjudicated|File .*% ' | head
```
若报缺少 coverage provider，先 `npm i -D @vitest/coverage-v8`（记录到 package.json devDependencies）。记录三个百分比。

- [ ] **Step 5：记录基线并提交**

将 6 个基线数字写入 `docs/superpowers/plans/phase2-coverage-baseline.md`（每行 `<文件>: 基线 X% → 目标 Y%`，目标取 Global Constraints 的阈值）。
```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-backend/requirements.txt r-mos-backend/scripts/coverage_godfiles.sh r-mos-frontend/package.json docs/superpowers/plans/phase2-coverage-baseline.md
git commit -m "test(phase2): 覆盖率工具与 6 个巨型文件基线

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`coverage_godfiles.sh` 可跑出三端点覆盖率；前端可跑出三组件覆盖率；基线文档记录 6 个数字。

---

### Task 2：`agent.py` 特征测试（→ ≥80%）

**Files:**
- Create: `r-mos-backend/tests/unit/test_agent_characterization.py`
- Reference: `r-mos-backend/tests/unit/test_skill_governance_api.py`（复用 `_build_client`/`_register_and_login`/`_grant_role_permissions` 样板）
- Reference: `r-mos-backend/app/api/v1/endpoints/agent.py`（36 路由，见下方清单）

**Interfaces:**
- Consumes: Task 1 的覆盖率脚本（验证阈值）。
- Produces: `test_agent_characterization.py`，锁定 agent.py 路由的当前响应行为。

- [ ] **Step 1：搭建测试骨架（复用样板）**

Create `tests/unit/test_agent_characterization.py`，顶部复制 `test_skill_governance_api.py` 的基建（imports、`TEST_SCHOOL_NAME`、`_build_client`、`init_models` 含 `School` 预置、`_register_and_login` 含 `role/school_name`、`_grant_role_permissions`）。这是特征测试的统一夹具。

- [ ] **Step 2：列出待覆盖路由清单**

Run: `grep -nE '@router\.(get|post|put|patch|delete)' app/api/v1/endpoints/agent.py | sed -E 's/.*(get|post|put|patch|delete)\("([^"]+)".*/\1 \2/'`
得到 36 条路由。对照 Task 1 基线的 `--cov-report=term-missing` 输出，标出**未覆盖的行/路由**作为本 Task 重点。

- [ ] **Step 3：为代表性路由写特征测试（示例 + 模式）**

为**每个未覆盖路由**写一个测试：构造请求 → 断言**当前**状态码与响应体关键字段。示例（一个写端点 + 一个读端点）：
```python
def test_agent_execute_returns_current_shape():
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="a@x.com", password="StrongPass123", full_name="A")
        _grant_role_permissions(sf, email="a@x.com", role_name="agent_user",
                                permission_keys=["agent:execute"])
        resp = client.post("/api/v1/agent/execute",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"action_type": "inspect", "target": "knee_left"})
        # 锁定当前行为：断言真实返回的状态码与字段（先跑一次看真实值再固化）
        assert resp.status_code in (200, 202)
        body = resp.json()
        assert "trace_id" in body or "status" in body
    finally:
        client.close(); app.dependency_overrides.clear()

def test_agent_v2_modules_lists_registered_modules():
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="b@x.com", password="StrongPass123", full_name="B")
        resp = client.get("/api/v1/agent/v2/modules",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), (list, dict))
    finally:
        client.close(); app.dependency_overrides.clear()
```
**写法**：先用断言占真实值跑一次，按报错把断言改成真实返回值（characterization）。对需要权限的路由用 `_grant_role_permissions` 授予对应 `permission_keys`（权限键见路由的 `require_permission(...)`，可在 agent.py 中 grep 确认）。

- [ ] **Step 4：补齐到覆盖率达标**

Run: `bash scripts/coverage_godfiles.sh tests/unit/test_agent_characterization.py 2>&1 | grep 'endpoints/agent.py'`
迭代补测试，直到 `agent.py` 行覆盖率 **≥80%**。对确实无法在单测触达的分支（外部副作用、后台任务），在测试文件用注释标注原因。
Expected: `agent.py` ≥80%。

- [ ] **Step 5：确认全绿并提交**

Run: `venv/bin/python -m pytest tests/unit/test_agent_characterization.py -p no:cacheprovider -o addopts='' -q`
Expected: 全部 passed。
```bash
git add r-mos-backend/tests/unit/test_agent_characterization.py
git commit -m "test(phase2): agent.py 端点特征测试，行覆盖率达标(≥80%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`agent.py` ≥80%；新测试全绿；未改动 `agent.py`。

---

### Task 3：`training.py` 特征测试（→ ≥80%）

**Files:**
- Create: `r-mos-backend/tests/unit/test_training_characterization.py`
- Reference: `app/api/v1/endpoints/training.py`（20 路由）；现有 `test_api_training_flow.py`、`test_training_phase2_api.py`（参考其夹具与 mock 方式）

**Interfaces:**
- Produces: `test_training_characterization.py`，锁定 training.py 路由当前行为。

- [ ] **Step 1：搭建骨架**

同 Task 2 Step 1 复用 `_build_client`/`_register_and_login` 样板，新建 `test_training_characterization.py`。training 路由多涉及 `training session` 与 `submission`，参考 `test_training_phase2_api.py` 如何 mock `submission_service`/`feedback_generator`。

- [ ] **Step 2：列路由清单**

Run: `grep -nE '@router\.(get|post|put|patch|delete)' app/api/v1/endpoints/training.py | sed -E 's/.*(get|post|put|patch|delete)\("([^"]+)".*/\1 \2/'`

- [ ] **Step 3：写特征测试（示例）**

```python
def test_create_training_session_returns_session_id():
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="s@x.com", password="StrongPass123", full_name="S")
        resp = client.post("/api/v1/training/sessions",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"project_id": "p-1"})
        # characterization：按真实返回固化
        assert resp.status_code in (200, 201)
        assert "session_id" in resp.json() or "id" in resp.json()
    finally:
        client.close(); app.dependency_overrides.clear()
```
对每个未覆盖路由重复此模式，断言真实状态码/字段。

- [ ] **Step 4：补齐到 ≥80%**

Run: `bash scripts/coverage_godfiles.sh tests/unit/test_training_characterization.py 2>&1 | grep 'endpoints/training.py'`
迭代到 `training.py` ≥80%。

- [ ] **Step 5：全绿并提交**

Run: `venv/bin/python -m pytest tests/unit/test_training_characterization.py -p no:cacheprovider -o addopts='' -q`
```bash
git add r-mos-backend/tests/unit/test_training_characterization.py
git commit -m "test(phase2): training.py 端点特征测试(≥80%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`training.py` ≥80%；全绿；未改动产品代码。

---

### Task 4：`teaching.py` 特征测试（→ ≥80%）

**Files:**
- Create: `r-mos-backend/tests/unit/test_teaching_characterization.py`
- Reference: `app/api/v1/endpoints/teaching.py`（24 路由）；现有 `test_teaching_api.py`、`test_api_teaching.py`

**Interfaces:**
- Produces: `test_teaching_characterization.py`，锁定 teaching.py 路由当前行为。

- [ ] **Step 1：搭建骨架**

复用样板新建 `test_teaching_characterization.py`。teaching 路由多为教师视角（监控/审批/学生管理），用 `_grant_role_permissions` 授予 teacher 相关权限（在 teaching.py grep `require_permission`/`_require_teacher` 确认）。

- [ ] **Step 2：列路由清单**

Run: `grep -nE '@router\.(get|post|put|patch|delete)' app/api/v1/endpoints/teaching.py | sed -E 's/.*(get|post|put|patch|delete)\("([^"]+)".*/\1 \2/'`

- [ ] **Step 3：写特征测试（示例）**

```python
def test_teacher_students_list_returns_current_shape():
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="t@x.com", password="StrongPass123", full_name="T")
        _grant_role_permissions(sf, email="t@x.com", role_name="teacher",
                                permission_keys=["teaching:read"])
        resp = client.get("/api/v1/teaching/students",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), (list, dict))
    finally:
        client.close(); app.dependency_overrides.clear()
```
（路由路径与权限键以 teaching.py 真实内容为准。）

- [ ] **Step 4：补齐到 ≥80%**

Run: `bash scripts/coverage_godfiles.sh tests/unit/test_teaching_characterization.py 2>&1 | grep 'endpoints/teaching.py'`
迭代到 `teaching.py` ≥80%。

- [ ] **Step 5：全绿并提交**

Run: `venv/bin/python -m pytest tests/unit/test_teaching_characterization.py -p no:cacheprovider -o addopts='' -q`
```bash
git add r-mos-backend/tests/unit/test_teaching_characterization.py
git commit -m "test(phase2): teaching.py 端点特征测试(≥80%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`teaching.py` ≥80%；全绿；未改动产品代码。

---

### Task 5：`SOPMaintenancePage` 特征测试（→ ≥70%）

**Files:**
- Modify/Create: `r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx`（新增，避免动现有两个测试文件）
- Reference: `src/pages/__tests__/SOPMaintenancePage.test.tsx`（复用其 mock 样板：react-router-dom / @react-three/fiber / @/adjudication）

**Interfaces:**
- Produces: 锁定 `SOPMaintenancePage` 渲染与关键交互的特征测试。

- [x] **Step 1：复用 mock 样板搭骨架**

Create `SOPMaintenancePage.characterization.test.tsx`，复制 `SOPMaintenancePage.test.tsx` 顶部的 mock（`react-router-dom` useNavigate/useSearchParams、`@react-three/fiber` Canvas stub、`@/adjudication` 含 `injectManifestPartRegistry`/`clearManifestPartRegistry`，以及 api/store mock）。

> 实施记录：Canvas mock 改为渲染 children（而非空 stub），使 3D 分支选择三元运算可观测；Atom01Interactive/SOPPlayerAdjudicated mock 捕获 props 回调，从而驱动隔离态状态机。

- [x] **Step 2：写渲染 + 交互特征测试**

覆盖现有测试未覆盖的分支：不同 `workspaceVariant`、SOP 列表加载态/空态、步骤切换、面板折叠/展开等。示例：
```tsx
it('renders sop list loading then content', async () => {
  getSOPScriptsMock.mockResolvedValue([{ id: 's1', name: '测试SOP', steps: [] }])
  render(<MemoryRouter><SOPMaintenancePage /></MemoryRouter>)
  expect(await screen.findByText('测试SOP')).toBeInTheDocument()
})

it('renders empty state when no sops', async () => {
  getSOPScriptsMock.mockResolvedValue([])
  render(<MemoryRouter><SOPMaintenancePage /></MemoryRouter>)
  // characterization：按真实空态文案固化
  expect(await screen.findByText(/暂无|empty|无可用/i)).toBeInTheDocument()
})
```
（mock 工厂名、空态文案以组件真实实现为准——先跑一次看真实 DOM 再固化断言。）

- [x] **Step 3：补齐到 ≥70%**

Run:
```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx \
  --coverage --coverage.include='src/pages/SOPMaintenancePage.tsx' 2>&1 | grep 'SOPMaintenancePage.tsx'
```
迭代到 `SOPMaintenancePage.tsx` 行覆盖率 ≥70%。**实测 75.78%（44 用例全绿）。**

- [x] **Step 4：全绿并提交**（commit 512fd2d2）

Run: `npx vitest run src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx`
Expected: 全 passed。
```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx
git commit -m "test(phase2): SOPMaintenancePage 特征测试(≥70%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`SOPMaintenancePage.tsx` ≥70%；全绿；未改动组件源码。

---

### Task 6：`Atom01Interactive` 特征测试（→ ≥55%）

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx`
- Reference: `src/components/Viewer3D/Atom01Interactive.tsx`（1207 行，3D 组件）

**Interfaces:**
- Produces: 锁定 `Atom01Interactive` 非 3D 逻辑（props、控制面板、部件选择回调、状态切换）的特征测试。

- [x] **Step 1：分析可测面 + 搭 mock**

Run: `grep -nE 'export|function |useState|props|onSelect|on[A-Z]|Canvas|useFrame|@react-three' src/components/Viewer3D/Atom01Interactive.tsx | head -40`
确定 3D 渲染部分（`@react-three/fiber`/`@react-three/drei`/`useFrame`）需 mock，逻辑部分（控制面板、回调、状态）可测。Create 测试文件，mock `@react-three/fiber`（`Canvas: () => <div>CanvasStub</div>`、`useFrame: () => {}`）与 `@react-three/drei`（按需 stub）。

- [x] **Step 2：写非 3D 逻辑特征测试**

断言：组件能挂载不崩溃；控制面板 DOM 出现；触发部件选择/关节控制回调时 props 回调被调用。示例：
```tsx
it('mounts without crashing and renders control affordances', () => {
  render(<Atom01Interactive /* 必填 props 以真实默认填入 */ />)
  // characterization：断言真实渲染出的控制元素（先跑看真实 DOM）
  expect(screen.getByTestId(/control|panel/i) ?? document.body).toBeTruthy()
})
```
（props、testid/文案以组件真实实现为准。）

- [x] **Step 3：补齐到 ≥55%**

Run:
```bash
npx vitest run src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx \
  --coverage --coverage.include='src/components/Viewer3D/Atom01Interactive.tsx' 2>&1 | grep 'Atom01Interactive.tsx'
```
迭代到 ≥55%。**3D 渲染路径（useFrame 回调、Three 场景图）在 jsdom 下不可达**，在测试文件注释说明，不强求更高。

- [x] **Step 4：全绿并提交**（commit 2c77b583，实测 84.14%，10 用例全绿）

Run: `npx vitest run src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx`
```bash
git add r-mos-frontend/src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx
git commit -m "test(phase2): Atom01Interactive 非3D逻辑特征测试(≥55%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`Atom01Interactive.tsx` ≥55%；全绿；未改动组件源码；3D 不可测部分有注释说明。

---

### Task 7：`SOPPlayerAdjudicated` 特征测试（→ ≥70%）

**Files:**
- Create: `r-mos-frontend/src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx`
- Reference: `src/components/Maintenance/SOPPlayerAdjudicated.tsx`（895 行）

**Interfaces:**
- Produces: 锁定 `SOPPlayerAdjudicated` 步骤播放/裁决交互的特征测试。

- [ ] **Step 1：分析依赖 + 搭 mock**

Run: `grep -nE 'import|props|useState|adjudicat|executor|onStep|on[A-Z]' src/components/Maintenance/SOPPlayerAdjudicated.tsx | head -40`
确定它对 `@/adjudication`（executor/decisionEngine）的依赖并 mock（参考 SOPMaintenancePage 的 `@/adjudication` mock，含 `injectManifestPartRegistry`/`clearManifestPartRegistry`）。Create 测试文件。

- [ ] **Step 2：写步骤播放/裁决特征测试**

断言：给定 SOP 步骤 props，渲染当前步骤；点击"执行/下一步"触发裁决并推进；裁决阻断时显示阻断原因。示例：
```tsx
it('renders current step and advances on execute', async () => {
  const sop = { id: 's1', name: '测试', steps: [{ step_index: 1, title: '步骤一' }] }
  render(<MemoryRouter><SOPPlayerAdjudicated sop={sop} /* 真实必填props */ /></MemoryRouter>)
  expect(screen.getByText('步骤一')).toBeInTheDocument()
})
```
（props 形状、按钮文案以组件真实实现为准。）

- [ ] **Step 3：补齐到 ≥70%**

Run:
```bash
npx vitest run src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx \
  --coverage --coverage.include='src/components/Maintenance/SOPPlayerAdjudicated.tsx' 2>&1 | grep 'SOPPlayerAdjudicated.tsx'
```
迭代到 ≥70%。

- [ ] **Step 4：全绿并提交**

Run: `npx vitest run src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx`
```bash
git add r-mos-frontend/src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx
git commit -m "test(phase2): SOPPlayerAdjudicated 特征测试(≥70%)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`SOPPlayerAdjudicated.tsx` ≥70%；全绿；未改动组件源码。

---

### Task 8：接入 CI 覆盖率门禁

**Files:**
- Modify: `.github/workflows/backend-ci.yml`（把三端点纳入门禁）
- Modify: `.github/workflows/frontend-ci.yml`（新增前端覆盖率门禁）
- Modify: `r-mos-frontend/vitest.config.ts`（配置 coverage provider 与三组件阈值）

**Interfaces:**
- Consumes: Task 2-7 达成的覆盖率。
- Produces: CI 门禁守护这 6 个文件的覆盖率，防止 Phase 3 重构期间回退。

- [ ] **Step 1：后端门禁纳入三端点**

在 `backend-ci.yml` 的"Pytest core 14 services coverage gate"步骤的 `--cov=` 列表中**追加**三行：
```yaml
            --cov=app.api.v1.endpoints.agent \
            --cov=app.api.v1.endpoints.training \
            --cov=app.api.v1.endpoints.teaching \
```
（保持现有 `--cov-fail-under=70`；因三端点目标 80% 高于 70%，不会拉低门禁。）

- [ ] **Step 2：前端 vitest 覆盖率阈值配置**

在 `r-mos-frontend/vitest.config.ts` 的 `test` 中新增 `coverage`：
```ts
    coverage: {
      provider: 'v8',
      include: [
        'src/pages/SOPMaintenancePage.tsx',
        'src/components/Viewer3D/Atom01Interactive.tsx',
        'src/components/Maintenance/SOPPlayerAdjudicated.tsx',
      ],
      thresholds: {
        'src/pages/SOPMaintenancePage.tsx': { lines: 70 },
        'src/components/Viewer3D/Atom01Interactive.tsx': { lines: 55 },
        'src/components/Maintenance/SOPPlayerAdjudicated.tsx': { lines: 70 },
      },
    },
```
（阈值与 Global Constraints 一致；`@vitest/coverage-v8` 已在 Task 1 加入 devDependencies。）

- [ ] **Step 3：前端 CI 增加覆盖率步骤**

在 `frontend-ci.yml` 的 `npm test` 之后新增：
```yaml
      - name: Coverage gate (god files)
        working-directory: r-mos-frontend
        run: npx vitest run --coverage
```

- [ ] **Step 4：本地验证两个门禁**

Run:
```bash
# 后端门禁（含三端点）
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && venv/bin/python -m pytest tests/ -o addopts='' -q \
  --cov=app.api.v1.endpoints.agent --cov=app.api.v1.endpoints.training --cov=app.api.v1.endpoints.teaching \
  --cov-fail-under=70 2>&1 | tail -3
# 前端门禁
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx vitest run --coverage 2>&1 | tail -5
```
Expected: 两者均通过（不报 fail-under / threshold 未达）。

- [ ] **Step 5：提交**

```bash
cd /Users/xuhehong/Desktop/r-mos
git add .github/workflows/backend-ci.yml .github/workflows/frontend-ci.yml r-mos-frontend/vitest.config.ts
git commit -m "ci(phase2): 巨型文件覆盖率纳入门禁(后端三端点 + 前端三组件)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：后端门禁含三端点且通过；前端覆盖率门禁通过；CI 配置已提交。

---

## Phase 2 收尾（最后一个 Task 完成后）

- [ ] 全量复验：后端 `pytest tests/` 全绿；前端 `vitest run --coverage` 达阈值；`tsc`/`eslint` 绿。
- [ ] 更新总控计划 `2026-06-22-quality-hardening-master-plan.md`：Phase 2 → ✅ Done。
- [ ] 更新记忆 `project_quality_hardening.md`：Phase 2 完成、6 文件覆盖率达标。
- [ ] 用中文汇报：6 文件覆盖率（前/后对比）+ 安全网就绪，可进入 Phase 3 重构。

## 自检（计划编写完成后）

- **Spec 覆盖**：Spec Phase 2 的「为巨型文件补特征测试」对应 Task 2-7；「纳入 CI 覆盖率门禁」对应 Task 8；「确认测试全绿」对应各 Task 验收 + 收尾复验。6 个 Spec 列出的目标文件各有专属 Task。
- **占位符**：无 TBD；每个测试 Task 给出可复用夹具样板 + 具体示例 + 路由/可测面清单 + 可量化的覆盖率目标与验证命令（特征测试天然是"按真实行为固化"，示例标注了"先跑看真实值再固化"）。
- **一致性**：`_build_client`/`_register_and_login`/`_grant_role_permissions`/`TEST_SCHOOL_NAME`/`injectManifestPartRegistry` 等夹具名跨 Task 一致；覆盖率阈值（80/70/55）在 Global Constraints、各 Task、Task 8 门禁三处一致。
