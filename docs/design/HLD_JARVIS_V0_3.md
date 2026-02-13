# HLD_JARVIS_V0_3｜R-MOS 数字孪生维保智能体 High-Level System Design
> 状态：Draft（可进入实现分解）  
> 依据：PROJECT_MANUAL.md（As-built）、AUTHZ_RBAC_SPEC_REVISED.md、AI_AUTHZ_INTEGRATION_SPEC_REVISED.md、AI_TWIN_AGENT_SPEC_REVISED.md、ACCEPTANCE_TEST_MATRIX.md  
> 目标：在不推倒既有系统的前提下，增量实现 Jarvis v0.3：可控执行、可审计、可回放、可治理、可扩展。

---

## 0. 核心结论
1) **增量架构**：复用现有 API/服务/数据模型与执行闭环（SOP→Task→Event/Snapshot→Evidence→Diagnosis + 教学闭环 + WS 遥测），在其上新增 AI 子系统（Command/Skill/Approval/RAG/Timeline/Eval）。  
2) **安全先行**：所有 AI 能力必须继承 AUTHZ（RBAC+对象级）与统一响应码（Read 越权 404；Write 越权 403），并对 deny/写操作全审计。  
3) **三层能力落地路径**：Layer A（RAG Read-only）→ Layer B（Agent 工具调用 + 审批）→ Layer C（Eval/Replay/Regression），顺序不可反。  

---

## 1. As-built 基线（必须复用）
### 1.1 已实现链路（关键资产）
- 执行闭环：`SOP -> Task -> StepExecution -> Event/Snapshot -> Score -> Report`  
- 教学闭环：`Assignment -> Attempt -> TaskExecution -> Evidence -> Diagnosis`  
- 适配器 API：结构查询、故障注入/清除、活动故障、健康检查  
- WS 遥测：`WS /ws/robot/status`（5Hz 推送 + Ping/Pong）  

> 以上已在 PROJECT_MANUAL 明确列出，不可重复造轮子，所有智能体工具应优先调用现有服务能力。  

---

## 2. v0.3 目标能力（系统级）
### 2.1 Jarvis v0.3 关键新增模块（来自 spec）
- Skill Registry + Governance（版本/签名/权限/风险/回滚/审计策略）  
- 指令入口 Command API + 常驻调度 Scheduler/Policy  
- 审批流 Approval（medium/high/critical 写工具门控）  
- 多模态时间轴（timeline + alignment_map）  
- RAG（检索 + 对象级后过滤 + 引用）  
- Eval/Replay/Regression（离线评估、回放、红队用例）  

---

## 3. 高层架构（组件划分）
### 3.1 逻辑组件（服务/模块）
1) **Auth Service（现有系统补齐）**  
   - JWT/Session、RBAC、对象级权限校验、统一 403/404 策略、审计写入接口  
2) **Core Domain Services（现有）**  
   - SOPService / TaskService / EventService / SnapshotService / EvidenceService / DiagnosisService  
   - Teaching：Course/Class/Enrollment/Assignment/Attempt  
   - Adapter：structure/faults/inject/clear  
3) **AI Gateway（新增）**  
   - 统一入口：`POST /api/v1/ai/commands`（Command 协议）  
   - 统一输出：command_result（queued/running/waiting_approval/done/failed）  
4) **Skill Runtime（新增）**  
   - Tool/Skill 调度器：解析“需要调用的 Skill” → 校验 → 执行 → 记录 tool_call  
   - 读工具：直接执行（仍审计）  
   - 写工具：创建 Approval，进入等待态  
5) **Skill Registry + Governance（新增）**  
   - skills 表（元数据：risk_level/side_effects/preconditions/allowlist_resources/签名/版本）  
   - 发布流程：draft → review → published → deprecated  
   - 规则：side_effects 非空 → risk_level 不得 low（硬约束）  
6) **Approval Service（新增）**  
   - approvals 表 + approval_policies 表  
   - 状态机：pending → approved/rejected/expired  
   - 权限键：approvals:read/propose/approve/reject（auditor 落地）  
7) **RAG Service（新增）**  
   - 索引构建：SOP/故障库/历史 evidence/diagnosis（按 scope 分区）  
   - 查询：向量检索候选 → 对象级后过滤 → 组装 citations  
   - 说明：**RAG 过滤=检索层返回空**，不等同于 HTTP 资源访问响应码；HTTP GET 仍遵循 404 策略  
8) **Timeline Service（新增）**  
   - timeline/segments/alignment_map 管理  
   - 为“证据卡片/回放/AR 高亮/反事实”提供定位能力  
9) **Eval/Replay Service（新增）**  
   - 记录 ai_messages/ai_tool_calls/ai_eval_runs  
   - 以 trace_id 回放完整链路：输入→检索命中→工具→审批→审计→输出  

---

