# LLD_TASK_BREAKDOWN_V0_3｜R-MOS Jarvis v0.3 模块级设计与小任务拆分
> 状态：Draft（可直接进入开发派工）  
> 输入依据：HLD_JARVIS_V0_3、AUTHZ_RBAC_SPEC_FINAL、AI_AUTHZ_INTEGRATION_SPEC_REVISED、AI_TWIN_AGENT_SPEC_REVISED、ACCEPTANCE_TEST_MATRIX  
> 输出目标：将 v0.3 大任务拆成“可执行小任务”，每个任务都有：范围、依赖、产物、完成标准（DoD）、验收用例映射（Test ID）。

---

## 0. 全局硬约束（所有模块必须遵守）
### 0.1 统一响应码与审计（AUTHZ）
- Read 越权：返回 **404**；Write 越权：返回 **403**。:contentReference[oaicite:2]{index=2}  
- 所有 deny（包含 401/403/404 的权限相关失败）必须写 `audit_events`，并记录真实 `resource_id`（即使对外返回 404）。:contentReference[oaicite:3]{index=3}  
- auditor 试图审批非 critical 或执行普通写操作：返回 403（AUTHZ_005）。:contentReference[oaicite:4]{index=4}

### 0.2 risk_level 硬约束（Skill 治理）
- `side_effects` 非空 ⇒ `risk_level` 不能为 low（RISK-001）。:contentReference[oaicite:5]{index=5}  
- `side_effects` 含关键资源（assignments/grades/publishing/bulk_dispatch/faults/delete）⇒ `risk_level` ≥ high（RISK-002）。:contentReference[oaicite:6]{index=6}  
- `risk_level=critical` ⇒ feature_flag 默认 false + rollback_strategy 非空（RISK-003）。:contentReference[oaicite:7]{index=7}

### 0.3 RAG 过滤 vs HTTP 响应码（必须分通道）
- RAG 的“对象级后过滤返回空”属于检索层策略；HTTP GET 仍严格遵循 Read=404。:contentReference[oaicite:8]{index=8}  
- 验收矩阵中不得出现“404或过滤”二义性（必须拆分断言）。:contentReference[oaicite:9]{index=9}

---

## 1. 里程碑与依赖顺序（派工顺序）
M0：AUTHZ 地基（认证/RBAC/对象级/审计）  
M1：Skill 治理 + Tool Executor（先 Read Tool，再 Write Tool）  
M2：Approval 流程（medium→high→critical）  
M3：Command API（统一指令入口 + trace_id 串联）  
M4：RAG Read-only（对象级后过滤 + citations）  
M5：Timeline 最小版（evidence_refs 可回放）  
M6：Eval/Replay/Regression（trace 回放 + 红队用例）

> 该顺序与 HLD 的模块拆分一致：Command/Skill Runtime/Registry/Approval/RAG/Timeline/Eval。:contentReference[oaicite:10]{index=10}

---

## 2. 模块 A：AUTH（认证与会话）
### A.1 组件与接口
- Auth API：register/login/refresh/logout
- Token：access 15min + refresh 7d；refresh 可撤销（登出）:contentReference[oaicite:11]{index=11}

### A.2 小任务列表
**A-001 注册接口**
- 依赖：DB users 表（既有/或新增）
- 产物：POST /api/v1/auth/register
- DoD：通过 AUTH-T001~AUTH-T003:contentReference[oaicite:12]{index=12}

**A-002 登录接口**
- 产物：POST /api/v1/auth/login（返回 access+refresh+user.roles）
- DoD：通过 AUTH-T004~AUTH-T005:contentReference[oaicite:13]{index=13}

**A-003 刷新与撤销**
- 产物：POST /api/v1/auth/refresh；POST /api/v1/auth/logout（撤销 refresh）
- DoD：通过 AUTH-T006~AUTH-T009:contentReference[oaicite:14]{index=14}

---

## 3. 模块 B：RBAC + 对象级权限（Object-level）
### B.1 组件与规则
- Service 层对象级规则：OBJ-001~OBJ-004（student owner；teacher 课程范围；admin 全量；auditor 只读）:contentReference[oaicite:15]{index=15}  
- 统一响应码策略：Read=404，Write=403:contentReference[oaicite:16]{index=16}

### B.2 小任务列表
**B-001 权限键与路由守卫（RBAC）**
- 产物：require_role/require_permission 中间件（或依赖注入）
- DoD：SKILL-T002（缺少角色→403 AUTHZ_001）:contentReference[oaicite:17]{index=17}

**B-002 对象级校验落地（Attempt/Evidence/Task）**
- 产物：AttemptService.get_attempt / get_evidence 等实现对象级规则
- DoD：SEC-T006（WRITE 越权→403+审计）；MVP-008（Read 越权→404+审计）:contentReference[oaicite:18]{index=18} :contentReference[oaicite:19]{index=19}

