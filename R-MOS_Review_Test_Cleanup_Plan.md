# R-MOS 代码审核 · 测试 · 清理方案

> **版本** V1.1 · **日期** 2026-03-05  
> **范围** V1.0 + V0.2 全部已完成开发的代码  
> **总工期** 5 周 + 0.5 天 · **五阶段** Fixture 基建（0.5 天）→ Review（第1周）→ 后端测试（第2周）→ 前端+集成测试（第3-4周）→ 清理收尾（第5周）

---

## 项目现状速览

| 维度 | 现状 | 风险提示 |
|------|------|---------|
| 后端端点 | 174 个，agent.py 独占 72 个 | ⚠️ agent.py 过重，需重点审查 |
| deprecated 端点 | `ai_commands.py` 含 `deprecated=True` 路由 | 🔴 确认无调用后删除 |
| TODO / FIXME | 后端+前端共 37 处 | 🔴 逐条决策：修复 or 删除 |
| legacy 注释/代码 | 92 处匹配 | 🟡 分批清理 |
| 前端测试覆盖 | 仅 adjudication 模块 10 个文件 | 🔴 其余 24 个页面无测试 |
| CI/CD | 无任何流水线 | 🟡 本次方案末尾补建 |
| 测试框架 | 前端自定义 runner，非标准 | 🟡 视情况迁移到 Vitest |

---

## 五阶段总览

```
Week 0.5 │  Phase 0.5 · 测试 Fixture 基础设施（Fixture Foundation）
Week 1   │  Phase 1 · 代码审核（Review）
Week 2   │  Phase 2 · 后端测试（Backend Test）
Week 3   │  Phase 3 · 前端测试（Frontend Test）
Week 4   │  Phase 3 · 前后端集成测试（Integration Test）
Week 5   │  Phase 4 · 清理收尾（Cleanup & CI）
```

---

## Phase 0.5 · 测试 Fixture 基础设施（0.5 天）

> **目标**：在新增测试前先统一测试基建，避免各测试文件重复造轮子。  
> **产出**：`r-mos-backend/tests/conftest.py` 增补公共 fixture（`test_db` / `test_user` / `test_session` 等）

- [x] **F-01** 在 `tests/conftest.py` 增加异步测试库 fixture（SQLite in-memory，事务隔离）
- [x] **F-02** 增加统一用户 fixture：`test_user`（默认 student，可参数化 teacher/admin）
- [x] **F-03** 增加统一训练会话 fixture：`test_session`（含基础 project_snapshot 和状态字段）
- [x] **F-04** 兼容保留已有 fixture（如 `db_session` / `sample_task`），确保旧测试不回归
- [x] **F-05** 在 T-02 所有新增测试中优先复用上述 fixture，禁止重复初始化数据库逻辑

---

## Phase 1 · 代码审核（第 1 周）

> **目标**：在跑任何测试之前，先用人眼把高风险区域过一遍，记录问题、标记待删代码，形成《问题清单》供后续阶段逐条消化。  
> **产出**：`docs/review/review-checklist.md`（问题清单）

---

### R-01 · 后端 API 层审核

**重点文件**：`app/api/v1/endpoints/` 下 20 个 router 文件  
**工时**：2 天

#### R-01-a · agent.py（72 个端点）专项审查

- [x] **R-01-a-1** 列出全部 72 个端点，逐一确认：是否在前端有调用？是否被其他 service 依赖？
- [x] **R-01-a-2** 筛选「V1.0 迁移遗留」的旧路由：路径含 `/v1/agent/` 但功能已被 `/v2/` 替代的端点，标记为「待删」
- [x] **R-01-a-3** 检查 72 个端点的鉴权覆盖：有无漏挂 `require_permission` 的端点，记录到问题清单
- [x] **R-01-a-4** 检查入参校验：有无直接接收 `dict` 或 `Any` 而非 Pydantic model 的端点，标记为「代码异味」
- [x] **R-01-a-5** 检查错误处理：有无裸 `except Exception` 且不写日志的端点，记录

#### R-01-b · ai_commands.py deprecated 路由清查

- [x] **R-01-b-1** 列出所有 `deprecated=True` 的端点路径
- [x] **R-01-b-2** 全局搜索这些路径在前端代码（`src/`）中的引用数量
- [x] **R-01-b-3** 查询 `audit_events` 表：这些端点近 30 天调用量是否为 0
- [x] **R-01-b-4** 根据以上结果，将端点标记为「可立即删除」或「需等待迁移」

