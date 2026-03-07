# R-MOS 项目全面梳理报告（As-Is）

- 生成时间：2026-03-04 22:10:59（Asia/Shanghai）
- 生成人：Codex
- 代码基线：`/Users/xuhehong/Desktop/r-mos` 当前工作区（非强制 clean tree）
- 目标：对当前项目做可落地、可追溯、可执行的全景盘点，覆盖：
  - 项目功能
  - 前端情况（详细）
  - 后端情况（详细）
  - 智能体构建情况（详细）
  - 大模型 API 接入情况（详细）
  - “任务编排（大脑）+ 技能库（手册）+ 状态估计（眼睛）+ 控制执行（手脚）+ 安全门禁（刹车）+ 证据与回放（审计）”设计
  - 记忆系统设计
  - 知识库设计
  - 现状结论与后续建议

---

## 1. 一页结论（先看）

### 1.1 当前系统本质
R-MOS 当前不是“已接入真实大模型并可自主闭环执行的生产级智能体系统”，而是：

1. 一个已可运行的“维保教学+任务执行+证据沉淀+审计回放”平台；
2. 一个已经搭出“智能体治理骨架”的系统（命令、审批、审计、回放、策略、证据、知识治理等模块齐备）；
3. 但在“模型推理层（LLM API）”“多代理实战协同”“统一记忆/知识中台”上仍处于过渡阶段。

### 1.2 能力成熟度（简版）
- 教学闭环（Assignment/Attempt/Evidence/Diagnosis）：`较成熟`
- 审计与可追溯链路（trace_id + audit_events + replay）：`较成熟`
- 审批与技能治理（Skill Registry + Approval）：`较成熟`
- Agent V2（FSM/Policy/Belief/Evidence/Replay）：`功能多，但大量 in-memory/演示实现`
- LLM API 真接入：`未接入`
- 前后端一体化程度：`中等（部分页面真实 API，部分页面仍 mock）`

### 1.3 总体判断
项目已具备“可被升级为 AI 智能体平台”的结构基础，但尚不宜对外宣称“完整 AI Agent 已上线生产”。最准确口径应为：

**“R-MOS 已完成智能体治理与审计骨架建设，核心教学/执行链路可用；当前处于从规则驱动向大模型驱动升级的关键过渡期。”**

---

## 2. 事实源与盘点口径

### 2.1 本次事实源优先级（遵循仓库规则）
1. `docs/testing/TEST_REPORT.md`
2. `docs/testing/TEST_PLAN.md`
3. `docs/ops/RUNBOOK.md`
4. `docs/adr/ADR.md`
5. `DEVELOPMENT_LOG.md`

### 2.2 代码级核验范围
- 后端：`r-mos-backend/main.py`、`app/api/v1/endpoints/*`、`app/services/*`、`app/models/*`
- 前端：`r-mos-frontend/src/App.tsx`、`src/pages/*`、`src/components/*`、`src/api/*`
- 配置与依赖：`requirements.txt`、`package.json`、`vite.config.ts`

### 2.3 规模快照（当前代码统计）
- 后端 HTTP 路由：`155`
- 后端 service 文件：`41`
- 后端 model 文件：`24`
- 后端 unit test 文件：`35`
- 前端页面：`19`（`src/pages`）+ `4`（`src/teaching/pages`）
- 前端组件：`28`
- 前端 API 封装：`13`
- 3D 模型：`364` 个 `.glb`
- alembic 迁移：`22`

---

## 3. 项目功能全景

### 3.1 业务主线功能
1. SOP 管理与任务执行：SOP 列表、创建任务、步骤执行、任务报告。
2. 教学闭环：班级/课程/报名/作业/尝试、证据摘要、诊断报告。
3. 故障与运维域：故障案例、事件、观测、证据包、外部评估。
4. 机器人可视化：Atom01 演示页 + 3D 交互维护页。
5. AI/Agent 相关：命令入口、审批、技能治理、审计、回放、策略评估、知识治理等。

### 3.2 技术主线功能
1. FastAPI + SQLAlchemy Async + Alembic 的服务化后端。
2. React + AntD + Three.js 的前端控制台。
3. Trace/Audit 统一可观测。
4. RBAC/权限键/对象级拒绝语义（404/403）基础能力。

---

## 4. 前端情况（详细）

## 4.1 技术架构与组织
- 技术栈：React 18 + TypeScript + Vite + Ant Design + axios + Zustand + React Three Fiber。
- 入口：`r-mos-frontend/src/App.tsx`
- 主布局：`src/components/Layout/AppLayout.tsx`
- API 统一前缀：`src/api/client.ts` 中 `baseURL = /api/v1`

