# A4 安全、控制与实时通道审计报告

- 版本：0.1.1
- 上一正式版本与被替代关系：替代 0.1.0（恢复提交 `cef83be2`）；本次修订按 A5 发现更正 §9 G3 中关于越权测试的错误表述，其余结论未变
- 日期：2026-08-28
- 状态：**Approved**（0.1.0 于 2026-08-28 获董事会确认；0.1.1 为表述更正版，不改变已确认的安全结论）
- 阶段：A4（董事会方向指令 0.2.0 §A4）
- 被审对象：整个 R-MOS 项目
- 现状基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 上游输入：[A1（0.1.1）](./2026-08-26-a1-system-function-and-asset-inventory-v0.1.1.md)、[A2](./2026-08-27-a2-user-roles-and-business-closure-audit-report-v0.1.0.md)、[A3（提交 `d3020017`）](./2026-08-27-a3-current-architecture-and-data-boundaries-v0.1.0.md)
- 主审：Claude｜异源复核：Codex
- 生产代码改动：**0**

## 1. 执行摘要

A4 审查所有跨领域安全与机器人控制边界。结论：**认证边界成立，但只覆盖 `/api/v1`；
授权在读路径部分建立、在写路径几乎缺失。**

> 本节数字为**异源复核修正后**的最终版本。主审初版有 6 处判定被复核方推翻，
> 其中 3 处是**把问题说重了**（漏识别 `ownership.py` 的检查辅助函数），处置见 §10。

**认证侧：** `/api/v1` 全量路由由 `enforce_authenticated` 默认拒绝网关兜底，公开白名单 7 条且条条有理由与 ADR 留痕，
嵌套 router 全部挂在已注册父 router 下——**`/api/v1` 内无绕过**。
但**网关只管 `/api/v1`**：应用还有 5 个入口在网关之外，无令牌可访问（见 §3）。

**授权侧：** 187 条入口的画像分布——

| 画像 | 条数 | 含义 |
|---|---:|---|
| PUBLIC（白名单） | 7 | 匿名可访问，有理由 |
| **网关外 HTTP** | **5** | `/`、`/openapi.json`、`/docs`、`/docs/oauth2-redirect`、`/redoc`，**匿名 200** |
| **WebSocket 无认证** | **2** | 零令牌、零机器人隔离 |
| **AUTH_ONLY（端点拿不到身份）** | **85** | 其中 **46 条是写操作** |
| ACTOR（有身份，无归属校验） | 20 | — |
| ACTOR + 归属校验 | 24 | 读路径为主 |
| require_permission | 42 | — |
| require_permission + 归属校验 | 2 | — |

**最能说明问题的一组数字：**

| | 总数 | 有对象归属校验 | 占比 |
|---|---:|---:|---:|
| 读操作（GET） | 86 | 16 | 19% |
| **写操作（POST/PUT/PATCH/DELETE）** | **94** | **10** | **11%** |

**10 条有归属校验的写操作全部集中在 `robots`／`onboarding`**。也就是说：
除机器人资产管理外，**全系统的写操作基本没有对象级授权**。

四条最硬的事实：

1. **46 条写操作的端点在代码层面拿不到调用者身份**，其中 **27 条路径直接带对象 ID**——
   调用者可指定任意对象，实现上已排除做归属校验的可能。最刺眼的是
   `POST /api/v1/attempts/{attempt_id}/grade`，签名为 `grade_attempt(attempt_id, request, db)`，
   **任何持有效令牌的用户都能给任意作业打分**。同类：任意用户删任意 SOP、批准任意维保草稿、提交他人训练会话。

2. **`force-submit` 是「看起来有防护」的混淆代理。**
   `POST /training/sessions/{id}/force-submit` **做了**教师管辖权校验——但校验的是
   **请求体里传来的 `request.teacher_id`**，不是认证身份。任何持有效令牌的用户只要填入一个
   对目标学生有管辖权的教师编号即可通过，且该编号会被当作操作人写入记录。**有检查，但检查的是攻击者自己提供的身份。**

3. **WebSocket 完全在认证体系外，且「定向消息」实为广播。**
   两条 WS 端点零令牌校验，`robot_id` 源码注释明写「暂不用于数据过滤」；
   更进一步，`websocket_manager.send_to_user()` 的实现里注释写着
   「目前简化为向所有连接广播」，然后遍历**全部**连接——**跨用户、跨班级的消息泄露**。

