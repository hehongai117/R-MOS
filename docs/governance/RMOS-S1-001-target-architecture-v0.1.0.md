# RMOS-S1-001｜目标架构

- 版本：**0.2.0**｜日期：2026-09-05（**定向重开修订**）
- 主干阶段：**S1｜目标架构**
- 主干任务编号：**RMOS-S1-001**
- 事实基线：`cb00b293`
- 取证依据：`evidence/2026-09-05-s1-current-module-and-data-ownership-facts-v0.1.0.md`（异源产出）

> **0.2.0 修订**（董事会 2026-09-05 定向重开，选项 A）：
> S3 试点实测证伪了本文件的一个隐含假设——「模块划分能表达分层」。
> 试点后强连通分量非但没解开，还由 size 11 增至 12。
> 本版**新增 §1.5「层与模块」**，把「层」引入架构定义，并重新界定模块耦合口径。
> **§2 的模块划分与数据归属不变**；变的是「什么算模块之间的依赖」。
>
> **0.1.1 修订**（董事会 2026-09-05 退回，四处修正 + 四项裁决）：
> ①主干残留 S0-001 引用已改为 S1-001（主干文件侧）；
> ②「16 个子包全部保留」与删除 `policy/` 自相矛盾，已改为保留 15 个；
> ③Agent 空置表**漏了 `conversation_turns`**，已补入并一并裁决（四表→五表处置）；
> ④`audit_events` 直写者为 **3 个 endpoint + 2 个 service**，初稿误写 4+2。
> §3.4 由「待裁决」改为「已裁决」，目标表数由 65 降为 62。
> 另修正 §2、§5 遗留的「65 张各归其一／65=65」口径——该表述在合并裁决后已不成立。

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
| 有应用层写入路径的表 | 50 | **15 张无**，即定义了却没有应用在写；其中 12 张已由 §3.4 裁决处置 |
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

## 1.5 层与模块（**0.2.0 新增**）

### 1.5.1 为什么必须引入「层」

0.1.x 只定义了**模块**（纵切的业务域），没有定义**层**（横切的职责）。
后果在 S3 试点中实测暴露：

- 每个模块同时含 `api/v1/endpoints/`、`services/`、`models/` 三种文件；
- 于是「甲模块的**端点**调用乙模块的**服务**」——一次正常的分层调用——
  被计为「模块甲依赖模块乙」；
- 同理，「甲模块的服务引用乙模块的 **ORM 类型**」也被计为模块依赖；
- 结果是 12 个模块全部纠缠成一个强连通分量，**依赖图无法用于排序**。

**问题不在代码耦合，在于「模块依赖」这个概念当时定义得太粗。**

### 1.5.2 三层定义

| 层 | 位置 | 职责 | 跨模块规则 |
|---|---|---|---|
| **接口层** | `api/v1/endpoints/` | HTTP 路由、请求响应、**跨模块编排** | **允许**调用任意模块的领域层——编排本就是接口层的职责 |
| **领域层** | `services/` | 业务逻辑 | **受限**。领域层之间的调用**才算模块耦合**，构成模块依赖图 |
| **数据层** | `models/` | ORM 定义 | **共享**。任何模块可引用任何 ORM 类型；引用类型不构成行为依赖 |

### 1.5.3 模块耦合的定义（本版核心）

> **只有领域层之间的调用算模块耦合。**
> 接口层发出的跨模块调用不算（那是编排）；指向数据层的引用不算（那是类型）。

**写入权规则（§2.3）不受影响**：一张表仍只有一个模块可以写——
数据层「共享」指的是**可以引用 ORM 类型**，不是可以随便写。

### 1.5.4 实测验证（同一脚本，三种口径）

| 口径 | 跨模块边 | 双向对 | 强连通分量 |
|---|---:|---:|---|
| 全部 import（0.1.x 口径） | 94 | 10 | **1 个，size 12** |
| 排除接口层发出 | 89 | 9 | 1 个，size 10 |
| **只算 service→service**（本版口径） | **45** | **2** | **1 个，size 3，且只含 S1／S2／S3** |