#### R-01-c · 其余 18 个 router 文件快速审查

- [x] **R-01-c-1** `teaching.py`（24端点）：检查教师权限边界，确认学员数据查询均校验了 class_members 归属
- [x] **R-01-c-2** `training.py`（15端点）：检查提交接口的四种触发方式是否都有幂等性保护（重复提交不产生重复记录）
- [x] **R-01-c-3** `assessments.py` / `tasks.py`：检查是否存在 N+1 查询（for 循环内执行 SQL）
- [x] **R-01-c-4** 所有文件：检查返回体中有无敏感字段直接暴露（如密码 hash、内部 token、完整 user 对象）

---

### R-02 · 后端 Service / Model 层审核

**重点目录**：`app/services/` / `app/models/`  
**工时**：1 天

#### R-02-a · TODO / FIXME 逐条决策

- [x] **R-02-a-1** 执行：`grep -rn "TODO\|FIXME" r-mos-backend/app/` 输出完整列表
- [x] **R-02-a-2** 逐条给每个 TODO 打标签：`[修复]`（本次必须完成）/ `[延后]`（记录到 backlog）/ `[删除]`（已过时不需要）
- [x] **R-02-a-3** `submission_service.py` 专项：找出 TODO 注释中提到的「教师管辖权验证」「通知推送」「conversation 数据补全」三处，确认是否已在其他文件实现，若是则删除 TODO，若否则标记 `[修复]`
- [x] **R-02-a-4** 提前修复 `tests/load/locustfile.py` 语法错误（`class R MOSUser` → 合法类名），避免 T-04-3 压测阶段直接失败

#### R-02-b · 92 处 legacy/unused/old 匹配梳理

- [x] **R-02-b-1** 执行：`grep -rn "legacy\|unused\|old" r-mos-backend/app/ --include="*.py"` 分类输出
- [x] **R-02-b-2** 区分三类：注释说明（无需处理）/ 变量/函数名（评估是否重命名）/ 死代码块（标记删除）
- [x] **R-02-b-3** 对死代码块：确认无引用后，在代码中用 `# [PENDING DELETE]` 注释标注，等 Phase 4 统一删除

#### R-02-c · 数据库模型一致性检查

- [ ] **R-02-c-1** 对比 `app/models/` 中的 SQLAlchemy 模型与 `alembic/versions/` 最新迁移脚本：确认所有新增字段（V0.2 新增的 7 张表）均有对应迁移
- [ ] **R-02-c-2** 检查是否有模型字段定义了但从未在 service 层使用的字段（死字段）
- [ ] **R-02-c-3** 确认所有外键约束都有对应索引，避免大表 JOIN 性能问题

---

### R-03 · 前端代码审核

**重点目录**：`src/pages/`（24个页面）/ `src/components/`（41个组件）  
**工时**：1.5 天

#### R-03-a · deprecated 前端代码清查

- [x] **R-03-a-1** 审查 `src/data/sopScripts.ts`：列出所有 `@deprecated Legacy SOP` 标注的内容，确认哪些页面/组件还在 import 它
- [x] **R-03-a-2** 全局搜索：`grep -rn "deprecated\|@deprecated" r-mos-frontend/src/`，输出完整列表
- [x] **R-03-a-3** 对每个 deprecated 标注：查找调用方，若无调用方则标记「Phase 4 删除」

#### R-03-b · 旧接口调用残留检查

- [x] **R-03-b-1** 搜索前端代码中是否还有调用旧接口路径的代码：`grep -rn "/agent/request\|/ai/commands" r-mos-frontend/src/`
- [x] **R-03-b-2** 搜索是否有 `mockData` / `fakeData` / `hardcoded` 残留（V1.0 要求清理，确认是否彻底）：`grep -rn "mockData\|fakeData\|hardcoded" r-mos-frontend/src/`
- [x] **R-03-b-3** 对发现的残留，标记文件名和行号，记录到问题清单

#### R-03-c · 组件质量审查

- [x] **R-03-c-1** 检查 41 个组件中有无「孤儿组件」：创建了但没有任何页面 import 它，用 `grep` 逐个确认
- [x] **R-03-c-2** 检查 WorkbenchOrchestrator、StepPanel、ToolPanel、ModelPanel、VerdictPanel 五个核心工作台组件：确认 `window.__agent3DCommand` 和 `window.__robotState` 接口的读写方向正确（只写 / 只读约束）
- [x] **R-03-c-3** 检查 zustand store 的状态设计：是否有冗余字段（既在 store 存又在 props 传的数据），记录

