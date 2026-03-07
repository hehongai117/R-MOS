# 智能体改造验收问题与解决建议汇总（统一收敛版）

## 目的
本清单用于汇总智能体改造各阶段验收中发现的问题与解决建议。根据当前决策，这些问题暂不在当前阶段打断实施，统一在整体方案实施结束后集中修复与回归。

## 处理原则
- 当前状态统一标记为 `DEFERRED`。
- 不回滚已交付功能，不在 Phase 0 期间做破坏性调整。
- 进入“统一收敛窗口”后按优先级一次性修复并完成全链路回归。

## Phase 0 问题与建议

| ID | 问题描述 | 证据位置 | 风险影响 | 解决建议 | 处理时机 | 状态 |
|---|---|---|---|---|---|---|
| P0-DI-001 | 前端 `agent-v2.ts` 已调用 `/agent/v2/*`，后端未提供对应路由实现。 | `r-mos-frontend/src/api/agent-v2.ts`；`r-mos-backend/app/api/v1/endpoints/agent.py` | V2 SDK 无法端到端联调，接口调用会失败。 | 在后端补齐 `/agent/v2/request`、`/agent/v2/policy/evaluate`、`/agent/v2/evidence/requirements/{action_type}`、`/agent/v2/resources/validate`、`/agent/v2/idempotency/{key}`、`/agent/v2/trace/*`；补充契约测试与前后端联调回归。 | 全方案实施结束后统一处理 | DEFERRED |
| P0-DI-002 | Week 2 Alembic 迁移文件包含大量超出范围的删除/结构改动（非“仅新增字段”）。 | `r-mos-backend/alembic/versions/20260304_0858_869864251bc9_phase0_week2_extend_command_toolcall_.py` | 存在破坏现有功能与历史数据结构的风险，不满足“向后兼容、不动现有功能”约束。 | 重生成为“最小增量迁移”：仅保留 Command/AIToolCall/Skill 新增字段及必要索引/约束；删除与 Phase 0 无关的 drop/alter 操作；补跑 migration contract 与升级/回滚演练。 | 全方案实施结束后统一处理 | DEFERRED |
| P0-DI-003 | `resource_parser` 与 `policy_matrix` 已创建，但未接入主请求执行链路。 | `r-mos-backend/app/core/resource_parser.py`；`r-mos-backend/app/services/policy_matrix.py`；全局引用检索结果 | Gate-0 核心能力停留在“组件存在”，未形成强制门禁闭环。 | 在 `agent` 主入口链路接入：请求解析 -> resource binding 校验 -> policy evaluate -> 审批/放行决策；失败路径补审计与拒绝语义测试。 | 全方案实施结束后统一处理 | DEFERRED |
| P0-DI-004 | 前端构建当前失败（TypeScript 现存错误），影响验收与集成验证效率。 | `r-mos-frontend` 执行 `npm run build` 输出 | 影响前端回归与交付可靠性，掩盖新增改动真实质量。 | 统一收敛窗口内清理 TS 错误，确保 `npm run build` 绿灯；新增最小 CI 门禁（构建必过）。 | 全方案实施结束后统一处理 | DEFERRED |

## Phase 1 问题与建议

