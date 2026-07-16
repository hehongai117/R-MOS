# P2-1b Playwright 浏览器级 E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立真浏览器黄金路径 E2E（登录→选机器人→场景→SOP 实操→报告），本地可跑、CI 有独立工作流——补上测试网 1256 个测试里"零真浏览器测试"的盲区。

**Architecture:** Playwright + chromium 落在 `r-mos-frontend/e2e/`；前端由 Playwright webServer 启 vite dev（:3000，代理 /api/v1→:8000 有保证）；后端独立起（本地=开发者的 `python main.py`，CI=workflow 起 uvicorn+PG+种子数据）；global-setup 健康检查后端并给出可操作的失败信息。3D 资产在 CI 缺失是已知事实——断言只针对页面结构与降级文案，绝不断言 canvas 内容。

**Tech Stack:** @playwright/test（chromium）、vite dev server、seed_demo_full.py、GitHub Actions

## Global Constraints

- **勘察事实为准**（2026-07-16 Explore 报告）：登录选择器 `#login-email`/`#login-password`/`button[type="submit"]`；student 登录后 → `/dashboard`、teacher → `/workbench/teaching`；场景页 `/scenarios` 点击后跳 `/maintenance?sop_id=<id>`；无 3D 资产时 `useAssemblyManifest` 静默 `hasManifest:false` → GLB 兜底 → 空则灰字"该机器人暂无 3D 模型"，SOP 面板不受影响
- 账号（seed_demo_full.py 产出）：`student1@rmos.demo`/`Student@123`、`teacher1@rmos.demo`/`Teacher@123`
- 本地库现状：3 台 READY 机器人（ATOM-01/GRx-N1/6DOF-A-06，资产完整）→ dashboard **手动选卡**；CI 种子只建 ATOM-01 → **自动选中**。测试必须两态兼容
- 前端门禁不许破：`tsc --noEmit`、`eslint --max-warnings 0`、vitest 465+ 全绿；后端 791 passed / 3 skipped 不动
- **允许的产品代码改动上限**：≤5 处 `data-testid` 添加（仅当 role/text 选择器无法稳定定位时；每处在报告登记组件与理由）。除此之外零产品改动
- Playwright 产物（playwright-report/、test-results/）入 .gitignore
- 每 commit 尾部：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_017NYSjrARdtgRbQxW5TCv7N`；不 push
- 前端命令在 `r-mos-frontend/`、后端命令在 `r-mos-backend/`（venv）下执行

---

### Task 1: Playwright 工程接入 + 登录 helper + auth.spec 本地跑通

**Files:**
- Modify: `r-mos-frontend/package.json`（devDependency + scripts）
- Create: `r-mos-frontend/playwright.config.ts`
- Create: `r-mos-frontend/e2e/global-setup.ts`
- Create: `r-mos-frontend/e2e/helpers.ts`
- Create: `r-mos-frontend/e2e/auth.spec.ts`
- Modify: `.gitignore`（仓库根，追加 playwright 产物）

**Interfaces:**
- Produces（Task 2/3 消费）：`login(page, email, password)`、常量 `ACCOUNTS.student/.teacher`；npm script `npm run e2e`

- [ ] **Step 1: 安装依赖与浏览器**

```bash
cd r-mos-frontend
npm i -D @playwright/test
npx playwright install chromium
```

package.json scripts 追加：

```json
    "e2e": "playwright test",
    "e2e:ui": "playwright test --ui"
```

- [ ] **Step 2: playwright.config.ts**

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
```

- [ ] **Step 3: global-setup（后端健康检查，失败信息可操作）**

```typescript
// e2e/global-setup.ts
export default async function globalSetup() {
  const url = 'http://localhost:8000/api/v1/health'
  try {
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`health ${resp.status}`)
  } catch (err) {
    throw new Error(
      `后端未就绪（${url}）：${err}\n` +
        '本地请先启动：cd r-mos-backend && source venv/bin/activate && python main.py\n' +
        'CI 由 e2e-browser-ci.yml 负责启动 uvicorn。',
    )
  }
}
```