4. **一个 GET 请求会写数据库。** `GET /attempts/{attempt_id}/evidence` 在证据不存在时
   调用 `EvidenceEngine.generate_bundle_for_task()`，该方法内含 `await self.db.commit()`。
   读接口被改成了写接口，且无身份校验。

**控制侧：** 与 A2 一致——**系统没有机器人运动控制或急停端点**，适配器契约只有连接、读取与故障注入。
A4 要求覆盖的「命令状态机、停止、断网、重试、真机边界」在当前系统无对应实现，记为 MISSING。

**审批侧：** `PolicyMatrix` 有 5 条 `requires_approval=True` 规则，但 `policy_matrix.evaluate()`
**全仓只有 2 处调用**，都在 AI Agent 路径——**46 条无隔离写操作没有一条经过策略评估**；
AI 路径触发的审批又落在进程内内存队列（A3 S-01，不写库）。

**跨租户：** 涉及学校维度的入口共 7 条（含 `ensure_user_scope()` 的同校教师判定），
**其中 5 条是读接口，写侧只有注册**。CLAUDE.md 声明的租户约束在写路径未落地。

**本批未执行任何越权请求，全部结论基于静态代码与配置，验证等级上限 E1。**
陈述的是**代码中不存在检查**，而非**已实证的可利用漏洞**。（复核方另做了无令牌连通性实测，见 §10。）

## 2. 方法与口径

| 项 | 内容 |
|---|---|
| 认证边界 | 读 `main.py` 的路由注册、`app/core/public_routes.py` 白名单、`app/services/authz_guard.py` 的 `enforce_authenticated` |
| 绕过检查 | 枚举全部 `include_router` 调用（`main.py`、`app/api/v1/__init__.py`、各端点模块），确认嵌套 router 的挂载父级 |
| 授权画像 | AST 提取每个端点函数的 `Depends(...)` 依赖、`require_permission("key")` 参数；正则识别对象归属校验（`user_id/owner_id/teacher_id/student_id == actor.*`、`_require_own*`、`verify_owner` 等）、角色判定、`school_*` 过滤 |
| 角色权限 | 只读查询数据库 `permissions`／`roles`／`role_permissions` |
| 审批链路 | 追踪 `policy_matrix.evaluate()` 的全部调用点与 `requires_approval=True` 规则 |
| 未做的事 | **未发起任何越权请求**、未执行测试、未启动长驻服务、未连真机、未写数据库、未 push |

**方法局限（必须随结论引用）：**
1. 归属校验用正则识别，可能**漏判**（若某端点用未覆盖的写法做了校验）。因此"无归属校验"应读作
   "未在代码中找到归属校验"，逐条确认需要 A5 的执行期证据或人工复核。
2. 本批**没有实际发起越权请求**，所有结论是静态的。代码中缺少检查 ≠ 已证实可利用；
   但对写操作而言，缺少身份参数在实现上已排除了做检查的可能。
3. 授权画像按端点函数聚合，同一函数服务多个方法时按最宽口径归类。

## 3. 身份签发与认证边界

| 项 | 事实 | 结论 |
|---|---|---|
| 网关 | `app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(enforce_authenticated)])` | ✅ 默认拒绝成立 |
| 白名单 | `PUBLIC_ROUTES` 7 条：health、auth/register、auth/login、auth/refresh、auth/logout、schools、schools/{school_name}/teachers | ✅ 每条有注释理由，判定规则写在文件内，ADR 留痕 |
| router 级依赖 | `app/api/v1/__init__.py` 中 `dependencies=` 出现 **0 次** | ⚠️ 授权完全依赖端点自身声明 |
| `/api/v1` 内绕过 | 嵌套 router（`agent_knowledge`／`agent_evidence`／`agent_v2`／`agent_governance` → `agent.router`；`teaching_roster` → `teaching.router`；`training_workbench` → `training.router`）全部在网关内 | ✅ `/api/v1` 内无绕过 |
| **网关外入口** | 网关只挂在 `/api/v1` 前缀上。应用另有 5 个 HTTP 入口不在其内：`GET /`（`main.py` 根路由）、`/openapi.json`、`/docs`、`/docs/oauth2-redirect`、`/redoc`。**复核方实测：无令牌均返回 200** | ❌ **完整接口契约（全部路径、参数、数据结构）对匿名开放** |
| **WebSocket** | `app.include_router(websocket_router)` **无 dependencies**；处理函数无任何令牌校验 | ❌ **完全在认证体系之外** |
| 令牌 | 双令牌（access／refresh），`access_tokens` 389 行、`refresh_tokens` 389 行 | 已使用 |
| 角色 | 4 个（admin／teacher／student／auditor），12 个权限键，23 条角色权限映射 | 见 §4.3 |

