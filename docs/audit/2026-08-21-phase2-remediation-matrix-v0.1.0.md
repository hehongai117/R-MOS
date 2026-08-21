# R-MOS Phase 2 修复矩阵（29 项）

- 版本：0.1.0
- 日期：2026-08-21
- 状态：Active（Phase 2 产物；**不代表任何一项已修复**）
- 基线提交：`09ec02a19488504449a3f6f8439d3a4f73d33774`
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`
- 证据来源：`docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`（**唯一权威**，本文件不替代它）

## 0. 使用规则

- 本文件把 Phase 1 的 29 项发现映射到可复现门禁与执行批次，供 Phase 3/4 排期与 Phase 5 逐条核对使用。
- **完整证据、代码位置与影响以 Phase 1 主报告为准。** 本文件的"目标文件"是修复落点，不是证据引用。
- 每一项的"当前状态"在 Phase 2 结束时**全部为 `NOT_STARTED`**。Phase 2 只写文档，不改应用代码。
- 关闭一项的充分条件写在"关闭标准"栏。**任何一项都不得因为 ADR 写完、计划排好或自动测试通过而关闭。**
- 门禁编号 `AUTH-GATE` / `CTRL-GATE` / `EVID-GATE` / `AI-GATE` / `RT-GATE` / `DEP-GATE` 来自 `docs/testing/TEST_PLAN.md` 的"Phase 1 审查后的强制补充门禁"表。
- `AC-xx` / `T-xx` 来自 `docs/testing/2026-08-10-rmos-single-school-five-robot-acceptance-matrix-v0.1.0.md`；`DR-xx` 与 `REL-BLOCK-01` 来自 `docs/plans/2026-08-10-rmos-single-school-five-robot-deployment-rollback-v0.1.0.md`。引用它们表示"最终验收时该项须一并满足"，**不表示这些真机/预生产条件已具备**。

## 1. ADR 索引

| 代号 | 文件 | 覆盖发现 |
|---|---|---|
| ADR-AUTHN | `docs/adr/ADR-2026-08-21-authn-default-deny-and-object-ownership.md` | AUTH-101～105、RT-101 认证面 |
| ADR-ROBOT | `docs/adr/ADR-2026-08-21-robot-binding-and-adapter-registry.md` | CTRL-101～105、RT-101～104 隔离面 |
| ADR-EVID | `docs/adr/ADR-2026-08-21-evidence-integrity-and-sop-versioning.md` | EVID-101～105 |
| ADR-AI | `docs/adr/ADR-2026-08-21-ai-approval-and-audit-gating.md` | AI-101～105 |
| ADR-RUNTIME | `docs/adr/ADR-2026-08-21-runtime-topology-and-production-deployment.md` | DEP-101～105 |

五份 ADR 状态均为 **Proposed**，各自"待确认事项"未获用户确认前不得进入实现。

## 2. 总表

批次编号含义：`P3-n` = Phase 3 第 n 批（见 `docs/plans/2026-08-21-rmos-phase3-auth-control-realtime.md`）；`P4-n` = Phase 4 第 n 批（见 `docs/plans/2026-08-21-rmos-phase4-evidence-ai-deployment.md`）。

| 编号 | 级别 | 类型 | ADR | 批次 | 门禁 | 关联验收 | 当前状态 |
|---|---|---|---|---|---|---|---|
| AUTH-101 | P0 | 事实 | ADR-AUTHN | P3-1 | AUTH-GATE | AC-01 / T-01-N,B,E | NOT_STARTED |
| AUTH-102 | P1 | 事实 | ADR-AUTHN | P3-1 | AUTH-GATE | AC-01 / T-01-B | NOT_STARTED |
| AUTH-103 | P1 | 事实 | ADR-AUTHN | P3-3 | AUTH-GATE | AC-06 / T-06-E | NOT_STARTED |
| AUTH-104 | P1 | 事实 | ADR-AUTHN | P3-2 | AUTH-GATE | AC-01 / T-01-E | NOT_STARTED |
| AUTH-105 | P2 | 事实 | ADR-AUTHN | P3-3 | AUTH-GATE | AC-01 / T-01-E | NOT_STARTED |
| CTRL-101 | P1 | 事实 | ADR-ROBOT + ADR-AI | P3-4 | CTRL-GATE | AC-02 / T-02-E | NOT_STARTED |
| CTRL-102 | P1 | 事实 | ADR-ROBOT | P3-4 | CTRL-GATE | AC-03 / T-03-B,E | NOT_STARTED |
| CTRL-103 | P1 | 事实 | ADR-ROBOT | P3-4 | CTRL-GATE | AC-02 / T-02-E | NOT_STARTED |
| CTRL-104 | P1 | 事实 | ADR-ROBOT | P3-5 | CTRL-GATE | AC-08 / T-08-N,E；DR-03 | NOT_STARTED |
| CTRL-105 | P2 | **推断** | ADR-ROBOT | P3-5 | CTRL-GATE | AC-03 / T-03-B | NOT_STARTED |
| RT-101 | P1 | 事实 | ADR-AUTHN + ADR-ROBOT | P3-6 | RT-GATE | AC-07 / T-07-N,E | NOT_STARTED |
| RT-102 | P1 | 事实 | ADR-ROBOT | P3-6 | RT-GATE | AC-07 / T-07-N | NOT_STARTED |
| RT-103 | P2 | 事实 | ADR-ROBOT | P3-6 | RT-GATE | AC-07 / T-07-E | NOT_STARTED |
| RT-104 | P2 | 事实 | ADR-ROBOT | P3-6 | RT-GATE | AC-07 / T-07-N | NOT_STARTED |
| EVID-101 | P1 | 事实 | ADR-EVID | P4-1 | EVID-GATE | AC-04 / T-04-E | NOT_STARTED |
| EVID-102 | P1 | 事实 | ADR-EVID | P4-1 | EVID-GATE | AC-04 / T-04-E | NOT_STARTED |
| EVID-103 | P1 | 事实 | ADR-EVID | P4-1 | EVID-GATE | AC-04,AC-05 / T-04-E,T-05-E | NOT_STARTED |
| EVID-104 | P1 | 事实 | ADR-EVID | P4-2 | EVID-GATE | AC-04,AC-05 / T-04-B,T-05-N | NOT_STARTED |
| EVID-105 | P1 | 事实 | ADR-EVID | P4-2 | EVID-GATE | AC-05 / T-05-E | NOT_STARTED |
| AI-101 | P1 | 事实 | ADR-AI | P4-4 | AI-GATE | AC-02 / T-02-E | NOT_STARTED |
| AI-102 | P1 | 事实 | ADR-AI | P4-3 | AI-GATE | AC-02 / T-02-E | NOT_STARTED |
| AI-103 | P1 | 事实 | ADR-AI | P4-3 | AI-GATE | AC-02 / T-02-E | NOT_STARTED |
| AI-104 | P1 | 事实 | ADR-AI | P4-5 | AI-GATE | AC-04 / T-04-E | NOT_STARTED |
| AI-105 | P1 | 事实 | ADR-AI | P4-4 | AI-GATE | AC-01 / T-01-E；DR-05 | NOT_STARTED |
| DEP-101 | P1 | 事实 | ADR-RUNTIME | P4-6 | DEP-GATE | AC-09 / T-09-E；**受待定 J 阻塞** | NOT_STARTED |
| DEP-102 | P1 | 事实 | ADR-RUNTIME | P4-6 | DEP-GATE | AC-03 / T-03-B | NOT_STARTED |
| DEP-103 | P1 | 事实 | ADR-RUNTIME | P4-6 | DEP-GATE | AC-10 / T-10-N；DR-06 | NOT_STARTED |
| DEP-104 | P1 | 事实 | ADR-RUNTIME + ADR-EVID | P4-6 | DEP-GATE | AC-10 / T-10-N,E；DR-01,DR-02 | NOT_STARTED |
| DEP-105 | P1 | 事实+未知 | ADR-RUNTIME | P4-7 本地准备；**Phase 5 联网核查** | DEP-GATE | — | NOT_STARTED |

计数核对：P0 = 1（AUTH-101）；P1 = 24；P2 = 4（AUTH-105、CTRL-105、RT-103、RT-104）。合计 29。事实 28 项，推断 1 项（CTRL-105）。

## 3. 逐项修复规格

格式：**目标文件** → 修复落点；**失败测试** → Phase 3/4 必须先写、且当前必然为红的测试；**通过门槛** → 二元判据；**迁移/回滚**；**关闭标准**。

### AUTH-101｜关键任务和教学接口可绕过令牌认证（P0）

- 目标文件：新增 `app/core/public_routes.py`；`main.py:336` 挂 `enforce_authenticated`；`app/services/authz_guard.py:52` 加请求级缓存。
- 失败测试：`tests/unit/test_auth_boundary.py` 反转后的全路由参数化用例——遍历 `/api/v1` 全部 `APIRoute`，不在白名单者无令牌必须 401。当前 182 个路由函数中静态可见 111 个无认证依赖（AST 扫描；Phase 1 的动态探针为 109，差异来自挂载展开方式，两者均为待分类数，**都不是漏洞数**）。
- 通过门槛：`AUTH-GATE` —— 匿名访问非白名单路由成功 **0 次**；公开路由必须在白名单文件中显式登记。
- 迁移/回滚：无迁移。`git revert` 即回到逐路由自愿状态。
- 关闭标准：白名单经用户签字；反转后的边界测试在当前提交为绿；临时移除一条白名单项时该测试必须变红（门禁自检通过）。

### AUTH-102｜认证边界测试会跳过漏加认证的接口（P1）

- 目标文件：`tests/unit/test_auth_boundary.py:60-76`（`_collect_protected_endpoints` → `_collect_must_auth_endpoints`）。
- 失败测试：同 AUTH-101。二者是同一批次的一体两面——不先修测试，AUTH-101 无法被证明。
- 通过门槛：`AUTH-GATE` —— 非公开路由覆盖率 100%（对应 `T-01-B` 的"少 1 个即 FAIL"）。
- 迁移/回滚：无。
- 关闭标准：`_has_auth_dependency`（29-32 行，已能穿透 `require_permission` 返回的 `_dependency`）保留复用；筛选条件从"跳过无依赖"改为"无依赖且不在白名单即失败"。

### AUTH-103｜私有或未发布机器人资产可匿名列出和下载（P1）

- 目标文件：`app/api/v1/endpoints/robots.py:498`（tools）、`:516`（assets 清单）、`:543`（assets 下载）。
- 失败测试：匿名请求私有/草稿/其他教师/其他学校机器人的资产清单与文件 → 404；资产清单响应中不得出现存储路径字段。
- 通过门槛：`AUTH-GATE` + `AC-06` —— 越权读取成功 0 次、对外 404 率 100%、拒绝审计 100% 含真实 `resource_id`。
- 迁移/回滚：无迁移。公开发布资产走新路径，旧路径收紧为认证专用。
- 关闭标准：公开路径只接受不可猜测的发布标识且校验 `status=READY` 与 `visibility=public`；私有路径全部要求认证 + 归属。

### AUTH-104｜可伪造客户端身份头参与权限和审计（P1）

- 目标文件：`app/api/v1/endpoints/teaching_roster.py` 的 10 处 `Header(alias="X-RMOS-Role"/"X-User-ID")`；`app/services/access_control.py:20-24`。
- 失败测试：(a) 携带合法学生令牌但伪造 `X-RMOS-Role: teacher` → 仍按学生范围；(b) **省略角色头** → 不得放宽范围（当前 `if x_rmos_role and ...` 的写法使省略即绕过）；(c) 审计 `actor_user_id` 恒等于令牌主体。
- 通过门槛：`AUTH-GATE` + `T-01-E` —— 伪造/省略身份头改变授权结果 0 次。
- 迁移/回滚：无迁移。破坏面为 51 处测试 + `scripts/run_gate2_smoke.sh:126,134`；**前端不受影响**（`r-mos-frontend` 全仓无这两个头，且 `src/api/client.ts:60-68` 已挂 Bearer 令牌）。
- 关闭标准：全仓除测试外 `X-RMOS-Role` / `X-User-ID` 读取点为 0；可用 `tests/unit/test_deny_audit_entrypoint_gate.py:30` 的架构门禁范式加一条静态断言。

### AUTH-105｜登录入口没有失败次数限制或临时锁定（P2）

- 目标文件：`app/api/v1/endpoints/auth.py:197-262`。
- 失败测试：同一账号连续 5 次错误密码后第 6 次返回受限状态并写审计；15 分钟窗口结束后恢复；正确密码在锁定期内同样被拒；成功登录清零计数。
- 通过门槛：`AUTH-GATE` —— 达到阈值后受限；换来源不能无限绕过；正常登录不受明显影响。
- 迁移/回滚：无迁移。计数为进程内 TTL 结构（与 ADR-RUNTIME D1 单进程一致），重启即清空。
- 关闭标准：阈值 5 次 / 15 分钟窗口 / 15 分钟锁定、不做永久锁定，已由用户确认。

### CTRL-101｜故障注入和清除入口可匿名修改共享模拟状态（P1）

- 目标文件：`app/api/v1/endpoints/adapter.py:50,74`。
- 失败测试：匿名与学生请求注入故障 → 拒绝 + 审计；教师对非授权机器人 → 拒绝；成功路径必须存在审批记录且 `trace_id` 贯穿命令/审批/执行/审计。
- 通过门槛：`CTRL-GATE` + `AC-02` —— 控制写入必须同时具备身份、角色、机器人归属、审批与审计。
- 依赖：需要 ADR-AI 的 **D1a**（`approvals` 表增加通用资源三元组）先落地，否则故障注入无法进入数据库审批。
- 迁移/回滚：随 ADR-AI 的审批表迁移。
- 关闭标准：`ROBOT_MODE=physical` 时该入口默认关闭；模拟入口与生产入口隔离。

### CTRL-102｜任务、执行、快照没有不可变机器人绑定（P1）

- 目标文件：`app/models/task.py`、`app/models/task_execution.py`、`app/models/snapshot.py`；`app/adapters/factory.py:44-108`；`app/services/snapshot_service.py:29-85`。
- 失败测试：两台机器人并行执行时，命令、快照、事件、报告只出现各自 `robot_model_id`；跨机器人访问与订阅被服务端拒绝；创建后修改 `robot_model_id` 被拒绝。
- 通过门槛：`CTRL-GATE` + `AC-03` / `T-03-B` —— 跨机器人命令/快照/报告 **0 条**。
- 迁移/回滚：单个 Alembic 迁移（`down_revision = "20260817_sop_three_phase"`，当前唯一 head，共 38 个 revision），三表加列 + 回填 + 加约束；`alembic downgrade -1` 删列。
- 关闭标准：`settings.DEFAULT_ROBOT_MODEL_ID` 在业务路径的读取点为 0。

### CTRL-103｜执行前检查在机器人或工具状态未知时放行（P1）

- 目标文件：`app/api/v1/endpoints/tasks.py:42-50`（`robot_id = None` 硬编码 + 整段前检查包在 `if request.user_id:` 内）；`app/services/preflight_check.py:193-200`、`228-237`、`276-315`。
- 失败测试：缺机器人 / 离线 / 被占用 / 维护中 / 工具状态未知 / 缺工具 六种情形各自返回 BLOCK；不带 `user_id` 的创建请求也必须执行前检查。
- 通过门槛：`CTRL-GATE` —— 缺状态默认阻断；只有来自授权机器人的新鲜状态可通过。
- 迁移/回滚：无迁移。`tests/unit/test_preflight_check.py` 中断言"缺 robot_id 仍 PASS"的用例须改写为 BLOCK。
- 关闭标准：设备检查读取真实适配器状态与设备锁，`online/locked/maintenance_mode` 不再写死。

### CTRL-104｜没有统一、可审计的取消或紧急停止入口（P1）

- 目标文件：新增 `POST /api/v1/tasks/{task_id}/cancel`；`app/models/task.py:11-27` 的 `CANCELLED` 已定义可直接用。
- 失败测试：进行中与暂停任务均可停止；重复请求幂等、不产生重复动作；无权/跨机器人停止被拒绝并审计；终态任务返回当前状态而非报错。
- 通过门槛：`CTRL-GATE` + `AC-08` / `DR-03` —— 教师确认的软件停止 100% 可用；自动重发 0 次。
- 迁移/回滚：无迁移。
- 关闭标准：**软件停止不替代物理急停。** `DR-03` 的真机部分属 E3/Phase 6，本项在 Phase 3 只能关闭软件侧。

### CTRL-105｜并发步骤提交可能产生重复事件和快照（P2，**推断**）

- 目标文件：`app/services/task_service.py:93-304`。
- 失败测试（**先取事实，不预设结论**）：对同一任务同一步骤并发提交 **20 轮 × 5 并发**，每轮检查 `events` 表、`snapshots` 表、`tasks.current_step_index` 三处唯一性。
- 通过门槛：`CTRL-GATE` —— 每轮最多一个成功副作用。
- 迁移/回滚：若需唯一约束则随 CTRL-102 的迁移合并。
- 关闭标准（**本项独有，Phase 5 严格执行**）：
  - 若复现 → 修复后并发测试转绿方可关闭。
  - 若**未**复现 → 只有在达到上述 20×5 轮次、三处检查范围全覆盖，**且由用户明确接受残余风险**后，才能以"未复现、风险接受"关闭。
  - 未达门槛或用户未接受 → **保持未关闭，E1 不得提升**。
  - 任何情况下都不得写成"已修复"。

### RT-101｜匿名连接可收到全局遥测，订阅没有服务端隔离（P1）

- 目标文件：`app/api/v1/endpoints/websocket.py:13-34`；`app/services/websocket_manager.py:47-67,139-175,195-223`。
- 失败测试：匿名/过期令牌/无权机器人连接被拒绝并审计；两台机器人 + 两个用户并行推送时跨机器人、跨用户消息 **0 条**；`broadcast_to_channel` 与 `send_to_user` 不再退化为全广播。
- 通过门槛：`RT-GATE` + `AC-07` / `T-07-N,E` —— 匿名连接 0 次；跨订阅消息 0 条。
- 迁移/回滚：无迁移。`/ws/robot/status`（无 `robot_id`）下线属对外契约变更。
- 关闭标准：连接表与适配器注册表均按 `robot_model_id` 隔离；所有消息携带并校验机器人编号。

### RT-102｜客户端心跳回包未进入连接管理（P1）

- 目标文件：`app/api/v1/endpoints/websocket.py:28-34`（未调用已存在的 `ConnectionManager.handle_client_message`）。
- 失败测试：用可控时钟连续运行超过四个心跳周期；有效 pong 保持健康与持续 5 Hz 推送；缺失 pong 才按阈值关闭；断开后连接与后台任务均清理。
- 通过门槛：`RT-GATE` —— 四个心跳周期持续健康。
- 迁移/回滚：无。
- 关闭标准：`websocket_manager.py:82-137` 的 `handle_client_message` 与 `last_pong` 真实生效。

### RT-103｜实时时间格式不统一且测试没有校验（P2）

- 目标文件：`app/services/websocket_manager.py:109,149-152`（对已含 `+00:00` 的时间再追加 `"Z"`）。
- 失败测试：对 ping 与 telemetry 时间执行严格 RFC 3339 解析、往返与时序断言；双后缀输入必须失败。
- 通过门槛：`RT-GATE` —— 时间 100% 严格可解析。
- 迁移/回滚：无。属对外消息格式变更，前端需同步确认解析兼容。
- 关闭标准：由消息模型统一序列化，只输出一种 UTC 形式。

### RT-104｜页面切换机器人时不会重建对应连接（P2）

- 目标文件：`r-mos-frontend/src/hooks/useWebSocket.ts:200-203`（空依赖数组 effect）。
- 失败测试：同一组件内依次切换两个 `robotId`；旧连接关闭一次、新连接地址正确、旧连接后续消息不再更新页面。
- 通过门槛：`RT-GATE` —— 切换机器人有自动测试覆盖。
- 迁移/回滚：无。
- 关闭标准：连接生命周期显式依赖 `robotId`，切换时先取消旧重连定时器与旧连接。

### EVID-101｜不存在的证据包编号可让训练步骤判 PASS（P1）

- 目标文件：`app/services/training/workbench_execution_service.py:133-135`（`has_evidence = bool(evidence_bundle_id)`）。
- 失败测试：不存在、其他用户、其他会话、其他步骤、未封存、哈希不一致的证据包均不能判 PASS；有效证据只能被正确会话步骤使用。
- 通过门槛：`EVID-GATE` + `AC-04` / `T-04-E` —— 伪造、跨对象、损坏、未封存证据通过 **0 次**。
- 迁移/回滚：随 ADR-EVID 迁移 1。
- 关闭标准：判定在同一事务内加载证据包并校验六项（存在、归属、会话/步骤、封存、内容哈希、未撤销）。保留 `:235-241` 的会话归属校验这一正向边界。

### EVID-102｜旧证据门禁忽略类型并跨会话共享状态（P1）

- 目标文件：`app/services/evidence_enforcement.py:50-52,63-77,79-102`；`app/api/v1/endpoints/agent_evidence.py:25-32`。
- 失败测试：跨会话同名 `step_id` 并行不互相污染；伪类型、伪编号、重启前后、其他用户证据均不满足当前步骤。
- 通过门槛：`EVID-GATE` —— 伪造证据满足门禁 0 次。
- 迁移/回滚：无迁移。
- 关闭标准：进程内门禁**不再作为裁决来源**（退化为缓存或整体删除），裁决一律查库。注意 `collect_evidence` 当前只存 `evidence_id` 却在 `validate_step_completion` 里当类型比较，两者必须一并修正。

### EVID-103｜证据"封存"不能证明底层内容未改变（P1）

- 目标文件：`app/services/evidence_service.py:27-59,91-131`；`app/services/evidence_engine.py:141-157`；`app/models/evidence.py:12-45`。
- 失败测试：修改任一事件载荷、快照传感器值或底层文件后校验必须失败；伪造 URI/哈希不能创建封存包；跨学校与跨会话读取被拒绝。
- 通过门槛：`EVID-GATE` + `AC-05` / `T-05-E` —— 发布后修改证据必须被检出。
- 迁移/回滚：ADR-EVID 迁移 1（两表加列）；`alembic downgrade -1` 删列，存量数据不丢。
- 关闭标准：服务端读取真实字节重算哈希；`bundle_hash` manifest 覆盖服务端复核后的每项哈希 + 任务/机器人/会话/步骤/SOP 版本。**存量 legacy 证据不补复核，显式标注且不得用于新判定。**
- 已有可复用实现：`workbench_execution_service.py:53-64` 的上传路径**已经在服务端对真实字节算 sha256**，缺的是复核环节与存储抽象。

### EVID-104｜无步骤证据也可完成、评分并生成报告（P1）

- 目标文件：`app/schemas/task.py:53-58`（`StepExecutionRequest` 无证据字段）；`app/services/task_service.py:93-304`、`:188-211`；`app/services/scoring_service.py:42-142`。
- 失败测试：关键步骤无证据 / 证据损坏 / 归属错误时任务不能完成、不能判 PASS；非关键缺失按明确策略降级并在报告中显示为"证据缺口"。
- 通过门槛：`EVID-GATE` + `AC-04` / `T-04-B` —— 0 条证据时完成成功 0 次。
- 迁移/回滚：随 ADR-EVID 迁移 1。
- 关闭标准：证据要求由 `sop_steps.is_critical` 在服务端声明；`tests/unit/test_evidence_engine.py:60-82` 一类"无证据也能完成"的特征化测试已改写。

### EVID-105｜已被任务使用的 SOP 可物理删除（P1）

- 目标文件：`app/services/sop_service.py:126-204`；`app/models/sop.py:25`；`app/api/v1/endpoints/sops.py:153`。
- 失败测试：停用或发布新版本后旧任务报告仍能完整回放原步骤、版本与哈希；对已被任务引用的版本执行物理删除在数据库层被阻断。
- 通过门槛：`EVID-GATE` + `AC-05` —— 历史任务依据可回放。
- 迁移/回滚：ADR-EVID 迁移 2（建 `sop_versions`、`tasks.sop_version_id`、`sops.is_archived`）。**回滚前必须先导出 `sop_versions` 全表**，否则丢失已发布的新版本内容。
- 关闭标准：`delete_sop(force=True)` 不再置空 `tasks.sop_id`、不再删除 `SOPStep`；外键 `ondelete="RESTRICT"` 在数据库层兜底。

### AI-101｜普通 Agent 用户可创建并批准自己的旁路审批（P1）

- 目标文件：删除 `app/services/approval_queue.py`（226 行）与 `app/api/v1/endpoints/agent_governance.py:12,34-145`、`app/schemas/agent.py:142-151`；`app/services/approval_service.py:56-68` 加自批拒绝。
- 失败测试：普通 Agent 用户、请求创建者本人、伪造 `approved_by` 均不能批准；审批重启后仍存在；所有状态变化有同一 `trace_id` 与审计事件。
- 通过门槛：`AI-GATE` + `AC-02` / `T-02-E` —— 学生自批、伪造批准发送 0 次。
- 迁移/回滚：**带迁移**（ADR-AI D1a：`approvals` 表增加 `resource_type` / `resource_id` / `action` / `priority` / `expires_at`，并把 `command_id` / `tool_call_id` 放开为可空）。删除动作单独成提交。
- 关闭标准：`app/models/approval.py` 已有的 `created_by_user_id` 与 `decided_by_user_id` 用于自批比较；`agent_governance.py` 其余 4 个非审批路由（`:150-186`、`:191-228`、`:233-304`）保留。
- **阻塞项**：删除会连带删掉 `tests/regression/test_p0_bugs_2026_07.py:241` —— 一个被 `pytest.ini:11` 定义为"永不放松"的 `regression` 用例。须用户明确批准。

### AI-102｜持久化命令的身份和审批触发由客户端输入决定（P1）

- 目标文件：`app/api/v1/endpoints/agent.py:144-281`（`Command.actor_user_id` 取 `request.user_id`）。
- 失败测试：伪造 `user_id` 不改变任何运行时或审计主体；删除客户端 `side_effects` 仍不能绕过写工具审批；未知/未发布工具被拒绝并审计。
- 通过门槛：`AI-GATE` —— 写操作风险不得低于 medium；创建者不能批准自己的请求。
- 迁移/回滚：无迁移（`Command.risk_level` 列已存在，只是未写入）。
- 关闭标准：操作者只取令牌；工具名解析到已发布技能版本，风险与副作用由服务端登记表决定。可复用 `app/models/skill_registry.py` 已有但运行时未使用的 `evidence_requirements` / `approval_workflow` / `policy_rules` 三个 JSON 列。

### AI-103｜未知动作默认放行，审批结论未形成执行门禁（P1）

- 目标文件：`app/services/policy_matrix.py:212-221`（默认 `allowed=True`）；`app/services/orchestrator_v2.py:351-433`（只在 `allowed=False` 时停止）。
- 失败测试：未知动作、缺规则动作、需审批动作均不能进入模块执行；批准前副作用次数 0，拒绝或过期后始终 0。
- 通过门槛：`AI-GATE` —— 未知动作默认拒绝。
- 迁移/回滚：无迁移。
- 关闭标准：`requires_approval=True` 时必须持久化命令并进入等待状态。可对齐 `app/api/v1/endpoints/skills.py:65` 已有的 `_validate_publish_risk` / `RISK_LEVEL_ORDER` / `CRITICAL_SIDE_EFFECT_KEYWORDS`——其中"未知风险等级即拒绝"正是本项要的范式。

### AI-104｜伪造的引用编号可被当作有效检索命中（P1）

- 目标文件：`app/services/tool_executor.py:78-95`（只做 UUID 正则）、`:187-215`（直接拼 citations/hits）。
- 失败测试：随机 UUID、其他用户、其他课程、已撤销引用均不能进入 `hits`/`citations`；有效引用可由同一用户回放。
- 通过门槛：`AI-GATE` + `AC-04` —— 伪引用命中 **0 条**。
- 迁移/回滚：无迁移。
- 关闭标准：工具执行前批量查询并应用对象级访问过滤。可复用 `app/api/v1/endpoints/ai_commands.py:100-153`——仓库里唯一"引用 ID → 查库 → 校验归属 → deny 审计 → 404 掩蔽"的正确实现；抽成 helper 时须一并修正其 `owner_user_id` 为空即放行的缺口，并按决策 K 补 school 维度。

### AI-105｜审计写入失败不阻断审批或拒绝流程（P1）

- 目标文件：`app/services/audit_event_service.py:58-66`（`except → rollback → return None`）；`app/api/v1/endpoints/approvals.py:200-241`（先改状态执行、后补审计）。
- 失败测试：人为使审计写入失败后，批准与所有写副作用必须为 **0**；拒绝仍能在可靠介质中找到真实 `resource_id`；恢复后可重放且不重复执行。
- 通过门槛：`AI-GATE` + `DR-05` —— 审计失败时写副作用 0 次。
- 迁移/回滚：无迁移。**可用性代价已由用户确认接受**：审计库故障期间安全关键写入不可用。
- 关闭标准：`log_event` 增加 `strict` 参数；安全关键路径与审计同事务；`approvals.py` 的"先执行后审计"顺序反转。可复用 `app/services/access_control.py:37` 作为全仓 38 处审计写入的唯一收敛入口（已被 `tests/unit/test_deny_audit_entrypoint_gate.py` 锁定为单一入口）——改动集中在两个包装器与 `log_event`。

### DEP-101｜只有开发编排，误用于生产会绕过门禁（P1）

- 目标文件：新增 `docker-compose.production.yml`；`app/core/config.py:80-87` 的 `validate_production()`；`.env.example`；`main.py` 的 `/docs` 开关。
- 失败测试：干净环境缺任一生产必填变量时启动必须失败；默认口令、`latest` 浮动 tag、`DEBUG=true`、模拟回退、错误 CORS 命中 0 次（静态门禁检查）。
- 通过门槛：`DEP-GATE` + `AC-09` / `T-09-E`。
- 迁移/回滚：无迁移。新增文件删除即回退。
- 关闭标准：**受待定 J 阻塞**（现场形态、TLS 终结方未定），J 未答复前**不得关闭**。附带修正：`http://127.0.0.1:55173` 目前全仓只出现在 `AGENTS.md:46`，`config.py:22-27` 默认列表与 compose 覆盖值均不含它——该固定约束现只靠未跟踪的本地 `.env` 维持，须写入代码默认与 `.env.example`。