## 4.2 路由与页面现状
当前路由同时包含：
1. 维保/教学主线页：`/sops`、`/tasks/:taskId`、`/teaching/...`
2. 运营后台页：`/admin/faults`、`/admin/seed-data`、`/admin/approvals`、`/admin/acceptance`
3. Agent 页：`/agent/workbench`、`/agent/replay`、`/ai-chat`、`/knowledge`

默认首页已指向 `AgentWorkbenchPage`（AI 工作台）。

## 4.3 前端 API 对接成熟度

### A. 真实 API 对接较好的页面
1. `AgentWorkbenchPage`：调用 `/agent/v2/request`、`/agent/v2/trace/{trace}/events`
2. `KnowledgePage`：调用 `/agent/knowledge/*`
3. `AIChatPage`：调用 `/agent/request`（旧入口）
4. 教学域页面：整体与 `teaching.py` 路由链对齐度较高

### B. 仍含明显 mock/fallback 的页面
1. `ReplayPage`：trace 数据为本地 mock。
2. `admin/ApprovalQueuePage`：待审批和历史为 mock。
3. `admin/AcceptanceDashboardPage`：API 失败时 fallback mock。
4. `IncidentListPage`/`EvidencePage`/`AssessmentStatusPage`：后端失败时 fallback mock。

### C. 权限前端实现现状
- 存在 `PermissionHint` 组件与前端权限矩阵，但角色体系与后端真实 RBAC 并未完全统一。
- 管理页面可见性主要靠菜单与路由组织，不是完整鉴权防线。

## 4.4 前端优势与问题

### 优势
1. 页面覆盖面广，功能演示完整。
2. 3D 资产与交互能力充足。
3. AI 工作台交互已具备“对话 + 风险标签 + trace 查看”的雏形。

### 问题
1. 多处关键页面仍依赖 mock，真实联调深度不足。
2. `AIChatPage` 仍走旧 `/agent/request`（deprecated）。
3. 管理域与安全域（审批/审计）存在“UI 可达但后端权限不一定打通”的风险。

---

## 5. 后端情况（详细）

## 5.1 后端总体架构
- 入口：`r-mos-backend/main.py`
- API 前缀：统一 `/api/v1`
- 中间件：请求日志 + trace_id 注入 + 响应头回传 `X-Trace-ID`
- 异常体系：业务异常、鉴权异常、对象级拒绝异常、安全违规异常、全局兜底
- WebSocket：`/ws/robot/status`

## 5.2 路由域分布（按端点文件）
- `agent.py`：`68`（最大）
- `teaching.py`：`24`
- `assessments.py`：`11`
- `tasks.py`：`8`
- `ai_commands.py`：`6`
- `approvals.py`：`4`
- `skills.py`：`3`
- `audit.py`：`1`
- 其余为运维与业务域路由

## 5.3 数据模型核心

### 执行与审计链
1. `commands`
2. `ai_tool_calls`
3. `approvals`
4. `audit_events`

### 知识与引用
1. `ai_knowledge_chunks`（RAG 引用对象）
2. `skills` / `skill_reviews` / `skill_releases`

### 教学闭环
1. `assignments`
2. `assignment_attempts`
3. `evidence_bundles`
4. `evidence_links`

### Agent 运行态持久化（新）
1. `belief_state_records`
2. `decision_records`
3. `approval_records`
4. `replay_checkpoints`

## 5.4 后端核心能力判定

### A. 相对成熟能力
1. 教学服务层（状态机、评分前提、证据/诊断生成）。
2. 审计查询和 trace 回放能力。
3. 读越权 404、写越权 403 的统一语义与 deny 审计落地。
4. 审批流：pending -> granted/rejected + tool_call 状态联动。

### B. 过渡中能力
1. `/agent/*` 下大量能力是 in-memory/简化实现。
2. `orchestrator_v2`、`multi_agent_coordinator`、`decision_recalculator` 等具备结构，但非生产化实现。
3. `runtime_persistence` 已有 DB 结构与服务，但与主要请求链路整合还不充分。

---

## 6. 智能体构建情况（详细）

当前存在“两套并行智能体体系”：

## 6.1 体系 A：审计优先的最小 AI 主链路（Gate-2/3 主线）
核心在 `ai_commands.py + approvals.py + audit.py + skills.py`：

1. Command 入口：`POST /api/v1/ai/commands`
2. 工具规划：最小 planner（dispatch 场景补 tool plan）
3. Tool Call：创建 `ai_tool_calls`（pending/success/failed）
4. 有副作用即审批：创建 `approvals`，待 grant/reject
5. 审计：全链写入 `audit_events`
6. 回放：`/api/v1/ai/replay/{trace_id}`
7. 指标：Read Tool 成功率、Red Team 通过率接口

