# A3 当前架构与数据边界审计报告

- 版本：0.1.0
- 日期：2026-08-27
- 状态：**Approved**（2026-08-27 获董事会确认；4 条 MISMATCH 已关闭）
- 阶段：A3（董事会方向指令 0.2.0 §A3）
- 被审对象：整个 R-MOS 项目
- 现状基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 上游输入：[A1（0.1.1，Approved）](./2026-08-26-a1-system-function-and-asset-inventory-v0.1.1.md)、[A2（Approved，提交 `be72b6e5`）](./2026-08-27-a2-user-roles-and-business-closure-audit-report-v0.1.0.md)
- 主审：Claude｜异源复核：Codex
- 生产代码改动：**0**

## 1. 执行摘要

A3 回答「系统为什么形成当前行为，以及模块是否有可替换边界」。**本阶段不决定目标目录，也不设计新接口。**

**先说好的一面：后端分层是干净的。** 230 个 `app/` 模块的 import 图里，跨层边全部是
`api → services`（82 条）与 `services → models`（109 条）这类向下依赖，**不存在 `models → services`、
`services → api`、`models → api` 任何一条反向边**；全仓只有 **1 组循环依赖**（LLM 路由与两个 provider 互相 import）。
这说明当前行为不是"意大利面"造成的，架构骨架站得住。

**问题集中在三处，而且都不是分层问题：**

**（一）35 个进程内业务单例把系统钉在单实例部署上。**
`app/` 顶层共 74 个实例化赋值 = 36 个 `router = APIRouter()` + 3 个常量式赋值 + **35 个业务服务单例**，
其中 **8 个明确持有可变状态**（`approval_queue`、`knowledge_governance`、`login_throttle`、
WebSocket `manager`、`analysis_worker`、`memory_hub`、`short_term_memory`、`long_term_memory`）。
其中最要紧的是 `approval_queue`——`/api/v1/agent/approval/*` 这一整套审批走的是**进程内内存字典**
（`self._requests: Dict`），根本不写数据库，这直接解释了 A2 发现的"`approval_records` 表是空的"：
不是没人用，是**没有任何写入路径**。同类还有 `login_throttle`（登录限流）、`memory_hub`／`short_term_memory`
（Agent 记忆）、`analysis_worker`（后台分析）。这些状态一旦多开进程就会分叉，重启即丢。

**（二）数据所有权有三种失序。**
**15 张表在应用代码里没有写入路径**（9 张连脚本都不写，6 张只由种子脚本写）；
**16 张表被 API 端点层直接构造 ORM 对象**，绕过服务层；
`audit_events`、`evidence_bundles`、`robot_assets` 等表有 3~4 个并列的应用侧写入者。

**（三）知识数据有两套存储，其中一套没有持久化保障。**
PostgreSQL 的 `knowledge_documents` 表之外，`app/services/knowledge_governance.py` 还用本地 JSON 文件
`data/knowledge_store.json` 存了一份 `KnowledgeEntry`，而 `docker-compose.yml` 的 backend 服务**只挂载了
`data/robot-assets`，没有挂载这个文件**。该文件被 Git 跟踪、并由 `Dockerfile` 的 `COPY . .` 打进镜像，
因此：**同一容器 `restart` 不丢（可写层保留）；容器被重建（`up --force-recreate`／重新构建镜像）时，
运行期写入全部丢失并回退到镜像中的初始版本。** 两套存储之间没有任何同步机制。

**可替换边界只有 4 处：** 机器人适配器、文件存储、LLM 路由、开机前检查器（`BaseChecker`，3 个具体实现）。
其余模块之间没有接口抽象，替换任何一块都要改调用方。

**本批未执行测试，验证等级上限 E1。**

## 2. 方法与口径

| 项 | 内容 |
|---|---|
| 依赖图 | AST 解析 `app/**/*.py` 的 `Import`/`ImportFrom`（含相对导入还原），只保留 `app.` 内部边；用 Tarjan 求强连通分量检测循环 |
| 分层归属 | 按顶层包名归入 `api`／`services`／`models`／`schemas`／`core`／`adapters` |
| 数据写入者 | AST 找 ORM 类的**构造调用**（`Model(...)`）与 `update(Model)`／`delete(Model)`；读取者找 `select(Model)` |
| 共享状态 | AST 只取**模块顶层**的实例化赋值，不含函数内局部对象 |
| 部署拓扑 | `docker-compose.yml`、两个 `Dockerfile`、`main.py` 的启动参数 |
| 未做的事 | 未执行测试、未启动长驻服务、未连真机、未写数据库、未 push |

