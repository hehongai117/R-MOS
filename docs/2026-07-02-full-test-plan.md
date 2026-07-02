# R-MOS 完整测试规划

> 日期：2026-07-02
> 目标：对全项目做一次完整测试,系统暴露问题。重点维度：**集成 & E2E 端到端**。
> 交付：本规划文档 + 已立即执行的自动化部分结果(见 §6)+ 问题清单(见 §7)。

## 1. 测试分层与现状（执行前已核实）

| 层 | 工具 | 规模 | 现状 |
|----|------|------|------|
| 后端 单元/集成 | pytest | `tests/unit` + `tests/integration` | 663 passed / 3 skipped |
| 后端 E2E | pytest（`@e2e` mark） | `tests/e2e` 29 用例 | 全通过（**但需正确 scope,见问题 P1**） |
| 后端 全量 | `pytest tests/` | 692 用例 | **692 passed / 3 skipped** |
| 前端 单元/组件 | vitest + jsdom | 60 文件 | **465 passed / 2 skipped** |
| 前端 类型 | `tsc --noEmit` | 全项目 | 干净 |
| 前端 词法 | eslint（`--max-warnings 0`） | `src/` | 干净 |
| 覆盖率门禁 | pytest-cov / vitest v8 | 端点+组件+hook | 全部达阈值 |
| 性能基线 | Lighthouse/trace/ws-probe/timing | Phase 4 工具就绪 | **未采集**（待全栈环境） |
| 依赖安全 | npm audit / pip check | — | pip 无冲突；**npm 有 high 漏洞（P2）** |

**关键认知：全绿 ≠ 无 bug。** Phase 2 的特征测试锁定的是"当前可观测行为"——其中 8 处锁定的是**错误行为**（见 §7 P0 组）。所以套件绿,只代表行为未回退,不代表行为正确。

## 2. 完整跑一遍的标准命令

### 2.1 后端
```bash
cd r-mos-backend && source venv/bin/activate
# 全量（含 e2e，scope 到 tests/ 避免扫到第三方 robot-assets junk）
python -m pytest tests/ -o addopts='' -p no:warnings -q
# 仅 e2e
python -m pytest tests/e2e -o addopts='' -p no:warnings -q
# 覆盖率门禁（巨型端点，规避 py3.13 segfault：不单列端点为 --cov 目标）
python -m pytest tests/ -o addopts='' -p no:warnings -q --cov=app --cov-config=.coveragerc >/dev/null 2>&1
coverage report --include='*/app/api/v1/endpoints/agent*.py,*/app/api/v1/endpoints/training*.py,*/app/api/v1/endpoints/teaching*.py' --fail-under=80
# 需真实 DB 的门禁（当前 skip，见 P3）
DATABASE_URL=postgresql+asyncpg://... python -m pytest tests/unit/test_audit_query_index_gate.py tests/unit/test_skill_registry_migration_gate.py -o addopts='' -q
```
> ⚠️ **不要**用裸 `pytest`（无参数）从仓库根跑——会扫到 `data/robot-assets/*/uploads/*/tests/` 第三方测试与 `scripts/backend_stress_test.py`,触发 import-mode 冲突导致 4 个收集错误。始终 scope 到 `tests/`。

### 2.2 前端
```bash
cd r-mos-frontend
npx vitest run                 # 全量单元/组件
npx vitest run --coverage      # 含覆盖率门禁
npx tsc --noEmit               # 类型
npx eslint src/ --ext .ts,.tsx --max-warnings 0   # 词法
```

### 2.3 端到端全链路（需全栈：Postgres + FastAPI + Vite + 浏览器）
E2E 的 pytest 用例用 TestClient + SQLite 内存库（不需真实全栈）。但**浏览器级真实链路**（登录→选机器人→SOP 执行→裁决→提交→反馈→报告）需手动或后续引入 Playwright（见 §5 缺口）。

### 2.4 性能基线
见 `docs/superpowers/plans/phase4-baseline-collection-cheatsheet.md`（Phase 4 Track C 前置）。

## 3. 集成 & E2E 覆盖清单（重点维度）

现有 29 个后端 E2E 用例覆盖的业务链路：

| E2E 文件 | 覆盖链路 |
|----------|----------|
| test_e2e_student_training_flow | 学生完整训练流程（会话→步骤→提交） |
| test_e2e_teacher_flow | 教师视角（监控/审批） |
| test_e2e_resume_training | 训练会话暂停/恢复 |
| test_e2e_timeout_submit | 超时自动提交 |
| test_e2e_sop_adjudication | SOP 裁决执行（含步骤字段/模型过滤） |
| test_e2e_sop_draft_review_flow | SOP 草案→审阅流程 |
| test_e2e_memory_loop | 技能画像记忆闭环 |
| test_e2e_robot_project_semantic_flow | 机器人项目语义流程 |
| test_e2e_knowledge_missing | 知识缺失兜底 |
| test_e2e_cross_role_access | 跨角色权限隔离 |
| test_agent_diagnosis_flow / test_agent_execute | Agent 诊断/执行 |

**已覆盖的关键链路**：训练闭环、SOP 裁决、教师监控、权限隔离、记忆回写。

## 4. 各维度测试要点（如需扩展执行）