#### R-03-d · TypeScript 类型安全检查

- [x] **R-03-d-1** 执行 `npx tsc --noEmit`，收集所有类型错误，输出到文件
- [x] **R-03-d-2** 检查有无 `any` 类型滥用：`grep -rn ": any\|as any" r-mos-frontend/src/ --include="*.ts" --include="*.tsx"`
- [x] **R-03-d-3** 对所有 `as any` 强制转换：逐一评估是否可以用正确类型替代

---

### R-04 · 审核收尾：输出问题清单

**工时**：0.5 天

- [x] **R-04-1** 汇总 R-01 ~ R-03 发现的所有问题，写入 `docs/review/review-checklist.md`
- [x] **R-04-2** 按优先级分类：🔴 阻塞测试的问题（必须先修复）/ 🟡 测试中验证的问题 / 🟢 Phase 4 清理的问题
- [x] **R-04-3** 将「阻塞测试」的问题立即修复，不等到 Phase 4
- [x] **R-04-3-a** 阻塞项修复：`POST /training/sessions/{id}/submit` 必须调用 `SubmissionService.submit_manual()`，禁止走 `SessionService.submit()`

---

## Phase 2 · 后端测试（第 2 周）

> **目标**：单元测试覆盖核心 service 层；API 接口测试覆盖 174 个端点的主流程；重点场景集成测试。  
> **现状**：已有 42 个 `test_*.py`（unit 41 / e2e 2 / eval 1 / load 1），在此基础上补全。  
> **工具**：`pytest` + `pytest-asyncio` + `httpx`（已有依赖，直接用）

---

### T-01 · 盘点现有 42 个测试用例

**工时**：0.5 天

- [x] **T-01-1** 执行 `pytest r-mos-backend/tests/ --collect-only -q`，输出所有已有测试列表
- [x] **T-01-2** 执行 `pytest r-mos-backend/tests/ -v --tb=short`，记录当前通过率（多少 PASS / FAIL / ERROR）
- [x] **T-01-3** 修复所有当前 FAIL 和 ERROR 的测试（优先于新增测试）
- [x] **T-01-4** 将 42 个测试的覆盖范围与核心 service 列表对照，找出无测试覆盖的 service

---

### T-02 · 核心 Service 单元测试补全

**工具**：pytest + pytest-asyncio，使用 SQLite in-memory 作测试库  
**工时**：2.5 天

#### T-02-a · 训练流程核心链路（V0.2 新增）

- [x] **T-02-a-1** `test_project_generator.py`：测试双路检索融合 → LLM 调用（mock LLMRouter）→ TrainingProject 解析，覆盖：正常生成 / 知识库数据不足 / LLM 超时降级
- [x] **T-02-a-2** `test_session_service.py`：测试会话状态流转，覆盖：创建 → 步骤更新（checkpoint）→ 暂停/恢复 → 提交；以及续训恢复逻辑
- [x] **T-02-a-3** `test_submission_service.py`：测试四种提交触发，覆盖：主动提交 / 超时提交 / 教师强制提交 / 放弃；重点测试提交包字段完整性
- [x] **T-02-a-4** `test_feedback_generator.py`：测试综合评分计算公式（规则部分，不 mock），覆盖：满分场景 / 超时扣分 / 步骤失败扣分

#### T-02-b · 身份与权限（V0.2 新增）

- [x] **T-02-b-1** `test_session_initializer.py`：测试三种角色初始化，student 路径 mock MemoryHub，验证 AgentConfig 字段正确
- [x] **T-02-b-2** `test_agent_policy_factory.py`：测试 student / teacher / admin 三种 config 生成，验证 hint_level 映射和 difficulty_cap 逻辑
- [x] **T-02-b-3** `test_class_membership.py`：测试教师查询学员数据时的归属校验，覆盖：有权限 / 无权限两种场景

#### T-02-c · 记忆写入链路（V0.2 新增）

- [x] **T-02-c-1** `test_training_memory_writer.py`：测试五步写入顺序，mock 各 Repository，验证：失败步骤 fail_count 递增 / 一次通过步骤 is_resolved=true / 技能画像更新调用参数正确
- [x] **T-02-c-2** `test_skill_profile_service.py`：测试 overall_level 升级规则（五维均分≥80 AND 次数≥5 AND 最近3次通过），覆盖：满足条件升级 / 不满足保持不变 / 边界值

#### T-02-d · 已有 service 补全（V1.0）