**方法局限：**
1. 写入者判定基于**静态构造调用**。若某处用 `session.execute(text(...))` 写裸 SQL，或通过 ORM 关系级联写入，本批会漏判。
   「无写入路径」应读作「未找到静态写入代码」。
2. 依赖图是**模块级**，不区分「函数内延迟导入」与「顶层导入」，也不反映运行时实际调用频次。
3. 单例清单只覆盖 `app/`，不含 `scripts/`。

## 3. 进程与部署拓扑

| 项 | 事实 |
|---|---|
| 编排 | `docker-compose.yml` 定义 4 个服务：`postgres:16-alpine`、`backend`（本地构建）、`frontend`（本地构建）、`minio` |
| 副本 | **无任何 `replicas`／`deploy` 配置**，全部单实例 |
| 后端启动 | `main.py` 末尾 `uvicorn.run(host=settings.HOST, port=settings.PORT)`，**未配置 workers** |
| 端口 | backend 8000、frontend 80、postgres 与 minio 各自暴露 |
| 持久化卷 | `pgdata`、`miniodata`；backend 仅挂载 `./r-mos-backend/data/robot-assets`。`data/knowledge_store.json` 未挂载，但被 Git 跟踪并由 `COPY . .` 打进镜像 |
| 对象存储 | `STORAGE_BACKEND` 默认 `local`，compose 中同时备好 MinIO 与 S3_* 环境变量 |
| 数据库扩展 | `plpgsql 1.0`、`vector 0.8.2`（pgvector） |

**拓扑结论：** 当前是**单进程单实例**架构。这与 §5 的 35 个业务单例（8 个有可变状态）是自洽的——
但也意味着**横向扩展在今天不成立**：一旦起第二个 backend 实例，审批队列、登录限流、Agent 记忆、
WebSocket 连接表都会各持一份。这是事实陈述，扩展需求是否存在由 A6 决定。

## 4. 当前模块地图（表 1）

### 4.1 后端分层

| Module_ID | 层 | 模块数 | 责任 | 入口 | 输出 | 数据所有权 | 依赖方向 | 消费方 |
|---|---|---:|---|---|---|---|---|---|
| M-API | `app/api` | 39 | HTTP／WS 端点、请求校验、权限判定 | FastAPI 路由 | JSON 响应 | **直写 16 张表**（越界，见 §6） | → services(82)、core(42)、models(39)、schemas(23) | 前端、测试 |
| M-SVC | `app/services` | 115 | 业务逻辑、编排、外部集成 | 被端点调用 | 领域对象 | 主要写入者 | → models(109)、core(34)、schemas(12)、adapters(6) | M-API |
| M-MODEL | `app/models` | 40 | SQLAlchemy ORM 定义 | — | 表结构 | 65 张表的定义 | 无出边（叶子层） | M-SVC、M-API |
| M-SCHEMA | `app/schemas` | 18 | Pydantic 请求／响应契约 | — | 校验后的 DTO | 无 | → models(1) | M-API、M-SVC |
| M-CORE | `app/core` | 11 | 配置、数据库会话、异常、中间件 | — | 基础设施 | 无 | → models(2) | 全体 |
| M-ADAPTER | `app/adapters` | 5 | 机器人适配器（base／mock／factory／schemas） | 工厂 | 遥测与故障数据 | 无 | → core(1)、services(1) | M-SVC、M-API |

**跨层方向核对：`models → services`、`services → api`、`models → api` 三个方向的边数均为 0。** 分层未被破坏。

### 4.2 服务层内部分组

17 个子目录：`analysis` 9、`knowledge` 11、`llm` 7、`training` 6、`memory` 5、`identity` 4、`diagnosis` 3、
`orchestration` 3、`teaching` 3、`intent` 2、`maintenance` 2、`pipeline` 2、`simulation` 2、`sop` 2、`storage` 2、`policy` 1。

**但还有 35 个服务文件直接放在 `app/services/` 根目录下**（`agent_service.py`、`approval_queue.py`、
`evidence_engine.py`、`evidence_service.py`、`task_service.py`、`sop_service.py`、`policy_matrix.py` 等）。
根目录文件数超过任何一个子目录，**责任边界在这一层是模糊的**。