这条链路的价值是“可追溯、可测试、可裁决”，与 Charter/TEST_REPORT 高度一致。

## 6.2 体系 B：功能覆盖更广的 Agent V1/V2 体系
核心在 `agent.py + orchestrator_v2 + belief_state + evidence_collector + ...`：

1. `/agent/v2/request` 支持 intent、resource_ref、policy_context、idempotency_key。
2. 内置 FSM（task create/transition/status）。
3. 有 belief/evidence/replay/metrics/monitor 等大量子端点。

但当前问题是：
1. 很多实现是 in-memory，进程重启即丢。
2. 多模块注释明确“生产应替换为 DB/LLM”。
3. 与 A 体系（审计硬链路）尚未统一成单一主入口。

## 6.3 智能体现状判定
- **治理框架完整度：高**（门禁、审批、审计、回放齐）
- **推理智能化程度：中低**（主要为规则/模板/占位）
- **生产可用性：中**（教学与审计链可用，Agent 全栈仍在收敛）

---

## 7. 大模型 API 接入情况（详细）

## 7.1 依赖与代码检索结论
在 `requirements.txt`、`package.json` 与后端/前端代码中，未发现以下真实接入：
- OpenAI / Anthropic / Ollama / LangChain / LiteLLM 等 SDK
- 对外 LLM HTTP 调用（如 `/v1/chat/completions`）

## 7.2 当前“AI”来源
1. 规则与模板逻辑（policy/rule-based）。
2. 关键路径上的 deterministic stub（如 `tool_executor.execute_read_tool`）。
3. 部分服务明确写明“in production use LLM”。

## 7.3 接入成熟度结论
**当前无真实大模型 API 接入。**

项目现阶段更准确描述为：
- 已搭好“模型可插拔的控制平面与治理平面”；
- 尚未完成“模型推理平面（LLM）”的生产接入。

---

## 8. 六件套架构设计映射（大脑/手册/眼睛/手脚/刹车/审计）

## 8.1 任务编排（大脑）
1. `ai_commands._plan_tool_call`：最小规划器。
2. `orchestrator_v2`：意图分类、模块分发、FSM、幂等、预算。
3. `policy_matrix.evaluate`：动作前风险判断。

现状：大脑骨架在，核心决策仍以规则为主。

## 8.2 技能库（手册）
1. `skills` 表 + review/release 体系。
2. 风险校验：RISK-001/002/003（publish 阶段强制）。
3. 与审批链、审计链联动。

现状：治理能力较完整，但“技能执行实现”仍多为 stub。

## 8.3 状态估计（眼睛）
1. `belief_state`：belief/world_model/revision（当前 in-memory）。
2. `evidence_collector`：证据收集与校验。
3. `system_monitor`：系统健康与告警。

现状：有观测面，但持久化与主链统一仍在推进。

## 8.4 控制执行（手脚）
1. 传统任务执行链：`TaskService + Adapter`（含 mock adapter）。
2. AI tool 执行链：`tool_executor`（read/write stub）。

现状：业务执行可跑；AI 工具执行层尚未接入真实外部能力。

## 8.5 安全门禁（刹车）
1. `authz_guard`：Bearer token + role + permission。
2. `access_control`：deny/allow 审计统一入口。
3. 安全校验：黑名单、注入模式、伪造引用、参数越界。
4. side_effects 写操作必须经审批链。

现状：门禁设计明确且有测试证据，是当前系统强项。

## 8.6 证据与回放（审计）
1. `audit_events` 统一审计表。
2. trace replay 接口可按 `trace_id` 拉全链事件。
3. 指标接口（成功率、红队通过率）可供验收。
4. 教学域有 evidence bundle + diagnosis 的可追溯链。

现状：审计回放能力较完整。

---

## 9. 记忆系统设计（详细）

当前记忆并非单体系统，而是“多层记忆拼接”：

## 9.1 短期/会话记忆（in-memory）
1. `belief_state`：按 `trace_id` 保存 belief、world model、revision。
2. `orchestrator_v2`：task context、event_history、idempotency cache。
3. `evidence_collector`：证据索引与状态。

特点：实时性好，但跨进程持久性弱。

## 9.2 事务记忆（数据库）
1. `commands` / `ai_tool_calls` / `approvals`：动作链记忆。
2. `audit_events`：裁决与访问行为记忆。
3. 教学域 `assignment_attempts/evidence_links/evidence_bundles`：训练过程记忆。

特点：可追溯、可审计、可回放。

## 9.3 运行态持久化记忆（新建但整合中）
1. `belief_state_records`
2. `decision_records`
3. `approval_records`
4. `replay_checkpoints`

特点：设计已落地，需进一步接入主请求链才能成为“默认记忆底座”。