**按本版口径，9 个业务模块（A–I、O）全部无环，可拓扑排序。**

唯一剩余的环是三个支撑模块构成的 mock／仿真三角：
`llm/mock_provider → simulation/fault_scenarios`、
`adapters/mock → simulation/fault_scenarios`、
`simulation/simulation_executor → adapters/mock`、
`diagnosis/fault_diagnosis_engine → llm/prompts`、
`llm/telemetry_context_builder → adapters/schemas`。
范围小且集中在 mock 路径，单列处置。

测量脚本随本版入库：`evidence/2026-09-05-layered-dependency-measure.py`。

### 1.5.5 业务模块的真实依赖（11 条边）

```
A → F        B → A        D → C (2)
E → H        F → E (4)    F → H
G → B        G → C (2)    G → H
I → C        O → G
```

拓扑序（调用者在前）：**D → I → O → G → B → A → C → F → E → H**

---

## 2. 目标模块

系统由 **9 个业务模块 + 3 个支撑模块** 构成。
**当前 65 张表均已明确目标去向；目标态保留 62 张，另外 3 张合并**（合并去向见 §3.4 裁决三）。

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
| **I** | **Agent 运行时** | 意图、编排、工具调用、审批闸门、技能注册、记忆与回放 | `commands`、`ai_tool_calls`、`approvals`、`skills`、`skill_reviews`、`skill_releases`、`belief_state_records`、`conversation_turns`、`agent_runtime_snapshots` | 9 |

**目标态合计 10+7+2+6+5+11+5+7+9 ＝ 62。**

当前运行期 ORM 枚举为 **65 张**；差额 3 张来自 §3.4 裁决三的合并
（`approval_records`→`approvals`、`decision_records`→`audit_events`、`replay_checkpoints`→`agent_runtime_snapshots`）。
**数据不丢，是并表**；`decision_records` 的承接方 `audit_events` 属模块 **A**，故 A 的表数不变。

> 65 → 62 是**目标态**。合并动作属 S3，需迁移脚本与数据搬运，本文件不设计其步骤。

> **模块 O｜应用编排** 已在 S3 试点中落地（`app/services/orchestration_app/`），
> 由 S2-001 §2.2 定义：跨模块**只读**聚合，不拥有任何表，只允许 O→业务模块。
> 它属**领域层**，其跨模块调用计入模块耦合（§1.5.3）。

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
`audit_events` 现被 **3 个 endpoint**（`admin`／`auth`／`training`）**+ 2 个 service**（`audit_event_service`／`llm/audit`）直写；
`assignment_attempts` 被 `evidence_engine` 与 `teaching_service` 两处写。

---

## 3. 现有实现的取舍

### 3.1 保留（多数）

16 个一级子包中**保留 15 个**（`policy/` 删除，见 §3.3），它们已按域/能力组织，与 §2 的模块划分基本吻合：
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

### 3.4 重复与空置的处置（M-14／M-16）——**董事会 2026-09-05 已裁决**

原为待决四组，董事会已逐组裁定如下。**本节记录裁决结果与其对模块边界的影响**。

#### 裁决一：两套 replay 都保留，各司其职

| 接口 | 归属模块 | 职责边界 |
|---|---|---|
| `GET /ai/replay/{trace_id}` | **I** Agent 运行时 | **Agent 审计回放**——读 `audit_events`，回答「这次 Agent 调用做了什么」 |
| `GET /teaching/attempts/{id}/replay` | **F** 教学 | **教学过程回放**——读时间线诸表，回答「学生这次作业是怎么做的」 |

两者场景不重叠，**不属 M-14 的「同一件事多套实现」**。前端目前均无调用，属未接入而非冗余。

#### 裁决二：教学时间线三表保留在模块 F，标记为「尚未实现」

`alignment_map`、`multimodal_timelines`、`timeline_segments` 留在模块 **F** 的数据归属内，
但状态明确为**尚未实现**：**先补写入路径，再开放教学过程回放**。

> 顺序不可颠倒：无写入即无数据，此时开放回放接口只会返回空结果，
> 那正是「接口存在但能力不存在」——本项目已有的病症之一。