## 4. 身份与对象矩阵（表 1）

### 4.1 按授权画像聚合

矩阵共 **187 行** = 181 条 HTTP（含根路由 `/`）+ 2 条 WebSocket + 4 条 FastAPI 自带路由。
**100% 非公开入口已进入矩阵**（退出门禁 1）。
列含义：✅ 允许且有隔离；⚠️ 允许但**无对象隔离**（可操作他人对象）；❌ 拒绝。

| 画像 | 条数 | 匿名 | 学生本人 | 其他学生 | 本班教师 | 其他教师 | 跨校 | 管理员 | 审计 |
|---|---:|---|---|---|---|---|---|---|---|
| PUBLIC（白名单） | 7 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **网关外 HTTP** | **5** | **⚠️** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **⚠️** | ⚠️ | ⚠️ |
| **WebSocket 无认证** | 2 | **⚠️** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **⚠️** | ⚠️ | ⚠️ |
| **AUTH_ONLY（46 写 + 39 读）** | 85 | ❌ | ⚠️ | **⚠️** | ⚠️ | **⚠️** | **⚠️** | ⚠️ | ⚠️ |
| ACTOR（无归属校验） | 20 | ❌ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **⚠️** | ⚠️ | ⚠️ |
| ACTOR + 归属校验 | 24 | ❌ | ✅ | ✅ | ✅ | ✅ | 部分 ✅ | ✅ | ✅ |
| require_permission | 42 | ❌ | 按权限 | **⚠️** | 按权限 | **⚠️** | **⚠️** | ✅ | 按权限 |
| require_permission + 归属校验 | 2 | ❌ | ✅ | ✅ | ✅ | ✅ | 部分 ✅ | ✅ | ✅ |

**读法：** 除 7 条白名单外，`/api/v1` 上的匿名请求一律被网关拒绝——**认证边界在 `/api/v1` 内成立**；
但网关外 5 个入口与 2 条 WebSocket 匿名可达。
「其他学生／其他教师」两列显示：**有归属校验的 26 条（24 ACTOR+OWNER、2 PERM+OWNER）建立了对象隔离，
其余 147 条非公开入口没有**。「跨校」一列只有涉及 `ensure_user_scope()` 的少数读接口成立。

**读写不对称是本阶段最关键的结构性事实：**

| | 总数 | 有对象归属校验 | 占比 |
|---|---:|---:|---:|
| 读操作（GET） | 86 | 16 | 19% |
| **写操作** | **94** | **10** | **11%** |

10 条有归属校验的写操作**全部在 `robots`／`onboarding`**——除机器人资产管理外，
全系统写操作没有对象级授权。

逐条 187 行完整矩阵见 [A4 安全证据](./evidence/2026-08-28-a4-security-evidence-v0.1.0.md)。

### 4.2 无对象隔离的写操作（46 条，按域）

| 域 | 条数 | 代表端点 | 后果（静态推断） |
|---|---:|---|---|
| `training` | 7 | `POST /training/sessions/{id}/submit`、`force-submit`、`pause`、`abandon` | 任意用户可提交／放弃他人训练会话 |
| `assessments` | 6 | `POST /assessments/{id}/revoke`、`dispute`、`reinstate` | 任意用户可撤销／申诉任意评估 |
| `teaching_roster` | 6 | **`POST /attempts/{id}/grade`**、`PATCH /attempts/{id}`、`POST /classes`、`POST /enrollments` | **任意用户可给任意作业打分**；可建班、可加人 |
| `maintenance` | 5 | `POST /maintenance/drafts/{id}/approve`、`reject`、`submit-review` | 任意用户可批准／驳回维保草稿 |
| `tasks` | 5 | `POST /tasks`、`/tasks/{id}/start｜step｜pause｜resume` | 任意用户可操作他人任务 |
| `pipeline` | 4 | `POST /pipeline/executions/{id}/complete` | 任意用户可完结他人执行 |
| `fault_cases` | 3 | `POST｜PUT｜DELETE /fault-cases` | 任意用户可增删改故障案例 |
| **`adapter`** | 2 | **`POST /adapter/inject-fault`**、`DELETE /adapter/fault/{code}` | **任意用户可向机器人注入／清除故障**；该域连 `get_db` 都没有，依赖列表为空 |
| `sops` | 2 | `POST /sops`、**`DELETE /sops/{sop_id}`** | 任意用户可创建／删除任意 SOP |
| 其余（`ai_assistant`、`evidence`、`incidents`、`observations`、`teaching`、`training_workbench`） | 各 1 | — | 同类 |

