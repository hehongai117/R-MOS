# 全量功能+非功能测试计划 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为教师/学生/管理员三角色建立“全功能+全按钮+全 API+非功能”可审计测试计划，并完成可复现的手工+自动化回归闭环。

**Architecture:** 采用“全量清单 + 风险分级”的测试架构：页面/按钮/权限/API 四层清单互相引用，P0/P1/P2 分级覆盖；手工测试覆盖全量清单，自动化覆盖 P0/P1 与回归链路；非功能覆盖性能/稳定性/安全/兼容。

**Tech Stack:** 后端 Python(FastAPI)，前端 Vite+React，数据库 PostgreSQL，自动化建议 Playwright。

---

## 测试环境与前置条件

**后端启动方式**
- 命令（必须在后端目录 .venv 内）：
  ```bash
  cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
  source .venv/bin/activate
  export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
  ./.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
  ```
- 若 8000 绑定失败：切换至 18000，并记录实际端口到 `docs/testing/TEST_REPORT.md`。

**数据库初始化/Seeder**
- 教学演示数据：
  ```bash
  cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
  source .venv/bin/activate
  python scripts/seed_teaching_demo.py
  ```
- 诊断规则样本：
  ```bash
  cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
  source .venv/bin/activate
  python scripts/seed_teaching_diagnosis_cases.py --case all
  ```

**测试账号凭据（需由负责人补充）**
- 教师：账号=<待补充> 密码=<待补充>
- 学生：账号=<待补充> 密码=<待补充>
- 管理员：账号=<待补充> 密码=<待补充>

---

## 自动化策略（工具选型）

- 首选：Playwright（端到端 UI + API 回归）
- 覆盖范围：P0/P1 关键链路、关键页面按钮、权限边界与回归冒烟
- 证据落点：`docs/testing/TEST_REPORT.md`

---

## 清单层级（四层）

1) 页面清单（按路由/入口/角色）
2) 按钮清单（按页面/按钮/状态/权限）
3) 权限矩阵（角色 × 页面/按钮）
4) 后端 API 清单（OpenAPI → 与按钮清单交叉引用）

---

## 缺陷管理

- 记录位置：`docs/testing/TEST_REPORT.md` 的缺陷小节 + `DEVELOPMENT_LOG.md`
- 分级规则：
  - P0：阻断核心流程、数据不可恢复、越权漏洞
  - P1：关键功能错误、评分/诊断不可信、严重体验问题
  - P2：一般性功能缺陷或低频问题
- 每个缺陷必须包含：复现步骤、期望/实际、日志/截图、影响范围

---

# 任务计划（每步 2-5 分钟，频繁提交）

### Task 1: 生成页面清单（按角色与入口）

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 列出所有路由与页面入口**
- 手工整理前端路由与菜单入口，按教师/学生/管理员归类。

**Step 2: 标注页面状态**
- 为每页标注空态/有数据/异常/权限不足。

**Step 3: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add full page inventory for test plan"
```

### Task 2: 生成按钮清单（全按钮覆盖）

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 列出每页按钮/交互控件**
- 按页面列出按钮、链接、表单提交、快捷操作。

**Step 2: 为每按钮定义 3 条路径**
- 正常路径/异常路径/权限路径。

**Step 3: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add full button inventory for test plan"
```

### Task 3: 权限矩阵与角色覆盖

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 角色×页面/按钮矩阵**
- 教师/学生/管理员逐列标注可见/可用/不可用。

**Step 2: 标注越权与边界用例**
- 每个不可用项增加越权验证。

**Step 3: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add role permission matrix"
```

### Task 4: 后端 API 清单与按钮交叉引用

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 从 OpenAPI 抽取接口清单**
- 以 `openapi.json` 的路径和方法为基础，列出 API 列表。

**Step 2: 按按钮映射 API**
- 每个按钮绑定其对应 API（可多对一）。

**Step 3: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add api inventory and button mapping"
```

### Task 5: 风险分级（P0/P1/P2）

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 标注 P0/P1/P2**
- P0：关键闭环与数据写入
- P1：高频操作与重要读写
- P2：低频展示

**Step 2: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add risk tiering for test cases"
```

### Task 6: 自动化覆盖策略（Playwright）

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 定义自动化范围**
- P0/P1 主流程、关键按钮、权限回归。

**Step 2: 定义用例模板**
- 入口、步骤、断言、证据。

**Step 3: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add automation strategy"
```

### Task 7: 非功能测试计划

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`

**Step 1: 性能基线**
- 关键页面首屏、关键 API 响应。

**Step 2: 稳定性与安全**
- 长跑/并发、越权、输入校验。

**Step 3: 兼容性矩阵**
- 桌面浏览器：Chrome/Edge/Safari。

**Step 4: 提交**
```bash
git add docs/testing/TEST_PLAN.md
git commit -m "docs: add non-functional test plan"
```

### Task 8: 证据模板与收口规则

**Files:**
- Modify: `docs/testing/TEST_REPORT.md`

**Step 1: 定义证据模板**
- 每条用例包含：环境、步骤、证据片段、结论。

**Step 2: 提交**
```bash
git add docs/testing/TEST_REPORT.md
git commit -m "docs: add test report templates"
```

---

## 执行说明（阶段收官）
- 每次回归完成后：更新 `docs/testing/TEST_REPORT.md` 并在 `DEVELOPMENT_LOG.md` 建索引链。
- 严禁在未完成证据收集时标记 PASS。

---

Plan complete and saved to `docs/plans/2026-02-03-full-project-test-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration

2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