## 4. 数据存储设计（High-level）
### 4.1 主库（PostgreSQL，延续）
- 现有：SOP/Task/Event/Snapshot/EvidenceBundle/Attempt/Diagnosis/Assignment…（已实现 21 张表的规模）  
- 新增（最小集合）：
  - `skills`（Skill 元数据、版本、签名、风险、side_effects、allowlist）  
  - `skill_releases`（发布记录：review/published/deprecated）  
  - `commands`（Command 协议输入）  
  - `command_results`（状态与产物引用）  
  - `ai_messages`（输入/输出/引用/trace_id）  
  - `ai_tool_calls`（tool 名称、args 摘要、结果摘要、trace_id）  
  - `approvals`（审批对象）  
  - `approval_policies`（risk_level→required_approvers）  
  - `multimodal_timeline` / `timeline_segments` / `alignment_map`  
  - `ai_eval_runs` / `ai_eval_cases` / `ai_eval_metrics`  
- 审计表 `audit_events` 扩展字段（trace_id、skill_id、approval_id、side_effects_applied 等）

### 4.2 对象存储（可选但建议）
- 视频/音频/大体积日志：存对象存储；PG 只存引用与片段索引（segments）  

---

## 5. 关键协议与接口契约
### 5.1 Command API（统一交互入口）
- `POST /api/v1/ai/commands`
- request（核心字段）：intent, scope(assignment_id/attempt_id/task_id), constraints, trace_id（服务端生成亦可）
- response：command_id, status, next_actions, citations/evidence_refs, approval_required?

### 5.2 Skill 调用契约（内部或对外）
- 输入：skill_id, version, args, trace_id, actor_user_id
- 输出：result + `evidence_refs`（强制）+ side_effects_applied（若写入成功）

### 5.3 Approval API
- `POST /api/v1/approvals`（propose）
- `POST /api/v1/approvals/{id}/approve`
- `POST /api/v1/approvals/{id}/reject`
- 权限：approvals:*（见 AUTHZ）

### 5.4 RAG 查询接口（Read-only）
- `POST /api/v1/ai/rag/query`
- 返回：answer + citations + denied_count（可选审计字段）
- 强制：对候选文档做对象级后过滤

---

## 6. 权限与安全门控（系统级落点）
### 6.1 响应码统一策略
- Read 越权：404  
- Write 越权：403  
- 但 deny 必须写审计：记录真实 resource_id 与 reason（即使对外返回 404）

### 6.2 AI 的继承规则
- AI 只能访问当前 user 可访问的数据（对象级过滤）  
- Skill 的 `preconditions` 与 `allowlist_resources` 必须校验  
- side_effects 非空 ⇒ risk_level ≥ medium ⇒ 必须审批  
- 引用 ID 强制服务端校验存在且可访问，禁止伪造引用  

### 6.3 反注入与参数校验
- 工具参数 schema 校验 + 黑名单/注入模式检查  
- 用户输入不得直接拼接成执行命令；所有执行通过 Skill Registry  

---

## 7. 状态机设计（High-level）
### 7.1 Command 状态机
- queued → running → (waiting_approval) → done/failed
- waiting_approval：必须可恢复（服务重启不丢）

### 7.2 Approval 状态机
- pending → approved / rejected / expired
- approved 后：Skill Runtime 才可执行写工具

### 7.3 失败处理（统一）
- 缺乏数据：返回缺失项 + 补采清单（禁止确定性结论）
- 引用校验失败：ValidationError + 审计 reference_validation_failed
- 权限不足：Read 场景对外 404；Write 场景 403；均写审计

---

## 8. 端到端可追溯（Traceability）
### 8.1 trace_id 链路（必须一致）
- Command(trace_id) → ai_messages(trace_id) → ai_tool_calls(trace_id) → approvals(trace_id) → audit_events(trace_id)
- 回放：按 trace_id 拉取全链路并渲染成时间线

---

## 9. 性能与扩展点（最小约束）
- RAG：优先元数据预过滤（owner_user_id/course_id）再向量检索，后过滤兜底  
- 审批：批量场景需异步执行并可部分失败回滚（后续）  
- Timeline：先覆盖 log/event/snapshot；视频/音频分期接入  

---

## 10. 实施顺序（必须按此推进）
1) AUTHZ/RBAC + 对象级 + 审计 + 403/404 统一策略  
2) Skill Registry（含 risk_level 硬约束）+ Skill Runtime（先读工具）  
3) Approval Service（medium 写工具最小闭环）  
4) Command API（消息即指令）+ trace_id 串联回放  
5) RAG Read-only（对象级后过滤 + 引用）  
6) Timeline 最小版（evidence_cards 可回放）  
7) Eval/Regression + 红队用例（纳入 CI 或跑批）  

---

## 11. 验收映射（与 ACCEPTANCE_TEST_MATRIX 对齐）
- AUTHZ：OBJ/SEC 用例（401/403/404、对象级、审计 deny）  
- Skill：SKILL 用例（side_effects→risk_level 硬约束）  
- Approval：APPR 用例（pending/approved/rejected/expired）  
- RAG：RAG 用例（越权过滤返回空 + 审计 deny_count/trace_id）  
- E2E：E2E-T006/007/008（trace_id 串联、回放完整性、引用可回放）  

---

## 12. 开放问题（必须在实现前定稿）
1) critical 动作的双人确认组合：teacher+admin vs teacher+auditor（是否允许 auditor 参与）  
2) 对象级过滤性能：是否做“权限元数据预过滤”必选（建议必选）  
3) 多模态数据的最小接入范围：v0.3 是否先只做 log/event/snapshot 对齐  

---
> 守护规则：无引用不结论；写工具必审批；deny 必审计；trace_id 必可回放。