- [ ] **Step 4: helpers 与 auth.spec**

```typescript
// e2e/helpers.ts
import { Page, expect } from '@playwright/test'

export const ACCOUNTS = {
  student: { email: 'student1@rmos.demo', password: 'Student@123' },
  teacher: { email: 'teacher1@rmos.demo', password: 'Teacher@123' },
} as const

export async function login(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.fill('#login-email', email)
  await page.fill('#login-password', password)
  await page.click('button[type="submit"]')
}

/** 学生进入 dashboard 后确保机器人上下文就绪：多台则点第一张卡，单台自动选中。 */
export async function ensureRobotSelected(page: Page) {
  await page.waitForURL('**/dashboard')
  // RobotCards 仅在多台时渲染选择卡；等页面稳定后按需点击
  const firstCard = page.locator('[data-testid="robot-card"]').first()
  if (await firstCard.isVisible({ timeout: 3000 }).catch(() => false)) {
    await firstCard.click()
  }
  // 上下文写入 localStorage('rmos_current_robot_id')
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem('rmos_current_robot_id')), {
      timeout: 10_000,
    })
    .not.toBeNull()
}
```

（`data-testid="robot-card"` 是本计划授权的 testid 之一：加在 DashboardPage 的 RobotCards 单卡容器上；若该组件已有稳定可选特征则用之并去掉此 testid——以实现时探索为准，报告登记。）

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login } from './helpers'

test('学生登录成功跳转 dashboard', async ({ page }) => {
  await login(page, ACCOUNTS.student.email, ACCOUNTS.student.password)
  await page.waitForURL('**/dashboard')
  await expect(page).toHaveURL(/\/dashboard/)
})

test('教师登录成功跳转教学监控台', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.waitForURL(/\/(workbench\/teaching|onboarding\/robots)/)
  // teacher 未完成 onboarding 会去 /onboarding/robots——两者都算登录成功
})

test('错误密码停留登录页并出错误提示', async ({ page }) => {
  await login(page, ACCOUNTS.student.email, 'WrongPass@999')
  await expect(page).toHaveURL(/\/login/)
  // antd message 错误提示（登录失败/密码错误类文案），宽松匹配避免绑死文案
  await expect(page.locator('.ant-message, [role="alert"]').first()).toBeVisible({ timeout: 5000 })
})
```

- [ ] **Step 5: .gitignore 追加（仓库根）**

```
# Playwright
r-mos-frontend/playwright-report/
r-mos-frontend/test-results/
```

- [ ] **Step 6: 本地验证（需本地后端在跑）**

```bash
# 终端确认后端: curl -sf http://localhost:8000/api/v1/health
cd r-mos-frontend && npx playwright test e2e/auth.spec.ts
```
Expected: 3 passed。同时跑前端门禁：`npx tsc --noEmit && npm run lint && npm test` 全绿。

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/package.json r-mos-frontend/package-lock.json r-mos-frontend/playwright.config.ts r-mos-frontend/e2e/ .gitignore
git commit -m "test(e2e): Playwright 工程接入+登录三用例(真浏览器)"
```

### Task 2: 学生黄金路径 spec + 教师 smoke spec

**Files:**
- Create: `r-mos-frontend/e2e/student-golden-path.spec.ts`
- Create: `r-mos-frontend/e2e/teacher-smoke.spec.ts`
- Modify（如需 testid，≤5 处配额内）: 相关页面组件

**Interfaces:**
- Consumes: Task 1 的 `login/ensureRobotSelected/ACCOUNTS`

**选择器探索约定（本任务核心工作方式）：** 场景卡、SOP 步骤面板、步骤提交按钮的选择器不在本计划预写——打开 `ScenarioPickerPage.tsx`、`SOPMaintenancePage` 及其 `sopMaintenance/`、`sopPlayer/` 子组件，优先用 `getByRole`/`getByText`（中文文案）定位；确实不稳定处才加 `data-testid`（计入 ≤5 配额，报告逐处登记）。**3D 区域只断言"页面未崩"（SOP 面板可见即证），绝不断言 canvas 内容。**

