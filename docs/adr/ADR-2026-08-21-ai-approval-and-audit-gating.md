# ADR-2026-08-21：AI 审批与审计门禁

- 状态：**Accepted**（2026-08-21 用户批准删除 `regression` 标记用例）；**D4 的 critical 多人确认阈值仍待定，见"剩余待定"——该项属 Phase 4，不阻塞 Phase 3**
- 覆盖发现：`AI-101`、`AI-102`、`AI-103`、`AI-104`、`AI-105`
- 上位规则：`AGENTS.md` §7、`docs/testing/ACCEPTANCE_CHARTER.md` 的 G2、G4
- 落地阶段：Phase 4（本 ADR 不改代码）

## 背景

系统里**同时存在两套审批**，一套合规、一套是旁路。

**旁路审批（内存，不合规）：** `app/api/v1/endpoints/agent_governance.py` 的 5 个审批路由，背后是 `app/services/approval_queue.py:55-221` 的进程内单例。该 router 无自身 prefix，经 `agent.py:43` 的 `APIRouter(prefix="/agent")` 与 `main.py:336` 的 `/api/v1` 前缀挂载，完整路径为 `/api/v1/agent/approval/*`。`approval_queue.py:225` 是模块级单例 `approval_queue = ApprovalQueue()`，用两个字典存状态，默认 TTL 3600 秒，无持久化、无 `trace_id`、无 command/tool_call 关联、无对象归属校验、无审计。

- `create_approval_request`（34-51 行）只要求 `require_permission("agent:execute")`，且 `requester_id` **取自请求体**（`app/schemas/agent.py:142-151` 的 `CreateApprovalRequest`）；端点连 `ActorContext` 都没接住（依赖写成 `_: None = Depends(...)`），无从比对。
- `approve_request`（116-132 行）签名为 `(request_id: str, approved_by: str, _: None = Depends(require_permission("agent:execute")))`——`approved_by` 是**客户端查询参数**，所需权限与创建请求**完全相同**，没有教师/管理员要求，没有"审批人不得等于申请人"的检查。
- `ApprovalQueue.approve`（`approval_queue.py:113-140`）只检查状态是否 `PENDING` 与是否过期，**不校验 `approved_by` 身份，也不校验它与 `requester_id` 是否同一人**。
- 该文件内 5 个审批端点**没有任何一处**调用 `log_allow_event` / `log_deny_event`。
- `tests/unit/test_agent_characterization.py:1607-1640` 用同一个普通 `agent_user` 创建并批准请求、`approved_by=admin-001` 由客户端填写，并断言成功。**该测试通过本身就是 AI-101 的动态证据。**
- 能力边界：这套队列没有接 `ApprovalService` 的持久化写工具桩，本审查未证明它当前能触发真实外部副作用；但它对外暴露为审批结果，已足以破坏审批可信度。

**数据库审批（合规基础已具备）：** `app/api/v1/endpoints/approvals.py` 的 4 个 `/ai/approvals/*` 路由 + `app/services/approval_service.py`。

- `grant_approval`（173 行起）用 `decided_by_user_id=actor.user_id`——**主体取自令牌**；`request.state.trace_id` 从审批记录恢复，`log_allow_event` 带 `approval_id`、`skill_id`、`side_effects_applied`。
- `app/models/approval.py:17-27` 已有 `trace_id`、`command_id`、`tool_call_id`、`status`、`created_by_user_id`、`decided_by_user_id`、`decided_at`。**禁止自批所需的两个字段已经存在**，只是没有比较。
- 缺口：无自批检查；无角色要求；`grant → log_allow_event → execute_after_grant` 的顺序使审计失败不阻断执行。

**其余四项缺口：**

