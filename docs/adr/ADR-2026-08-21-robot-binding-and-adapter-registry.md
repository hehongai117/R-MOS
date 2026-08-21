# ADR-2026-08-21：机器人不可变绑定与适配器隔离

- 状态：Proposed（待用户确认存量回填口径后转 Accepted）
- 覆盖发现：`CTRL-101`、`CTRL-102`、`CTRL-103`、`CTRL-104`、`CTRL-105`，以及 `RT-101`/`RT-104` 的机器人隔离面
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md` 的 G2、G5
- 落地阶段：Phase 3（本 ADR 不改代码）

## 背景

单校五台机器人的交付前提是"任务、命令、快照、遥测、报告不串线"。当前实现无法证明这一点：

**数据链没有机器人维度。**

- `app/models/task.py:38-82`：`tasks` 表有 `sop_id`、`assignment_id`、`guidance_policy_id`、`user_id`，**没有 `robot_id`**；且 `user_id = Column(Integer, nullable=True)`（66 行）既无外键也可为空。
- `app/models/task_execution.py:11-22`：`task_executions` 有 `student_id`（非空、索引），**没有 `robot_id`**。
- `app/models/snapshot.py:17-33`：`snapshots` 有 `task_id`、`step_index`、`adapter_type`（字符串），**没有 `robot_id`**。
- 正向事实：`app/models/sop.py:27` 的 `sops` 表**已有 `robot_model_id`**——机器人绑定的权威来源已经存在，只是没有沿任务链传递下去。

**适配器是全局单例，接口层就没有机器人参数。**

`app/adapters/factory.py:44-108` 的 `AdapterFactory._instance` 是类变量单例，`get_adapter()` **不接受任何参数**，配置从 `settings.DEFAULT_ROBOT_MODEL_ID`（`app/core/config.py:46`，默认 `1`）读取。`adapter_type == "gazebo"` 与 `"real"` 均直接 `raise NotImplementedError`。因此当前已确认的是"共享同一个模拟适配器状态"，**尚不能外推为已能控制真机**。

**控制写入口无认证、无审批、无审计。**

`app/api/v1/endpoints/adapter.py:50` 的 `POST /adapter/inject-fault`、`:74` 的 `DELETE /adapter/fault/{fault_code}` 直接调用工厂单例，函数签名只有请求体与 `db`。

**执行前检查在关键输入缺失时放行。**

- `app/api/v1/endpoints/tasks.py:42-50`：`create_task` 里 `robot_id = None` 是**硬编码**的；且整段前检查包在 `if request.user_id:` 之内——请求不带 `user_id` 时**完全不执行前检查**。
- `app/services/preflight_check.py:193-200`：`if not robot_id: return CheckResult(status=PASS, message="未指定设备，跳过设备检查")`。
- 同文件 228-237：设备检查虽然会查 incidents 表，但最终 PASS 分支把 `online: True`、`locked: False`、`maintenance_mode: False` 直接写死，**从未读取适配器实时状态或设备锁**。
- 同文件 288-315：工具短缺判断的前提是 `if required_tools and isinstance(available_tools, list)`；调用方未提供 `available_tools` 时直接落到 PASS 分支并返回 `message="所需工具全部可用"`，即使 SOP 的 `tools_required` 非空。

**没有统一停止通道。**

`app/models/task.py:27` 定义了 `TaskStatus.CANCELLED`，但 `tasks.py` 的 9 个路由只有开始、步骤、暂停、恢复。`cancel_task` / `stop_task` / `emergency_stop` 在应用路由与服务层无实际停止路径，`emergency_stop` 只存在于模拟执行器与模拟适配器内部。

**并发步骤提交无保护（CTRL-105，推断）。**

`app/services/task_service.py:93-304` 读取 `current_step_index` 后创建事件与快照，最后才更新并提交；未见行锁、版本号、幂等键或唯一约束。当前**没有并发测试**，因此不登记为已复现事实。

## 决策

### D1：任务链建立不可变机器人绑定

`tasks`、`task_executions`、`snapshots` 三张表各增加 `robot_model_id`（Integer，外键指向 `robot_models.id`，`ondelete="RESTRICT"`，建索引）。

- **写入时机：** `create_task` 从 `sops.robot_model_id` 推导（SOP 已带该字段），推导不出则拒绝创建，**不再默认 `DEFAULT_ROBOT_MODEL_ID`**。
- **不可变：** 创建后禁止修改，在服务层拒绝并写审计；不依赖数据库触发器。
- `task_executions.robot_model_id` 与 `snapshots.robot_model_id` 从所属 Task 继承，写入时校验一致。
- `snapshots.adapter_type` 保留（描述适配器实现），新字段描述目标机器人，两者不重合。

### D2：适配器按机器人隔离

`AdapterFactory` 从"单实例 + 无参 `get_adapter()`"改为"按 `robot_model_id` 键控的注册表"：

```python
async def get_adapter(cls, robot_model_id: int) -> BaseRobotAdapter
async def close_adapter(cls, robot_model_id: int | None = None) -> None
```

- 每个 `robot_model_id` 一个实例、一把锁、一份连接状态；同一台机器人**同时只有一个控制所有者**。
- 现有双重检查锁定结构保留，只把 `_instance` 换成 `_instances: dict[int, BaseRobotAdapter]`。
- `_load_joint_names_from_manifest(robot_id)` 已经接受 `robot_id` 参数（`factory.py:17`），无需改造。
- `settings.DEFAULT_ROBOT_MODEL_ID` 仅保留给启动自检与开发脚本，**业务路径不得再读它**。
- Gazebo / real 分支继续 `NotImplementedError`。本 ADR 不实现真机适配器。

调用方同步改造：`app/api/v1/endpoints/health.py:44`（改为对已登记机器人逐台检查或只做存活探针）、`app/services/websocket_manager.py:143`（见 D5）、`app/services/snapshot_service.py`、`app/api/v1/endpoints/adapter.py`。

### D3：控制写入口纳入认证、归属、审批与审计

`adapter.py` 的故障注入与清除：

- 路径改为携带机器人：`POST /adapter/{robot_model_id}/inject-fault`、`DELETE /adapter/{robot_model_id}/fault/{fault_code}`。
- 要求认证 + 教师或管理员角色 + 目标机器人归属（`robot_models.owner_teacher_id` 或 `teacher_robot_bindings`）。
- 风险等级不低于 medium，走审批（见 ADR-ai-approval），命令、审批、执行、审计共用同一 `trace_id`。
- 模拟故障注入与生产入口隔离：`ROBOT_MODE=physical` 时该入口默认关闭。

### D4：执行前检查默认阻断

- `create_task` 删除 `robot_id = None` 硬编码，改为从 SOP 推导；前检查**无条件执行**，不再依赖 `request.user_id` 是否存在（操作者改由 D1 of ADR-authn 的 `ActorContext` 提供）。
- `preflight_check.py:193-200`：缺 `robot_id` 从 PASS 改为 **BLOCK**。
- 设备检查读取该机器人适配器的实时状态与设备锁；状态未知、超时、离线、被占用、维护中一律 BLOCK，**不得**再写死 `online/locked/maintenance_mode`。
- 工具检查：`available_tools` 不是列表（即库存未知）时，若 SOP 声明了 `tools_required` 则 BLOCK，消息为"工具状态未知"，**不得**返回"所需工具全部可用"。
- 检查结果绑定到 (task, robot_model_id) 并设置短时有效期，过期需重检。

### D5：遥测与实时通道按机器人隔离

`app/services/websocket_manager.py` 的连接表从全局集合改为按 `robot_model_id` 分组；`_push_telemetry`（139-175 行）改为对每台已订阅机器人分别取适配器并推送；`broadcast_to_channel`（195-207 行）与 `send_to_user`（209-223 行）当前带注释"目前简化为向所有连接广播"，改为真实的 channel / user 映射。

`app/api/v1/endpoints/websocket.py:13-34` 的 `_handle_websocket` 增加握手认证与订阅授权：

- 令牌通过查询参数传递（浏览器原生 `WebSocket` 无法设置请求头，`r-mos-frontend/src/hooks/useWebSocket.ts` 使用原生 API），服务端校验后立即建立连接上下文；令牌不得写入访问日志。
- 无令牌、令牌失效、目标机器人无权订阅 → 拒绝握手并写审计。
- 向后兼容路由 `/ws/robot/status`（不带 `robot_id`）**下线**：它天然无法做机器人隔离。前端改用 `/ws/robot/{robot_id}/status`。
- 客户端消息交给已存在但从未被调用的 `ConnectionManager.handle_client_message`（`websocket_manager.py:82-137`），使 `last_pong` 生效（RT-102）。
- 时间戳统一：`websocket_manager.py:109,149-152` 当前对已含 `+00:00` 的时间再追加 `"Z"`，产生 `...+00:00Z`。改为由消息模型负责序列化，只输出一种 UTC 形式（RT-103）。
- 前端 `useWebSocket.ts:200-203` 的空依赖数组 effect 改为显式依赖 `robotId`，切换时先清理旧重连定时器与旧连接（RT-104）。

### D6：统一停止通道

新增 `POST /api/v1/tasks/{task_id}/cancel`，独立于普通步骤流：

- 认证 + 角色 + 任务归属 + 机器人归属校验。
- 幂等：重复请求不产生重复动作，已处于终态时返回当前状态而非报错。
- 状态流转 `PENDING/IN_PROGRESS/PAUSED → CANCELLED`（`task.py:11-27` 已定义该枚举与流转规则）。
- 调用对应机器人适配器的停止能力；失败、超时按明确策略升级并写审计。
- **软件停止不替代物理急停。** 真机场景的现场急停验证属于 E3，不在 Phase 3 范围。

### D7：并发步骤提交先取事实再修复

Phase 3 先写并发复现测试，**不预先假定 CTRL-105 成立**：

- 复现门槛：对同一任务同一步骤并发提交 **20 轮 × 5 并发**，每轮检查 `events` 表、`snapshots` 表、`tasks.current_step_index` 三处唯一性。
- 若复现：在 `task_service.py` 的步骤提交事务内对任务行加锁（`SELECT ... FOR UPDATE`）或引入乐观版本列，并对 `(task_id, step_index)` 建唯一约束 + 幂等键。
- 若未复现：按上述门槛记录"未复现"，保留测试作为回归网，**不得**写成"已修复"。是否以"未复现、风险接受"关闭由 Phase 5 报用户裁决。

## 备选

1. **只在 `tasks` 加 `robot_id`，`snapshots` 通过 join 取。** 少一列，但快照是证据链的一环，join 依赖 `tasks` 行不被改动；一旦任务被改或软删，历史快照无法独立证明来自哪台机器人。放弃。
2. **适配器保持单例，靠调用方传 `robot_id` 过滤。** 无法保证"同一台机器人只有一个控制所有者"，也无法隔离连接状态。放弃。
3. **停止通道复用 `PATCH /tasks/{id}` 改状态。** 停止是安全动作，需要独立的权限、幂等、超时与审计语义，混进通用更新会被普通业务权限覆盖。放弃。
4. **先修 CTRL-105 再复现。** 违反"先取事实"的纪律，且无法证明修复有效。放弃。

## 影响

- **数据结构：** 三张表各加一列 + 索引 + 外键；`tasks.user_id` 的收紧（见 ADR-authn D3）合并进同一迁移。
- **接口：** `adapter.py` 两个路径变更（含 `robot_model_id`）；新增 `POST /tasks/{id}/cancel`；WebSocket 下线 `/ws/robot/status`。属于对外契约变更，前端 `useWebSocket.ts` 与监控页需同步。
- **测试：** `tests/unit/test_preflight_check.py`、`tests/unit/test_mock_adapter.py`、`tests/test_robot_service.py`、`tests/unit/test_task_service.py` 中断言"缺 robot_id 仍 PASS"的用例属于特征化测试，必须改写为 BLOCK 断言。
- **性能：** 每台机器人一个适配器实例与一条推送循环。五台规模下可忽略。
- **不影响：** 证据模型、AI 策略、SOP 内容。

## 迁移策略

单个 Alembic 迁移，`down_revision = "20260817_sop_three_phase"`（当前唯一 head，共 38 个 revision）：

1. 三张表 `add_column("robot_model_id", Integer, nullable=True)`。
2. 数据回填：
   - `tasks`：能从 `sops.robot_model_id` 推导的按 SOP 回填；推导不出的（`sop_id IS NULL` 或 SOP 无该字段）回填 `1`（ATOM-01），并在 `tasks` 增加 `is_legacy_robot_binding`（Boolean，默认 false）标记为 true。
   - `task_executions`、`snapshots`：从所属 `tasks` 继承。
3. 改 `nullable=False`，加外键 `ondelete="RESTRICT"` 与索引。
4. 同一迁移内把 `tasks.user_id` 收紧（口径待用户确认，见下）。

`is_legacy_robot_binding` 的作用只是让报告和审计能区分"当时真的绑定了这台机器人"与"迁移时推定的"，**不作为归属校验的豁免开关**。

回填目标 `robot_model_id=1` 的前提是 ATOM-01 确为 id=1；实施前必须在目标库核对 `SELECT id, brand, model_name FROM robot_models WHERE id=1`，不一致则停止迁移。

## 回滚策略

- `alembic downgrade -1` 删除三列与 `is_legacy_robot_binding`。存量业务数据不因回滚丢失（回填值随列一起删除）。
- 适配器注册表、停止通道、前检查阻断、WebSocket 隔离均为代码改动，`git revert` 即可。
- 回滚后系统回到"无机器人绑定"的原状态，**CTRL 链路重新变为 FAIL**，不得因回滚成功而认为风险已关闭。

## 待确认事项（阻塞本 ADR 转 Accepted）

1. **`tasks.user_id` 存量为 NULL 的行如何处理**：回填到系统账号并置 legacy 标记，还是保留可空并在服务层拒绝这类历史任务的新操作。建议前者。
2. **`/ws/robot/status` 下线的时间点**：是否需要一个版本的并存期供外部工具迁移（`r-mos-frontend/scripts/perf/ws-probe.mjs` 使用该地址）。
3. **WebSocket 令牌通过查询参数传递**是否可接受（会进入服务端访问日志，需同步配置日志脱敏）；若不接受，替代方案是连接后首帧发送令牌、超时未认证即断开。
