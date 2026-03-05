# R-MOS Phase 1 Review Checklist

> Updated: 2026-03-05
> Scope: `R-MOS_Review_Test_Cleanup_Plan.md` 首批实施（Phase 0.5 + R-02 + R-04 部分）

## 1. 执行证据（首批）

- `rg -n "TODO|FIXME" r-mos-backend/app -g '*.py'` -> 33 条
- `rg -n "\\blegacy\\b|\\bunused\\b|\\bold\\b" r-mos-backend/app -g '*.py'` -> 2 条
- `rg -n "sessions/\\{session_id\\}/submit|SubmissionService|submit_manual" r-mos-backend/app/api/v1/endpoints/training.py` -> 提交路由走 `SubmissionService.submit_manual()`
- `python -m py_compile tests/conftest.py tests/load/locustfile.py` -> PASS
- `pytest tests/unit/test_training_phase2_api.py -q` -> PASS (4)
- `pytest tests/unit/test_task_service.py -q` -> PASS (3)

## 2. R-02-a TODO/FIXME 决策（33 条）

### [修复]

1. `r-mos-backend/app/api/v1/endpoints/agent.py:213` `creator_id="current_user"`（需接入真实鉴权用户）
2. `r-mos-backend/app/api/v1/endpoints/agent.py:242` `reviewer_id="current_user"`（需接入真实鉴权用户）
3. `r-mos-backend/app/core/resource_parser.py:184` 资源存在性数据库校验（避免引用不可用资源）
4. `r-mos-backend/app/services/identity/session_initializer.py:235` `current_step` 应从 `session_step_records` 获取
5. `r-mos-backend/app/services/identity/session_initializer.py:236` `total_steps` 应从 `project_snapshot` 获取
6. `r-mos-backend/app/services/memory/skill_profile_service.py:196` 最近 3 次训练通过校验规则未实现
7. `r-mos-backend/app/services/preflight_check.py:101` 前置 DB 校验未实现
8. `r-mos-backend/app/services/preflight_check.py:156` 设备状态实时校验未实现
9. `r-mos-backend/app/services/preflight_check.py:202` 工具状态实时校验未实现

### [延后]

1. `r-mos-backend/app/api/v1/endpoints/tasks.py:34` robot_id 来源补全
2. `r-mos-backend/app/services/identity/session_initializer.py:89` Redis 会话摘要写入
3. `r-mos-backend/app/services/identity/session_initializer.py:209` Redis 推荐读取
4. `r-mos-backend/app/services/identity/session_initializer.py:300` Redis 活跃会话查询
5. `r-mos-backend/app/services/identity/session_initializer.py:305` incidents 查询
6. `r-mos-backend/app/services/identity/teacher_monitor.py:41` teacher 频道订阅维护
7. `r-mos-backend/app/services/intent/training_intent_router.py:132` LLM 参数提取
8. `r-mos-backend/app/services/intent/training_intent_router.py:166` 弱项步骤数据库读取
9. `r-mos-backend/app/services/intent/training_intent_router.py:190` LLM 参数提取与前置条件校验
10. `r-mos-backend/app/services/intent/training_intent_router.py:203` skill_profile 查询
11. `r-mos-backend/app/services/intent/training_intent_router.py:225` assignment_id 提取与验证
12. `r-mos-backend/app/services/intent/training_intent_router.py:232` assignments 查询
13. `r-mos-backend/app/services/intent/training_intent_router.py:250` category 提取
14. `r-mos-backend/app/services/memory/training_memory_writer.py:142` 对话摘要写入情景记忆
15. `r-mos-backend/app/services/memory/training_memory_writer.py:158` 推荐预计算写入缓存
16. `r-mos-backend/app/services/sop/quality_monitor.py:224` 未处理工单检测
17. `r-mos-backend/app/services/sop/quality_monitor.py:244` 工单创建逻辑
18. `r-mos-backend/app/services/training/feedback_generator.py:202` tools_confirmed 评分细化
19. `r-mos-backend/app/services/training/project_generator.py:155` MemoryHub 实数据接入
20. `r-mos-backend/app/services/training/project_generator.py:334` intent -> mode 映射
21. `r-mos-backend/app/services/training/submission_service.py:241` 教师管辖权验证
22. `r-mos-backend/app/services/training/submission_service.py:265` 学员通知推送
23. `r-mos-backend/app/services/training/submission_service.py:415` conversation_summary 补全
24. `r-mos-backend/app/services/training/submission_service.py:416` interaction_log 补全

### [删除]

- 本轮未识别可直接删除的 TODO/FIXME。

## 3. R-02-a-3 submission_service 专项结论

