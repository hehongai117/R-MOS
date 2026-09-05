# RMOS-S1-001｜目标架构

- 版本：0.1.0｜日期：2026-09-05
- 主干阶段：**S1｜目标架构**
- 主干任务编号：**RMOS-S1-001**
- 事实基线：`cb00b293`
- 取证依据：`evidence/2026-09-05-s1-current-module-and-data-ownership-facts-v0.1.0.md`（异源产出）

---

## 0. 本文件的边界

主干 §3 规定 S1 的通过条件是「主要模块清楚、每个模块的职责和数据归属清楚、董事会批准总体方向」，
并明确 **「本阶段不要求提前设计完所有接口、文件和代码」**。

因此本文件**只回答三个问题**：

1. 系统由哪些主要模块构成？
2. 每个模块负责什么、拥有哪些数据？
3. 现有实现中哪些保留、合并、替换、删除？

**本文件不写**接口签名、文件清单、目录迁移脚本或改造步骤——那是 S2／S3 的事。
本文件也**不宣布阶段通过**（主干 §4）。

---

## 1. 设计依据：当前事实

| 事实 | 数值 | 含义 |
|---|---:|---|
| 业务表 | 65 | 数据归属的分母 |
| 有归属字段的表 | 23 | 42 张无——但并非全都需要（见 §3.2） |
| 有应用层写入路径的表 | 50 | **15 张无**，即定义了却没有应用在写 |
| `services/` 根目录文件 | 36 | 平铺，未归组 |
| `services/` 一级子包 | 16 | 已按域/能力组织，组织良好 |
| 内部模块 / import 边 | 229 / 636 | 循环依赖仅 **1 组**（LLM provider 互引） |
| 持业务状态的进程内单例 | 7 | 重启即丢 |

**关键判断：本系统的分层是干净的**（api→services→models 单向，A3 已测得三个反向方向边数均为 0，
本次复测循环依赖仍仅 1 组）。**问题不在分层，在同一层内部没有分组**——
79 个文件在 16 个子包里组织得不错，36 个文件平铺在根目录没有归属。

> 这决定了目标架构的性质：**不是重写，是给已有的东西划清边界。**
> A6 已判定「整体重写缺乏架构依据」，本文件不推翻该判定。

---

## 2. 目标模块

系统由 **9 个业务模块 + 3 个支撑模块** 构成。65 张表在 9 个业务模块中**各归其一，无重复无遗漏**。

### 2.1 业务模块

| # | 模块 | 职责 | 拥有的数据（写入权） | 表数 |
|---|---|---|---|---:|
| **A** | **身份与访问控制**（横切） | 认证、授权、角色、归属判定、审计留痕。**全系统唯一的身份事实源** | `users`、`user_preferences`、`access_tokens`、`refresh_tokens`、`roles`、`permissions`、`role_permissions`、`user_roles`、`schools`、`audit_events` | 10 |
| **B** | **机器人资产** | 机型登记、资产文件、解析管线、可见性与绑定 | `robot_models`、`robot_assets`、`teacher_robot_bindings`、`analysis_tasks`、`robot_projects`、`robot_project_files`、`robot_part_manifests` | 7 |
| **C** | **知识** | 文档切块、向量化、检索底料、知识治理 | `ai_knowledge_chunks`、`knowledge_documents` | 2 |
| **D** | **SOP 与维保** | SOP 定义与版本、维保草稿与审批、故障案例 | `sops`、`sop_steps`、`sop_audit_logs`、`robot_sop_drafts`、`fault_cases`、`fault_sop_mappings` | 6 |
| **E** | **任务执行** | 维保任务生命周期、步骤执行、快照与评分 | `tasks`、`task_executions`、`task_step_results`、`events`、`snapshots` | 5 |
| **F** | **教学** | 班级、课程、选课、作业、尝试、教学证据与时间线 | `classes`、`courses`、`enrollments`、`assignments`、`assignment_attempts`、`guidance_policies`、`evidence_cards`、`evidence_links`、`alignment_map`、`multimodal_timelines`、`timeline_segments` | 11 |
| **G** | **训练** | 训练会话、提交、步骤记录、技能画像 | `training_sessions`、`training_submissions`、`session_step_records`、`student_skill_profiles`、`student_weak_steps` | 5 |
| **H** | **证据与评估** | 证据包与条目、事件、观测、外部评估 | `evidence_bundles`、`evidence_items`、`incidents`、`observations`、`external_assessments`、`assessment_providers`、`assessment_audit_events` | 7 |
| **I** | **Agent 运行时** | 意图、编排、工具调用、审批闸门、技能注册、记忆与回放 | `commands`、`ai_tool_calls`、`approvals`、`approval_records`、`skills`、`skill_reviews`、`skill_releases`、`belief_state_records`、`conversation_turns`、`decision_records`、`replay_checkpoints`、`agent_runtime_snapshots` | 12 |