### 4.2.1 越权面的性质区分

46 条无隔离写操作**不是同一种风险**，按是否操作既有对象拆开：

| 类型 | 条数 | 越权面 | 代表 |
|---|---:|---|---|
| **操作既有对象**（路径含 `{id}`） | **27** | **明确的跨用户越权**：调用者可指定任意对象 ID，代码无从判断归属 | `POST /attempts/{id}/grade`、`DELETE /sops/{id}`、`POST /maintenance/drafts/{id}/approve`、`POST /training/sessions/{id}/submit`、`POST /tasks/{id}/start｜step｜pause｜resume`、`POST /assessments/{id}/revoke` |
| **创建型**（无对象 ID） | 19 | 越权面取决于**请求体是否允许指定归属字段**（如 `user_id`、`teacher_id`、`class_id`）。本批未逐条核对请求 schema，**记为 UNKNOWN** | `POST /classes`、`POST /enrollments`、`POST /sops`、`POST /tasks`、`POST /adapter/inject-fault` |

**这 27 条是本阶段最确定的安全结论**：路径参数直接指定对象，端点又没有身份，
两者叠加在实现上排除了做归属校验的可能。19 条创建型的实际影响需要逐条核对 Pydantic 请求模型，
留给 A5 与 A6。

### 4.3 角色与权限（RBAC 现状）

| 角色 | 权限键 | 问题 |
|---|---|---|
| admin | 全部 12 个 | — |
| teacher | `agent:execute`、`agent:read`、`assignment_attempts:read`、`teaching:read` | — |
| student | `agent:read`、`assignment_attempts:read`、`teaching:read` | `assignment_attempts:read` 无对象过滤，学生可读**任意**作业尝试 |
| **auditor** | `approvals:grant`、`approvals:reject`、`approvals:read`、`audit_events:read` | ❌ **审计员拥有审批通过与拒绝权限，违反职责分离**；且该角色 0 个账号、0 个前端入口（A2） |

RBAC 数据本身由种子脚本灌入，应用代码零写入（A3 §6.1）——**运行期无法调整角色权限**。

## 5. 写操作与审批矩阵（表 2）

| Action_ID | 动作类别 | 风险 | 发起角色 | 是否经策略评估 | 审批落点 | 拒绝审计 | 当前结论 |
|---|---|---|---|---|---|---|---|
| **AC-01** | AI Agent 执行（`/agent/v2/*`、orchestrator） | R1~R3（`PolicyMatrix` 5 条规则标 `requires_approval=True`） | teacher／admin（`agent:execute`） | ✅ `policy_matrix.evaluate()` | **进程内内存队列 `approval_queue`，不落库**（A3 S-01） | `approval_records` 表零写入 | **PARTIAL**：有策略、无持久化 |
| **AC-02** | 普通 HTTP 写操作（94 条中的 46 条无隔离写） | 未评级 | 任何已登录用户 | ❌ **不经过策略矩阵** | 无 | 无 | **FAIL**：无授权、无审批、无审计 |
| **AC-03** | 审批动作本身（`/ai/approvals/{id}/grant｜reject`） | 高 | `approvals:grant`／`reject`（admin **与 auditor**） | — | `approvals` 表（由 `api/agent.py` 端点直写，A3 §6.3） | — | **PARTIAL**：唯一完整 UI 不可达（A2 BR-07），且审计员可批 |
| **AC-04** | 机器人故障注入（`/adapter/inject-fault`） | 高（直接影响机器人状态） | **任何已登录用户** | ❌ | 无 | 无 | **FAIL**：零依赖、零授权 |
| **AC-05** | 用户角色变更（`POST /admin/users/{id}/role`） | 高 | `users:write`（仅 admin） | ❌ | 无 | — | **PARTIAL**：权限受控但无前端入口（A2 BR-13） |
| **AC-06** | 机器人资产写（`robots` 域 8 条） | 中 | teacher／admin + **对象归属校验** | ❌ | 无 | — | **PASS（对象级）**：全系统唯一有归属校验的域 |