- `AI-102`：`app/api/v1/endpoints/agent.py:144-281` 中 `Command.actor_user_id` 取 `request.user_id`（客户端），而工具调用与审计操作者取令牌用户——同一条追踪链会出现两个不同主体；是否创建审批只看客户端提交或最小规划器产生的 `side_effects`；未从技能登记表读取风险等级；`Command.risk_level` 未写入。正向边界：批准后的写执行是 `app/services/tool_executor.py:227-254` 的确定性桩，不访问外部系统。
- `AI-103`：`app/services/policy_matrix.py:212-221` 对无匹配规则的动作返回 `allowed=True, risk_level=R0, requires_approval=False, warnings=["No matching policy rule found, default allow"]`。`app/services/orchestrator_v2.py:351-433` 只在 `allowed=False` 时停止，`requires_approval=True` 也直接分发模块，不进入等待审批状态。能力边界：当前 Orchestrator V2 模块只生成回答、草稿与建议，未发现直接真机写入。
- `AI-104`：`tool_executor.py:78-95` 只用 UUID 正则校验 `evidence_refs`；187-215 行把客户端 `ref_ids` 直接拼成 `citations` 与 `hits`，不查知识块是否存在或可访问。正向对照：`app/api/v1/endpoints/ai_commands.py:100-153` 的单条引用读取**会查库并校验所有者**——正确实现已经存在，只是没用在工具执行前。
- `AI-105`：`app/services/audit_event_service.py:58-66` 的 `log_event` 捕获全部异常、`rollback()` 后返回 `None`，且所有调用方都不检查返回值。注意它内部执行 `await self.db.commit()`——审计与业务共用同一会话，审计提交会把同事务内的业务写入一并提交。

## 决策

### D1：旁路审批整体下线

删除 `app/services/approval_queue.py` 整文件与 `agent_governance.py` 中的 5 个审批路由。审批只保留数据库一套。

**已实测的爆炸半径：**

| 位置 | 内容 | 处置 |
|---|---|---|
| `app/services/approval_queue.py` | 整文件 226 行，仅被 `agent_governance.py:12` 引用 | 删除 |
| `app/api/v1/endpoints/agent_governance.py:12,34-145` | import + 5 个审批路由 | 删除；**同文件其余 4 个路由（`/evaluation/report` :150-186、`/sop/quality/check` :191-228、`/preference*` :233-304）与审批无关，必须保留，不能整文件删** |
| `app/schemas/agent.py:142-151` | `CreateApprovalRequest` | 删除 |
| `r-mos-frontend/src/api/agent-v2.ts:570-645` | `ApprovalRequest` 接口 + `getPendingApprovals` / `getApprovalHistory` / `approveRequest` / `rejectRequest` 四个函数 | **是死代码**：全仓检索这四个函数名，除定义处外零调用点。直接删除 |
| 后端测试 11 个用例 | 见下 | 见下 |

**前端不需要迁移。** `r-mos-frontend/src/pages/admin/ApprovalQueuePage.tsx:11` 已经 `import ... from '@/api/approvals'`（即 `/ai/approvals/*` 数据库路由），页面第 209 行副标题明确写着"统一切换到 /ai/approvals 真实路由"——这次迁移在更早的批次已经完成。`agent-v2.ts` 里那套只是残留的死代码。

**后端测试影响（11 个用例，跨 3 个文件）：**

| 文件 | 用例数 | 标记 |
|---|---|---|
| `tests/unit/test_agent_characterization.py:1451-1733` | 8 | `characterization`——按 pytest.ini 定义即"锁定现状行为，修 bug 时按新规格更新断言"，可随删除一并移除 |
| `tests/unit/test_agent_authz.py:254,280` | 2 | 断言 `status_code in [200, 403]` 一类宽松条件，可随删除一并移除 |
| `tests/regression/test_p0_bugs_2026_07.py:241` | 1 | **`regression` 标记**——`pytest.ini:11` 定义为"已修复 bug 的回归测试（断言正确行为，**永不放松**）" |

最后一条构成规则冲突：删除旁路审批就必须删掉一个被项目自身标记为"永不放松"的回归测试。**用户已于 2026-08-21 批准删除**，处理方式见"决议与剩余待定"。

### D1a：删除前必须补齐数据库审批的能力缺口

内存那套有、数据库那套**没有**的能力（若不补，删除即为功能倒退）：

| 能力 | 内存实现 | 数据库现状 |
|---|---|---|
| 优先级 | `ApprovalPriority` 四级 + 按优先级排序（`approval_queue.py:27-32,165-182`） | `approvals` 表无 `priority` 列 |
| 过期 | `expires_at` + `check_expirations()`（`approval_queue.py:101,206-221`），默认 TTL 3600s | 无 `expires_at`，无过期状态 |
| **通用资源审批** | `resource_type` / `resource_id` / `action` 三元组，任意资源可提审批（`approval_queue.py:39-42`） | **只能绑 `command_id` + `tool_call_id`**，非 Command 类资源无法提审批 |
| 证据引用 | `evidence_refs` 列表 | 无 |