| ID | 问题描述 | 证据位置 | 风险影响 | 解决建议 | 处理时机 | 状态 |
|---|---|---|---|---|---|---|
| P1-DI-001 | `OrchestratorV2.process_request()` 使用 `policy_decision.model_dump()`，但 `PolicyDecision` 为 dataclass，无该方法。 | `r-mos-backend/app/services/orchestrator_v2.py`；运行命令 `python -c "from app.services.orchestrator_v2 import orchestrator_v2; orchestrator_v2.process_request(...)"` 报 `AttributeError` | `/agent/v2/request` 主流程可在运行期直接异常，V2 主入口不可用。 | 统一改为 `dataclasses.asdict(policy_decision)` 或将 `PolicyDecision` 改为 Pydantic 模型；补充 V2 请求路径单测。 | 全方案实施结束后统一处理 | DEFERRED |
| P1-DI-002 | `/agent/v2/policy/evaluate` 同样使用 `decision.model_dump()`，且参数签名与前端 body 约定不一致风险高。 | `r-mos-backend/app/api/v1/endpoints/agent.py`（`evaluate_policy_v2`） | 策略评估端点可能 422/500，前端策略评估链路不稳定。 | 将入参改为 Pydantic Request Model（含 `action`,`context`），返回统一 Response Model，并补 API 契约测试。 | 全方案实施结束后统一处理 | DEFERRED |
| P1-DI-003 | “预算控制/Feature Flag”能力未形成真实门禁：`check_budget/consume_budget` 仅定义未在请求主链路执行，Feature Flag 主要用于查询接口。 | `r-mos-backend/app/services/orchestrator_v2.py`；`r-mos-backend/app/services/feature_flag.py`；`r-mos-backend/app/api/v1/endpoints/agent.py` | Week 4/5 声称能力存在功能空洞，无法保证预算与灰度策略生效。 | 在 `/agent/v2/request` 与任务转换路径接入预算检查/扣减；在 V1/V2 分流与关键 V2 功能入口接入 flag 判定。 | 全方案实施结束后统一处理 | DEFERRED |
| P1-DI-004 | Frontend `AgentWorkbenchPage.tsx` 新增多处未使用符号，构建失败输出包含该文件错误。 | `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`；`npm run build` 输出 | 增量交付无法通过前端构建门禁，影响联调与发布质量。 | 清理未使用 import/state，补页面级最小测试；将 `npm run build` 纳入阶段验收必跑。 | 全方案实施结束后统一处理 | DEFERRED |
| P1-DI-005 | 缺少 Phase 1 新增能力的配套自动化测试（未检索到 V2/FSM/Feature Flag 专项测试）。 | 检索命令：`rg -n \"orchestrator_v2|v2/request|v2/task|v2/policy|feature flag\" r-mos-backend/tests` 未命中 | 回归风险高，后续修改容易产生无感回归。 | 增补最小测试集：V2 request happy path、policy evaluate、task FSM transition、feature flag gate、idempotency cache 行为。 | 全方案实施结束后统一处理 | DEFERRED |

## Phase 2 问题与建议

| ID | 问题描述 | 证据位置 | 风险影响 | 解决建议 | 处理时机 | 状态 |
|---|---|---|---|---|---|---|
| P2-DI-001 | Week 7 核心服务 `compensation_planner.py` 仍缺失，但 `agent.py` 已强依赖导入并暴露补偿端点。 | `test -f r-mos-backend/app/services/compensation_planner.py` 返回 `MISSING`；`r-mos-backend/app/api/v1/endpoints/agent.py` 导入与 `/compensation/*` 端点 | 补偿分析/计划/执行链路在运行期不可用，Week 7 交付阻断。 | 补齐 `compensation_planner.py`（含 `FailureType/CompensationStrategy/analyze_failure/generate_compensation_plan/update_plan_status`）并补最小单测。 | 全方案实施结束后统一处理 | DEFERRED |
| P2-DI-002 | `EvidencePanel` 为演示态：仍使用本地 mock 证据与 mock requirements，未接 `evidence/v2` 真实接口。 | `r-mos-frontend/src/components/Agent/EvidencePanel.tsx`（`Mock data for demonstration`） | 证据面板展示与后端真实证据链脱节，无法作为验收证据来源。 | 接入 `/agent/evidence/v2/{trace_id}/chain` 与 `/agent/evidence/v2/requirements/{action_type}`，补错误态/空态与加载态。 | 全方案实施结束后统一处理 | DEFERRED |
| P2-DI-003 | `ApprovalQueuePage` 为演示态：待审批与历史记录均使用 mock 数据，批准/拒绝未调用后端审批 API。 | `r-mos-frontend/src/pages/admin/ApprovalQueuePage.tsx`（`Mock data`、`Mock API call`） | 审批页无法反映真实审批状态，Week 8 页面不具备实用管理能力。 | 接入 `/agent/approval/request|pending|{id}/approve|{id}/reject`，补分页/筛选/拒绝原因提交流程与失败处理。 | 全方案实施结束后统一处理 | DEFERRED |
| P2-DI-004 | `CompensationConfirm.tsx` 使用不存在的图标 `SkipForwardOutlined`，定向 TypeScript 编译失败。 | `npm exec tsc ... CompensationConfirm.tsx` 报 `TS2724`；文件 `r-mos-frontend/src/components/Agent/CompensationConfirm.tsx` | 补偿确认 UI 不能通过类型编译，影响前端交付稳定性。 | 替换为可用图标（如 `ForwardOutlined`）并清理未使用 import；纳入前端 build 门禁。 | 全方案实施结束后统一处理 | DEFERRED |
| P2-DI-005 | Belief/Evidence/Approval 当前均为进程内内存存储，无持久化。 | `r-mos-backend/app/services/belief_state.py`、`evidence_collector.py`、`approval_queue.py` 均使用内部 dict/list | 服务重启即丢失状态与审批历史，难满足追溯、审计与复盘要求。 | 增加持久化（DB 表或事件存储）与索引，并补“重启后可恢复”回归测试。 | 全方案实施结束后统一处理 | DEFERRED |
| P2-DI-006 | Phase 2 新增能力缺少专项自动化测试覆盖。 | 检索命令：`rg -n "belief_state|evidence_collector|compensation_planner|approval_queue|/agent/belief|/agent/evidence/v2|/agent/compensation|/agent/approval|EvidencePanel|CompensationConfirm|ApprovalQueuePage" ... --glob '*test*'` 未命中 | 回归风险高，无法形成稳定验收证据。 | 增补后端接口契约测试与前端组件/页面最小测试（渲染、交互、API 成功/失败路径）。 | 全方案实施结束后统一处理 | DEFERRED |

