# DEV_TASK_BRIEFING_001｜R-MOS v0.3（Jarvis）正式开发任务书

> 版本：v1  
> 日期：2026-02-06  
> 目标：将现有“维保教学与裁决平台”进入可持续迭代的工程化开发节奏；本文件是本轮开发的唯一入口文档（Single Source of Truth）。
> “以 docs/testing/ACCEPTANCE_CHARTER.md 为验收裁决规则，以 ACCEPTANCE_TEST_MATRIX.md 为验收点清单。”

---

## 0. 背景与现状（不争论）
R-MOS 当前已具备：
- SOP 执行、任务管理、过程事件、快照、评分、证据包、教学作业与诊断报告等闭环能力
- 前端 3D 模型交互与裁决流程演示
- 后端以 MockRobotAdapter 为主，真实硬件链路尚未打通
- 鉴权/授权与 AI 能力尚未落地（本轮优先补齐鉴权地基 + AI 入口治理）

现状说明以 `PROJECT_MANUAL.md` 为准。

---

## 1. 本轮任务总目标（必须同时满足）
1) **用户注册/登录 + RBAC 权限体系落地**（路由级 + 对象级 + 审计）  
2) **Jarvis（AI 数字孪生维保智能体）最小可用链路落地**：以“建议/生成/解释”为主，严格人类确认（human-in-the-loop），与 RBAC/审批门控联动  
3) **验收矩阵可执行**：按 `ACCEPTANCE_TEST_MATRIX.md` 分阶段可回归，做到“每次改动可证据化”

---

## 2. 范围（In Scope / Out Scope）
### 2.1 In Scope（本轮做）
- AuthN/AuthZ：注册、登录、刷新、密码重置、角色/权限、对象级访问控制、审计日志
- AI：Command API 入口、Tool/Skill Registry 治理、审批门控、RAG（如已在 ADR 中定义）、最小 Jarvis Teacher/Student 场景链路（按 AI Twin Agent Spec）
- 测试：按验收矩阵完成 Phase 1~3 的必测集 + 冒烟回归

### 2.2 Out Scope（本轮不做）
- 企业级 SSO/OIDC
- 无人工确认的高危写操作
- 自动执行真实机器人动作（仅生成计划/提示/验证）
- 无证据引用的确定性维修结论

---

## 3. 交付物（Deliverables）
必须在仓库内形成以下交付物：
- 代码：后端/前端功能实现（最小可用闭环）
- 文档：必要的 ADR/规范增补（仅当实现引入新约束或新模块）
- 测试证据：可复现的测试命令与结果摘要（对应验收矩阵条目）

---

## 4. 验收标准（Acceptance）
以 `docs/specs/ACCEPTANCE_TEST_MATRIX.md` 为最终验收口径，并满足：
- Auth/RBAC：Phase 1 全部必测条目通过
- Skill 治理与审批：Phase 2 必测条目通过
- AI 能力（RAG + Agent）：Phase 3 必测条目通过（至少完成最小链路，不追求全量功能）

---

## 5. 文件优先级（冲突时按此裁决）
1) `docs/adr/ADR.md` + `docs/adr/ADR-AI-STACK-001.md`（技术栈与硬约束）
2) `docs/specs/AUTHZ_RBAC_SPEC_FINAL.md`
3) `docs/specs/AI_AUTHZ_INTEGRATION_SPEC_REVISED.md`
4) `docs/specs/AI_TWIN_AGENT_SPEC_REVISED.md`
5) `docs/specs/ACCEPTANCE_TEST_MATRIX.md`
6) `docs/design/HLD_JARVIS_V0_3.md`
7) `docs/design/LLD_TASK_BREAKDOWN_V0_3.md`
8) `docs/ops/RUNBOOK.md`
9) `docs/ops/CODEX_RULES.md`
10) `PROJECT_MANUAL.md`（现状说明与地图）

---

## 6. 开发组织方式（里程碑）
- M1：Auth/RBAC 地基（Phase 1）
- M2：Skill 治理 + 审批门控（Phase 2）
- M3：AI 最小链路（Phase 3）
- 每个里程碑必须：
  - 对应验收矩阵条目通过
  - 写入 DEVELOPMENT_LOG.md（记录变更点、测试证据、风险）

---

## 7. 关键红线（必须遵守）
- 安全红线：AI 调用必须继承用户权限上下文；高危动作必须审批与人工确认
- 语义红线：READ 越权按规范返回（例如对象级 READ 越权 → 404 的策略如规范所述）
- 可回归红线：每次改动必须能通过最小回归命令集（后端 pytest + 前端裁决测试）
- 文档红线：除非新增约束，否则不改 spec 的“规则性条款”，只在实现中遵守

---

## 8. 本轮最小成功定义（Definition of Done）
- 能创建用户并登录
- 不同角色访问同一资源得到不同的可预期结果（允许/拒绝/审计）
- 教师通过 AI Command 生成一份“派单草案”（SOP+任务链+rubric），进入审批，审批后落库可见
- 学生通过 AI 语音/文本交互获取 SOP 步骤解释（最小 demo），所有输出带 evidence_refs 或明确“无证据”
- Phase 1~3 的必测条目通过，并能复现

---