**关键结论：`PolicyMatrix` 只覆盖 AI Agent 路径。** 全仓 `policy_matrix.evaluate()` 仅 2 处调用
（`agent_v2.py` 的策略评估端点、`orchestrator_v2.py`），普通业务写操作完全不经过风险评级与审批。

## 6. 机器人与实时矩阵（表 3）

| Channel_ID | 通道 | 身份 | 订阅对象 | 控制对象 | 断线 | 重试 | 停止 | 跨机器人隔离 |
|---|---|---|---|---|---|---|---|---|
| **CH-01** | `WS /ws/robot/status` | **无任何认证** | 全量遥测 | **无控制能力** | `WebSocketDisconnect` 捕获后 `manager.disconnect()` | 客户端侧 `useWebSocket` 自行重连 | **无** | **无**（单一广播） |
| **CH-02** | `WS /ws/robot/{robot_id}/status` | **无任何认证** | 全量遥测 | **无控制能力** | 同上 | 同上 | **无** | **无**——源码注释明写 `robot_id: MVP阶段接收但暂不用于数据过滤` |
| **CH-03** | 机器人动作控制 | — | — | — | — | — | — | **MISSING**：`BaseRobotAdapter` 10 个抽象方法无任何运动控制 |
| **CH-04** | 急停 | — | — | — | — | — | — | **MISSING**：仅存在于 `MockRobotAdapter.apply_maintenance_action()` 的 `emergency_stop` 分支，由中文关键词「停机／急停」触发，无端点、不在适配器契约内 |
| **CH-05** | 故障注入（`/adapter/*`） | **无任何依赖** | — | 故障状态 | — | — | — | **无授权**（见 AC-04） |

| **CH-06** | `websocket_manager.send_to_user(user_id, message)` | — | **声称按用户定向** | — | — | — | — | **无**——实现注释写着「目前简化为向所有连接广播」，随后遍历**全部**连接 |

**服务端不处理客户端消息**（`# MVP阶段不处理客户端消息，仅接收`），因此 WS 不构成控制面，
只构成**未鉴权的数据出口**。

**CH-06 是本表最严重的一条（异源复核独立发现）：** 系统提供了一个名为「向指定用户发送」的接口，
但实现是向所有连接广播。调用方按其命名合理地假定消息是定向的，实际每一条都发给了全部在线客户端——
**跨用户、跨班级的消息泄露，且调用方无从察觉**。结合 CH-01／CH-02 的零认证，
任意匿名连接都能收到这些「定向」消息。

## 7. AI 与证据边界（表 4）

| Tool_ID | 对象 | 读/写 | 引用校验 | 对象过滤 | 审批 | 真机能力 | 降级 |
|---|---|---|---|---|---|---|---|
| **T-01** | AI 引用查询 `/ai/citations/{ref_id}` | 读 | ✅ 有 `citation_scope_mismatch` 作用域校验并写审计 | ✅ 作用域内 | — | 无 | — |
| **T-02** | AI 回放 `/ai/replay/{trace_id}` 及 metrics | 读 | — | `_is_trace_replay_reader(actor)` 角色判定 | — | 无 | `replay_checkpoints` 等表全空（A2／A3） |
| **T-03** | Agent 知识 `/agent/knowledge/*` | 读写 | — | `agent:read`／`agent:execute` 权限，**无对象归属** | — | 无 | 知识存双份，JSON 侧无挂卷（A3 D-13） |
| **T-04** | Agent 执行 `/agent/execute`、`/agent/v2/*` | 写 | — | 权限受控 | ✅ `PolicyMatrix` 评估 | 无 | 审批落内存队列 |
| **T-05** | AI 证据采集 `/agent/evidence/collect` | 写 | — | 权限受控 | — | 无 | `evidence_cards`／`evidence_items` 空（A2 D-03） |
| **T-06** | AI 助手 `/ai-assistant/chat` | 写 | — | **无身份依赖** | ❌ | 无 | — |

**引用校验只在 T-01 一处成立**，其余 AI 工具没有对引用真实性的校验。
**AI 全链路没有真机能力**——与 CH-03／CH-04 一致。

## 8. 关键发现