**合计 10+7+2+6+5+11+5+7+12 ＝ 65**，与运行期 ORM 枚举的 65 张业务表一一对应。

### 2.2 支撑模块（不拥有业务表）

| # | 模块 | 职责 | 数据归属 |
|---|---|---|---|
| **S1** | **LLM 接入** | 供应商路由、提示词、降级与调用审计 | 无自有表；调用审计写入 **A** 的 `audit_events` |
| **S2** | **实时通道** | WebSocket 连接、鉴权、遥测推送；机器人适配器 | 无表（连接状态天然绑进程，见 §4.2） |
| **S3** | **仿真与诊断引擎** | 故障场景、仿真执行、诊断推理、维保计划生成 | 无自有表；产出交给 **D**／**E** 落库 |

### 2.3 数据归属的唯一规则

> **一张表只有一个模块可以写。** 其他模块需要改动该表的数据时，走该模块提供的能力，不直接写库。

这条规则是本架构的核心约束，它同时是三个现存问题的解法：

- **M-16**（内存代替落库）：写入权归属明确后，「谁该落库」不再有歧义
- **M-22**（任务终态写入责任未收口）：终态写入者唯一
- **M-12**（租户隔离）：租户维度只需在拥有该表的模块内实施一次

**当前违反该规则的实例**（S2 需逐条处置，本文件只登记）：
`audit_events` 现被 4 个 endpoint + 2 个 service 直写；
`assignment_attempts` 被 `evidence_engine` 与 `teaching_service` 两处写。

---

## 3. 现有实现的取舍

### 3.1 保留（多数）

16 个一级子包**全部保留**，它们已按域/能力组织，与 §2 的模块划分基本吻合：
`analysis/`→B、`knowledge/`→C、`maintenance/`+`sop/`→D、`pipeline/`→E、
`teaching/`→F、`training/`+`memory/`→G、`orchestration/`+`intent/`→I、
`llm/`→S1、`simulation/`+`diagnosis/`→S3、`storage/`→B、`identity/`→A。

### 3.2 合并：36 个根目录文件归入所属模块

这是 **M-25「模块责任／目录边界模糊」的直接解法**。根目录文件按 §2 的模块归位，例如：
`authz_guard`／`access_control`／`ownership`／`robot_visibility`／`login_throttle`／`audit_event_service` → **A**；
`robot_service`／`robot_asset_validator` → **B**；
`sop_service`／`fault_service` → **D**；
`task_service`／`event_service`／`snapshot_service`／`scoring_service`／`preflight_check` → **E**；
`teaching_service`／`diagnosis_service` → **F**；
`evidence_*`／`incident_service`／`observation_service`／`assessment_service` → **H**；
`agent_service`／`orchestrator_v2`／`multi_agent_coordinator`／`policy_matrix`／`tool_executor`／`approval_service`／`knowledge_governance` → **I**（`knowledge_governance` 的存储侧归 **C**）。

> **移动文件本身有风险且不产出功能价值。** S2 应把它排在「有独立价值的模块改造」之后，
> 或与该模块的其他改动**同批进行**，不单独为整理而整理。

### 3.3 删除

| 对象 | 依据 |
|---|---|
| `services/policy/risk_scorer.py`（及 `policy/` 包） | **零调用者**——全仓仅 `core/enums.py` 的一行注释提到它；且与根目录 `policy_matrix.py` 命名撞车，是 M-25 的具体实例 |

> 删除前须按 M-05／裁定 §9-1 的先例核验：无前端调用、无测试依赖、不在真实执行路径上。