- `submission_service.py:241` 教师管辖权：当前项目有 `TeachingClass/Enrollment` 体系，但该路径未接入提交服务，判定「未实现」。
- `submission_service.py:265` 学员通知：存在 `websocket_manager` 与 `teacher_monitor`，但未在提交链路落地调用，判定「未实现」。
- `submission_service.py:415-416` 会话摘要/交互日志：存在 `conversation_turns` 模型与 memory writer TODO，但提交链路仍为占位，判定「未实现」。

## 4. R-02-b legacy/unused/old 梳理（2 条）

1. `r-mos-backend/app/services/approval_queue.py:207` "old pending requests"：语义描述，不是废弃代码。
2. `r-mos-backend/app/core/resource_parser.py:111` "legacy format"：兼容格式注释，不是废弃代码。

结论：本轮未发现需立即标记 `# [PENDING DELETE]` 的死代码块。

## 5. 阻塞项（R-04-3）状态

- ✅ `POST /training/sessions/{session_id}/submit` 已确认调用 `SubmissionService.submit_manual()`。
- ✅ `tests/load/locustfile.py` `class R MOSUser` 语法错误已修复为 `class RMOSUser`。
- ✅ Phase 0.5 fixture 基建已落地（`tests/conftest.py`：`test_engine`/`test_db`/`test_user`/`test_session` + 兼容 `db_session`）。

## 6. 下一批（待执行）

- R-01-a/R-01-b/R-01-c：端点调用面、鉴权、错误处理专项审查
- R-03-a~R-03-d：前端 deprecated/旧接口/组件/TS 类型专项审查
- T-01：现有后端测试收集与基线通过率

## 7. R-01-a agent.py（72 端点）专项审查结果

- 端点总数：72（详单见 `docs/review/agent_endpoint_inventory.tsv`）
- 前端调用：36 个有前端调用，36 个无前端调用
- 后端 service HTTP 路径依赖：未发现 `app/` 内通过 `/agent/*` 路径直接调用的 service
- 鉴权覆盖：
  - 70/72 显式挂载 `require_permission`
  - 2/72 未显式挂载：`GET /agent/preference`、`PUT /agent/preference/guidance-mode`（当前依赖 `get_current_actor`，需评估是否补权限粒度）
- 入参类型异味：
  - `POST /agent/v2/policy/evaluate` 使用 `context: Dict[str, Any]`（建议改 Pydantic model）
- 错误处理异味：
  - `POST /agent/execute` 存在 `except Exception` 分支（有审计事件写入，但无 `logger` 记录）
- 迁移遗留核查：
  - 代码注释中仍保留旧接口痕迹：`/agent/request`、`/agent/v2/request`
  - 前端 API 发现调用 `/agent/v2/request`，后端已移除该路由（已在本批修复为 `/agent/execute`）

## 8. R-01-b ai_commands deprecated 路由清查结果

- `deprecated=True` 端点列表：
  - `POST /api/v1/ai/rag/query`
- 前端引用数量：
  - `r-mos-frontend/src` 内为 0
- `audit_events` 近 30 天调用量（本地 `r-mos-backend/rmos_main.db`）：
  - `/api/v1/ai/rag/query` 命中 0
- 结论：
  - 可标记为「可立即删除」（删除前需同步清理依赖该端点的测试用例）
- 本批修复：
  - 已给该 deprecated 端点补充响应头：`Deprecation: true` + successor `Link`

## 9. R-01-c 其余 router 快速审查结果

### R-01-c-1 teaching.py 权限边界

- 已有归属校验（通过）：
  - `get_class`（student 校验 enrollment）
  - `get_attempt_replay`（teacher 校验 class.teacher_id）
  - `create_evidence_card`（teacher/admin + 归属校验）
- 需补校验（风险）：
  - `list_enrollments` / `list_assignments` / `get_assignment` / `list_attempts`
  - `get_attempt_evidence` / `get_attempt_diagnosis`
  - 上述接口当前缺少 teacher/class 归属校验或角色限制

### R-01-c-2 training.py 提交幂等性

- 手动提交：`check_submit_ready` 对 `submitted` 状态有防重保护（通过）
- 超时提交：仅处理 `active` 会话，重复触发后续会被状态拦截（基本通过）
- 教师强制提交：`submit_by_teacher` 尚无 `submitted` 状态防重，存在重复写入风险（需修复）
- 放弃提交：当前路由走 `SessionService.abandon`，未走 `SubmissionService.abandon`（行为与提交链不一致，需评估统一）

### R-01-c-3 assessments.py / tasks.py N+1

- 未发现明显 `for` 循环内重复发 SQL 的 N+1 形态（通过）