### 4.3 端点模块 → 服务 → 数据映射（A1 功能定位，退出门禁 1）

| 端点模块 | 服务依赖数 | 主要服务 | 端点层直写的表 |
|---|---:|---|---|
| `auth` | 3 | access_control、session_initializer、login_throttle | `access_tokens`、`refresh_tokens`、`users` |
| `robots` | 5 | authz_guard、project_ingest_service、robot_asset_validator | `analysis_tasks`、`robot_assets`、`robot_models`、`teacher_robot_bindings` |
| `agent` | 9 | access_control、agent_service、authz_guard | `ai_tool_calls`、`approvals`、`commands` |
| `training` | 8 | access_control、class_membership、authz_guard | `audit_events` |
| `tasks` | 6 | authz_guard、event_service、ownership | — |
| `teaching_roster` | 5 | access_control、diagnosis_service、authz_guard | `evidence_cards` |
| `training_workbench` | 5 | project_generator、session_service、authz_guard | — |
| `agent_governance` | 5 | **approval_queue（内存）**、sop.quality_monitor | — |
| `agent_knowledge` | 4 | project_ingest_service／worker | — |
| `agent_v2` | 4 | access_control、orchestrator_v2 | — |
| `skills` | 2 | access_control、authz_guard | `skills`、`skill_releases`、`skill_reviews` |
| `maintenance` | 2 | sop_draft_generator、verdict_step_generator | `robot_sop_drafts` |
| `admin` | 1 | authz_guard | `audit_events` |
| `onboarding` | 1 | authz_guard | `teacher_robot_bindings` |
| 其余 22 个端点模块 | 0~3 | 见证据文档 | — |

**6 个端点模块完全没有服务层依赖**：`adapter`、`health`、`scenarios`、`schools`、`student_tasks`、`teaching_common`。
其中 `scenarios`、`schools`、`student_tasks` 直接从端点查询 ORM 模型（只读），`teaching_common` 是共享辅助，
`health` 与 `adapter` 无数据访问。

**A1 的 36 个功能域全部定位到端点模块、服务与数据表，无遗漏。** 逐条见 [A3 架构证据](./evidence/2026-08-27-a3-architecture-evidence-v0.1.0.md)。

### 4.4 前端模块边界

| 目录 | 文件数（非测试） | 责任 |
|---|---:|---|
| `components` | 93 | 通用与领域组件 |
| `pages` | 25 | 路由页面 |
| `api` | 21 | HTTP 客户端 |
| `adjudication` | 15 | SOP 裁决引擎（前端本地逻辑） |
| `teaching` | 9 | **教学模块（含自己的 `pages/`）** |
| `types` | 9 | 类型定义 |
| `config` | 6 | 路由权限、导航、品牌等配置 |
| `store` | 5 | Zustand 状态（含自建 axios 的 `authStore`） |
| `hooks`、`data`、`utils`、`lib`、`features`、`styles` | 各 1~3 | 其余 |

**结构不一致：** 教学页面在 `src/teaching/pages/`，其余页面在 `src/pages/`——**页面分散在两个并列的顶层目录**。
`adjudication` 是前端本地的裁决引擎，与后端 SOP 裁决并存（职责边界见 §7 B-07）。

## 5. 依赖与共享状态（表 2）

`app/` 顶层共 74 个实例化赋值，其中 36 个是 `router = APIRouter()`（框架惯例，无状态）、
3 个是常量式赋值（`_DEFAULT_STORE_PATH`、`DEFAULT_RESPONSE`、`EXPLANATION_RESPONSE`），
其余 **35 个是业务服务单例**。其中 **8 个明确持有可变状态**，是单实例约束的真正来源，按风险排序：

