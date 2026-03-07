# OPENCLAW_AGENT_UPGRADE_BLUEPRINT_V1｜R-MOS 智能体改造蓝图（修订版）
> Status: Draft for Review  
> Version: v1.1  
> Date: 2026-03-04  
> Baseline Verdict: CONDITIONAL PASS  
> Owner: Codex + 项目负责人  
> References: `docs/testing/ACCEPTANCE_CHARTER.md`, `docs/testing/TEST_PLAN.md`, `docs/testing/TEST_REPORT.md`, `docs/ops/RUNBOOK.md`, `docs/adr/ADR.md`

---

## 0. BLUF（结论先行）
当前系统可判定为“智能体雏形”，但尚未达到“可控执行 + 可验收智能体”标准。  
本蓝图将以下 4 项定义为 Gate-0 硬门禁，不满足任一项即不得宣称“AI 驱动智能体”：
1. 端点收敛：外部写入口唯一（`POST /api/v1/agent/request`）。  
2. 对象级寻址：每次执行必须绑定 `resource_ref`。  
3. 决策可复算：必须持久化 `planner/prompt/input/tool-selection` 证据字段。  
4. 策略矩阵：审批从 `risk_level` 直切升级为 `action × resource × reversibility`。  

---

## 1. 目标定义与边界

### 1.1 最终目标（Must）
1. 实现单一编排入口，彻底消除调用方绕过 orchestrator 的路径。  
2. 实现对象级授权与审计，所有动作均能追溯“对哪个对象做了什么”。  
3. 实现可复算回放，能证明“输入 -> 决策 -> 工具序列 -> 结果”。  
4. 实现可控执行，具备审批、熔断、补偿、预算约束。  

### 1.2 非目标（Non-Goals）
1. 不替换 FastAPI/React 主框架。  
2. 不在本期引入必须依赖的新外部云服务。  
3. 不重写现有 SOP/Task 领域模型，仅做兼容式增强。  

---

## 2. 现状审计（As-Is）

### 2.1 已具备能力（强点）
1. 已有 `POST /api/v1/agent/request` 作为统一入口雏形。  
2. 已有 `Command/AIToolCall/Skill/Approval/Audit` 运行骨架。  
3. 已有 trace_id 贯穿基础能力、回放与指标接口。  

### 2.2 结构性问题（阻断项）
1. 路由层形成“三套入口并存”：
   - `/api/v1/ai/*`（RAG/commands/replay）  
   - `/api/v1/agent/request`（编排入口）  
   - `/api/v1/agent/coach|diagnoser|knowledge|coordinate`（并行子入口）  
2. `Skill.allowlist_resources` 存在，但执行请求缺强制 `resource_ref`。  
3. Replay 侧有结果回看，但缺关键“决策可复算字段”。  
4. 审批触发仍偏 `risk_level` 直切，存在审批风暴风险。  

---

## 3. Gate-0 硬门禁（必须先过）

### H1. 端点收敛（Single Write Entry）
目标：
1. 对外写入口只保留 `POST /api/v1/agent/request`。  
2. 对外只读/运维接口可保留（`task-status`、`replay`、`metrics`、`evidence status`）。  
3. `coach/diagnoser/knowledge/coordinate` 从“外部能力入口”下沉为 orchestrator 内部模块调用。  

执行要求：
1. 前端 SDK 层禁止直接调用子能力写端点。  
2. 保留兼容期时，旧端点必须 `deprecated` 且记录审计事件 `legacy_endpoint_called`。  
3. 兼容期结束后，旧写端点统一返回 `410 Gone` 或受控 `403`（按策略定稿）。  

验收口径：
1. 线上写流量 100% 收敛到 `/agent/request`。  
2. 旧入口调用次数在 2 个迭代内归零。  

### H2. 资源对象级寻址（Object-Level Resource Binding）
目标：
1. 每条 Command 与 ToolCall 必须携带可解析 `resource_ref`。  
2. Policy 与 Approval 以 `resource_ref` 作为对象级裁决主键。  

最小字段要求：
1. `CommandCreateRequest.resource_ref: string`（必填，推荐）。  
2. `CommandCreateRequest.resource_scope: object`（可选，扩展对象上下文）。  
3. `AIToolCall.resource_ref: string`（持久化快照）。  

统一格式（示例）：
1. `tenant://school/{school_id}/robot/{robot_id}`  
2. `tenant://school/{school_id}/course/{course_id}/attempt/{attempt_id}`  
3. 禁止自由字符串，必须通过解析器校验。  