### 3.4 需董事会裁决的重复与空置（M-14／M-16）

本文件**不替董事会决定**，只把选项摆清：

| 组 | 事实 | 待决 |
|---|---|---|
| replay 两套 | `/ai/replay/{trace_id}`（读 `audit_events`）与 `/teaching/attempts/{id}/replay`（读时间线四表）；**前端均无调用** | 保留哪套，或都留但明确各自场景 |
| 教学时间线三表 | `alignment_map`、`multimodal_timelines`、`timeline_segments` **整组无应用写入** | 是补写入路径，还是承认为未实现能力并从模块 F 的归属中移出 |
| Agent 四表 | `approval_records`、`decision_records`、`replay_checkpoints`、`agent_runtime_snapshots` 无应用写入 | 同上 |
| RBAC 四表 | `roles`／`permissions`／`role_permissions`／`user_roles` 仅种子脚本写 | 是否需要运行期管理入口 |

---

## 4. 目标架构如何对应当前问题清单

### 4.1 本架构直接解决的

| 问题 | 解法 |
|---|---|
| **M-25** 模块责任／目录边界模糊 | §2 的 12 个模块 + §3.2 的归位规则 |
| **M-16** 定义先行与内存代替落库 | §2.3 写入权唯一 + §3.4 逐组裁决空置表 |
| **M-22** 任务终态写入责任未收口 | 终态写入者唯一归模块 **E** |
| **M-14** 新旧实现并存 | §3.4 逐组裁决，不做整体关闭 |

### 4.2 本架构给出方向、但需 S2／S3 落实的

**M-19（业务状态驻留进程内）**：7 个持状态单例应分两类处置——

| 单例 | 判定 |
|---|---|
| `manager`（WebSocket 连接）、`memory_hub` 的 Redis fallback、`login_throttle` | **内存合理**。连接天然绑进程；fallback 本就是降级路径；限流在单实例下可接受 |
| `orchestrator`、`orchestrator_v2`、`multi_agent_coordinator`、`evidence_enforcer` | **持业务状态，应落库**。归模块 **I**，其数据归属已在 §2.1 明确（`commands`／`ai_tool_calls`／`agent_runtime_snapshots` 等表已存在，正是当前无写入路径的那几张） |

> 注意 `orchestrator_v2._trace_owner_user_ids`（第 18 批新增）扩大了该状态面，
> 在 S0 清单中标记为 `CHANGED_WORSE`。本架构给出的方向是落库，不是继续在内存里加字段。

### 4.3 本架构**不**解决的（须单独处理）

`M-07`（急停契约）、`M-11`（健康检查语义）、`M-18a`（备份恢复）、`M-18b`（监控告警）、
`M-20`（容器与供应链）、`M-13`（角色多源与 auditor 职责分离）、`M-06` 断点④（真实写工具）——
这些是**运行能力与安全契约**问题，模块划分改变不了它们。

**不得因 S1 通过而认为上述问题有所推进。**

---

## 5. S1 通过条件逐项结果

| # | 主干 §3 条件 | 结果 | 依据 |
|---|---|---|---|
| 1 | 主要模块清楚 | ✅ **达成** | §2：9 业务模块 + 3 支撑模块 |
| 2 | 每个模块的职责和数据归属清楚 | ✅ **达成** | §2.1／§2.2：65 张表各归其一，计数校验 65=65；§2.3 写入权唯一规则 |
| 3 | 董事会批准总体方向 | ⬜ **待董事会** | 本文件即为该批准的输入 |

---

## 6. 下一阶段申请

前两项已达成。若董事会认可本架构方向，请回复准确口令：

```
确认主干阶段 S1 完成，进入 S2
```

### 6.1 批准前需注意

1. **本文件不改变任何代码。** 通过后进入 S2 决定模块改造顺序，S3 才动代码。
2. **§3.4 的四组待决事项**建议在 S2 一并裁决——它们决定模块 F 与 I 的真实边界。
3. 本架构**不推翻 A6 的判定**「整体重写缺乏架构依据」：目标架构是给现有结构划清边界，不是重写。
4. §4.3 列出的七个问题**不因 S1 通过而推进**。