## 9.4 记忆系统结论
当前记忆体系可满足“审计与业务复盘”，但尚未形成“统一长期记忆中台”。

---

## 10. 知识库设计（详细）

当前存在两条知识线：

## 10.1 RAG 引用知识库（持久化）
- 模型：`AIKnowledgeChunk`
- 能力：
  1. citations 按 `ref_id` 回查
  2. 按 owner/角色做可见性过滤
  3. 命中可过滤为空并返回 insufficient_data
- 价值：支持“可引用、可验证、可审计”的知识引用链

## 10.2 Knowledge Governance（治理知识库，当前内存态为主）
- 模型对象：scope / contraindications / risk / expiry / confidence / history
- 流程：draft -> pending -> approved/rejected -> expired
- 能力：审核、版本演进、适用范围控制、禁忌规则

## 10.3 知识系统关键问题
1. 两套知识系统尚未统一（`AIKnowledgeChunk` 与 `knowledge_governance`）。
2. 前端 `KnowledgePage` 走 `/agent/knowledge/*`（治理线），与 RAG 引用线并未打通。
3. 缺少统一索引与检索编排层。

## 10.4 知识系统结论
知识治理理念完整，但在“统一存储/统一检索/统一授权/统一引用”上仍需收敛。

---

## 11. 安全与合规设计现状

## 11.1 已落地
1. READ 越权返回 404，WRITE 越权返回 403。
2. deny/allow 都可审计，且记录真实 resource_id。
3. trace_id 可串联 command/toolcall/approval/audit。
4. 审批查询需权限与角色（admin/auditor）。

## 11.2 风险点
1. `/agent/*` 大量端点未统一接入 `require_permission` 依赖。
2. 前端管理页部分仍 mock，用户易误判“已真实入库”。
3. 端口/CORS 实际配置与文档约束存在漂移风险（需统一）。

---

## 12. 测试与证据现状

基于 `docs/testing/TEST_REPORT.md`：
1. Gate-3 与 Phase5 多组 E2E/EVAL 用例已记录 PASS。
2. 审计链、回放链、红队越权拦截有明确证据。
3. 前端 build/test 在报告口径下通过。

这说明：
- “可验证治理链”是系统最稳的部分；
- “真实智能推理能力”仍不是当前测试主通过来源。

---

## 13. 关键差距清单（必须正视）

1. LLM API 未接入：当前不具备真实模型推理能力。
2. Agent 双轨并存：`/ai/*` 与 `/agent/*` 尚未收敛单入口。
3. 知识双轨并存：RAG chunk 与治理知识未打通。
4. 前端 mock 残留：回放/审批/验收看板存在演示数据链。
5. 运行态持久化整合不足：belief/decision/checkpoint 与主路径串联不充分。

---

## 14. 建议的收敛路线（可执行）

## P0（先做，2~4 周）
1. 统一 Agent 主入口：前端与后端收敛到单一路径（建议 `/api/v1/ai/commands` 或其 V2 统一版）。
2. 替换关键页面 mock：`ReplayPage`、`ApprovalQueuePage`、`AcceptanceDashboardPage` 全部改真实 API。
3. 给 `/agent/*` 增加统一鉴权中间层与权限依赖。

## P1（随后，4~8 周）
1. 接入首个可控 LLM Provider（保留“可关闭/可回退”特性）。
2. 把 `runtime_persistence` 接入主链，形成持久化记忆默认路径。
3. 打通知识双轨：治理知识发布后落盘为可引用 chunk。

## P2（中期，8~12 周）
1. 建立统一“模型路由 + 提示模板 + 评测指标”体系。
2. 完成策略中心与审批中心可配置化。
3. 做生产级 SLO/SLA 与容量压测，形成上线门禁。

---

## 15. 终极总结与最终结论

## 15.1 答案总结
R-MOS 当前已经形成“平台底座 + 治理骨架 + 教学闭环 + 审计回放”的完整框架：

1. 前端：页面完整，AI 工作台雏形可用，但多处管理/回放仍存在 mock。
2. 后端：路由规模大，教学与审计链稳定；AI 工具执行层当前以 stub 为主。
3. 智能体：有完整六件套架构映射，但智能推理核心仍未接 LLM。
4. 安全：对象级拒绝语义、审批链、审计链是当前最强资产。
5. 记忆与知识：设计丰富，但存在多系统并行、尚未统一的现状。

## 15.2 最终结论（裁决）

**结论：R-MOS 已具备“可验收、可审计、可持续演进”的智能体工程框架，但尚未达到“真实大模型驱动的生产级自治智能体”状态。**

更精确的对外口径建议：

**“我们已经完成智能体控制平面与安全治理平面的工程化，下一阶段将聚焦 LLM 推理平面接入与双轨系统收敛。”**