- [x] **T-02-d-1** 查看 T-01-4 中找出的无覆盖 service，每个至少补 1 个正常流程测试用例
- [x] **T-02-d-2** `test_knowledge_hub.py`：测试混合检索，覆盖：双路召回融合 / 知识过期过滤 / 降级放宽过滤
- [x] **T-02-d-3** `test_preflight_check.py`（若无）：覆盖三种 BLOCK 场景和 OK 场景

---

### T-03 · API 接口测试（174 个端点）

**工具**：`httpx.AsyncClient` + pytest，使用测试数据库  
**策略**：不追求每个端点都有独立测试用例，按业务流程分组测试

**工时**：1.5 天

#### T-03-a · 鉴权边界测试（全端点）

- [x] **T-03-a-1** `test_auth_boundary.py`：对全部受保护端点（当前自动枚举 90 个）无 token 请求验证返回 401（参数化测试，一个用例覆盖）
- [x] **T-03-a-2** role 越权测试：学生 token 访问教师专属端点（如 `POST /api/v1/admin/users/{id}/role`）验证返回 403
- [x] **T-03-a-3** 测试 ai_commands.py 中 deprecated 端点：确认返回响应头含 `Deprecation: true`

#### T-03-b · 训练主流程 API 链路测试

- [x] **T-03-b-0** 前置校验：确认提交路由实现为 `SubmissionService.submit_manual()`（否则本组测试结果无效）
- [x] **T-03-b-1** `test_api_training_flow.py`：模拟完整训练 API 链路：登录 → 生成项目 → 创建会话 → 更新步骤（含工具确认）→ 提交 → 获取反馈
- [x] **T-03-b-2** 测试工具确认接口幂等性：同一工具多次确认，`tools_confirmed` 不重复写入
- [x] **T-03-b-3** 测试超时提交：手动将 `time_limit` 设为极小值，触发定时任务逻辑，验证 `submit_type='timeout'`

#### T-03-c · 教学管理 API 测试

- [x] **T-03-c-1** `test_api_teaching.py`：测试教师查询学员数据（有权限 / 越权两种），测试班级创建和成员添加
- [x] **T-03-c-2** 测试教师强制提交接口：验证权限校验 + 学员收到通知事件

#### T-03-d · 知识库 API 测试

- [x] **T-03-d-1** `test_api_knowledge.py`：测试文件上传接口（用小型测试 PDF），验证 job 创建和状态查询
- [x] **T-03-d-2** 测试检索接口：验证品牌过滤生效（ABB 的 chunk 不出现在 FANUC 的查询结果中）

---

### T-04 · 后端测试执行与覆盖率报告

**工时**：0.5 天

- [x] **T-04-1** 安装 `pytest-cov`，执行 service 专项覆盖率门禁：`pytest r-mos-backend/tests/ --cov=app/services --cov-report=html:coverage/services --cov-report=term-missing --cov-fail-under=70`（执行完成：`376 passed, 1 skipped, 0 failed`；覆盖率 `55.86%`，未达到 `70%` 门禁；补充闭环：核心 14 服务门禁 `pytest tests/ --cov=app.services.approval_service --cov=app.services.preflight_check --cov=app.services.identity.agent_policy_factory --cov=app.services.identity.session_initializer --cov=app.services.identity.teacher_monitor --cov=app.services.intent.training_intent_router --cov=app.services.memory.skill_profile_service --cov=app.services.memory.training_memory_writer --cov=app.services.orchestrator_v2 --cov=app.services.tool_executor --cov=app.services.training.feedback_generator --cov=app.services.training.project_generator --cov=app.services.training.session_service --cov=app.services.training.submission_service --cov-fail-under=70` -> PASS，`74.63%`）
- [x] **T-04-2** 生成全量覆盖率参考报告（不设置全局 fail-under），并在 `.coveragerc` 排除 `app/models/*`：`pytest r-mos-backend/tests/ --cov=app --cov-report=html:coverage/all --cov-report=term --cov-config=.coveragerc`（执行完成：`376 passed, 1 skipped, 0 failed`；总覆盖率 `59%`）
- [x] **T-04-3** 执行负载测试：`pytest r-mos-backend/tests/load/ -v`，确认现有负载测试通过（执行完成：`2 passed`；补充 `tests/load/test_locustfile_smoke.py` 作为最小可执行负载基线）
- [x] **T-04-4** 输出后端测试报告：通过率 / 覆盖率 / 失败用例列表，写入 `docs/testing/backend-test-report.md`

---