验收口径：
1. `resource_ref` 为空的写请求拦截率 100%。  
2. deny 审计均包含真实 `resource_ref`。  

### H3. 决策可复算证据（Deterministic Replay）
目标：
1. Replay 不仅回看结果，还能复核“为何如此决策”。  

必须持久化字段（至少）：
1. `planner_version`  
2. `prompt_hash`  
3. `inputs_hash`  
4. `selected_tools`（数组）  
5. `tool_selection_rationale`（结构化字段）  
6. `random_seed`（若策略/模型使用随机性）  
7. `policy_decision_snapshot`（allow/deny + rule_id + reason）  

验收口径：
1. 任意 trace 可重建“输入->计划->工具选择->审批->执行结果”。  
2. 缺字段 trace 一律标记 `non_replayable`。  

### H4. 策略矩阵替代 risk 直切（Policy Matrix）
目标：
1. 审批判定由 `action × resource × reversibility` 决定。  

最小矩阵规则（v1）：
1. `WRITE + irreversible + cross_resource` -> 必审（双人/多角色）。  
2. `WRITE + reversible + owned_resource` -> 可策略自动放行（额度/频次限制）。  
3. `READ` -> 默认不审，受预算门禁与对象级授权约束。  

验收口径：
1. 审批队列中的无效请求比例（可自动放行却送审）下降到 <10%。  
2. 越权写放行率 0%。  

---

## 4. 目标架构（To-Be）

### 4.1 外部接口层
1. 唯一写入口：`POST /api/v1/agent/request`。  
2. 只读观测入口：`GET /api/v1/agent/task-status/{user_id}`、`GET /api/v1/ai/replay/*`、`GET /metrics/*`。  

### 4.2 内部编排层
1. Planner（意图拆解与工具候选）  
2. Policy Evaluator（对象级授权 + 审批判定）  
3. Executor（prepare/execute/verify/commit/compensate）  
4. Critic/Replanner（失败或不确定场景重规划）  

### 4.3 内部能力模块（不再作为外部写入口）
1. Coach Module  
2. Diagnoser Module  
3. Knowledge Module  
4. Coordination Module  

---

## 5. 数据结构修订（必须落库）

### 5.1 CommandCreateRequest v2（API）
1. `intent`  
2. `input_text`  
3. `skill_id`  
4. `tool_name`  
5. `tool_args`  
6. `side_effects`  
7. `approval_id`  
8. `resource_ref`（新增，必填）  
9. `idempotency_key`（新增，必填）  
10. `deadline_ms`（新增，选填）  
11. `budget`（新增，选填：token/time/calls）  
12. `trace_id`（新增，选填，服务端可补）  

### 5.2 Command（持久化）
新增字段：
1. `resource_ref`  
2. `idempotency_key`  
3. `planner_version`  
4. `prompt_hash`  
5. `inputs_hash`  
6. `selected_tools`  
7. `tool_selection_rationale`  
8. `random_seed`  
9. `deadline_at`  
10. `budget_snapshot`  

### 5.3 AIToolCall（持久化）
新增字段：
1. `resource_ref`  
2. `request_payload_snapshot`  
3. `policy_decision`（allow/deny）  
4. `policy_rule_id`  
5. `policy_reason`  
6. `reversibility`  
7. `compensation_plan`  
8. `compensation_status`  

### 5.4 Skill（治理）
新增/强化字段：
1. `resource_scope_schema`（定义该 skill 可作用对象模式）  
2. `action_type`（READ/WRITE/DELETE/EXECUTE）  
3. `reversibility`（reversible/irreversible）  
4. `approval_strategy`（none/single/double）  
5. `max_budget_default`  

---

## 6. 路由收敛与迁移计划

### 6.1 迁移策略
1. Sprint N：旧端点标记 deprecated + 审计埋点。  
2. Sprint N+1：前端与 SDK 完成调用面切换。  
3. Sprint N+2：旧写端点关闭（410/403），仅保留只读观测端点。  

### 6.2 迁移清单（写端点）
待收敛到 orchestrator 内部调用：
1. `/api/v1/agent/coach/recommend`  
2. `/api/v1/agent/diagnoser/diagnose`  
3. `/api/v1/agent/knowledge`  
4. `/api/v1/agent/knowledge/{entry_id}/submit`  
5. `/api/v1/agent/knowledge/{entry_id}/approve`  
6. `/api/v1/agent/coordinate`  

---

## 7. 实施路线（12 周，重排后）