### DEP-102｜双进程会拆分实时、适配器、审批和幂等状态（P1）

- 目标文件：`r-mos-backend/Dockerfile:15`（`--workers 2` → `--workers 1`）。
- 失败测试：发布前检查脚本断言 worker 数为 1；生产编排不提供 `replicas`。
- 通过门槛：`DEP-GATE` + `AC-03` / `T-03-B` —— 每台机器人同时只有一个控制所有者。
- 迁移/回滚：无迁移。
- 关闭标准：ADR-RUNTIME D1 已把单进程登记为**显式架构约束**并写明解除条件。依据：后端 `app/` 下共 **62 个模块级单例，分布在 61 个文件**，其中至少适配器、WebSocket 连接表、审批、幂等缓存、证据门禁、分析 worker 六类持有请求间共享状态。建议用 `scripts/backend_stress_test.py` 取一次单进程基线，不仅凭推断。

### DEP-103｜容器启动没有迁移和后端就绪门禁（P1）

- 目标文件：`main.py:38-73`（lifespan 无 Alembic）；`app/api/v1/endpoints/health.py:30-85`；新增 `/api/v1/readyz`。
- 失败测试：分别用空库、上一版库、故意缺字段的库启动——前两者按迁移策略成功，缺契约时 `/readyz` 返回 **503** 且不放量；重复执行不产生副作用。
- 通过门槛：`DEP-GATE` + `AC-10` / `DR-06`。
- 迁移/回滚：无迁移。`/readyz` 为新增端点。
- 关闭标准：迁移在 `deploy.sh` 中显式执行并校验，不放进 lifespan。附带修正：`/health` 当前 docstring 写"503: 服务异常"但**从未设置状态码**，`overall_status="unhealthy"` 时仍返回 200——须修正（注意 `docs/testing/TEST_PLAN.md` 的 API-02 当前断言 200，需同步更新）。

