# R-MOS Review Test Cleanup Execution Plan (Batch Mode)

> Source Plan: `R-MOS_Review_Test_Cleanup_Plan.md`
> Start Date: 2026-03-05
> Execution Rule: 逐项完成即标记、每批次可验证、全程可追溯

## 1. 执行原则

1. 每批次最多 3-6 项任务，完成后必须跑最小验证命令。
2. 每项完成后立即在源计划文档勾选（`[ ] -> [x]`）。
3. 每批次结束必须更新：
   - `docs/review/review-checklist.md`
   - `DEVELOPMENT_LOG.md`
4. 只在当前批次涉及文件做最小化改动。

## 2. 批次拆分

### Batch 1（已完成）

- Phase 0.5：F-01/F-02/F-03/F-04
- Phase 1：R-02-a-1/a-2/a-3/a-4
- Phase 1：R-02-b-1/b-2/b-3
- 阻塞项：R-04-3-a + T-03-b-0
- 产出：
  - `r-mos-backend/tests/conftest.py` fixture 基建
  - `r-mos-backend/tests/load/locustfile.py` 语法修复
  - `docs/review/review-checklist.md` 首版

### Batch 2（已完成）

- Phase 1：R-01-a（agent.py 72 端点审查）
- Phase 1：R-01-b（deprecated 端点调用/审计核查）
- Phase 1：R-01-c（training/teaching/tasks 重点审查）

### Batch 3（已完成）

- Phase 1：R-03-a~R-03-d（前端审查）✅ 已完成
- Phase 1：R-04-1/R-04-2（汇总与分级）✅ 已完成
- Phase 1：R-04-3（红色阻塞项即时修复）✅ 已完成

### Batch 4（已完成）

- Phase 2：T-01 基线测试收集与存量失败修复（T-01-1/2/3/4 ✅）
- Phase 2：T-02 核心 service 单测补全（T-02-a/b/c/d ✅）
- 产出：
  - 新增/补强核心 service 测试：`test_project_generator.py`、`test_session_service.py`、`test_submission_service.py`、`test_feedback_generator.py`
  - 新增/补强身份与权限测试：`test_session_initializer.py`、`test_agent_policy_factory.py`、`test_class_membership.py`
  - 新增/补强记忆与检索测试：`test_training_memory_writer.py`、`test_skill_profile_service.py`、`test_knowledge_hub.py`
  - 扩展 BLOCK 场景：`test_preflight_check.py`
  - 对剩余缺口服务补最小正常流：`test_teacher_monitor.py`、`test_training_intent_router.py`、`test_orchestrator_v2.py`、`test_tool_executor_service.py`

### Batch 5（已完成）

- Phase 2：T-03 API 接口测试（T-03-a/b/c/d ✅）
- 产出：
  - 新增：`tests/unit/test_auth_boundary.py`
  - 新增：`tests/unit/test_api_training_flow.py`
  - 新增：`tests/unit/test_api_teaching.py`
  - 新增：`tests/unit/test_api_knowledge.py`
  - 新增 API：`POST /api/v1/training/sessions/{session_id}/force-submit`
  - 新增 API：`POST /api/v1/agent/knowledge/upload`
  - 新增 API：`GET /api/v1/agent/knowledge/upload/{job_id}`
  - 修复：`/api/v1/agent/knowledge/search` 使用 `KnowledgeSearchQuery` 传参，消除 `AttributeError`

### Batch 6（已完成）

- Phase 2：T-04 后端测试执行与覆盖率报告（T-04-1/2/3/4 ✅）
- 产出：
  - `r-mos-backend/.coveragerc`（排除 `app/models/*`）
  - `r-mos-backend/tests/load/test_locustfile_smoke.py`（负载测试最小 smoke）
  - `docs/testing/backend-test-report.md`（通过率/覆盖率/失败用例汇总）
  - 失败闭环修复：
    - `tests/unit/test_audit_query_index_gate.py`：非 PostgreSQL 跳过执行计划断言
    - `tests/unit/test_skill_registry_migration_gate.py`：补齐 `created_at/updated_at` 插入字段
  - 验证结果：
    - Service 覆盖率门禁：`376 passed, 1 skipped, 0 failed`，覆盖率 `55.86%`（未达 `70%` 门禁）
    - 全量覆盖率参考：`376 passed, 1 skipped, 0 failed`，总覆盖率 `59%`
    - 负载测试：`2 passed`