### Phase 0（第 1-2 周）：Gate-0 硬门禁落地
1. 完成 H1-H4 全部实现。  
2. 修复既有契约问题（fault PATCH/PUT、tasks、双前缀、状态枚举、WS 心跳、CORS 口径）。  
3. 新增 ADR：入口收敛、对象级寻址、可复算回放、策略矩阵。  
DoD:
1. 外部写入口唯一。  
2. 每条写动作有 `resource_ref` 且可审计。  
3. 每条 trace 可判定 replayable。  

### Phase 1（第 3-5 周）：编排 MVP
1. RunGraph + Step 状态机。  
2. 内部模块编排（coach/diagnoser/knowledge/coordinate）。  
3. 幂等与预算控制初版。  

### Phase 2（第 6-8 周）：状态估计与执行补偿
1. BeliefState 与多源融合。  
2. 补偿机制与失败恢复。  
3. 策略引擎与审批队列优化。  

### Phase 3（第 9-10 周）：证据与回放增强
1. 回放引擎升级为“可复算模式”。  
2. 前端时间线展示 `决策依据+规则命中+审批路径`。  

### Phase 4（第 11-12 周）：验收冲刺
1. Gate 指标复核。  
2. 回归/红队/压测闭环。  
3. 交付最终验收证据包。  

---

## 8. 量化验收指标（强制）

| Metric_ID | 指标 | 目标值 | 测量方法 | 告警阈值 |
|---|---|---|---|---|
| M-ENTRY-001 | 外部写入口唯一性 | 100% | 网关日志统计写流量路径占比 | <100% |
| M-OBJ-001 | 写请求对象绑定率 | 100% | 写请求含有效 `resource_ref` 比例 | <100% |
| M-REPLAY-002 | 可复算 trace 覆盖率 | >=98% | replayable trace / 总 trace | <95% |
| M-SAFE-001 | 越权写放行率 | 0% | 审计 deny/allow 对账 | >0 |
| M-APP-002 | 无效审批占比 | <10% | 可自动放行却进入审批的比例 | >15% |
| M-LAT-001 | 执行延迟 P95 | <=2s(read)/<=5s(write) | APM 采样 | >3s/7s |

---

## 9. 审批与策略矩阵（v1）

| Action | Resource Scope | Reversibility | Approval | Notes |
|---|---|---|---|---|
| READ | owned/cross | n/a | none | 仅对象级鉴权+预算门禁 |
| WRITE | owned | reversible | policy_auto_allow | 受额度/频次/时窗限制 |
| WRITE | cross_resource | reversible | single_approve | teacher/admin 任一 |
| WRITE | owned/cross | irreversible | double_approve | 双人确认，强审计 |
| DELETE/PUBLISH/BULK | any | irreversible | double_approve | 默认 critical |

---

## 10. 风险、回滚与应急

### 10.1 主要风险
1. 端点收敛引发短期调用兼容问题。  
2. `resource_ref` 规范初期导致请求改造成本上升。  
3. 可复算字段落库增加存储与处理成本。  

### 10.2 缓解策略
1. 以 SDK 封装做平滑迁移，禁用直连端点。  
2. 提供 `resource_ref` 解析器与校验器，统一报错码。  
3. 对可复算字段做冷热分层与压缩归档。  

### 10.3 回滚策略
1. 入口收敛采用 feature flag，故障时可回退旧入口（仅短时）。  
2. 新字段均采用前向兼容迁移，不破坏旧数据读取。  
3. 策略矩阵支持 shadow mode，先观察后强制。  

---

## 11. 第一周执行单（落地版）
1. 定义并实现 `resource_ref` 解析规范与校验中间件。  
2. 扩展 `CommandCreateRequest` 与 `Command/AIToolCall` 模型字段。  
3. 实现策略矩阵最小判定器（替换 risk 直切）。  
4. 标记并统计旧能力写端点 deprecated 调用。  
5. 前端统一改为仅调用 `/api/v1/agent/request`。  

---

## 12. 最终裁决标准（是否可宣称“智能体”）
同时满足以下四条才可通过：
1. 外部写入口唯一。  
2. 每次动作有对象级 `resource_ref`。  
3. 每次决策可复算。  
4. 失败可控（deny/compensate/evidence 链闭合）。  

缺任一项，结论退回：`LLM 增强业务系统`，不得标称 `AI 驱动智能体`。

---

> 守护底线：不绕过入口、不绕过对象级控制、不绕过审批、不伪造回放证据。