- [ ] **Step 1: 学生黄金路径 spec（骨架完整，选择器按探索约定落地）**

```typescript
// e2e/student-golden-path.spec.ts
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login, ensureRobotSelected } from './helpers'

test('学生黄金路径：登录→机器人上下文→场景→SOP实操→报告页', async ({ page }) => {
  // 1. 登录 + 机器人上下文（单/多台两态兼容）
  await login(page, ACCOUNTS.student.email, ACCOUNTS.student.password)
  await ensureRobotSelected(page)

  // 2. 场景选择页：至少一张场景卡，点第一张
  await page.goto('/scenarios')
  const scenarioCard = page.locator('[data-testid="scenario-card"]').first()
  await expect(scenarioCard).toBeVisible({ timeout: 15_000 })
  await scenarioCard.click()

  // 3. 落到实操工作台，SOP 面板渲染（3D 区域降级与否都不影响此断言）
  await page.waitForURL(/\/maintenance\?sop_id=/)
  const stepPanel = page.locator('[data-testid="sop-step-panel"]')
  await expect(stepPanel).toBeVisible({ timeout: 20_000 })

  // 4. 执行第一步：点步骤主操作按钮，断言出现裁决/进度反馈
  //    （按钮与反馈选择器按探索约定从 sopPlayer 组件确定）
  const primaryAction = page.locator('[data-testid="sop-step-action"]').first()
  await expect(primaryAction).toBeVisible()
  await primaryAction.click()
  await expect(page.locator('[data-testid="sop-step-feedback"]').first()).toBeVisible({
    timeout: 15_000,
  })

  // 5. 报告页可达且渲染（列表可为空，断言页面骨架）
  await page.goto('/reports')
  await expect(page.getByText(/报告|维保/).first()).toBeVisible({ timeout: 10_000 })
})
```

（上述三个 `data-testid` 是**候选名**——探索后若有稳定 role/text 选择器则替换为之并不消耗配额；需要 testid 时用这些名字加到对应组件。）

- [ ] **Step 2: 教师 smoke spec**

```typescript
// e2e/teacher-smoke.spec.ts
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login } from './helpers'

test('教师登录后教学监控台渲染', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.waitForURL(/\/(workbench\/teaching|onboarding\/robots)/)
  if (page.url().includes('/onboarding')) {
    // 本地教师已 onboard 不会进此分支；CI 新种子可能进——onboarding 页渲染即算通过
    await expect(page.getByText(/机器人|绑定/).first()).toBeVisible({ timeout: 10_000 })
  } else {
    await expect(page.getByText(/班级|监控|学生/).first()).toBeVisible({ timeout: 10_000 })
  }
})

test('SOP 管理页渲染', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.goto('/sops')
  await expect(page.getByText(/SOP/).first()).toBeVisible({ timeout: 10_000 })
})
```

- [ ] **Step 3: 本地全量 E2E + 稳定性验证**

