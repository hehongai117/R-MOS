# ACCEPTANCE_CHARTER｜R-MOS v0.3（Jarvis）验收标准总纲
> 状态：Active  
> 目的：把“通过验收”定义为唯一目标；任何开发活动以此为终点。  
> 适用范围：所有 v0.3 相关开发、修复、重构、文档与测试。  
> 规范关系：本文件定义“如何判定通过”；ACCEPTANCE_TEST_MATRIX.md 定义“测哪些点”。

---

## 1. 验收裁决规则（Definition of Acceptance）
一次改动被判定“通过”，必须同时满足：
1) **功能满足**：实现的功能点符合对应 Spec（AUTHZ/AI 集成/智能体规范）。  
2) **安全满足**：鉴权/授权/对象级控制/审批门控/审计记录符合 Spec。  
3) **可回归**：通过最小回归集（见第 5 节），且不破坏已通过的门禁项。  
4) **证据可复现**：提供可复制命令 + 输出摘要 + 失败时完整错误（记录入 DEVELOPMENT_LOG）。  
5) **验收点覆盖**：明确声明并实际通过对应的验收点（Test ID），不允许“只跑部分但声称完成”。

---

## 2. 门禁分级（Gates）与里程碑绑定
> 任何里程碑的“完成”必须通过对应 Gate；不得跳过。

### Gate-1：AUTH 基线门禁（M1 必须通过）
- 认证链路：注册/登录/刷新/登出
- RBAC：角色与权限键生效
- 对象级控制：越权读/写按规则裁决
- 审计：deny 必记录（含真实 resource_id）

### Gate-2：审批与技能治理门禁（M2 必须通过）
- Skill Registry：风险分级与 side_effects 一致性校验（RISK-001/002/003）
- Approval：medium 写入必须 teacher confirm；critical 双人确认按策略
- 审计链：tool_call_pending → approval_granted → tool_call_success/failed 可追踪

### Gate-3：Jarvis 最小链路门禁（M3 必须通过）
- Command 入口：统一输入输出结构
- RAG：对象级后过滤（返回空/insufficient_data），引用可验证
- Timeline/Replay：引用可定位可回放（最小版）
- trace_id：Command → ToolCall → Approval → Audit 串联一致

---

## 3. 关键语义裁决（不允许二义性）
### 3.1 HTTP 响应码裁决（对象级）
- **Read 越权（GET/READ）**：对外返回 **404**（防资源探测）
- **Write 越权（POST/PATCH/DELETE/WRITE）**：对外返回 **403**
- 无论 404/403：都必须写审计（记录真实 resource_id + reason）

### 3.2 RAG 过滤 vs HTTP 响应码
- **RAG 后过滤返回空**是“检索层行为”，不等同 HTTP 404
- 若同一资源：
  - HTTP GET 越权：404
  - RAG 命中但被过滤：返回空/insufficient_data（可选记录 denied_count 审计）

### 3.3 写工具门控（Human-in-the-loop）
- 任意 `side_effects` 非空：必须 `risk_level >= medium` 且走审批
- 未审批不得落库，不得绕过审批直接写入

---

## 4. 证据要求（Evidence Requirements）
每个验收点（Test ID）通过必须有证据，格式如下：
- Test ID：
- Command(s) Run：
- Key Output：
- Result：PASS/FAIL
- Linked Commit Hash：
- Notes/Risks：

证据必须写入 DEVELOPMENT_LOG.md；不得只在聊天中口头描述。

---

## 5. 最小回归集（Minimum Regression Set）
> 每次提交/合并前必须至少跑一遍（按项目现状存在的脚本/命令）。

- 后端：
  - 单元/集成测试（如 pytest 或现有脚本）
  - Health check：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:<BACKEND_PORT>/health`
- 前端：
  - build（npm run build）或等价可复现命令
- 端到端（如存在）：
  - scripts/run_phase3_regression.sh 或后续 Jarvis 回归脚本

若某项暂不存在，必须在 TEST_PLAN 中标记为 N/A，并说明原因与替代验证。

---

## 6. 例外处理（Exception Policy）
允许出现 N/A 仅在以下条件同时满足时：
- 该验收点在当前里程碑不适用（明确写明不适用原因）
- 提供替代验证方式（如 mock/日志/接口替代）
- 在 TEST_PLAN 与 DEVELOPMENT_LOG 同步记录

严禁为了凑数而编造通过或跳过。

---

## 7. Codex 执行要求（以终为始）
Codex 每次任务必须：
1) 在开始时声明：本次目标 Gate、对应 Test IDs、预期证据
2) 在结束时提交：Test IDs 的执行命令与输出摘要，并写入 DEVELOPMENT_LOG
3) 若未通过：必须给出失败原因、修复计划与回滚策略

---

## 8. 与测试矩阵的关系
- 本文件：定义“通过的裁决规则、门禁、证据格式、回归最小集”
- ACCEPTANCE_TEST_MATRIX.md：列出每条 Test ID 的具体场景/步骤/断言/期望

冲突裁决：若矩阵出现二义性（例如“404或过滤”），以本 Charter 的语义为准，并修正矩阵。