| 发现 | 事实 | 证据 |
|---|---|---|
| **A4-F-01** | **86 条端点在代码层面拿不到调用者身份**（46 条为写操作，其中 **27 条路径直接带对象 ID**），无法做任何对象级授权 | AST 依赖提取 |
| **A4-F-02** | `POST /attempts/{id}/grade` 签名 `(attempt_id, request, db)`，**任何登录用户可给任意作业打分** | 源码 `teaching_roster.py:727` |
| **A4-F-03** | `DELETE /sops/{sop_id}`、`POST /maintenance/drafts/{id}/approve` 同样无身份参数 | 源码 |
| **A4-F-04** | **WebSocket 完全在认证体系外**，零令牌校验，`robot_id` 明示不用于过滤 → 跨机器人隔离不存在 | `main.py:348`、`websocket.py` |
| **A4-F-05** | **`adapter` 域 5 条端点依赖列表为空**，其中 `POST /adapter/inject-fault` 是写操作 | AST |
| **A4-F-06** | 涉及学校维度的入口共 **7 条**（含 `ensure_user_scope()` 的同校教师判定），**其中 5 条是读接口，写侧只有注册**；CLAUDE.md 的租户约束在**写路径**未落地 | `ownership.py` + 调用链检索 |
| **A4-F-07** | **`auditor` 角色拥有 `approvals:grant`／`reject`**，违反职责分离；同时该角色 0 账号 0 入口 | `role_permissions` 表 |
| **A4-F-08** | **`PolicyMatrix` 只覆盖 AI 路径**，`evaluate()` 全仓 2 处调用；普通写操作零风险评级 | 调用点检索 |
| **A4-F-09** | `require_permission` 的 44 条中只有 **2 条**同时做对象归属校验（`GET /ai/approvals`、`POST /ai/skills/{id}/submit-review`）；`student` 的 `assignment_attempts:read` 无对象过滤 | AST + RBAC 表 |
| **A4-F-10** | 对象归属校验共 **26 条**，分布在 `robots`／`tasks`／`training`／`teaching_roster`／`students`／`skills`／`approvals`；但**读写严重不对称**——86 条读里 16 条有校验（19%），**94 条写里只有 10 条（11%），且全部在 `robots`／`onboarding`** | `ownership.py` 辅助函数 + AST |
| **A4-F-11** | 机器人控制与急停在系统层面不存在（复核 A2 结论）；故 A4 要求覆盖的「命令状态机、停止、真机边界」记为 MISSING | `adapters/base.py` |
| **A4-F-12** | **`force-submit` 是混淆代理**：`POST /training/sessions/{id}/force-submit` 做了教师管辖权校验，但校验对象是**请求体里的 `request.teacher_id`** 而非认证身份；该编号还会被当作操作人写入记录。**有检查，但检查的是调用方自己提供的身份** | `training.py:312-333`（异源复核独立发现） |
| **A4-F-13** | **「定向」实时消息实为全量广播**：`websocket_manager.send_to_user()` 的实现注释写着「目前简化为向所有连接广播」，随后遍历**全部**连接发送——跨用户、跨班级消息泄露 | `websocket_manager.py:210-222`（异源复核独立发现） |
| **A4-F-14** | **GET 请求写数据库**：`GET /attempts/{attempt_id}/evidence` 在证据不存在时调用 `EvidenceEngine.generate_bundle_for_task()`，该方法内含 `await self.db.commit()`。读接口被改成写接口 | `teaching_roster.py:764-774` + `evidence_engine.py:62`（异源复核独立发现） |
| **A4-F-15** | **完整接口契约对匿名开放**：`/openapi.json`、`/docs`、`/redoc`、`/docs/oauth2-redirect` 与根路由 `/` 在默认拒绝网关之外，复核方实测无令牌返回 200 | `main.py` 路由注册（异源复核独立发现） |

## 9. 退出门禁自评

| 门禁 | 要求 | 本报告 | 结论 |
|---|---|---|---|
| A4-G1 | **100% 非公开入口进入身份与对象矩阵** | 183 行覆盖 181 HTTP + 2 WS，无遗漏；7 条公开入口单列 | ✅ 达标 |
| A4-G2 | 所有写入口、实时订阅和机器人动作均有当前结论或 UNKNOWN | 94 条写入口全部归入 §4.2／§5；2 条实时订阅见 §6；机器人动作记为 MISSING | ✅ 达标 |
| A4-G3 | **严重越权和未审批动作不得被测试绿灯掩盖** | §4.2 的 46 条无隔离写操作中，多条有后端测试通过（如 `POST /classes` 测试 6、`grade` 测试 4）——**测试覆盖的是功能正确性，不覆盖越权**。本报告显式登记该事实 | ✅ 达标 |
| A4-G4 | 不得把「代码存在」写成「真实可用」 | 全部结论标注为静态证据，明确声明未发起越权请求，验证等级 E1 | ✅ 达标 |
| §5.8 | 主审与复核异源 | Codex 13 条断言复核完成，6 条 MISMATCH 全部采纳，另接受其 4 个独立发现 | ✅ 达标 |