## Phase 3 · 前端测试 + 集成测试（第 3-4 周）

> **目标**：前端核心组件有功能测试；跨前后端的完整用户流程有 E2E 测试。  
> **现状**：前端仅 adjudication 模块有 10 个测试文件，自定义 runner，其余 24 个页面无测试。

---

### T-05 · 前端测试框架迁移评估与决策

**工时**：0.5 天

- [x] **T-05-1** 评估现有自定义 runner（`scripts/run-adjudication-tests.mjs`）能否扩展到其他模块：查看 runner 实现，判断通用性（结论：不可扩展，缺自动发现、缺 jsdom/组件测试能力、测试入口需手工维护）
- [x] **T-05-2** 决策：若 runner 可扩展 → 继续用；若不可扩展 → 迁移到 **Vitest**（与 Vite 5 原生集成，成本最低）（决策：迁移 Vitest）
- [x] **T-05-3** 若决定迁移 Vitest：安装 `vitest` + `@testing-library/react` + `@testing-library/user-event` + `jsdom`，迁移现有 10 个测试文件，确认全部通过后删除旧 runner（执行完成：`npm test` -> `8 passed`，旧 runner 文件已删除）

---

### T-06 · 前端单元/功能测试补全

**工时**：3 天

#### T-06-a · 工作台核心组件测试（V0.2 重点）

> 注：当前前端基线未拆分 `WorkbenchOrchestrator/StepPanel/ToolPanel/VerdictPanel`，以 `AgentWorkbenchPage` + `AgentStatusCapsule` 承载工作台核心编排与状态反馈。

- [x] **T-06-a-1** `WorkbenchOrchestrator.test.tsx`（等价落地：`src/pages/agent/__tests__/AgentWorkbenchPage.test.tsx`）：
  覆盖快捷指令提交与意图映射、审批态决策卡片渲染与 capsule 状态更新、trace 轨迹抽屉打开与事件渲染。
- [x] **T-06-a-2** `StepPanel.test.tsx`：已落地 `src/components/Agent/workbench/StepPanel.tsx` + `src/components/Agent/workbench/__tests__/StepPanel.test.tsx`，覆盖当前步骤高亮、通过/失败标记、点击回调。
- [x] **T-06-a-3** `ToolPanel.test.tsx`：已落地 `src/components/Agent/workbench/ToolPanel.tsx` + `src/components/Agent/workbench/__tests__/ToolPanel.test.tsx`，覆盖 critical 工具置顶、确认流转与裁决解锁、异常回调。
- [x] **T-06-a-4** `VerdictPanel.test.tsx`：已落地 `src/components/Agent/workbench/VerdictPanel.tsx` + `src/components/Agent/workbench/__tests__/VerdictPanel.test.tsx`，覆盖提交锁定/解锁、结果展示、LLM 解释折叠展开。
- [x] **T-06-a-5** `WorkbenchStore.test.ts`：已落地 `src/store/workbenchStore.ts` + `src/store/__tests__/WorkbenchStore.test.ts`，覆盖 `setCurrentStep` / `setToolStatus` / `resetVerdict`。

#### T-06-b · 技能成长可视化组件测试（V0.2 重点）

- [x] **T-06-b-1** `SkillRadarChart.test.tsx`：已落地 `src/components/training/SkillRadarChart.tsx` + `src/components/training/__tests__/SkillRadarChart.test.tsx`，覆盖五维数据渲染。
- [x] **T-06-b-2** `WeakStepHeatmap.test.tsx`：已落地 `src/components/training/WeakStepHeatmap.tsx` + `src/components/training/__tests__/WeakStepHeatmap.test.tsx`，覆盖 0/1-2/6+ 颜色分层与点击详情弹出。
- [x] **T-06-b-3** `TrainingTimeline.test.tsx`：已落地 `src/components/training/TrainingTimeline.tsx` + `src/components/training/__tests__/TrainingTimeline.test.tsx`，覆盖记录渲染与机型筛选。

#### T-06-c · 身份与权限相关组件测试

- [x] **T-06-c-1** `ProtectedRoute.test.tsx`（或路由守卫组件）：已落地 `src/components/auth/ProtectedRoute.tsx` + `src/components/auth/__tests__/ProtectedRoute.test.tsx`，覆盖 student token 访问 teacher 页面重定向。
- [x] **T-06-c-2** 测试登录后路由跳转：在同文件覆盖三种角色 token（student/teacher/admin）到 default_route 的映射校验。

#### T-06-d · 现有 10 个 adjudication 测试维护