| ID | 单例 | 所在模块 | 状态内容 | 同步方式 | 风险 | 可隔离性 |
|---|---|---|---|---|---|---|
| **S-01** | `approval_queue` | `services/approval_queue.py` | `_requests: Dict`、按状态分桶的队列 | **无**（纯内存） | **审批记录不落库**；重启即丢；多实例分叉。直接导致 `approval_records` 表零写入 | 低（无接口抽象，改造须换存储） |
| **S-02** | `login_throttle` | `services/login_throttle.py` | 登录失败计数 | 无 | 多实例下限流失效，可绕过 | 低 |
| **S-03** | `manager`（WebSocket） | `services/websocket_manager.py` | 活跃连接表 | 无 | 多实例下无法跨实例广播 | 中（连接本就绑进程，需外部 pub/sub） |
| **S-04** | `knowledge_governance` | `services/knowledge_governance.py` | `_knowledge_store: Dict` + 本地 JSON 文件 | 文件读写 | **Docker 下无挂卷**：同容器 `restart` 保留可写层，**容器重建时运行期写入丢失并回退到镜像内的初始版本**（该文件被 Git 跟踪并由 `COPY . .` 打进镜像）；与 DB 表重复 | 低 |
| **S-05** | `memory_hub`／`short_term_memory`／`long_term_memory` | `services/memory/*` | Agent 记忆 | 无 | 多实例记忆分叉 | 低 |
| **S-06** | `analysis_worker` | `services/analysis/worker.py` | 后台分析任务队列 | 无 | 多实例重复消费或漏消费 | 中 |
| **S-07** | `orchestrator`／`orchestrator_v2`／`multi_agent_coordinator`／`coach_agent`／`diagnoser_agent`／`intent_engine` | `services/*` | Agent 编排运行时 | 无 | 运行时状态不可观测、不可迁移 | 低 |
| **S-08** | `llm_router`、`prompt_engine`、`embedding_service`、`query_embedding_service`、`fallback_embedding_service` | `services/llm/*`、`services/knowledge/*` | provider 注册与缓存 | 无 | 主要是无状态注册，风险低 | 高 |
| **S-09** | `settings` | `core/config.py` | 配置快照 | 启动时读取 | 配置变更需重启 | 高（框架惯例） |
| **S-10** | 其余 25 个无状态策略对象（`policy_matrix`、`evidence_enforcer`、`teacher_monitor`、`preflight_check_service`、`verdict_enhancer`、`resource_parser`、`diagnosis_engine`、`maintenance_plan_generator`、`teaching_chat_engine`、`llm_audit`、`telemetry_builder`、`llm_risk_scorer`、`project_ingest_service` 等） | 各处 | 多为无状态策略对象 | — | 低 | 高 |

### 5.1 循环依赖

全仓**唯一一组**：

```
services.llm.router → services.llm.deepseek_provider → services.llm.router
services.llm.router → services.llm.minimax_provider → services.llm.router
```

典型的 router 与 provider 互相 import。影响面限于 LLM 子系统，不扩散。

## 6. 数据模型归属（表 3）

### 6.1 无写入路径的表（应用代码内合计 15 张）

| Data_ID | 表 | 事实 | 迁移风险 |
|---|---|---|---|
| D-01 | `approval_records` | ORM 类 `ApprovalRecordDB` 只在 `models/__init__.py` 导出，**全仓从未被构造**；对应功能走内存队列 S-01 | 删表无影响；但若要落库审批需重写 |
| D-02 | `agent_runtime_snapshots` | 无写入代码 | 同上 |
| D-03 | `decision_records` | 无写入代码；A2 已记 `/agent/replay/*` 前端悬空调用 | 同上 |
| D-04 | `conversation_turns` | 无写入代码 | 同上 |
| D-05 | `replay_checkpoints`、`timeline_segments`、`multimodal_timelines`、`alignment_map` | 无写入代码，回放与时间线能力未落地 | 同上 |
| D-06 | `sop_audit_logs` | 无写入代码，SOP 审计无记录 | 同上 |

**这 9 张表是「定义先行、实现未跟上」的产物**，与 A2 的空表清单互相印证，但结论更强：
空表可能是没跑过，**无写入路径是根本跑不出来**。

已排除误判：对这 9 张表逐一检索了裸 SQL（`text("INSERT ...")`）与 `insert()` 语句，全仓零命中；
`SOPAuditLog(` 的两处命中分别是类定义行与 `__repr__` 字符串，均非构造调用。

**一个具体后果：** `api/v1/endpoints/teaching_roster.py` 中存在 `reason="missing_timeline_segments"`
的降级分支——而 `timeline_segments` 表既无写入路径也无数据，**该降级分支是常态而非异常路径**。
这类「为不存在的数据写的兜底」应由 A5 在执行期证据中一并核实。

**另有 6 张表只由种子／运维脚本写入，应用代码零写入：**
`fault_sop_mappings`、`permissions`、`role_permissions`、`roles`、`schools`、`user_roles`。
这批是「运行期只读、部署期灌入」的配置型数据——**权限与角色表在此列**，
意味着 RBAC 的授权数据不能在运行期由应用维护，只能靠脚本重灌（与 A2 BR-13「管理员无法在 UI 改角色」同源）。