> **G3 的具体说明（0.1.1 更正）：** 0.1.0 原文写「没有一条测试尝试越权访问」，**这与事实相反**，已由 A5 更正。
> 实际情况：全仓存在成体系的对象归属边界测试——`tests/e2e/test_object_ownership_boundary.py`
> 覆盖跨学生读→404、**跨校教师读→404**、无主任务拒绝、查询参数提权防护及正向边界；
> `tests/unit/test_teaching_identity_boundary.py` 覆盖伪造 `X-RMOS-Role`／`X-User-ID`；
> 拒绝类断言合计 **28 处 `403` + 72 处 `404`**（该库刻意用 404 表达归属拒绝以避免泄露对象存在性）。
>
> **G3 修正后仍然成立的部分：** 这些用例集中在**读路径**。本报告 §4.2 点名的高危**写**端点中，
> `DELETE /sops/{sop_id}`、`POST /maintenance/drafts/{draft_id}/approve`、`POST /adapter/inject-fault`
> 所在的测试文件既无 403 也无归属边界用例——**写路径的越权仍无测试反证**。
> 「测试绿灯不覆盖写路径授权」这一门禁关切成立，只是范围应限定在写路径，不能推广到全仓。

## 10. 异源复核记录

| 项 | 内容 |
|---|---|
| 复核方 | Codex（工作目录在被审仓库之外，授网络访问，明令只读；复核后被审工作区确认零改动） |
| 复核范围 | 13 条安全断言（D-01~D-13），并**额外要求其独立提出主审未列出的安全问题** |
| 结论 | **OVERALL: MISMATCH(6)** — 7 条 AGREE、**6 条 MISMATCH**，另**独立提出 4 个主审完全没发现的问题** |
| 处置 | 6 条 MISMATCH 全部复验，**全部成立，全部采纳**；4 个独立发现全部复验属实，已列为 A4-F-12~15 |
| 复核方额外动作 | 做了**无令牌连通性实测**（主审只做静态分析）：确认 `/`、`/docs`、`/redoc`、`/openapi.json` 匿名 200，两条 WebSocket 无令牌可连 |

### 10.1 MISMATCH 处置

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MM-A4-01**（D-02） | 「没有任何 HTTP 路由绕过网关」不成立：网关只挂在 `/api/v1` 上，`/`、`/docs`、`/redoc`、`/openapi.json` 在其外，实测无令牌 200 | 成立。主审只检查了 `/api/v1` 及其嵌套 router，**把「`/api/v1` 内无绕过」错误地表述成「无任何绕过」** | **采纳**。§3 新增「网关外入口」行，§4.1 单列 5 条，新增发现 A4-F-15 |
| **MM-A4-02**（D-05） | 画像应单列「网关外 HTTP 1 条」，真正的 AUTH_ONLY 是 85 不是 86 | 成立。主审把根路由 `/` 并入了 AUTH_ONLY | **采纳**。矩阵重算为 187 行，AUTH_ONLY 85 |
| **MM-A4-03**（D-06） | 写操作 46 条数字正确，但归属的桶错了 | 成立，同 MM-A4-02 | **采纳** |
| **MM-A4-04**（D-07） | **归属校验不止在 `robots` 域**——`tasks`、`training`、`teaching_roster`、`students` 都有本人／同校／对象范围检查 | **成立，这是主审把问题说重了**。根因：主审的正则只覆盖字面比较，**完全没识别 `app/services/ownership.py` 的 `ensure_user_scope()`／`ensure_task_scope()` 辅助函数**（前者含"本人 / 管理员 / 同校教师"三段判定） | **采纳**。归属校验 **13 → 26**；结论改写为「读路径部分有隔离（16/86），写路径几乎没有（10/94）」 |
| **MM-A4-05**（D-08） | `require_permission` 与对象归属**不互斥**，`POST /ai/skills/{id}/submit-review` 两者兼有，不是 0 条 | 成立 | **采纳**。改为 2 条（另一条是 `GET /ai/approvals`） |
| **MM-A4-06**（D-09） | 学校维度不止 2 条——另有 5 条端点通过调用链进入同校检查，按真实行为至少 7 条 | 成立，同 MM-A4-04 的根因（只做字面搜索，不看调用链） | **采纳**。改为 7 条，并注明其中 5 条为读接口 |