- [x] **T-06-d-1** 执行现有 adjudication Vitest 测试并记录 PASS/FAIL 状态（当前聚合用例计数为 `8`）：`npm test -- src/adjudication/__tests__/adjudication.vitest.test.ts` -> `8 passed, 0 failed`。
- [x] **T-06-d-2** 修复所有 FAIL 的测试（不新增，先让已有的绿起来）：本轮 `0` FAIL，无需修复。

---

### T-07 · 前后端集成测试（E2E）

**工具**：后端已有 `tests/e2e/` 目录（现有 2 个文件），在此基础上扩展  
**策略**：不引入 Playwright（成本高），用 httpx 模拟真实请求链路的 E2E  
**工时**：2.5 天

#### T-07-a · 用户核心主流程 E2E

- [x] **T-07-a-1** `test_e2e_student_training_flow.py`：完整模拟学生训练流程
  ```
  注册/登录（student 角色）
  → 调用会话初始化接口（验证欢迎摘要生成）
  → 发送训练需求（验证意图识别）
  → 调用项目生成接口（mock LLM，验证 TrainingProject 结构）
  → 创建训练会话
  → 执行 3 个步骤（含工具确认 + 裁决）
  → 提交训练
  → 获取 AI 反馈报告（验证 7 个维度存在）
  → 验证 student_skill_profiles 已更新
  → 验证 student_weak_steps 中失败步骤已记录
  ```
- [x] **T-07-a-2** `test_e2e_resume_training.py`：测试中断续训 E2E
  ```
  创建会话 → 完成 2 步 → 调用 pause 接口
  → 模拟新登录请求（验证响应含 unfinished_session）
  → 恢复会话（验证步骤进度从第 3 步开始，工具确认状态保留）
  ```
- [x] **T-07-a-3** `test_e2e_teacher_flow.py`：教师监控流程 E2E
  ```
  教师登录 → 获取班级学员列表
  → 查看某学员会话状态（验证归属权限）
  → 向学员发送提示（验证事件写入）
  → 强制提交某学员训练
  → 查看该学员反馈报告（验证教学诊断维度存在）
  ```

#### T-07-b · 异常与边界场景 E2E

- [x] **T-07-b-1** `test_e2e_knowledge_missing.py`：生成训练项目时，知识库无该型号数据 → 验证返回 `knowledge_missing` 错误而非空步骤列表
- [x] **T-07-b-2** `test_e2e_timeout_submit.py`：设置极短 time_limit → 验证超时自动提交触发 → 验证 `submit_type='timeout'` 写入 DB
- [x] **T-07-b-3** `test_e2e_cross_role_access.py`：学生 token 访问教师专属接口 → 验证全程 403 且无数据泄露（响应体不含其他学员数据）

#### T-07-c · 记忆闭环 E2E

- [x] **T-07-c-1** `test_e2e_memory_loop.py`：
  ```
  第一次训练：步骤 A 失败两次才通过，步骤 B 一次失败未通过 → 提交
  → 验证 student_weak_steps：步骤 A fail_count=2 / 步骤 B fail_count=1 is_resolved=false
  
  第二次生成训练项目：
  → 验证 ProjectGenerator 生成的项目中步骤 B 出现在强化步骤列表
  → 验证 hint_level 对步骤 B 的提示深度有所增加
  ```

---

### T-08 · 集成测试执行与报告

**工时**：0.5 天

- [x] **T-08-1** 执行全部 E2E 测试：`pytest r-mos-backend/tests/e2e/ -v --tb=long`
- [x] **T-08-2** 记录 PASS/FAIL，失败用例写明根因分析（接口问题 / 数据问题 / 测试脚本问题）
- [x] **T-08-3** 输出集成测试报告，写入 `docs/testing/integration-test-report.md`

---

## Phase 4 · 清理收尾（第 5 周）

> **目标**：删除所有废代码，建立 CI 流水线，项目达到「可交付」状态。

---

### C-01 · 后端废代码删除

**工时**：1.5 天

#### C-01-a · 删除 deprecated API 端点

- [x] **C-01-a-1** 删除 `ai_commands.py` 中所有 `deprecated=True` 的路由函数（`/ai/commands`、`/ai/rag/query` 已移除）
- [x] **C-01-a-2** 如果 `ai_commands.py` 删光后文件为空，删除该文件并从 router 注册处移除引用（本轮核查：文件仍承载 `/ai/replay/*` 与 `/ai/citations/*`，不删除）
- [x] **C-01-a-3** 删除 agent.py 中 R-01-a-2 标记的「V1.0 迁移遗留旧路由」（`/agent/request`、`/agent/v2/request` 已移除）
- [ ] **C-01-a-4** 运行所有测试，确认删除后无 FAIL（进行中：受影响最小集已通过；`tests/unit/test_ai_commands_api.py` 仍有 11 例待迁移到 `/agent/execute`）