### DEP-104｜训练证据未持久化，发布、备份、恢复脚本缺失（P1）

- 目标文件：`app/services/training/workbench_execution_service.py:38`（写 `<backend>/storage/training-evidence`，`docker-compose.yml` 卷列表中不存在该目录）；新增 `scripts/release/{preflight,backup,deploy,rollback,verify}.sh`。
- 失败测试：重建容器后证据 100% 可读且哈希一致；连续三轮发布与回滚结果一致。
- 通过门槛：`DEP-GATE` + `AC-10` / `T-10-N,E`；`DR-01`、`DR-02`。
- 迁移/回滚：证据改走 `get_storage()` 随 ADR-EVID D5；存量本地文件需一次性迁移到对象存储并核对哈希。
- 关闭标准：**受待定 J 阻塞**（备份目标、RTO/RPO 未定）。Phase 4 允许在本地隔离环境做工具可用性演练，**该演练不得记为 DR 通过**；`DR-01`～`DR-06` 的真实演练属 Phase 6，`REL-BLOCK-01` 保持生效。

### DEP-105｜依赖已有高等级告警，生产影响尚未分类（P1）

- 目标文件：`r-mos-frontend/package.json`、`package-lock.json`（只读整理，不改依赖）。
- 失败测试：无（本项在 Phase 4 不产出通过性测试）。
- 通过门槛：`DEP-GATE` —— 生产依赖的 critical/high 可达风险为 0。
- 迁移/回滚：不适用。
- 关闭标准：**分两步**。Phase 4 只做本地准备：整理 dependencies/devDependencies 分界、记录 `lockfileVersion` 与直接依赖树、起草联网核查申请。**Phase 4 不运行 `npm audit`、不外发依赖清单、不执行自动修复。** 在线明细核查须用户明确授权后于 Phase 5 执行；未取得明细前本项**保持未关闭，E1 不得提升**。当前已知：18 个风险（5 moderate、11 high、2 critical），来源为 Phase 1 的 `npm install` 报告。