## Phase 3 问题与建议

| ID | 问题描述 | 证据位置 | 风险影响 | 解决建议 | 处理时机 | 状态 |
|---|---|---|---|---|---|---|
| P3-DI-001 | 后端主应用导入失败：`agent.py` 引用了不存在的 `app.services.compensation_planner`。 | `r-mos-backend/app/api/v1/endpoints/agent.py`；`python -c "import main"` 报 `ModuleNotFoundError` | 服务启动/测试收集被阻断，Phase 3 接口无法稳定验收。 | 补齐 `compensation_planner.py` 或移除/改为可选依赖导入；增加启动级 smoke test（`import main`/`uvicorn --factory`）。 | 全方案实施结束后统一处理 | DEFERRED |
| P3-DI-002 | `ReplayPage` 当前使用本地 mock 数据，未调用 `replayTrace/getTraceDecisions/getDecision` 等真实 API。 | `r-mos-frontend/src/pages/ReplayPage.tsx`（`loadTrace` 中构造 `mockTrace`） | 回放页面仅演示态，无法验证真实 trace/decision/evidence 链路。 | 将 `loadTrace` 改为调用 `replayTrace`，并补齐错误态/空数据态；将决策详情与复算按钮接入真实接口。 | 全方案实施结束后统一处理 | DEFERRED |
| P3-DI-003 | 决策记录与复算结果仅内存存储（`_decisions/_recalculations`），无持久化。 | `r-mos-backend/app/services/decision_recalculator.py` | 服务重启后回放与复算历史丢失，难满足审计追溯和覆盖率目标。 | 落库（或事件存储）并增加按 `trace_id/decision_id` 查询索引；提供回放一致性回归测试。 | 全方案实施结束后统一处理 | DEFERRED |
| P3-DI-004 | 前端构建失败包含 Phase 3 新增文件错误（如 `SkipForwardOutlined` 不存在、Replay/Agent 组件未使用符号）。 | `npm run build` 输出；`r-mos-frontend/src/components/Agent/CompensationConfirm.tsx`；`r-mos-frontend/src/pages/ReplayPage.tsx` | 新增回放/补偿相关 UI 不能通过构建门禁，交付不可发布。 | 修复错误图标导入与未使用符号，确保新增页面/组件通过 `tsc -b`；将 build 设为阶段硬门禁。 | 全方案实施结束后统一处理 | DEFERRED |
| P3-DI-005 | Phase 3 新增 replay/recalculate 端点缺少专项自动化测试。 | 测试检索结果未覆盖 `/agent/replay/*` 新端点；`pytest tests/unit/test_ai_replay_api.py -q` 在收集阶段即失败 | 回放与复算核心能力存在无感回归风险，无法形成稳定验收证据。 | 增补端点契约测试（record/get/list/recalculate/replay）；增加“记录 -> 复算 -> 差异报告”端到端单测。 | 全方案实施结束后统一处理 | DEFERRED |

## Phase 4 问题与建议