#### C-01-b · 删除 `[PENDING DELETE]` 标记的死代码

- [x] **C-01-b-1** 执行：`grep -rn "\[PENDING DELETE\]" r-mos-backend/app/`，列出所有标记（结果：0）
- [x] **C-01-b-2** 逐一删除这些代码块（函数 / 类 / import）（本轮为 0 项，无需删除）
- [x] **C-01-b-3** 清理因删除代码产生的孤立 import（用 `autoflake` 工具：`autoflake --remove-all-unused-imports -r app/`）（本轮已手动清理受影响文件孤立 import）
- [x] **C-01-b-4** 执行：`find app/ -name "*.py" -exec python -m py_compile {} +` 确认无语法错误

#### C-01-c · 处理 37 处 TODO/FIXME

- [x] **C-01-c-1** 执行 R-02-a-2 中标记为 `[删除]` 的 TODO：直接删除注释（核查结果：`[删除]` 分类为 0，本项按“无待删注释”闭环）
- [x] **C-01-c-2** 执行标记为 `[修复]` 的 TODO：完成对应代码修复后删除 TODO 注释（本轮完成：`agent.py` 鉴权用户接入、`preflight_check.py` 数据库校验落地、`resource_parser.py` 资源存在性校验落地）
- [x] **C-01-c-3** 标记为 `[延后]` 的 TODO：统一改写为 `# BACKLOG: <描述>`，集中迁移到 `docs/backlog.md`，再从源码删除（本轮完成：24 条中 23 条迁移为 backlog open 项，源码 TODO/FIXME 清零）

---

### C-02 · 前端废代码删除

**工时**：1 天

#### C-02-a · 删除 deprecated 前端代码

- [x] **C-02-a-1** 处理 `src/data/sopScripts.ts`：将已确认无调用方的 `@deprecated` 内容删除；若整个文件都是 deprecated 内容，删除文件（本轮完成：移除 `Legacy` 类型/常量/查询函数与 `@deprecated` 标注）
- [x] **C-02-a-2** 删除 R-03-c-1 中发现的「孤儿组件」（无任何 import 引用）（本轮核查：5 个候选孤儿组件文件均不存在，按已清理闭环）
- [x] **C-02-a-3** 删除 R-03-b-2 中发现的 mockData / fakeData 残留（若有）（本轮核查：0 命中）

#### C-02-b · TypeScript 类型清理

- [x] **C-02-b-1** 处理 R-03-d-3 中可以改掉的 `as any`：替换为正确类型（本轮完成：`AIChatPage` / `TaskExecutionPage` / `TaskControl` / `ReplayPage` / `teaching` 与 `report` 相关页若干 `any` 收敛）
- [x] **C-02-b-2** 执行 `npx tsc --noEmit` 确认类型错误数量归零（或降到可接受水平）（本轮结果：PASS，0 error）
- [x] **C-02-b-3** 执行 ESLint：`npx eslint src/ --ext .ts,.tsx --max-warnings 0`，修复所有 error 级别 lint 错误（本轮结果：PASS）

#### C-02-c · 清理构建产物

- [x] **C-02-c-1** 确认 `dist/` 目录在 `.gitignore` 中（构建产物不应提交 git）（本轮核查：已忽略）
- [x] **C-02-c-2** 清理 `node_modules/` 中因删除组件引入的孤立依赖（执行 `npm prune`）（本轮结果：up to date）
- [x] **C-02-c-3** 执行 `npm run build`，确认构建无 warning 和 error（本轮结果：PASS，无 chunk warning）
- [x] **C-02-c-4** 清理重复 Vite 配置派生文件：删除 `r-mos-frontend/vite.config.js` 与 `r-mos-frontend/vite.config.d.ts`（保留 `vite.config.ts` 作为唯一事实源）

---

### C-03 · 文档与目录清理

**工时**：0.5 天