**B-003 Auditor 限制规则（AUTHZ_005）**
- 产物：auditor 执行普通写 / 审批非 critical → 403 AUTHZ_005
- DoD：与 APPR 模块联动（见 APPR-T003/新增用例）:contentReference[oaicite:20]{index=20}

---

## 4. 模块 C：审计 Audit Events
### C.1 组件与字段
- audit_events 必含：actor_user_id、action、resource_type、resource_id（真实）、decision、reason、request_meta、trace_id（若有）:contentReference[oaicite:21]{index=21}

### C.2 小任务列表
**C-001 审计写入库（统一函数）**
- 产物：audit.log_event(...)（所有模块复用）
- DoD：AUDIT-T006（404 deny 仍记录真实 resource_id）:contentReference[oaicite:22]{index=22}

**C-002 审计查询接口**
- 产物：GET /api/v1/audit/events?trace_id=...
- DoD：AUDIT-T008（trace 序列完整且时间戳递增）:contentReference[oaicite:23]{index=23}

**C-003 审批审计**
- 产物：approval_granted / approval_rejected 审计事件
- DoD：AUDIT-T007 + APPR-T001:contentReference[oaicite:24]{index=24} :contentReference[oaicite:25]{index=25}

---

## 5. 模块 D：Skill Registry + Governance（治理）
### D.1 状态机
draft → review → published → deprecated（review 可 rejected）:contentReference[oaicite:26]{index=26}  
审核必须执行 RISK-001/002/003 检查清单:contentReference[oaicite:27]{index=27}

### D.2 数据表（最小集合）
- skills（skill_id/version/risk_level/side_effects/preconditions/input_schema/allowlist/feature_flag/rollback_strategy）
- skill_releases（status、review_notes、published_at、deprecated_at）

### D.3 小任务列表
**D-001 Skill 元数据模型与校验器**
- DoD：SKILL-T005（input_schema 校验失败→ValidationError）:contentReference[oaicite:28]{index=28}

**D-002 风险规则校验（RISK-001/002/003）**
- DoD：SKILL-T009、SKILL-T010、SKILL-T003（critical 双人确认要求）:contentReference[oaicite:29]{index=29} :contentReference[oaicite:30]{index=30}

**D-003 生命周期 API（draft/review/publish/deprecate）**
- DoD：SKILL-T007（状态流转）、SKILL-T008（废弃后新调用拒绝）:contentReference[oaicite:31]{index=31}

---

## 6. 模块 E：Tool Executor（工具执行器）
### E.1 执行模型（来自集成规范示例）
- medium：创建 Approval → waiting_approval → confirm → 执行写入 → 审计 tool_call_success:contentReference[oaicite:32]{index=32}  
- Read 越权：抛 NotFoundError（Read 404）并审计 access_denied/tool_call_failure:contentReference[oaicite:33]{index=33}

### E.2 小任务列表
**E-001 ToolCall 记录与 trace_id 贯穿**
- 产物：ai_tool_calls 表（或等价记录），包含 trace_id
- DoD：AUDIT-T008（tool_call_pending→approval_granted→tool_call_success 链）:contentReference[oaicite:34]{index=34}

**E-002 Read Tool 执行通道**
- DoD：AGENT-T001~AGENT-T004；AGENT-T003（越权失败+审计）:contentReference[oaicite:35]{index=35}

**E-003 Write Tool 执行通道（只做到 medium）**
- DoD：AGENT-T006（create_sop_draft waiting_approval）:contentReference[oaicite:36]{index=36}

**E-004 Security Guard（注入/引用/参数）**
- DoD：SEC-T001~SEC-T004:contentReference[oaicite:37]{index=37}

---

## 7. 模块 F：Approval Service（审批）
### F.1 风险→审批映射
- medium：teacher confirm（本人确认）:contentReference[oaicite:38]{index=38}  
- critical：需要双人确认（验收要求）:contentReference[oaicite:39]{index=39}  
- auditor：仅能参与 critical（否则 AUTHZ_005）:contentReference[oaicite:40]{index=40}

### F.2 小任务列表
**F-001 approvals 表与状态机（pending/approved/rejected/expired）**
- DoD：APPR-T001（teacher 确认 medium→approved）:contentReference[oaicite:41]{index=41}

**F-002 confirm/reject API**
- DoD：AUDIT-T007（approval_granted 审计）:contentReference[oaicite:42]{index=42}

**F-003 critical 双人确认（teacher+auditor）**
- DoD：APPR-T002（auditor 审批 critical 成功）:contentReference[oaicite:43]{index=43}  
- 同时新增/补齐：auditor 审批非 critical → 403 AUTHZ_005（建议新增 APPR-T003）

---

## 8. 模块 G：Command API（统一智能体入口）
### G.1 规范输出状态
queued/running/waiting_approval/done/failed（HLD）:contentReference[oaicite:44]{index=44}