| ID | 问题描述 | 证据位置 | 风险影响 | 解决建议 | 处理时机 | 状态 |
|---|---|---|---|---|---|---|
| P4-DI-001 | 声称新增 `compensation_planner.py`，但文件缺失，`agent.py` 仍强依赖导入。 | `test -f r-mos-backend/app/services/compensation_planner.py` 返回 `MISSING`；`python -c "import main"` 报 `ModuleNotFoundError` | 主应用启动与 API 测试收集被阻断，Phase 4 无法完整验收。 | 补齐 `compensation_planner.py` 并提供最小单测；或将导入改为可选并在未启用时降级。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-002 | `system_monitor.py` 依赖 `psutil`，当前运行环境未安装；且新增依赖未见 ADR 记录。 | `python -c "from app.services.system_monitor import system_monitor"` 报 `ModuleNotFoundError: psutil`；`requirements.txt` 新增 `psutil>=5.9.0` | 监控服务与相关端点不可运行，且违反“新增依赖需 ADR”约束风险。 | 在 `.venv` 安装并锁定依赖；补充 ADR 说明依赖引入、影响与回滚策略；增加依赖检查门禁。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-003 | 验收仪表盘页面仍使用本地 mock 数据，未接入 `/agent/metrics*` 真实接口。 | `r-mos-frontend/src/pages/admin/AcceptanceDashboardPage.tsx` 中 `mockMetrics` 与 “Mock data for demonstration” | 页面展示与后端真实指标脱节，验收结论不可追溯。 | 将 `loadMetrics` 接入 `GET /agent/metrics` + `POST /agent/metrics/report`，补充错误态/空态与刷新逻辑。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-004 | `/agent/monitor/metrics/history` 返回历史，但当前链路未调用 `record_metrics()`，历史数据可能长期为空。 | `system_monitor.py` 中 `record_metrics()` 未被端点调用；`agent.py` 仅调用 `get_metrics_history()` | 监控历史与趋势分析失效，告警/健康分析可信度低。 | 在指标查询或后台调度中落地定时 `record_metrics()`；补充历史端点行为测试。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-005 | 验收仪表盘页面存在 JSX 语法错误，前端构建失败。 | `npm run build` 报 `AcceptanceDashboardPage.tsx(324,33): TS1382`（`>=` 未转义） | Phase 4 前端交付不可构建，不可发布。 | 修复 JSX 文本转义（如 `&gt;=`），并补跑 `tsc -b`/`npm run build` 作为硬门禁。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-006 | 指标口径实现偏差：`M-ENTRY-001` 被硬编码为 100%；`M-SAFE-001` 将“未授权尝试”计入“放行率”，语义不一致。 | `r-mos-backend/app/services/acceptance_metrics.py`（`_unique_write_entries += 1`、`uniqueness_rate = 100.0`、`bypass_rate = unauthorized_attempts / total_write_requests`） | 指标可能误报通过/失败，验收结论失真。 | 以真实唯一 entry_id 去重计算；将 M-SAFE-001 改为“未授权但被放行的比例”，区分“尝试”与“放行”。 | 全方案实施结束后统一处理 | DEFERRED |
| P4-DI-007 | Phase 4 新增 metrics/monitor/acceptance dashboard 缺少专项自动化测试。 | 检索命令：`rg -n "acceptance_metrics|system_monitor|/agent/metrics|/agent/monitor|AcceptanceDashboardPage" ... --glob '*test*'` 未命中 | 回归风险高，无法形成稳定验收证据链。 | 增补后端 API 契约测试与前端页面最小测试（加载/错误态/渲染断言）。 | 全方案实施结束后统一处理 | DEFERRED |

## 统一收敛验收门禁（建议）
- 后端：`pytest tests/unit/test_migration_contract.py -q` 通过。
- 后端：新增 `agent v2` 契约/路由测试全部通过。
- 前端：`npm run build` 通过。
- 联调：`/agent/v2/request` 与策略/资源/trace 相关端点最小链路可用。
- 审计：deny/approval/replay 关键路径均有可追溯证据。

## 备注
- 本文档仅做问题与建议汇总，不改变当前实施节奏。
- 统一收敛时应与 `docs/testing/TEST_PLAN.md`、`docs/testing/TEST_REPORT.md` 同步更新。
