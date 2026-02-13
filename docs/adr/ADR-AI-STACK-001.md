# ADR-AI-STACK-001｜Jarvis v0.3 智能体增量技术栈决策
> 状态：Proposed（待执行）  
> 日期：2026-02-06  
> 适用范围：AI_TWIN_AGENT_SPEC v0.3 + AI_AUTHZ_INTEGRATION_SPEC + ACCEPTANCE_TEST_MATRIX  
> 目标：在不推倒现有后端栈的前提下，引入 Jarvis v0.3 所需的 AI/检索/编排/多模态/观测与评估能力。

---

## 1. 核心结论
- 基础后端继续沿用既有体系：Python + FastAPI + PostgreSQL + WebSocket，不重构语言/框架。
- 仅补齐 Jarvis v0.3 的“增量能力栈”：向量检索、LLM 网关、Agent 编排、异步任务调度、多模态存储与时间轴索引、观测与评估回放。
- 所有 AI 能力必须满足：可审计、可追溯（trace_id）、可回放、可门控（权限/审批/风控）。

---

## 2. 背景与问题
Jarvis v0.3 引入以下新能力面：
- RAG（向量检索 + 引用）
- Agent/Skill（工具调用 + 风险分级 + 审批）
- 多模态时间轴（视频/语音/传感器/日志对齐）
- 常驻编排（Scheduler/Policy）
- Eval/Replay/Regression（离线评估、回归、红队用例）
若不做技术栈约束，开发将出现多套实现与不可控运维成本。

---

## 3. 决策驱动（必须满足的硬约束）
- D1：可控执行：写工具必须审批与审计，不可绕过。
- D2：可追溯：任何 RAG/工具/审批/审计必须可通过 trace_id 串联。
- D3：可回放：能够复现“输入→检索→工具→审批→输出”。
- D4：最小引入：P0 只引入必要组件，避免平台化过早。
- D5：可迁移：当规模/性能不满足时，能从 P0 方案平滑迁移。

---

## 4. 决策内容（Tech Stack 增量选型）

### 4.1 向量检索（RAG Index）
- P0 决策：使用 PostgreSQL + pgvector（同库同备份、运维最小）。
- 迁移触发条件：
  - 索引规模显著增长导致延迟不可接受；
  - 召回/过滤能力不足；
  - 需要多索引/分片/高可用向量服务。
- 迁移路径：抽象 `vector_store` 接口，后续可替换为独立向量库（如 Qdrant/Milvus）。

### 4.2 LLM 接入层（LLM Gateway）
- P0 决策：自建统一 `llm_gateway`（模块/服务均可），必须记录：
  - model_id、prompt_version、system_prompt、input、output、citations、latency、cost、trace_id
- 必须能力：
  - 限流/熔断；
  - 输出结构化校验（引用 ID 必须服务端校验）；
  - 可切换多模型提供方（接口抽象）。

### 4.3 Agent 编排（Workflow Orchestration）
- P0 决策：实现“可持久化状态机”能力，满足：
  - waiting_approval 状态可恢复；
  - 可插入人工确认；
  - 支持工具失败降级；
  - 全流程 trace_id 串联。
- 实现方式：
  - 优先轻量自研（以 spec 的状态机为准）；
  - 若复杂度提升，可替换为图编排框架（不在 P0 强制）。

### 4.4 异步任务与调度（Scheduler/Policy）
- P0 决策：引入可靠的任务队列与调度器（任务可持久化、可重试、可观测）。
- 要求：
  - 周报/提示等周期任务；
  - attempt 失败触发复盘等事件任务；
  - 禁止自动触发高危写操作（只生成建议与待审批单）。

### 4.5 多模态存储与时间轴索引
- P0 决策：
  - 大文件（视频/音频）进入对象存储（S3/MinIO 类）；
  - 时间轴元数据/索引（timeline/segments/alignment_map）存 PostgreSQL；
  - 任何高亮/反事实输出必须能定位到 timeline 片段。
- 原则：
  - 大文件不入主库；
  - 索引必须可查询、可审计、可回放。

### 4.6 观测与评估（Observability + Eval）
- P0 决策：
  - 分布式追踪：OpenTelemetry（或等价方案），trace_id 贯穿 Command→ToolCall→Approval→Audit；
  - 评估：离线评测集 + 回归跑批（最小可用即可）。
- 必须输出：
  - 幻觉率（无引用确定性结论）；
  - 引用覆盖率；
  - 工具调用成功率；
  - 审批等待时长与拒绝原因分布。

---

## 5. 非目标（Non-goals）
- 不做企业级 SSO/OIDC 统一身份平台（后续 ADR 再议）。
- 不做“全自动维修闭环”与无人工确认写入。
- 不在 P0 引入复杂数据湖/流处理平台。

---

## 6. 风险与缓解
- R1：pgvector 性能瓶颈
  - 缓解：接口抽象 + 可迁移；监控索引规模与查询延迟。
- R2：LLM 输出注入/伪造引用
  - 缓解：引用 ID 服务端校验；schema 校验；工具参数白名单。
- R3：异步任务导致状态不一致
  - 缓解：状态机持久化；幂等设计；审计与 trace 串联。
- R4：多模态存储成本与访问延迟
  - 缓解：对象存储分层；关键帧/片段索引；按需加载。

---

## 7. 实施顺序（与开发计划绑定）
1) AUTHZ/RBAC 落地（身份、对象级权限、审计）
2) AI_AUTHZ_INTEGRATION（Skill 风险/审批/审计字段统一）
3) llm_gateway + pgvector（RAG Read-only）
4) Scheduler/Policy（常驻编排）
5) 多模态时间轴最小版（log + event/snapshot，逐步扩展到 video/audio/sensor）
6) Eval/Replay/Regression（离线评估 + 红队用例）

---

## 8. 决策记录
- 决策采用“增量栈”策略：保持现有后端技术栈不变，只为 Jarvis v0.3 增加必需组件。
- 本 ADR 的任何变更必须通过新增 ADR 或更新状态（Accepted/Deprecated）。