```bash
npx playwright test                       # 全部 spec
npx playwright test e2e/student-golden-path.spec.ts --repeat-each=5   # 黄金路径抗 flake 验证
```
Expected: 全绿；repeat-each=5 零失败（这是总控计划"无 flake"验收的本地代理，CI 侧稳定性随后续推送持续验证）。前端门禁复跑全绿（tsc/eslint/vitest——若加了 testid 动了组件，vitest 快照/断言不许破）。

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/e2e/ r-mos-frontend/src/
git commit -m "test(e2e): 学生黄金路径+教师 smoke(真浏览器,3D 降级两态兼容)"
```

### Task 3: 后端 preflight 脚本 + CI 工作流

**Files:**
- Create: `r-mos-backend/scripts/e2e_preflight.py`
- Create: `.github/workflows/e2e-browser-ci.yml`

**Interfaces:**
- Consumes: seed_demo_full.py（幂等）、Task 1/2 的 `npm run e2e`

- [ ] **Step 1: preflight 脚本（种子数据健检，CI 失败提前到浏览器之前）**

```python
# r-mos-backend/scripts/e2e_preflight.py
"""浏览器 E2E 前置健检：账号可登录、学生可见机器人、场景/SOP 非空。

失败即退出非零并指明缺哪类数据——把"种子不全"从 Playwright 超时降级为秒级明确报错。
用法：BACKEND_URL=http://localhost:8000 python scripts/e2e_preflight.py
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000") + "/api/v1"


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def main() -> int:
    failures: list[str] = []

    try:
        auth = _post("/auth/login", {"email": "student1@rmos.demo", "password": "Student@123"})
        token = auth["access_token"]
        user_id = auth.get("user", {}).get("user_id") or auth.get("user_id")
        print(f"[PASS] student1 登录 (user_id={user_id})")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] student1 登录: {exc} —— 先跑 seed_demo_full.py")
        return 1

    robots = _get(f"/students/{user_id}/robots", token)
    robot_list = robots if isinstance(robots, list) else robots.get("items", robots.get("robots", []))
    if robot_list:
        print(f"[PASS] 学生可见机器人 ×{len(robot_list)}")
        robot_id = robot_list[0].get("id") or robot_list[0].get("robot_model_id")
    else:
        failures.append("学生可见机器人为空（检查 seed 的 SHARED/READY 机器人与绑定）")
        robot_id = None

    if robot_id:
        scenarios = _get(f"/scenarios?robot_model_id={robot_id}", token)
        s_list = scenarios if isinstance(scenarios, list) else scenarios.get("items", [])
        if s_list:
            print(f"[PASS] 场景列表 ×{len(s_list)}")
        else:
            failures.append(f"robot {robot_id} 场景列表为空（检查 seed 的 SOP/场景数据）")

    for f in failures:
        print(f"[FAIL] {f}")
    print("== preflight:", "通过 ✅" if not failures else f"失败 {len(failures)} 项 ❌", "==")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

（登录响应字段名 `user.user_id`/`user_id`、机器人与场景响应形态以实际 API 为准——先本地对 `python main.py` 实跑一次校准字段，报告登记。）

- [ ] **Step 2: 本地校准 preflight**

```bash
cd r-mos-backend && source venv/bin/activate
python scripts/e2e_preflight.py
```
Expected: 3 项 PASS（本地库账号与数据齐备）。字段不符先修脚本再过。

- [ ] **Step 3: CI 工作流**

```yaml
# .github/workflows/e2e-browser-ci.yml
name: Browser E2E

on:
  push:
    branches: [main]
    paths:
      - "r-mos-frontend/**"
      - "r-mos-backend/**"
      - ".github/workflows/e2e-browser-ci.yml"
  workflow_dispatch:

jobs:
  browser-e2e:
    runs-on: ubuntu-latest
    env:
      DEBUG: "true"
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: rmos_e2e_browser
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres -d rmos_e2e_browser"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
          cache-dependency-path: r-mos-backend/requirements.txt

      - name: Install backend deps
        working-directory: r-mos-backend
        run: pip install -r requirements.txt

      - name: Migrate + seed
        working-directory: r-mos-backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/rmos_e2e_browser
        run: |
          alembic upgrade head
          python scripts/seed_demo_full.py

      - name: Start backend
        working-directory: r-mos-backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/rmos_e2e_browser
          LLM_ENABLE_MOCK_FALLBACK: "true"
        run: |
          nohup python main.py > /tmp/backend.log 2>&1 &
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/api/v1/health && break
            sleep 2
          done
          curl -sf http://localhost:8000/api/v1/health

      - name: Preflight data check
        working-directory: r-mos-backend
        run: python scripts/e2e_preflight.py

      - name: Setup Node 22
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: r-mos-frontend/package-lock.json

      - name: Install frontend deps + chromium
        working-directory: r-mos-frontend
        run: |
          npm ci
          npx playwright install --with-deps chromium

      - name: Run Playwright
        working-directory: r-mos-frontend
        run: npx playwright test

      - name: Upload report on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: |
            r-mos-frontend/playwright-report/
            /tmp/backend.log

- [ ] **Step 4: 本地做一次"CI 等价"演练（临时 PG 库全链）**

```bash
createdb rmos_e2e_browser_local
cd r-mos-backend && source venv/bin/activate
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/rmos_e2e_browser_local" alembic upgrade head
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/rmos_e2e_browser_local" python scripts/seed_demo_full.py
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/rmos_e2e_browser_local" LLM_ENABLE_MOCK_FALLBACK=true python main.py &  # 记下 PID
python scripts/e2e_preflight.py
cd ../r-mos-frontend && npx playwright test
kill %1; dropdb rmos_e2e_browser_local
```
Expected: preflight 3 PASS + Playwright 全绿。**这一步在"CI 种子库（单机器人、无 3D 资产目录）"形态下验证了两态兼容与 3D 降级容忍**——注意本地 data/robot-assets 目录存在，ATOM-01 若被 seed 注册了资产则 3D 会真渲染，两种结果都算过（断言本就不碰 canvas）。

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/scripts/e2e_preflight.py .github/workflows/e2e-browser-ci.yml
git commit -m "ci: 浏览器 E2E 工作流(PG+种子+uvicorn+Playwright)+preflight 数据健检"
```

### Task 4: 文档回写 + 收口

**Files:**
- Modify: `CLAUDE.md`（Available Commands 加 e2e；测试规模行更新）
- Modify: `docs/项目交接与升级路线图.md`（T2-1 勾选——P2-1 整体完成；技术债表"测试"行更新）

- [ ] **Step 1: CLAUDE.md**

Available Commands 的 Frontend 段追加：

```markdown
/e2e-browser         # Playwright 浏览器 E2E（需本地后端在跑；cd r-mos-frontend && npm run e2e）
```

（若 CLAUDE.md 命令段格式为斜杠命令表则按现有格式融入；无对应 skill 时以注释行说明真实命令。）

- [ ] **Step 2: 路线图 T2-1 勾选**

T2-1 小节标题追加 `✅ 完成（2026-07-16）`，三条子项各标 ✅（分类/回归集=P2-1a、Playwright=本计划、CI Postgres=P0-2+P2-1a）；技术债表"测试"行改为：`~~无浏览器级 E2E~~ **已建 ✅**（Playwright 黄金路径+教师 smoke 进 CI 独立工作流）；特征测试已 marker 分类`。

- [ ] **Step 3: 全量门禁复跑 + Commit**

```bash
cd r-mos-frontend && npx tsc --noEmit && npm run lint && npm test
cd ../r-mos-backend && source venv/bin/activate && pytest -q
```
Expected: 前端三连绿；后端 791 passed / 3 skipped。

```bash
git add CLAUDE.md "docs/项目交接与升级路线图.md"
git commit -m "docs: P2-1 测试体系整体完成回写(含浏览器 E2E)"
```

---

## Self-Review 记录

1. **范围覆盖**：总控计划 P2-1 的 Playwright 项（黄金路径进 CI）→ Task 1-3；P2-1a 终审移交 5 条中 #2（CI PG 三件套翻刻）与 #3（DEBUG=true 前提）落在 Task 3 workflow，#5（审计前置健检思想）演化为 preflight 脚本；7 台缺资产机器人已由用户处置（方案 A），本地 3 台全完整。
2. **占位符扫描**：SOP 播放器交互选择器采用"探索约定 + 候选 testid 名 + ≤5 配额"的显式契约——这是对"计划无法预知组件内部结构"的诚实处理，每个候选名已定，非 TBD。preflight 字段名同理（先本地校准）。
3. **类型一致性**：`login/ensureRobotSelected/ACCOUNTS` Task 1 定义、Task 2 消费一致；`npm run e2e` Task 1 定义、Task 3 CI 使用 `npx playwright test`（等价直调，避免 npm 包装层吞退出码）；数据库名 rmos_e2e_browser 在 service 与两处 DATABASE_URL 一致。
4. **已知限制如实声明**：CI 稳定性"连续 10 次无 flake"以本地 `--repeat-each=5` 为验收代理 + CI 随后续推送持续验证（workflow 有 workflow_dispatch 可手动触发凑次数）；3D 渲染内容不在本计划断言范围（资产在 CI 不存在，降级行为已被勘察证实）。