第三项是硬阻塞：**ADR-robot-binding D3 要求故障注入等机器人控制写入口走审批，而那不是一次 AI Command。** 因此 `approvals` 表必须增加 `resource_type`（String）、`resource_id`（String）、`action`（String）、`priority`（String，默认 `normal`）、`expires_at`（TZDateTime，可空）五列，并把 `command_id` / `tool_call_id` 从 `nullable=False` 放开为可空（二者与 `resource_type/resource_id` 至少一组非空，由服务层约束）。过期检查在读取审批时惰性判定，不引入后台定时任务。

这使本 ADR **带一个 Alembic 迁移**，见"迁移策略"。

**另注：仓库里还有第三套、完全没被使用的审批持久化模型**——`app/models/agent_runtime.py:91-113` 的 `ApprovalRecordDB`（表 `approval_records`）与 `:63-88` 的 `DecisionRecordDB`（表 `decision_records`），由 `alembic/versions/20260304_2100_add_agent_runtime_state.py` 建表。它们的字段（`priority`、`requested_by`、`resolved_by`、`risk_level`、`requires_approval`、`approval_level`）恰好覆盖上表缺口。Phase 4 需先判定：是扩展 `approvals` 表（本决策），还是改用这两张已存在的空表。**建议扩展 `approvals`**——它才是唯一有活跃读写路径与前端页面的表；`approval_records` / `decision_records` 属于死表，应在同一批次删除，否则三套并存会让下一个接手的人重蹈覆辙。

### D2：未知动作默认拒绝

`policy_matrix.py:212-221` 的默认分支改为 `allowed=False`，理由 `no_matching_policy_rule`，并写审计。放行必须来自显式规则。

`orchestrator_v2.py:351-433` 的门禁改为：`allowed=False` → 停止；`requires_approval=True` → **持久化命令并进入等待审批状态，不分发模块**；只有绑定的有效审批（状态 `granted`、未过期、`approval.command_id` 匹配）才能继续。规划与执行使用不同动作类型与权限（`orchestrator_v2.py:124-128` 把 `execute-task` 映射为只读 `plan-task` 的做法保留，但两者的策略规则必须分别登记）。

### D3：操作者与风险等级只由服务端决定

- `agent.py` 的 `Command.actor_user_id` 改为取 `ActorContext.user_id`，**不再读 `request.user_id`**；客户端传入的 `user_id` 忽略并在审计的 `request_meta` 中记录差异。
- 工具名称必须解析到已发布技能版本；风险等级与副作用声明由服务端技能登记表决定，`Command.risk_level` 必须写入。
- 未知或未发布工具默认拒绝并写审计。
- 任何写工具风险不低于 medium 并强制创建审批，**与客户端是否提交 `side_effects` 无关**。

### D4：禁止自批 + 角色下限

`ApprovalService.grant`（`approval_service.py:56-68`）增加：

- `approval.created_by_user_id == str(actor.user_id)` → 拒绝，理由 `self_approval_forbidden`，写 deny 审计。
- 审批人角色下限为教师；`critical` 级别按对应方案的多人确认要求执行，**不得降级**。
- 已决、已过期、状态已变化的审批不得再次批准（`_transition`，84-119 行内实现）。

`approvals.py:173-278` 的 `grant`/`reject` 端点补上角色守卫，复用 `authz_guard.require_permission(..., required_role=...)`。

### D5：审计失败阻断业务写入

- `audit_event_service.log_event` 增加 `strict: bool = False` 参数：`strict=True` 时不吞异常，向上抛出。
- 安全关键路径（审批授予/拒绝、写工具执行、控制写入口）一律使用 `strict=True`，与业务写入处于同一事务：审计写不进去，业务写入随之回滚。
- 调整 `approvals.py` 的执行顺序：**先在同一事务内写审计事件，再执行 `execute_after_grant`**；当前"先改状态并执行、后补审计"的顺序必须反转。
- 拒绝路径（`raise_read_access_denied` / `raise_write_access_denied`）不能因审计失败而静默丢失：审计不可用时，拒绝事件降级写入应用日志的独立通道，并计入可观测指标。拒绝本身仍然生效。
- **已知代价：** 审计库故障期间系统对安全关键写入不可用。这是 G4"任意 deny 必须写审计"的必然结果，已由用户确认接受。

### D6：引用必须真实且可访问

`tool_executor.py:187-215` 生成 `citations`/`hits` 前，批量查询引用是否存在并应用对象级访问过滤，复用 `ai_commands.py:100-153` 已有的查询与所有者校验逻辑。不存在或不可访问的引用**不进入结果**（返回空结果或拒绝），不得凭 UUID 格式合法就生成命中项。