合计 **15 张表在应用代码里没有写入路径**（9 + 6）。

> **检测口径修正（异源复核 MISMATCH-A3-04 引出）：** 初版按 ORM 类名做构造匹配，产生两类误差：
> （a）**同名误判**——`EvidenceItem`、`AssessmentAuditEvent` 在部分模块指的是 Pydantic schema 而非 ORM；
> （b）**别名漏判**——ORM 常以 `from app.models.x import Y as YModel` 引入，构造 `YModel(...)` 时按原名匹配会漏。
> 最终检测改为**按 import 来源解析本地名到 ORM 真名**，两类误差同时消除，结果与复核方独立得出的 15 张完全一致。

### 6.2 多写入者的表（所有权不清）

| Data_ID | 表 | 写入者（应用侧） | 重复模型 | 风险 |
|---|---|---|---|---|
| D-07 | `audit_events` | `api/admin.py`、`api/training.py`、`services/audit_event_service.py`、`services/llm/audit.py`（4 个应用侧写入者） | — | 端点与服务并列写同一张审计表，审计口径可能不一致 |
| D-08 | `robot_assets` | 应用侧 4：`api/robots.py`、`analysis/assembly_builder.py`、`cad_converter.py`、`manifest_generator.py`；另有 3 个脚本 | — | 33,367 行的大表由 4 处写入 |
| D-09 | `evidence_bundles` | `services/evidence_engine.py`、`services/evidence_service.py`、`services/teaching/report_generator.py` | 与 `evidence_cards`／`evidence_items` 并存（A2 D-03） | 证据模型分裂 + 三写入者 |
| D-10 | `evidence_items` | `services/evidence_service.py`、`report_generator.py`（**2 个，非 3 个**——`workbench_execution_service.py` 构造的 `EvidenceItem` 来自 `app.schemas.evidence`，不是 ORM） | 同上（**该表为空**） | 同上 |
| D-11 | `sops`／`sop_steps` | `services/analysis/sop_extractor.py`、`services/sop_service.py` | — | AI 抽取与人工服务两条写入路径 |
| D-12 | `tasks` | `services/pipeline/task_pipeline_service.py`、`services/task_service.py` | — | 两条任务创建路径，与 A2 BR-05（无终态）相关 |

### 6.3 端点层直写的表（16 张，绕过服务层）

`access_tokens`、`ai_tool_calls`、`analysis_tasks`、`approvals`、`audit_events`、`commands`、`evidence_cards`、
`refresh_tokens`、`robot_assets`、`robot_models`、`robot_sop_drafts`、`skill_releases`、`skill_reviews`、
`skills`、`teacher_robot_bindings`、`users`。

这不违反分层（端点本就允许依赖 models），但意味着**这 16 张表的写入规则散落在端点里**，
没有服务层做统一约束——A4 的权限与审批矩阵需要特别关注这批。

### 6.4 双存储

| Data_ID | 主记录 | 副本 | 消费方 | 风险 |
|---|---|---|---|---|
| **D-13** | PostgreSQL `knowledge_documents`（30 行，27 PENDING） | 本地文件 `data/knowledge_store.json`（`KnowledgeEntry`） | JSON 侧被 `api/agent_knowledge.py`、`api/agent.py`、`services/orchestrator_v2.py` 使用 | **Docker 下该文件无挂卷**：同容器 `restart` 不丢，**容器重建时回退到镜像内版本**；两套数据无同步机制；A2 的「知识批准后无切块产物」与此相关 |

## 7. 可替换边界（表 4）