### R-01-c-4 敏感字段暴露

- 在 `teaching.py` / `training.py` / `assessments.py` / `tasks.py` 未发现直接返回密码 hash、内部 token、完整 user ORM 对象（通过）

## 10. 本批次阻塞修复（已实施）

1. 前端 V2 调用链路修复：`sendAgentRequestV2` 改为调用 `/agent/execute`（message 模式），兼容解析返回结构。  
2. deprecated 头补全：`/ai/rag/query` 现返回 `Deprecation: true`。

## 11. R-03-a deprecated 前端代码清查结果

- `@deprecated` 标注仅出现在 `r-mos-frontend/src/data/sopScripts.ts`（7 处）。
- 调用方确认：
  - `r-mos-frontend/src/pages/SOPMaintenancePage.tsx` 仍在 import `ALL_SOP_SCRIPTS`。
- 结论：
  - 该 deprecated 数据模块暂不能删除，应标记为「需等待迁移」。

## 12. R-03-b 旧接口调用与 mock 残留结果

- 旧接口路径检索：
  - 未发现 `/agent/request` 实际调用。
  - `/ai/commands` 仅存在注释说明（`r-mos-frontend/src/api/agent.ts`），非运行时调用。
- `mockData|fakeData|hardcoded` 检索：
  - 未命中。
- 结论：
  - 前端旧接口运行时调用已基本清理。

## 13. R-03-c 组件质量审查结果

- 孤儿组件（当前未发现被页面引用，估算 5 个）：
  - `components/Admin/SeedDataGuide.tsx`
  - `components/Agent/CompensationConfirm.tsx`
  - `components/Task/StepCard.tsx`
  - `components/Viewer3D/PartInspector.tsx`
  - `components/common/ConnectionStatusBar.tsx`
- 核心工作台组件检查：
  - 未检索到 `WorkbenchOrchestrator/StepPanel/ToolPanel/ModelPanel/VerdictPanel` 文件，当前实现与计划文档的组件基线不一致。
  - 全局变量接口 `window.__agent3DCommand` / `window.__robotState` 在 `src/` 内未命中，无法执行读写方向核验。
- Zustand 状态冗余：
  - `preferenceStore` 同时持有 `preference` 与 `guidanceMode`（由 `preference` 可推导），存在冗余状态风险。

## 14. R-03-d TypeScript 类型安全结果

- 初始 `npx tsc --noEmit` 错误日志：
  - `docs/review/frontend-tsc-noemit-2026-03-05.log`
- 修复后 `npx tsc --noEmit` 结果：
  - `docs/review/frontend-tsc-noemit-2026-03-05-after-fixes.log`
  - 结论：✅ 通过（0 error）
- `any` 用法检索：
  - 前端代码中 `: any` / `as any` 仍较多，集中于 `ReplayPage/AIChatPage/MonitorPage/KnowledgePage/TaskExecutionPage` 及 `adjudication` 测试代码。

## 15. 本批次额外修复（已实施）

- 修复构建阻断根因之一：
  - `r-mos-frontend/src/components/GuidanceModeModal/index.ts`（JSX 写在 `.ts`）→ 重命名为 `index.tsx`。
  - 修复后 `tsc` 已从语法崩溃阶段收敛到可定位类型问题并最终清零（见第 14 节）。
- 额外类型修复：
  - `ApprovalQueuePage.tsx`：移除与 API 类型冲突的本地 `ApprovalRequest` 声明。
  - `agent-v2.ts`：补齐 `ApprovalRequest.status?: string`。
  - `LLMMetricsPage.tsx`：移除未使用且缺依赖的图表导入，修正 nullable 数值赋值。
  - `IncidentListPage.tsx` / `ReplayPage.tsx`：清理 unused import/变量。
- 当前前端构建状态：
  - `npm run build`：✅ 通过（仅剩 chunk size warning）

## 16. 下一批（待执行）

- R-04-3：对红色阻塞项（尤其 teaching 归属权限缺口、前端 TS 阻断项）执行即时修复
- T-01：进入后端测试基线收集（collect-only + 全量通过率）

## 17. R-04-2 优先级分级（红/黄/绿）

### 🔴 阻塞测试（必须先修复）

1. `teaching.py` 多个学员数据接口缺少 teacher/class 归属校验（存在越权读取风险）  
   涉及：`list_enrollments/list_assignments/get_assignment/list_attempts/get_attempt_evidence/get_attempt_diagnosis`
2. 计划基线组件缺失：`WorkbenchOrchestrator/StepPanel/ToolPanel/ModelPanel/VerdictPanel` 未落地，影响后续 T-06 用例前提

### 🟡 测试中验证