#### 裁决三：Agent 数据简化，四表变两表

| 表 | 处置 | 去向 |
|---|---|---|
| `agent_runtime_snapshots` | **保留** | 模块 **I**；承接 `replay_checkpoints` 的职责 |
| `conversation_turns` | **保留** | 模块 **I** |
| `approval_records` | **合并** | → 现有审批表 `approvals`（模块 **I**） |
| `decision_records` | **合并** | → 审计记录 `audit_events`（模块 **A**）承接 |
| `replay_checkpoints` | **合并** | → 运行快照 `agent_runtime_snapshots`（模块 **I**） |

模块 **I** 因此由 12 张表降为 **9 张**，全系统目标态 **62 张**。

> **口径更正**：本文件 0.1.0 初稿把该组写成「Agent 四表」，**漏了 `conversation_turns`**——
> 它同样无应用写入路径，理应一并裁决。经董事会指出后补入，现为五表处置。

#### 裁决四：RBAC 四表保留，基础身份与细粒度权限分开

`roles`／`permissions`／`role_permissions`／`user_roles` **全部保留**在模块 **A**，
并明确两条边界：

1. **权限定义**（`permissions`、`role_permissions`）**不开放普通运行期管理**——
   仅通过发布流程变更，不提供运行期 CRUD 入口；
2. **用户与权限的关系**（`user_roles`）由模块 **A** 统一分配和撤销，其他模块不得直写。

这与 §2.3「一张表只有一个模块可以写」一致，也是 **M-13（角色多源）** 的收口方向——
但 M-13 本身仍未解决（见 §4.3），本裁决只确立目标，不代表已实施。

---

## 4. 目标架构如何对应当前问题清单

### 4.1 本架构直接解决的

| 问题 | 解法 |
|---|---|
| **M-25** 模块责任／目录边界模糊 | §2 的 12 个模块 + §3.2 的归位规则 |
| **M-16** 定义先行与内存代替落库 | §2.3 写入权唯一 + §3.4 五表处置已裁决（保留 2、合并 3） |
| **M-22** 任务终态写入责任未收口 | 终态写入者唯一归模块 **E** |
| **M-14** 新旧实现并存 | §3.4 已逐组裁决：两套 replay 场景不重叠故均保留，不属本问题；Agent 五表合并为两表 |

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
| 2 | 每个模块的职责和数据归属清楚 | ✅ **达成** | §2.1／§2.2：**当前 65 张表均已明确目标去向；目标态保留 62 张，另外 3 张合并**，脚本校验 62=62 无重无漏；§2.3 写入权唯一规则 |
| 3 | 董事会批准总体方向 | ⬜ **待董事会** | 本文件即为该批准的输入 |
| **4** | **（0.2.0 新增）层的定义清楚，且模块依赖图可用于排序** | ✅ **达成** | §1.5：三层定义 + 模块耦合口径；实测 9 个业务模块无环、可拓扑排序 |

---

## 6. 下一阶段申请

§5 的第 1、2、4 项已达成，第 3 项待董事会。若认可本版引入的层模型，请回复准确口令：

```
确认主干阶段 S1 完成，进入 S2
```

> 本文件 0.1.1 曾获批准，因 S3 试点证伪其隐含假设而**定向重开**（主干 §6 第 1 条）。
> 0.2.0 只改「什么算模块依赖」，**模块划分、数据归属、四项裁决全部不变**——
> 已批准的部分不重做。

### 6.1 批准前需注意

1. **本文件不改变任何代码。** 通过后进入 S2 决定模块改造顺序，S3 才动代码。
2. **§3.4 四组已由董事会 2026-09-05 裁决完毕**，模块 F 与 I 的边界据此确定；
   其中裁决三使目标表数由 65 降为 62，**合并动作属 S3**，本文件不设计其步骤。
3. 本架构**不推翻 A6 的判定**「整体重写缺乏架构依据」：目标架构是给现有结构划清边界，不是重写。
4. §4.3 列出的七个问题**不因 S1 通过而推进**。