| Boundary_ID | 当前接口 | 耦合点 | 可替换性 | 证据 |
|---|---|---|---|---|
| **B-01** | `BaseRobotAdapter`（ABC，10 个抽象方法） | `AdapterFactory` 单点实例化 | **可替换** | 已有 `MockRobotAdapter` 一个实现；契约只覆盖连接／读取／故障注入，**不含运动控制与急停**（A2 FL-14／FL-15） |
| **B-02** | `FileStorageBase`（ABC）+ `get_storage()` 工厂 | `STORAGE_BACKEND` 环境变量 | **可替换** | `LocalFileStorage`／`S3FileStorage` 双实现，`tests/test_storage.py` 双实现参数化契约测试 |
| **B-03** | `LLMRouter` + provider | `llm_router` 单例；router 与 provider 互相 import（§5.1 循环依赖） | **可替换但有耦合** | deepseek／minimax／mock 三实现；循环依赖使 provider 无法独立于 router 存在 |
| **B-04** | 数据库 | SQLAlchemy ORM + **pgvector 扩展** + `asyncpg` 方言 | **不可替换** | 65 张表直接绑定 SQLAlchemy；`vector 0.8.2` 扩展为向量检索所需 |
| **B-05** | 审批队列 | `approval_queue` 单例，无接口抽象，端点直接 import | **不可替换** | `agent_governance.py` 直接 `from app.services.approval_queue import approval_queue` |
| **B-06** | 知识治理存储 | `knowledge_governance` 单例 + 硬编码路径 `Path("data/knowledge_store.json")` | **不可替换** | 无存储抽象，路径写死在模块顶层 |
| **B-09** | `BaseChecker`（ABC，2 个抽象成员） | `PreflightCheckService` 组装 | **可替换** | 3 个具体实现：`QualificationChecker`、`DeviceLockChecker`、`ToolAvailabilityChecker` |
| **B-07** | 前端 SOP 裁决引擎 | `src/adjudication`（15 个文件）与后端 SOP 裁决并存 | **未知** | 需 A5 用执行期证据确认二者裁决是否一致 |
| **B-08** | 前端 HTTP 通道 | `apiClient`（统一拦截／重试／刷新）与 `authStore` 自建 axios 并存（A2 D-05） | **部分可替换** | 认证通道不共享拦截器策略 |

**可替换边界总计 4 处成立（B-01／B-02／B-03／B-09）**，其余模块之间没有接口抽象，替换任何一块都要改调用方。
初版漏记 `BaseChecker`（只按「外部基础设施替换点」筛选），由异源复核指出后补入。

## 8. 退出门禁自评

| 门禁 | 要求 | 本报告 | 结论 |
|---|---|---|---|
| A3-G1 | A1 每项功能均能定位到当前模块和数据 | §4.3 端点模块→服务→表全覆盖，36 个功能域无遗漏 | ✅ 达标 |
| A3-G2 | 所有跨模块数据写入点有所有者 | §6 逐表登记写入者；9 张无写入路径、16 张端点直写、6 张多写入者全部列名 | ✅ 达标 |
| A3-G3 | 重复模型、共享状态和不可替换边界均登记 | §5（74 个顶层实例化 = 36 APIRouter + 3 常量 + **35 个业务单例**，其中 8 个持可变状态）、§6.4（双存储）、§7（8 条边界，5 条不可替换或部分） | ✅ 达标 |
| A3-G4 | **不在本阶段决定目标目录或新接口** | 全报告只登记现状与边界，未提出任何目标结构或新接口 | ✅ 遵守 |
| A3-G5 | 不得把「代码存在」写成「真实可用」 | 写入路径以静态构造调用为准并声明局限；验证等级上限 E1 | ✅ 达标 |
| §5.8 | 主审与复核异源 | Codex 11 条断言复核完成，4 条 MISMATCH 全部复验采纳并修正 | ✅ 达标 |

## 9. 异源复核记录

| 项 | 内容 |
|---|---|
| 复核方 | Codex（工作目录设在被审仓库之外，授网络访问，明令只读；复核后被审工作区确认零改动） |
| 复核范围 | 11 条架构事实断言（C-01~C-11） |
| 结论 | **OVERALL: MISMATCH(4)** — 4 条 AGREE、3 条 AGREE_WITH_CAVEAT、**4 条 MISMATCH** |
| 处置 | 4 条全部由主审复验，**全部成立，全部采纳** |