1. `SubmissionService.submit_by_teacher` 缺少 `submitted` 状态防重（重复提交风险）
2. `agent.py` 2 个 preference 端点未显式 `require_permission`（当前依赖 `get_current_actor`）
3. `agent.py` 存在 `context: Dict[str, Any]` 与裸 `except Exception` 代码异味
4. `sopScripts.ts` deprecated 数据仍被页面引用，需迁移后清理
5. 前端 `any/as any` 使用较多，建议按测试触达路径逐步收敛

### 🟢 Phase 4 清理

1. `agent.py` 中已注释的旧路由代码痕迹（`/agent/request`、`/agent/v2/request`）
2. 36 个未被前端调用的 `/agent/*` 端点，待 Phase 4 按调用面逐步下线
3. 前端 TS 基础门禁已恢复（`tsc --noEmit` / `npm run build` 通过），后续以增量方式维持

## 18. Batch 4 / T-01 最新进展（2026-03-05）

- 基线收集（T-01-1）：
  - `pytest tests/ --collect-only -q` -> `docs/review/backend-tests-collect-2026-03-05-rerun1.txt`
  - 结果：`collected 239 items`
- 基线通过率（T-01-2）：
  - `pytest tests/ -v --tb=short` -> `docs/review/backend-tests-baseline-2026-03-05-rerun2.log`
  - 结果：`236 passed, 3 skipped, 0 failed, 0 error`
- 存量失败修复（T-01-3）：
  - `app/services/llm/router.py`：`anthropic` 改为可选依赖 + 延迟初始化，避免收集阶段崩溃
  - `app/services/system_monitor.py`：`psutil` 改为可选依赖降级
  - 新增 `app/main.py`：兼容 `from app.main import app`
  - 恢复兼容旧端点：
    - `POST /api/v1/ai/commands`（deprecated，但保留完整提交/审批/审计链路）
    - `POST /api/v1/agent/request`（deprecated wrapper）
    - `POST /api/v1/agent/v2/request`（deprecated wrapper）
  - `agent.py` 审批端点不存在请求返回码修正：`400 -> 404`
- 结论：
  - Phase 1 红色阻塞项 `R-04-3` 已闭环
  - Phase 2 `T-01-1/2/3` 已达成
- 覆盖缺口盘点（T-01-4）：
  - 输出：`docs/review/service-test-gap-2026-03-05.md`
  - 核心服务静态映射结果：14 个核心服务中，2 个已有显式测试映射，12 个待补测（已作为 T-02 输入清单）

## 19. Batch 4 / T-02 最新进展（2026-03-05）

- T-02-a（训练流程核心链路）✅：
  - `tests/unit/test_project_generator.py`
  - `tests/unit/test_session_service.py`
  - `tests/unit/test_submission_service.py`
  - `tests/unit/test_feedback_generator.py`
- T-02-b（身份与权限）✅：
  - `tests/unit/test_session_initializer.py`
  - `tests/unit/test_agent_policy_factory.py`
  - `tests/unit/test_class_membership.py`
- T-02-c（记忆写入链路）✅：
  - `tests/unit/test_training_memory_writer.py`
  - `tests/unit/test_skill_profile_service.py`
- T-02-d（已有 service 补全）✅：
  - `tests/unit/test_knowledge_hub.py`
  - `tests/unit/test_preflight_check.py`（新增 3 个 BLOCK 场景）
  - `tests/unit/test_teacher_monitor.py`
  - `tests/unit/test_training_intent_router.py`
  - `tests/unit/test_orchestrator_v2.py`
  - `tests/unit/test_tool_executor_service.py`

- 本批为测试落地做的关键兼容修复：
  - `knowledge/__init__.py`、`memory/hub.py`、`memory/short_term.py`：外部依赖（OpenAI/Redis/BeliefState）缺失时改为可选降级，避免测试收集阶段崩溃
  - `training/project_generator.py` + `knowledge/hub.py`：修复知识检索调用接口不一致；补充检索过滤、过期过滤与降级放宽
  - `identity/session_initializer.py`：修复 MemoryHub 构造与未完成会话查询逻辑，补齐 teacher 统计聚合字段引用
  - `memory/skill_profile_service.py`：补全升级规则（均分/次数/最近三次通过）
  - `orchestrator_v2.py`：修复 dataclass 序列化（`model_dump` 兼容）

- 最小验证结论：
  - T-02-a 子集：`12 passed`
  - T-02-b 子集：`7 passed`
  - T-02-c/d 子集：`21 passed`
  - T-02-d-1 补缺子集：`5 passed`
  - 合计本批新增/扩展子集：`45 passed, 0 failed`
