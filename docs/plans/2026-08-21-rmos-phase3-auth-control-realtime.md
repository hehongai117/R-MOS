# R-MOS Phase 3 执行计划：身份、控制与实时通道

- 版本：0.1.0
- 日期：2026-08-21
- 状态：Planned（**Phase 2 产物；进入 Phase 3 需用户另行批准**）
- 范围：`AUTH-101`～`AUTH-105`、`CTRL-101`～`CTRL-105`、`RT-101`～`RT-104`（共 14 项）
- 依据：`docs/audit/2026-08-21-phase2-remediation-matrix-v0.1.0.md`、ADR-AUTHN、ADR-ROBOT
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`

## 0. 进入条件（全部满足才能开工）

1. ✅ **已满足**（2026-08-21）：ADR-AUTHN 与 ADR-ROBOT 状态均为 Accepted。
2. ✅ **已满足**（2026-08-21）：公开路由白名单已由用户确认，共 6 条；机器人已发布资产明确排除，须另行单独审批。
3. ⬜ **未满足**：用户明确批准 Phase 3 的权限、数据结构与控制边界实现。**这是独立于 ADR 确认的第二道门，尚未取得——不得据"ADR 已 Accepted"自行开工。**
4. 从已确认的 Phase 2 最终提交建立独立工作区与分支。
5. 现场核对 Python 环境（`/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv`），输出 Read-first Checkpoint。

## 1. 纪律（每批都适用）

- **先写失败测试，再最小实现。** 每批第一个提交只含测试，且必须能看到它是红的；实现在后续提交。
- 每批结束输出：`git diff --name-only`、关键差异片段、可复制命令、真实结果摘要，并追加 `docs-archive/DEVELOPMENT_LOG.md` 的八字段记录。
- 每次后端全量测试后检查并恢复 `r-mos-backend/data/knowledge_store.json`（会被测试改写生成编号与时间）。
- 只对实际运行的范围下结论；跑定向测试就只说定向结论，**不得外推为全量回归或链路通过**。
- 模拟器验证不得写成真机停止或五机隔离通过。**本阶段禁止 AI 直接真机动作，禁止连接真机。**
- 不得未经许可 `git push`。

## 2. 测试基建（先做，避免第 15 份复制粘贴）

**现状（已实测）：** 后端 `tests/` 下 118 个 `test_*.py`、约 709 个测试函数。`pytest.ini` 只有 11 行，注册 3 个 marker（`e2e` / `characterization` / `regression`），无 `asyncio_mode`。conftest 共 3 个。

**严重重复：** `_build_client` 在 11 个文件各有一份、`_register_and_login` 在 14 个文件各一份、`_grant_role_permissions` 在 5 个文件各一份。

**批次 0（前置，约半天）：** 把下列既有实现上提到 `tests/conftest.py`，不新建框架：

| 上提对象 | 现址 | 用途 |
|---|---|---|
| `e2e_env` | `tests/e2e/conftest.py:34-69` | 唯一"真 app + 真 DB + 真 HTTP"环境，支持 `TEST_DATABASE_URL` 切 sqlite/PG |
| `register_and_login` | `tests/e2e/helpers.py:16-53` | 造用户 + 拿真令牌；`role="student"` 会自动补一位同校教师 |
| `auth_boundary_env` | `tests/unit/test_auth_boundary.py:79-107` | 全仓唯一 `scope="module"` 的 TestClient fixture，适合上百条参数化 |
| `_grant_role_permissions` | `tests/unit/test_auth_boundary.py:131-183` | 幂等造 Role/Permission/RolePermission/UserRole |
| `E2E_SCHOOL_NAME` | `tests/e2e/helpers.py:13` | 唯一种子学校名；已在 3 个文件被硬编码复制 |

**架构门禁范式：** `tests/unit/test_deny_audit_entrypoint_gate.py:30` 已是"用 pytest 锁定架构不变量（ALLOWLIST + 正则）"的现成范式。Phase 3 需要的静态门禁（如"除白名单外不得出现身份头读取"）照抄该文件结构即可，**不引入新框架**。

> 批次 0 是纯机械重构，**适合交 Codex**：给定"把这 5 个对象上提到 conftest，删除 30 份副本，全量测试保持绿"，无判断空间。

## 3. 六个批次

### P3-1｜默认拒绝与公开白名单门禁

**覆盖：** AUTH-101（P0）、AUTH-102

**先写的失败测试**
- `tests/unit/test_auth_boundary.py` 反转：`_collect_protected_endpoints`（60-76 行，当前 `if not _has_auth_dependency(...): continue` 跳过无认证路由）改为 `_collect_must_auth_endpoints`——遍历 `/api/v1` 全部 `APIRoute`，不在白名单者一律进入矩阵，断言 (a) 依赖树含 `get_current_actor` 或被网关覆盖，(b) 无令牌返回 401。
- `_has_auth_dependency`（29-32 行）与 `_sample_path`（35-57 行）**原样复用，不重写**——前者已能穿透 `require_permission` 返回的 `_dependency`。
- 门禁自检用例：临时把一条非公开路由移出白名单管辖时该测试必须失败。

**实现**
- 新增 `app/core/public_routes.py`（显式 `(method, route_template_path)` 集合）。
- 新增 `enforce_authenticated` 依赖，在 `main.py:336` 一处挂到 `api_router`。
- `app/services/authz_guard.py:52` 的 `get_current_actor` 增加 `request: Request` 与请求级缓存（约 4 行），避免网关与端点重复查库。

**通过条件（AUTH-GATE 第一部分）**
- 匿名访问非白名单路由成功 **0 次**。
- 白名单文件内容与用户签字版逐条一致。
- 后端全量绿。

**预期红→绿的既有测试：** 大量无令牌调用的用例会变红，本批只修 `test_auth_boundary.py` 自身；其余留到 P3-2 统一改。**因此 P3-1 结束时后端全量允许非绿，但必须逐条列出红的用例与原因**，不得声称通过。

### P3-2｜服务端身份、对象归属与拒绝审计

**覆盖：** AUTH-104，以及 AUTH-101 的对象归属部分

**先写的失败测试**
- 携带合法学生令牌但伪造 `X-RMOS-Role: teacher` → 仍按学生范围。
- **省略角色头** → 不得放宽范围（当前 `teaching_roster.py:159,282` 写成 `if x_rmos_role and ...`，省略即绕过）。
- 审计 `actor_user_id` 恒等于令牌主体。
- 跨学生、跨教师、跨班、跨校读取 → 404 且审计含真实 `resource_id`；跨对象写入 → 403 且同样审计。

**实现**
- `teaching_roster.py` 的 10 处 `Header(alias=...)` 全部替换为 `actor: ActorContext = Depends(get_current_actor)`。
- `app/services/access_control.py:20-24` 的 `_extract_actor_user_id` 删除头兜底，改从 `request.state.actor` 取。
- `ActorContext`（`authz_guard.py:27-34`）增加 `school_name: str | None`；`get_current_actor` 已在查 `User`，取值零额外查询。
- 角色判断改为白名单式：只有显式命中允许角色才放行。
- 对象归属拒绝一律走已有的 `raise_read_access_denied` / `raise_write_access_denied`。

**同批必须完成的测试改写（51 处）**
`tests/unit/test_teaching_characterization.py`（29）、`test_attempt_replay_api.py`（8）、`test_evidence_cards_api.py`（6）、`test_teaching_api.py`（4）、`test_api_teaching.py`（3）、`tests/e2e/test_e2e_cross_role_access.py`（1）改为携带真实令牌。`scripts/run_gate2_smoke.sh:126,134` 改为先登录取令牌。

> 51 处测试改写是机械工作，**适合交 Codex**：门禁语义由本批的新测试定义，Codex 只负责把旧用例从"发头"改成"发令牌"并保持断言语义。

**通过条件（AUTH-GATE 第二部分）**
- 伪造/省略身份头改变授权结果 **0 次**。
- 生产代码中 `X-RMOS-Role` / `X-User-ID` 读取点为 **0**（用架构门禁测试静态断言）。
- 跨对象拒绝 100% 落真实 `resource_id` 审计。
- **后端全量必须绿**（P3-1 遗留的红在本批清零）。

### P3-3｜资产边界与登录限流

**覆盖：** AUTH-103、AUTH-105

**先写的失败测试**
- 匿名请求私有/草稿/其他教师/其他学校机器人的资产清单与文件 → 404；资产清单响应中不得出现存储路径字段。
- 匿名可读取明确发布（`status=READY` 且 `visibility=public`）的资产。
- 同一账号连续 5 次错误密码后第 6 次返回受限状态并写审计；15 分钟窗口结束后恢复；锁定期内正确密码同样被拒；成功登录清零计数。
- **`AUTH-SCHOOLS-PII`**：匿名请求 `GET /api/v1/schools/{school_name}/teachers` 返回的 `email` 必须全部为脱敏形式；完整邮箱只对已认证且有权的调用者可见。

**实现**
- `robots.py:498,516,543` 拆成私有（认证 + 归属）与公开发布（不可猜测标识 + 状态校验）两条路径。可用字段：`robot_models.owner_teacher_id` / `visibility` / `status`（`app/models/robot_model.py:27-40`）。
- `auth.py:197-262` 增加按 `(账号, 来源 IP)` 的进程内 TTL 计数。**不引入 Redis**（与 ADR-RUNTIME D1 单进程一致）。
- `app/api/v1/endpoints/schools.py:30-53` 对 `email` 做服务端脱敏（保留首字符与域名）。该路由与 `GET /api/v1/schools` 同为白名单公开路由，注册流程必需（`RegisterPage.tsx:11`；`src/api/schools.ts:19,25` 用裸 axios，天然不带令牌）。

**通过条件**
- `AUTH-GATE` 全部满足；对应 `AC-06` / `T-06-E` 的"越权成功 0 次、404 率 100%、审计率 100%"。
- 后端全量 + 前端全量 + 前端构建全绿。
- **浏览器主流程复验**：前端 `src/api/client.ts:60-68` 已挂 Bearer 令牌且已实现 401 刷新，预期无需改造，但必须实际跑一次登录 → SOP → 任务 → 报告确认。

### P3-4｜机器人绑定、适配器隔离与现场检查

**覆盖：** CTRL-101、CTRL-102、CTRL-103

**先写的失败测试**
- 两台机器人并行执行时，命令、快照、事件、报告只出现各自 `robot_model_id`；跨机器人访问与订阅被拒绝。
- 任务创建后修改 `robot_model_id` 被拒绝。
- 前检查六种情形各自 BLOCK：缺机器人 / 离线 / 被占用 / 维护中 / 工具状态未知 / 缺工具。
- 不带 `user_id` 的创建请求也必须执行前检查（当前 `tasks.py:37` 把整段包在 `if request.user_id:` 内）。
- 匿名与学生注入故障 → 拒绝 + 审计；教师对非授权机器人 → 拒绝。

**实现**
- Alembic 迁移（`down_revision = "20260817_sop_three_phase"`）：`tasks` / `task_executions` / `snapshots` 加 `robot_model_id` + `tasks.is_legacy_robot_binding`；同一迁移收紧 `tasks.user_id`。回填口径见 ADR-ROBOT 迁移策略。**执行前必须核对 `SELECT id, brand, model_name FROM robot_models WHERE id=1` 确为 ATOM-01。**
- `AdapterFactory` 改为按 `robot_model_id` 键控注册表（`_instance` → `_instances: dict[int, ...]`），双重检查锁定结构保留。
- `preflight_check.py:193-200,228-237,276-315` 三处放行改 BLOCK。
- `tasks.py:42-50` 删除 `robot_id = None` 硬编码，从 `sops.robot_model_id` 推导。
- `adapter.py:50,74` 路径加 `robot_model_id`，接认证 + 角色 + 归属 + 审批 + 审计。

**依赖：** CTRL-101 的审批部分需要 ADR-AI D1a 的 `approvals` 表通用资源三元组。若 Phase 4 尚未落地，本批 CTRL-101 只完成认证 + 归属 + 审计，**审批部分明确标为未完成，不得关闭该项**。

**通过条件（CTRL-GATE 第一部分）**
- 跨机器人命令/快照/报告 **0 条**。
- 缺状态默认阻断；`settings.DEFAULT_ROBOT_MODEL_ID` 在业务路径读取点为 0。
- 迁移升级与 `alembic downgrade -1` 回滚各跑一次并核对回填计数。
- `tests/unit/test_preflight_check.py` 中"缺 robot_id 仍 PASS"的特征化用例已改写为 BLOCK。

### P3-5｜停止通道与并发复现

**覆盖：** CTRL-104、CTRL-105

**先写的失败测试**
- 进行中与暂停任务均可停止；重复请求幂等、不产生重复动作；无权/跨机器人停止被拒绝并审计；终态任务返回当前状态而非报错。
- **CTRL-105 复现测试（先取事实）：** 同一任务同一步骤并发提交 **20 轮 × 5 并发**，每轮检查 `events` 表、`snapshots` 表、`tasks.current_step_index` 三处唯一性。

**实现**
- 新增 `POST /api/v1/tasks/{task_id}/cancel`，独立于步骤流。`TaskStatus.CANCELLED`（`app/models/task.py:27`）已定义，直接用。
- CTRL-105 **视复现结果决定**：复现则在 `task_service.py:93-304` 的提交事务内加行锁或乐观版本列 + `(task_id, step_index)` 唯一约束 + 幂等键；未复现则保留测试作为回归网。

**通过条件（CTRL-GATE 第二部分）**
- 教师确认的软件停止 100% 可用；自动重发 0 次。
- CTRL-105 取得可复现事实**或**完成上述预定门槛的专项测试并保留结果。
- **CTRL-105 未复现 ≠ 已修复。** 是否以"未复现、风险接受"关闭，由 Phase 5 报用户裁决；本阶段只交付事实。
- **软件停止不替代物理急停。** `DR-03` 的真机部分属 E3/Phase 6。

### P3-6｜WebSocket 认证与隔离

**覆盖：** RT-101、RT-102、RT-103、RT-104

**先写的失败测试**
- 匿名 / 过期令牌 / 无权机器人连接被拒绝并审计。
- 两台机器人 + 两个用户并行推送时，跨机器人、跨用户消息 **0 条**。
- 用可控时钟连续运行超过四个心跳周期：有效 pong 保持健康与持续 5 Hz 推送；缺失 pong 才按阈值关闭；断开后连接与后台任务均清理。
- 对 ping 与 telemetry 时间执行严格 RFC 3339 解析、往返与时序断言；双后缀（`...+00:00Z`）输入必须失败。
- 前端：同一组件内依次切换两个 `robotId`，旧连接关闭一次、新连接地址正确、旧连接后续消息不再更新页面。

**实现**
- `websocket.py:13-34` 增加认证与订阅授权。**令牌走连接后首帧**（`{"type":"auth","token":"..."}`，5 秒超时即断开），**不走查询参数**——查询参数会把令牌写进访问日志、代理日志与浏览器历史。认证通过前不推送任何遥测。
- 下线 `/ws/robot/status`（无 `robot_id`，天然无法隔离），**不设并存期**。前端 `useWebSocket.ts:112-113` 已在 `robotId` 存在时走带 id 的地址，只需把 `robotId` 变必填并删掉 113 行的回退分支；`ws-probe.mjs:33` 的默认 `WS_URL` 同批改掉。经取证，这两处是仅有的消费方。
- 调用已存在但从未被调用的 `ConnectionManager.handle_client_message`（`websocket_manager.py:82-137`）。
- 连接表按 `robot_model_id` 分组；`broadcast_to_channel`（195-207）与 `send_to_user`（209-223）的"目前简化为向所有连接广播"改为真实映射。
- 时间戳由消息模型统一序列化（修 `websocket_manager.py:109,149-152`）。
- 前端 `useWebSocket.ts:200-203` 的空依赖数组改为显式依赖 `robotId`。

**通过条件（RT-GATE）**
- 匿名连接 **0 次**；跨订阅消息 **0 条**；四个心跳周期持续健康；时间 100% 严格可解析；切换机器人有自动测试覆盖。
- 对应 `AC-07` / `T-07-N,E` 的软件侧；**72 小时五台真机连续运行属 E3/Phase 6，本阶段不涉及**。

## 4. Phase 3 完成条件

1. 本阶段 14 项中，除 `CTRL-105` 的最终风险裁决外，定向门禁全部通过。
2. `CTRL-105` 已取得可复现事实，或已完成 Phase 2 预定义的 20×5 专项测试并保留结果。
3. 后端全量、前端全量、前端构建通过；无测试副作用残留（含 `knowledge_store.json`）。
4. 迁移升级与回滚各演练一次并记录。
5. `docs/testing/TEST_REPORT.md` 与 `docs-archive/DEVELOPMENT_LOG.md` 同步。
6. **E1 仍为 FAIL**，等待 Phase 4 与 Phase 5 收口。E2/E3/E4 保持 BLOCKED，`REL-BLOCK-01` 保持生效。

## 5. 分工建议

| 类型 | 承担方 | 说明 |
|---|---|---|
| 失败测试的定义与编写 | Claude | 门禁语义藏在断言里，不外包 |
| 白名单草案与安全边界判断 | Claude → 用户签字 | |
| 架构决策、ADR 变更 | Claude | |
| 批次 0 的 conftest 上提与去重（约 30 份副本） | **Codex** | 纯机械，验收标准是"全量保持绿" |
| P3-2 的 51 处测试改写（发头 → 发令牌） | **Codex** | 断言语义不变，只换认证方式 |
| Alembic 迁移脚本样板 | **Codex** | 回填逻辑由 Claude 指定 |
| PASS/FAIL 裁决、TEST_REPORT 回填 | Claude | 不外包 |
| diff 复核 | Claude | 不外包 |

交给 Codex 的任务一律采用"这些测试现在是红的，把它们变绿，不准改测试断言"的形式。