### Batch 7（已完成）

- Phase 2：T-04 未闭环风险补充闭环 + T-05 前端测试框架迁移（T-05-1/2/3 ✅）
- 产出：
  - 风险闭环：
    - 核心 14 服务覆盖率门禁命令通过：`74.63% >= 70%`
    - 报告目录：`r-mos-backend/coverage/services-core`
  - 前端测试框架迁移：
    - `r-mos-frontend/vitest.config.ts`
    - `r-mos-frontend/src/adjudication/__tests__/adjudication.vitest.test.ts`
    - `r-mos-frontend/package.json`（`test` 脚本切到 `vitest run`）
    - 删除旧 runner：
      - `r-mos-frontend/scripts/run-adjudication-tests.mjs`
      - `r-mos-frontend/src/adjudication/__tests__/run-adjudication-tests.ts`
  - 依赖更新：
    - `vitest`、`@testing-library/react`、`@testing-library/user-event`、`jsdom`
  - 验证结果：
    - `npm test` -> `8 passed`
    - `npm run build` -> PASS

### Batch 12（进行中）

- Phase 4：C-01 后端废代码删除（第一批）
- 已完成：
  - C-01-a-1：删除 `ai_commands.py` deprecated 路由（`/ai/commands`、`/ai/rag/query`）
  - C-01-a-2：核查 `ai_commands.py` 非空（保留 `/ai/citations/*`、`/ai/replay/*`）
  - C-01-a-3：删除 `agent.py` 旧兼容路由（`/agent/request`、`/agent/v2/request`）
  - C-01-b-1/2/3/4：`[PENDING DELETE]` 核查为 0，`py_compile` 全量通过
- 已验证：
  - `pytest tests/e2e/test_agent_execute.py tests/unit/test_auth_boundary.py tests/unit/test_agent_authz.py -q` -> PASS（`110 passed`）
- 待闭环：
  - C-01-a-4：`pytest tests/unit/test_ai_commands_api.py -q` 仍 `11 failed`（旧端点引用未迁移）

### Batch 13（已完成）

- Phase 4：C-01-c TODO/FIXME 收口（`C-01-c-1/2/3`）
- 完成项：
  - C-01-c-1：`[删除]` 分类核查为 0，按“无待删项”闭环
  - C-01-c-2：`[修复]` 收口
    - `agent.py`：`creator_id/reviewer_id` 改为真实鉴权用户
    - `preflight_check.py`：接入数据库用户/设备/工具校验
    - `resource_parser.py`：补齐资源存在性校验机制
  - C-01-c-3：`[延后]` 项迁移至 `docs/backlog.md`，并从源码删除 TODO/FIXME 注释
- 验证结果：
  - `pytest tests/unit/test_api_knowledge.py tests/unit/test_preflight_check.py tests/unit/test_resource_parser.py -q` -> `22 passed`
  - `find app -name "*.py" -exec python -m py_compile {} +` -> PASS
  - `rg -n "TODO|FIXME" r-mos-backend/app -g '*.py'` -> `0` 命中

### Batch 14（已完成）

- Phase 4：C-02 前端废代码删除 + C-03 文档与目录清理
- 完成项：
  - C-02-a：`sopScripts.ts` Legacy/deprecated 块删除；孤儿组件路径复核为已删除；mock/fake/hardcoded 残留为 0
  - C-02-b：可收敛 `any` 替换；补充 `.eslintrc.cjs`；`tsc/lint` 全绿
  - C-02-c：确认 `.gitignore`；执行 `npm prune`；`npm run build` 无 warning/error
  - C-03：README 新增 `docs-archive/`、`logs/`、`开源机器人/` 用途说明并明确边界
- 验证结果：
  - `npx tsc --noEmit` -> PASS
  - `npm run lint` -> PASS（`--max-warnings 0`）
  - `npm run build` -> PASS（无 chunk warning）
  - `rg -n "@deprecated|LEGACY_" r-mos-frontend/src/data/sopScripts.ts` -> 0 命中

## 3. 每批次验收模板

- Commands Run（可复制）
- Output 摘要（PASS/FAIL + 关键日志）
- Diff Summary（文件清单 + 关键片段）
- Source Plan 勾选状态更新
- DEVELOPMENT_LOG 追加