- **鉴权/RBAC**：`ActorContext` 权限矩阵——每个受保护端点验证「无权限 403 / 有权限 200」；cross-role 隔离已有 e2e。
- **数据一致性**：会话状态机（active→paused→submitted→expired）转移合法性；提交幂等。
- **WebSocket**：5Hz 遥测、断连指数退避重连、stale 检测（`useWebSocket` 已有健壮性,可加自动化验证）。
- **3D 查看器**：manifest 驱动渲染、WebGL 不支持降级（Phase 4 已加 ErrorBoundary）。
- **AI 管线**：项目生成/反馈/workbench 的失败态与超时（Phase 4 已补 per-call timeout）。
- **多机器人**：机器人上传→AI 分析→学生使用 的租户隔离与可见性。

## 5. 测试体系缺口（建议补强）

1. **无浏览器级 E2E**：缺 Playwright/Cypress 真实浏览器全链路。建议引入 Playwright 覆盖「登录→SOP 执行→提交→报告」黄金路径。
2. **e2e 依赖 SQLite 内存库**：与生产 Postgres 存在方言差异（如 JSON/时区/约束行为），部分 bug 在 SQLite 下不复现。建议关键 e2e 增加 Postgres 变体（CI 用容器）。
3. **DATABASE_URL 门禁被 skip**：审计索引 + 迁移门禁在无真实 DB 时跳过（P3）。
4. **性能/负载测试缺自动化基线**：Phase 4 工具就绪但未采集。
5. **前端交互 E2E 薄**：组件测试充分,但跨页面用户旅程未覆盖。

## 6. 本次执行结果（2026-07-02）

- 后端 `pytest tests/`：**692 passed / 3 skipped**（3 skip 为无 DATABASE_URL 的门禁）。
- 后端 `pytest tests/e2e`：**29 collected, 全通过**。
- 前端 `vitest run`：**465 passed / 2 skipped**（2 skip 在 adjudication vitest）。
- `tsc --noEmit`：干净。`eslint src/`：干净。
- `pip check`：No broken requirements。
- `npm audit`：**axios high 级漏洞多条**（SSRF via no_proxy bypass、prototype pollution）。

## 7. 问题清单（按严重度）

### P0 — 已锁定的真实功能 bug（Phase 2 特征测试锁的是错误行为，套件绿但行为错）
| # | 端点/位置 | 现象 | 根因 |
|---|-----------|------|------|
| 1 | `POST /agent/v2/policy/evaluate` | 500 | `PolicyDecision` 是 dataclass 却调 `.model_dump()` |
| 2 | `POST /agent/evaluation/report` | 无效 task_id → 500 | `ReportGenerator` 抛 `ValueError` 未捕获 |
| 3 | `POST /agent/sop/quality/check`（全扫） | 500 | `SOPQualityMonitor` 引用不存在的 `SOP.is_active` |
| 4 | `GET /agent/approval/history` | 恒空 | `get_request_history` 参数顺序错位（limit 传给了 requester_id） |
| 5 | `POST /agent/execute`（command 模式） | 恒 error | `Command(user_id=...)` 用错 kwarg（应 `actor_user_id`） |
| 6 | `POST /training/.../workbench draft` | 502 分支死代码 | `except ValueError` 在 `except json.JSONDecodeError` 之前（后者是子类）→ JSONDecodeError 实际返回 400 |
| 7 | `GET /teaching/attempts/{id}/diagnosis` | `task_id=None` → 500 | 未处理空 task_id（EVIDENCE_FALLBACK_FAILED） |
| 8 | `teaching._raise_not_found` | 404 响应 `error_type` 错为 `'HTTPException'` | `ResourceNotFoundError` 被转成通用 HTTPException,丢了类型 |

> 这些散落在 Phase 3 重构后的 `agent_v2.py`/`agent_governance.py`/`training_workbench.py`/`teaching_common.py`/`teaching_roster.py`（route 路径不变）。修复方式：改代码 → 同步把对应特征测试断言从「错误行为」改为「正确行为」。

### P1 — 测试基建（集成/E2E 重点）
- 裸 `pytest`（无 scope）从根目录收集第三方 `data/robot-assets/*/tests/` + `scripts/backend_stress_test.py`,触发 4 个收集错误。根因：`pytest.ini` 未配 `testpaths`。**修复**：`pytest.ini` 加 `testpaths = tests` + `norecursedirs = data scripts`。

### P2 — 依赖安全
- axios 多条 high 级漏洞（SSRF / prototype pollution）。**修复**：`npm audit fix` 或升级 axios 到已修复版本,回归前端测试。

### P3 — 环境门禁被跳过
- `test_audit_query_index_gate` / `test_skill_registry_migration_gate` 因无 `DATABASE_URL` 被 skip。**修复**：CI/本地提供真实 Postgres 后跑这两个门禁,确认审计索引与 skill 迁移一致性。

## 8. 建议执行顺序

1. **P1 先修**（1 行配置）——让"完整跑一遍"命令统一、干净。
2. **P0 逐个立项修复**——每个 bug：写正确行为的失败测试 → 修代码 → 更新原特征测试断言。优先 #5/#1/#3（直接 500/功能失效）。
3. **P2 axios 升级** + 前端回归。
4. **P3** 配 Postgres 跑门禁。
5. 补强缺口：引入 Playwright 黄金路径 E2E（§5.1）；Phase 4 性能基线采集。