`tool_executor.py:78-95` 的 UUID 格式校验保留为前置快速失败，但不再是唯一校验。

### D7：trace_id 全链贯穿

`Command → AIToolCall → Approval → AuditEvent` 四类对象共用同一 `trace_id`。`approvals.py:205` 已在 grant 时从审批记录恢复 `request.state.trace_id`，该模式推广到创建、执行、拒绝与失败路径。Phase 4 的门禁测试须能用一个 `trace_id` 检出完整链路。

## 备选

1. **保留旁路审批但强制它走数据库。** 等于把 `approval_queue` 重写成 `ApprovalService` 的薄包装，多一层无价值的间接；两套 API 并存还会持续产生"该调哪个"的歧义。放弃。
2. **旁路审批只加角色校验，不删。** 无持久化，重启即丢；单进程约束下也无法做真实的多人确认与追溯。放弃。
3. **审计失败只告警不阻断。** 违反 G4，且 AI-105 的复验方法明确要求"人为使审计写入失败，批准和所有写副作用必须为 0"。放弃。
4. **审计使用独立数据库会话以避免与业务事务耦合。** 独立会话意味着审计与业务无法原子，正是当前问题。反向做法是让审计与业务共用事务（D5）；`log_event` 内部的 `commit()` 需相应移除，由调用方事务边界统一提交。
5. **未知动作默认放行但强制审批。** 未知动作的风险等级本身不可知，无法决定审批级别。放弃。

## 影响

- **接口：** 删除 5 个 `/api/v1/agent/approval/*` 路由（对外契约变更，但无活跃客户端）；`/ai/approvals/{id}/grant|reject` 增加角色要求与自批拒绝。
- **前端：** 只删死代码（`agent-v2.ts:570-645`），审批页面无需改动。
- **数据结构：** `Command` 增加/启用 `risk_level` 写入；`approvals` 表现有字段已足够，**无新表**。
- **测试：** `tests/unit/test_agent_characterization.py:1607-1640` 等固化自批行为的用例必须改写为"自批被拒绝"；策略默认放行的用例同理。
- **可用性：** D5 使审计库成为安全关键写入的强依赖。
- **不影响：** 机器人控制语义、证据模型（引用真实性由 D6 与 ADR-evidence 分别覆盖各自范围）。

## 迁移策略

无数据库结构迁移。按批次落地：

1. 先落 D2 + D6（纯策略与查询改造，不动接口契约），此时未知动作被拒、伪引用不再命中。
2. 再落 D3 + D4（身份与自批），同批改写相关特征化测试。
3. 再落 D5（审计阻断）。这是可用性影响最大的一批，须单独提交并单独回归。
4. 最后落 D1（删旁路）。放最后是因为它是唯一的对外契约破坏；单独成一个提交，便于独立回滚。因前端无活跃调用方，不存在"中间状态下审批页面不可用"的风险。

## 回滚策略

- D1～D7 全部为代码改动，无迁移，`git revert` 即可。
- D1 单独成提交，便于在不回退 D2～D7 的前提下单独恢复旁路路由（仅在发现未知外部调用方时才需要）。
- 回滚后 AI 链路重新变为 FAIL。

## 决议与剩余待定

### 已确认决议（2026-08-21）

1. **删除 `regression` 标记用例**：用户已批准。删除 `tests/regression/test_p0_bugs_2026_07.py:241` 的 `test_p0_4_approval_history_returns_records`（测的是旁路审批 history 端点）。**必须在同一提交里于该文件顶部记录"P0#4 所属功能（内存旁路审批）已于本次整体下线，该回归用例随功能一并移除"**，不做无声删除——`pytest.ini:11` 的"永不放松"约定本身保持不变。
2. **审计与业务共用事务**：确认接受一次性排查 `log_event` 的全部调用点（全仓 38 处审计写入收敛于 `access_control.py:37`，实际排查面很小）。移除 `log_event` 内部的 `commit()`，由调用方事务边界统一提交。
3. **审批人角色下限为教师**：采纳为默认。

### 剩余待定（不阻塞 Phase 3，须在 Phase 4 开工前给出）

- **`critical` 级别的多人确认阈值**：是"两名教师"还是"一名管理员"，取决于院校实际审批流程。验收章程 G2 只要求"critical 必须遵守对应方案中更严格的多人确认要求，不得降级"，未给出具体人数。在用户给出阈值前，`critical` 一律按最严格解释处理（拒绝执行并提示需要人工流程），**不得**降级为单人教师确认。
