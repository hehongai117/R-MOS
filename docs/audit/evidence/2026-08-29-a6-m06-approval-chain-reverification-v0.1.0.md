# A6 订正证据：M-06 审批链复验

- 版本：0.1.0
- 日期：2026-08-29
- 用途：支撑 A6 报告 0.1.1 对 M-06 的订正
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 验证等级：**E1**（静态代码读取，无运行时探测）
- 主审：Claude｜异源复核：Codex（见 §6）
- 生产代码改动：**0**

## 1. 订正起因

A6 0.1.0 §3.2 的 M-06 写：

> 审批存在两套并行实现，且**被实际使用的一套用进程内内存队列不落库**

在 A6 提交董事会确认前的接手复验中，逐条核对两套实现的属性，发现该表述**把两套实现的属性写反了**：
用内存队列的那一套恰恰是**零消费者的死代码**，而落库的那一套有完整的生产者、服务层、
规范授权与完整页面。

## 2. 两套实现的逐项对比

| 维度 | `/agent/approval/*` | `/ai/approvals/*` |
|---|---|---|
| 端点定义 | `app/api/v1/endpoints/agent_governance.py:34,54,83,116,135`（5 条） | `app/api/v1/endpoints/approvals.py:46,127,173,280`（4 条） |
| 状态存储 | `app/services/approval_queue.py:225` 的模块级单例 `approval_queue = ApprovalQueue()`，**进程内内存** | `Approval` ORM + `ApprovalService` + `AsyncSession`，**落库** |
| 生产者 | 仅 `POST /approval/request` 端点自身 | `app/api/v1/endpoints/agent.py:262`，`POST /agent/execute` 在 planned tool 带 `side_effects` 时构造 `Approval` 行并置 command 为 `waiting_approval` |
| 服务层 | `ApprovalQueue.create_request/approve/reject`（内存操作） | `ApprovalService.grant/reject/_transition/execute_after_grant/fail_after_reject`，含 `await self.db.commit()`（`:116,158,173`） |
| 前端客户端 | `src/api/agent-v2.ts:591,603,624,640` 共 4 个函数 | `src/api/approvals.ts:25,32,37,42` 共 4 个函数 |
| 页面 | **无** | `src/pages/admin/ApprovalQueuePage.tsx`，功能完整（待审批/已批准/已拒绝三视图 + 拒绝原因提交） |
| 可达性 | 4 个客户端函数**零调用者** | 页面**零 import**；`src/config/routes.ts` 与 `src/config/nav.ts` 无任何 approval 条目 |
| grant/reject 授权 | `approved_by` / `rejection_reason` 由调用方传入 | `Depends(require_permission("approvals:grant"))` + `_ensure_admin_or_auditor(actor)` + `decided_by_user_id=actor.user_id`（**取自认证上下文**） |
| 审计 | 无 | `log_allow_event` / `log_deny_event`，`resource_type="Approval"` |

## 3. 复现命令

```bash
cd <worktree>

# 两套端点定义
grep -rn "approval" r-mos-backend/app/api/v1/endpoints/*.py \
  | grep -E "@router\.(get|post|put|patch|delete)"

# 内存队列宿主
grep -rn "approval_queue" r-mos-backend/app/

# 落库侧的 ORM / service / session
grep -nE "commit|db.add|Approval|select\(|db:" \
  r-mos-backend/app/api/v1/endpoints/approvals.py

# 生产者
grep -rn "Approval(" --include='*.py' r-mos-backend/app/ | grep -vE "class |^\s*#"
# → app/api/v1/endpoints/agent.py:262

# 服务层写方法
grep -nE "def |db.add|commit" r-mos-backend/app/services/approval_service.py

# 前端两套客户端
grep -rn "ai/approvals\|agent/approval" r-mos-frontend/src/

# 页面可达性
grep -rn "ApprovalQueuePage" r-mos-frontend/src/ | grep -v "ApprovalQueuePage.tsx:"
grep -n "approval" r-mos-frontend/src/config/routes.ts r-mos-frontend/src/config/nav.ts

# 死实现的调用者计数
for fn in getPendingApprovals getApprovalHistory approveRequest rejectRequest; do
  printf "%-22s callers: " "$fn"
  grep -rn "\b$fn\b" r-mos-frontend/src/ | grep -v "api/agent-v2.ts" | wc -l
done
# → 四项全部为 0
```

## 4. 订正后的 M-06 表述

> **本节曾有一版错误结论。** 主审初次复验后写的是「唯一断点是页面未注册路由，只差一行路由注册」。
> 异源复核（§6）判定 MISMATCH，主审逐条复验后**确认自己错了**，本节为改写后的版本。
> 错误原因见 §7。

**根因（订正后）：** 审批的持久化设施已建成（表、ORM、服务层、规范授权、审计事件、完整页面），
但**该设施不在真实用户执行路径上**；真实路径把「需要审批」当作**执行之后回填的标记**，
不是执行之前的闸门。另有一套零消费者的内存队列实现未清理。