## 4. 跨项依赖

| 依赖 | 说明 |
|---|---|
| CTRL-101 → AI-101 | 故障注入走审批，需先有 `approvals` 表的通用资源三元组（ADR-AI D1a） |
| AUTH-101 → 全部 | 默认拒绝是所有对象归属校验的前提 |
| AUTH-102 → AUTH-101 | 不先反转边界测试，AUTH-101 无法被证明 |
| EVID-101/104 → EVID-103 | 证据判定依赖服务端内容复核已就位 |
| DEP-104 → EVID-105(D5) | 训练证据持久化依赖存储抽象改造 |
| DEP-101/104 → 待定 J | J 未答复前不得关闭 |
| DEP-105 → 用户联网授权 | 未授权则保持未关闭 |

## 5. Phase 5 逐条核对清单（预留）

Phase 5 对每一项必须记录：代码位置、失败测试、修复提交、通过证据（命令 + 原始输出 + 提交号）、残余风险。本节在 Phase 5 填写，**Phase 2 结束时全部为空**。

E1 提升的充分条件（引自交接文档，不放宽）：29 项全部关闭；六个 GATE 全部取得当前提交证据；不存在 P0/P1 未决项；全量自动测试与必要浏览器流程通过；验收章程要求的 E1 证据齐全。

**即使 E1 提升，E2/E3/E4 仍保持 BLOCKED，`REL-BLOCK-01` 仍生效。**