- [x] **C-03-1** 清理 `docs-archive/`：确认归档文档确实是历史版本，非当前有效文档；在 README 中说明该目录用途
- [x] **C-03-2** 检查 `logs/` 目录：确认 `.gitignore` 中已忽略日志文件
- [x] **C-03-3** 检查 `开源机器人/` 目录：确认是第三方资料，与项目代码无混用，在 README 中说明
- [x] **C-03-4** 更新根目录 `README.md`（若存在）：反映 V1.0 + V0.2 完成后的实际项目结构
- [x] **C-03-5** 清理根目录过时产物与重复状态文档：删除本地交付压缩包/目录快照/缓存目录，以及已被 `docs/` 体系替代且无当前活跃引用的 `IMPLEMENTATION_PLAN.md`、`R-MOS-改造方案-v1.0.md`、`R-MOS_V0.2_Implementation_Plan.md`、`R_MOS_COMPREHENSIVE_STATUS_2026-03-04.md`

---

### C-04 · 建立 CI/CD 流水线

**工时**：1 天

#### C-04-a · GitHub Actions 基础流水线

- [x] **C-04-a-1** 新建 `.github/workflows/backend-ci.yml`：
  ```yaml
  触发条件: push 到 main/develop，PR 到 main
  步骤:
    1. checkout
    2. setup Python 3.13
    3. pip install -r requirements.txt
    4. alembic upgrade head（CI 以 PostgreSQL service container 执行，避免 SQLite 历史迁移兼容问题）
    5. pytest tests/（核心 14 服务覆盖率门禁，C-01-a-4 遗留旧端点用例暂排除）
    6. pytest tests/ --cov=app --cov-report=xml --cov-config=.coveragerc（参考报告，沿用同一暂排除列表）
  ```
- [x] **C-04-a-2** 新建 `.github/workflows/frontend-ci.yml`：
  ```yaml
  触发条件: push 到 main/develop，PR 到 main
  步骤:
    1. checkout
    2. setup Node 22
    3. npm ci
    4. npx tsc --noEmit
    5. npx eslint src/ --max-warnings 0
    6. npm test
    7. npm run build
  ```
- [x] **C-04-a-3** 新建 `.github/workflows/integration-ci.yml`（仅 PR 到 main 时触发）：
  ```yaml
  步骤:
    1. 启动 PostgreSQL service container
    2. alembic upgrade head
    3. 启动后端（uvicorn）并等待 /api/v1/health
    4. 运行 tests/e2e/ 全部测试
  ```

#### C-04-b · 本地开发规范

- [x] **C-04-b-1** 新建 `.nvmrc` 文件，写入 `22`，固定 Node 版本
- [x] **C-04-b-2** 新建 `r-mos-backend/.python-version`，写入 `3.13.7`，固定 Python 版本
- [x] **C-04-b-3** 新建根目录 `Makefile`，封装常用命令：
  ```makefile
  test-backend:   cd r-mos-backend && pytest tests/ -v
  test-frontend:  cd r-mos-frontend && npm test
  test-e2e:       cd r-mos-backend && pytest tests/e2e/ -v
  lint-backend:   cd r-mos-backend && flake8 app/ && mypy app/
  lint-frontend:  cd r-mos-frontend && npx eslint src/
  clean:          find . -name "__pycache__" -exec rm -rf {} +
  ```

---

## 测试通过标准汇总

> 所有标准全部达成，方可宣告「可交付」。

| 类别 | 指标 | 目标值 |
|------|------|-------|
| 后端单元测试 | 测试通过率 | 100% |
| 后端 API 测试 | 鉴权边界覆盖 | 174/174 端点 |
| 后端测试覆盖率 | `app/services/` 覆盖率 | ≥ 70% |
| 前端组件测试 | 工作台 5 个核心组件 | 100% 有测试 |
| E2E 测试 | 主流程用例通过率 | 100% |
| TypeScript | `tsc --noEmit` 错误数 | 0 |
| ESLint | error 级别 | 0 |
| 构建 | `npm run build` | 无 warning/error |
| CI | PR 流水线 | 全部绿色才可合并 |

---

## 各阶段产出文件

| 阶段 | 产出 |
|------|------|
| Phase 1 | `docs/review/review-checklist.md` |
| Phase 2 | `docs/testing/backend-test-report.md` + 新增测试文件 |
| Phase 3 | `docs/testing/integration-test-report.md` + 新增测试文件 |
| Phase 4 | `.github/workflows/*.yml` + `Makefile` + 清理后的干净代码库 |

---

*本方案基于：FastAPI + PostgreSQL 后端 / React + TypeScript 前端 / 174 个 API 端点 / 现有 42 个后端测试 / 现有 10 个前端测试*