### 10.2 复核方独立发现（主审完全未覆盖）

| 发现 | 主审复验结果 |
|---|---|
| `force-submit` 信任请求体中的 `teacher_id` | **属实且更严重**：该端点**做了**管辖权校验，但校验对象是调用方自己提供的编号，属典型混淆代理；伪造编号还会被写入记录作为操作人。已列为 **A4-F-12** |
| `send_to_user` 实为全量广播 | **属实**：源码注释直书「目前简化为向所有连接广播 / 实际实现应该维护 user_id → connection 映射」，随后遍历全部连接。已列为 **A4-F-13** |
| `GET /attempts/{id}/evidence` 会写库 | **属实**：无证据时调用 `generate_bundle_for_task()`，该方法内 `await self.db.commit()`。已列为 **A4-F-14** |
| OpenAPI 与文档页匿名可读 | **属实**，与 MM-A4-01 同源。已列为 **A4-F-15** |

### 10.3 方法教训

**本轮暴露的主审缺陷比前三轮都严重，因为方向是「把问题说重」。**

1. **只认字面模式，不认辅助函数。** 归属校验的正则只匹配 `xxx == actor.user_id` 这类字面比较，
   完全漏掉了项目自己封装的 `ensure_user_scope()`／`ensure_task_scope()`。
   **审计一个代码库前，应先找出它自己的安全辅助模块，再据此设计检测**——
   这与 A3 的「静态匹配必须解析到符号来源」是同一类教训的延伸：**不仅要解析符号，还要理解项目的抽象**。
2. **边界描述要写清适用范围。** 「无绕过」必须写成「`/api/v1` 内无绕过」；
   一个前缀级的网关天然管不到前缀外的路由。
3. **静态分析看不见"检查了错的东西"。** `force-submit` 有校验代码，任何"是否存在检查"的静态扫描都会给它打勾；
   只有读懂**校验的输入从哪来**才能发现问题。这类缺陷只能靠人工阅读或运行期实测发现——
   本批的最大盲区正在于此。
4. **复核方做了主审没做的实测。** 无令牌连通性探测直接证实了 4 条网关外入口，
   而主审停留在静态推断。**安全阶段应当把"无害的连通性实测"纳入主审标准动作**，
   已写入 §11 移交项。

## 11. 移交下阶段的问题

| 移交项 | 承接阶段 | 说明 |
|---|---|---|
| 46 条无隔离写操作的授权补齐 | A6 | 本阶段最大的一笔安全债 |
| WebSocket 认证与机器人隔离 | A6 | 当前是未鉴权数据出口 |
| `adapter` 域故障注入的授权 | A6 | 直接影响机器人状态 |
| 跨租户隔离（7 条入口涉及学校维度，其中 5 条为读接口，**写侧只有注册**） | A6 | 与 CLAUDE.md 的租户约束在**写路径**冲突 |
| `auditor` 的审批权（职责分离） | A6 | RBAC 数据由脚本灌入，改动需连带处理 A3 的"运行期不可维护" |
| 越权行为的执行期实证 | A5 | 本批只做静态分析，需实际请求验证可利用性 |
| **把无害连通性实测纳入主审标准动作** | A5 | 复核方靠无令牌探测直接证实 4 条网关外入口，主审的纯静态方法看不见 |
| **`force-submit` 类「校验了错的输入」缺陷的系统性排查** | A5 | 静态扫描对这类缺陷天然失效，需逐条读参数来源 |
| 授权测试缺口 | A5 | 现有测试不覆盖越权场景 |
| `PolicyMatrix` 覆盖面 | A6 | 是否扩展到普通写操作 |

## 12. 本批产出物

| 文件 | 说明 |
|---|---|
| 本报告 | A4 主报告 |
| [A4 安全证据](./evidence/2026-08-28-a4-security-evidence-v0.1.0.md) | 183 行逐条身份矩阵、守卫提取结果、RBAC 映射、复现命令 |