**受影响实例（订正后，四处断点，逐条已复验）：**

| # | 断点 | 证据 | 后果 |
|---|---|---|---|
| B-1 | **闸门不在执行路径上**：`OrchestratorV2.process_request` 在策略放行后**直接 `_dispatch_module()`**，没有「需审批则停止」分支，`requires_approval` 在分派之后才放入响应 | `app/services/orchestrator_v2.py:361-376` | 高风险动作**先执行、后标记**，人工审批无从介入 |
| B-2 | **持久化链的生产者从未被前端触发**：`Approval` 行只由 `/agent/execute` 的 **command 模式**创建，而前端 `agent-v2.ts:193` 硬编码 `mode:'message'`，全前端**无一处提交 `mode:'command'`** | `agent.py:262`、`agent-v2.ts:193`、全仓 grep `mode:'command'` 结果为空 | `approvals` 表无来源，与该表为空的观察一致 |
| B-3 | **前后端状态名不一致**：前端 `ApprovalStatus = 'pending' \| 'approved' \| 'rejected'`，后端 `_transition` 写入 `target_status="granted"` | `ApprovalQueuePage.tsx:17,23,219` vs `approval_service.py:65` | 即使挂上路由，已批准项也不会出现在「已批准」页签 |
| B-4 | **批准后执行的是桩**：`execute_write_tool_stub` docstring 明写「不触发外部 IO」，返回 `mode:"write_stub"` | `tool_executor.py:227-254` | 「批准即生效」不成立，不能作为真实动作的审批闭环证据 |

**严重度：保持 P0，且理由比 A6 0.1.0 所述更强。**
A6 0.1.0 的定性是「闸门存在但不可达」；实际是**闸门不在执行路径上**。
在运行后果上，后者严格劣于前者。

**处置（订正后）：** §5 MOD-05 **不能降为单纯 REFACTOR**。
持久化设施可复用（不需要重写表与服务层），但必须完成四件事：
把真实用户路径接到持久化审批链（B-1/B-2）、统一状态字面量（B-3）、
用真实执行替换 `write_stub`（B-4）、并删除内存队列死实现。
建议记为 **REFACTOR（设施复用）+ 接线与语义收口（新建工作量）**，
决策点 2「审批保留哪一套」的**保留对象**证据充分（保留持久化侧），
但**「删掉另一套即可完工」的推断不成立**。

## 5. 附带钉死的两条

### 5.1 M-13 已落到代码层

`app/api/v1/endpoints/approvals.py:180` 的 `_ensure_admin_or_auditor(actor)` 在代码中
**明确放行 `auditor` 执行 grant**。A4/A6 原将该职责分离冲突描述为配置层（RBAC 种子）问题；
本次复验确认**代码层同样放行**，迁移
`20260207_2130_9d8c7b6a5e4f_add_approvals_table_and_links.py:129-130` 也把
grant/reject 赋给 admin 与 auditor。M-13 的 P0 定级因此更强，且修复面多一处。

同时：前端 `src/store/authStore.ts:7` 的 `UserRole = 'student' | 'teacher' | 'admin'`
**不含 auditor**。即便后端赋权完整，审计员在前端没有任何界面路径——
与 A1「auditor 0 账号 0 前端入口」一致，但可补充「前端类型系统层面就不承认该角色」这一层。

### 5.2 A6 未覆盖的新发现：M-02 同类第二例

`POST /agent/execute` 已注入 `actor: ActorContext = Depends(get_current_actor)`（`agent.py:148`），
但构造 `Command` 时用的是 **`actor_user_id=request.user_id`**（`agent.py:188`）——
**请求体自带的身份被写入记录作为操作人**。

同一函数内 `Approval` 却用 `created_by_user_id=str(actor.user_id)`（`agent.py:267`），
**同一端点内两种身份来源并存**。

这与 M-02（`force-submit`）是**同一模式、同一严重度**：有认证、有身份，但业务记录取自请求体。
A6 0.1.0 未登记此例。建议并入 M-02 并把 M-02 的根因从「单点缺陷」改写为
**「认证身份与业务身份未强制绑定」的系统性模式**，受影响实例至少 2 处。

> **方法含义：** M-02 之所以被发现是因为异源复核逐个端点读过；
> 任何「是否存在身份依赖」的静态扫描对本例同样会打勾（它确实注入了 `actor`）。
> **应在改造阶段增加一条专项检查：注入了 `actor` 但业务字段取自请求体的端点。**

## 6. 异源复核（Codex）

| 项 | 内容 |
|---|---|
| 方式 | 只读沙箱，工作目录为被审工作区，禁止改动、禁止跑测试、禁止访问主审临时目录 |
| 复核后仓库状态 | `git status` 仅有本证据文件一个未跟踪项，被审仓库零改动 |
| 判定 | 6 条：SUPPORTED 2、MISMATCH 3、PARTIAL 1 |
| 主审处置 | **6 条全部逐条复验后采纳**，其中 3 条 MISMATCH 直接推翻主审初稿结论 |