### 9.1 MISMATCH 处置

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MISMATCH-A3-01**（C-06） | 顶层共享对象 74 个的正确拆分是 36 个 `APIRouter` + 38 个其他，不是主审断言的 37+37 | 成立。主审在派发断言**之后**已自查发现并先行修正为 36 + 3 常量 + 35 业务单例——`3+35=38`，与复核方口径一致，只是主审把常量式赋值单列 | **采纳**（两侧收敛到同一组数字，报告采用更细的三段拆分） |
| **MISMATCH-A3-02**（C-09） | 「容器重启后丢失」不准确：同一容器 `restart` 保留可写层；只有**重建容器**时运行期修改才丢失，并回退到镜像中的初始文件 | 成立。进一步核实：`data/knowledge_store.json` **被 Git 跟踪**，且 `Dockerfile` 用 `COPY . .` 打进镜像，所以重建后不是空文件而是回退到提交版本 | **采纳**。§1 与 §3 已按容器生命周期精确改写 |
| **MISMATCH-A3-03**（C-10） | 实质抽象边界是 **4 处**，主审漏了 `preflight_check.py` 的 `BaseChecker`（2 个抽象成员、3 个具体实现）；而 `s3_storage.py` 只是实现类 | 成立。主审初版只按「外部基础设施替换点」筛选，把纯业务侧的抽象漏掉了 | **采纳**。§7 新增 B-09，边界总数 3 → **4** |
| **MISMATCH-A3-04**（C-11） | `evidence_items` 只有 2 个直接写入者；`workbench_execution_service.py` 构造的 `EvidenceItem` 来自 `app.schemas.evidence`，是请求数据模型不是 ORM | 成立，**且问题比这一条更广**。主审据此重写检测逻辑，发现两类系统性误差：（a）**同名误判**——`EvidenceItem`、`AssessmentAuditEvent` 在部分模块指 Pydantic schema；（b）**别名漏判**——ORM 常以 `import X as XModel` 引入，按原名匹配会漏掉 `XModel(...)` 构造 | **采纳并推广**。检测改为按 import 来源解析本地名到 ORM 真名，两类误差同时消除。最终结果：**9 张完全无写入路径 + 6 张仅脚本写入 = 15 张应用代码内无写入**，与复核方 C-04 独立得出的 15 张**完全一致** |

### 9.2 口径说明（AGREE_WITH_CAVEAT）

| 断言 | 复核方补充 | 处置 |
|---|---|---|
| C-03 | 循环依赖的实际结构是 router 分别与两个 provider 互相引用，**两个 provider 之间没有直接引用** | 已在 §5.1 按此结构呈现 |
| C-04 | 严格只算 `app/` 时无写入者是 15 张，主审的 9 张含脚本口径 | 已由 MISMATCH-A3-04 的重算统一，两口径并列呈现 |
| C-08 | `agent.py` 只为兼容测试重新导入知识治理单例，**没有业务调用**（但导入可能触发首次加载） | §6.4 的消费方表述已按此收紧 |

### 9.3 方法教训

本轮 4 条 MISMATCH 中，**MISMATCH-A3-04 是最有价值的一条**：它从一张表的写入者数量出发，
暴露出「按类名做静态匹配」在存在 **schema/ORM 同名**与**别名导入**时会双向出错（既误判又漏判）。
这与 A2 的教训同类——**静态匹配必须解析到符号来源，不能停在名字上**。
修正后主审与复核方从两条独立路径收敛到同一组数字（15 张），互为印证。

## 10. 移交下阶段的问题

| 移交项 | 承接阶段 | 说明 |
|---|---|---|
| 35 个业务单例（其中 8 个有可变状态）与单实例部署约束 | A6 | 是否需要横向扩展决定要不要改；改造成本集中在 S-01～S-06 |
| 审批走内存队列、审批表零写入（S-01／D-01） | A4 | 审批是安全门禁的一环，A4 需判定当前形态是否可接受 |
| 16 张端点直写表的写入规则 | A4 | 权限与审批矩阵需覆盖这批散落的写入点 |
| 知识双存储与无挂卷丢数据（D-13） | A4、A6 | 既是数据边界问题也是部署风险 |
| 15 张应用代码内无写入路径的表（9 张全无 + 6 张仅脚本写入，含 RBAC 角色权限表）：删除或补实现 | A6 | 属"定义先行"的技术债 |
| 证据模型分裂 + 三写入者（D-09／D-10） | A6 | 与 A2 D-03 同源 |
| 前端裁决引擎与后端裁决的一致性（B-07） | A5 | 需执行期证据 |
| `services/` 根目录 35 个未分组文件 | A6 | 责任边界模糊，属结构债 |
| 前端页面分散在 `pages/` 与 `teaching/pages/` | A6 | 同上 |

## 11. 本批产出物

| 文件 | 说明 |
|---|---|
| 本报告 | A3 主报告 |
| [A3 架构证据](./evidence/2026-08-27-a3-architecture-evidence-v0.1.0.md) | 依赖图与循环检测、逐表写入者/读取者、单例清单、端点→服务→表全量映射 |