### G.2 小任务列表
**G-001 commands 表与状态机**
- DoD：E2E trace 链可查询（配合 AUDIT-T008）

**G-002 POST /api/v1/ai/commands**
- DoD：RAG-T006（无结果返回 insufficient_data 模板）:contentReference[oaicite:45]{index=45}

**G-003 Command → Tool Plan → ToolCall（最小规划器）**
- DoD：MVP-001（口述派单返回草案，waiting_approval）:contentReference[oaicite:46]{index=46}

---

## 9. 模块 H：RAG Service（只读检索）
### H.1 行为要求
- 对象级后过滤：越权文档不返回（返回空/insufficient_data），并可选记录 deny_count；不得泄露 resource_id 列表:contentReference[oaicite:47]{index=47}  
- citations 必须可验证：每个 ref_id 可通过 API 获取:contentReference[oaicite:48]{index=48}

### H.2 小任务列表
**H-001 向量索引构建（最小：SOP/故障库/历史 evidence/diagnosis）**
- DoD：RAG-T007（引用 100% 可验证）:contentReference[oaicite:49]{index=49}

**H-002 RAG 查询接口（通过 Command 或独立端点）**
- DoD：RAG-T006、RAG-T007:contentReference[oaicite:50]{index=50}

**H-003 RAG 过滤审计（deny_count）**
- DoD：RAG-T008（rag_filter_applied 不泄露对象 ID）:contentReference[oaicite:51]{index=51}

**H-004 “RAG 空≠HTTP 404”双断言用例支持**
- DoD：RAG 相关用例（Step1返回空 + Step2返回404）:contentReference[oaicite:52]{index=52}

---

## 10. 模块 I：Timeline（证据时间轴与回放）
### I.1 最小目标
- 能把 citations/evidence_refs 定位到可回放片段（先 text_logs/event/snapshot，视频后置）:contentReference[oaicite:53]{index=53}

### I.2 小任务列表
**I-001 timeline + segments + alignment_map 表**
- DoD：MVP-005（attempt replay 返回失败点 + 补采清单；引用可回放）:contentReference[oaicite:54]{index=54}

**I-002 GET /api/v1/teaching/attempts/{id}/replay**
- DoD：MVP-005 + E2E-T008（引用可回放性）

**I-003 evidence_cards 生成（最小：日志/事件/快照聚合）**
- DoD：E2E-T008（citations/evidence_refs 可回放）

---

## 11. 模块 J：Eval / Replay / Regression（评估回放）
### J.1 trace_id 端到端要求
Command → ToolCall → Approval → Audit trace_id 一致可追踪:contentReference[oaicite:55]{index=55}

### J.2 小任务列表
**J-001 trace_id 回放接口**
- 产物：GET/POST /api/v1/ai/replay/{trace_id}
- DoD：AUDIT-T008（审计序列完整）:contentReference[oaicite:56]{index=56}

**J-002 Read Tool 成功率统计**
- DoD：AGENT-T005（≥99%）:contentReference[oaicite:57]{index=57}

**J-003 红队用例跑批（注入/伪造引用/越权）**
- DoD：SEC-T001~SEC-T007（至少 P0 覆盖）:contentReference[oaicite:58]{index=58}

---

## 12. P0 MVP 业务闭环（与 AI_TWIN_AGENT_SPEC 对齐）
最小闭环必须能跑通：派单→草案→审批→学生执行→失败→复盘→回放→难度建议→采纳（可审计）:contentReference[oaicite:59]{index=59}

### P0 业务任务映射
- MVP-001：G-002 + E-003 + F-001  
- MVP-002：F-002 + C-003  
- MVP-003：G-002 + H-002（含引用）  
- MVP-004：Scheduler（后续）  
- MVP-005：I-002  
- MVP-006：Scheduler 生成建议（可先输出草案，不自动写）  
- MVP-007：F-002 + E-003（apply_difficulty）  
- MVP-008：B-002 + C-001

---

## 13. “可派工”任务清单总表（按里程碑排序）
### M0（AUTHZ地基）
- A-001~A-003
- B-001~B-003
- C-001~C-003

### M1（Skill治理+执行器）
- D-001~D-003
- E-001~E-004

### M2（审批）
- F-001~F-003

### M3（Command）
- G-001~G-003

### M4（RAG）
- H-001~H-004

### M5（Timeline）
- I-001~I-003

### M6（Eval/Replay）
- J-001~J-003

---

## 14. 交付定义（DoD 模板）
每个任务完成必须满足：
1) 接口可调用（或内部模块可被上层调用）  
2) 错误码/响应码符合 0.1（Read=404, Write=403）  
3) deny/关键动作写 audit_events（含真实 resource_id）  
4) 通过对应 Test ID（ACCEPTANCE_TEST_MATRIX）  
5) 关键链路有 trace_id（若涉及 AI/审批/审计）

---