| 复核判定 | 主审复验 |
|---|---|
| 内存队列是 `/agent/approval/*` 且零消费者 → SUPPORTED | 采纳，见 §2 |
| M-06 保持 P0 → SUPPORTED | 采纳 |
| 「只差一行路由注册」→ **MISMATCH** | **复验成立，主审初稿错误**，已改写为 §4 的四处断点 |
| 「处置降为 REFACTOR」→ **MISMATCH** | **复验成立**，已改写为「设施复用 + 接线与语义收口」 |
| 「A6 说内存队列被实际使用」写反 → MISMATCH（两套都不是实际路径） | 采纳，§4 已改为「设施不在执行路径上」 |
| 数据库链可复用 → PARTIAL | 采纳 |

**复核方另提出 5 条主审未覆盖的问题**，主审复验后 3 条纳入本文件
（§5.1 前端无 auditor 角色、§5.2 `Command` 身份取自请求体、§4 B-4 write_stub），
另 2 条涉及 M-14 的描述错误，登记于 §6.1。

### 6.1 M-14 的两组描述有误（需在 A6 0.1.1 一并订正）

| M-14 分组 | A6 0.1.0 描述 | 复验结果 |
|---|---|---|
| 后端入口 ×2（`main.py` vs `app/main.py`） | 列为「新旧实现并存未收口」 | **误判**。`app/main.py` 全文 5 行，内容为 `from main import app`，docstring 自述「Compatibility module for tests importing `app.main`」。**这是兼容垫片，不是第二套入口实现**，应从 M-14 移除 |
| 知识存储 ×2（表 + 本地 JSON） | 描述为两条路径 | **不完整**。实为至少三条：`data/knowledge_store.json` 治理库、`knowledge_documents` 表、`ai_knowledge_chunks` 表，且无统一迁移链 |

> M-14 共 8 组并存实现，本次只复核了 3 组（后端入口、HTTP 客户端、知识存储），
> 其中 **2 组描述有误、1 组过度简化**。**剩余 5 组（审批×2 已单列、回放×3、证据模型×2、角色存储×3、3D 栈×2）
> 未复核**，按同样比例存在描述错误的风险。这构成 A6 0.1.1 的一项待办，不应默认其正确。

## 7. 方法教训

### 7.1 A6 归并时的错误

A6 归并对 M-06 的两套实现只核到「存在两套 + 两表皆空 + 一套用内存队列」这一层，
**没有把「哪一套用内存」与「哪一套有消费者」这两个属性分别绑定到具体实现上**，
导致两个属性在表述中互换。

> **教训一：** 描述「新旧并存」类问题时，**每个属性都必须单独绑定到具体实现并各自留证**，
> 不能用「其中一套……另一套……」的句式概括。本次复核 M-14 的 3 组，**2 组描述有误**，
> 印证该句式是系统性风险源。

### 7.2 主审本轮的错误

主审发现 A6 属性写反后，**只核到「持久化侧设施齐全」就下了「只差一行路由注册」的结论**，
没有继续追问「这些设施在真实用户路径上会不会被走到」。
异源复核指出后复验，发现真实路径（message 模式）根本不经过审批链。

> **教训二：设施齐全 ≠ 路径接通。**
> 确认某能力「已实现」时，必须从**真实用户入口**正向走到该能力，而不是从能力反向看它有没有依赖齐备。
> 本次的具体形态是：生产者存在（`/agent/execute` command 模式），但**没有任何前端会调用生产者**。

> **教训三：修正别人的错误时，自己同样要接受复核。**
> 主审这次是在订正 A6 的错误，结果订正本身又出了一个方向相同的错误（都是「只看到一层就下结论」）。
> **订正轮不能豁免异源复核。**

## 8. 本文件的处置建议

本文件是 A6 0.1.1 的证据基础。A6 0.1.1 至少需订正：

| # | 订正项 | 依据 |
|---|---|---|
| 1 | M-06 根因、受影响实例、处置（§4） | §2、§4 |
| 2 | §5 MOD-05 由 `REWRITE_MODULE/UNKNOWN` 改为「设施复用 + 接线与语义收口」 | §4 |
| 3 | M-02 受影响实例增加 `agent.py:188`，根因改写为系统性模式 | §5.2 |
| 4 | M-13 补「代码层与迁移层均放行 auditor」「前端类型无 auditor」 | §5.1 |
| 5 | M-14 移除「后端入口 ×2」，知识存储改为三条路径，并登记「剩余 5 组未复核」 | §6.1 |
| 6 | §10 累计数 18/10 → 21/14 + 7 处矛盾（0.1.0 漏计 A6 自身那轮） | 交接文档 §6.3 与 A6 §9 自洽性核对 |
| 7 | 决策点 2 措辞：保留对象证据充分，但「删掉另一套即可完工」不成立 | §4 |

**未决**：M-14 剩余 5 组是否在 0.1.1 内一并复核，取决于董事会对 A6 订正范围的裁定。
