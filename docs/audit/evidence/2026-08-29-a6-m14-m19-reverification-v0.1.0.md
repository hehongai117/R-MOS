# A6 订正证据：M-14 并存实现剩余组 + M-19 单例口径复核

- 版本：0.1.0
- 日期：2026-08-29
- 用途：支撑 A6 报告 0.1.1 对 M-14、M-16、M-19 的订正
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 验证等级：**E1**（静态代码 + AST 机械分析，无运行时探测、无数据库访问）
- 主审：Claude｜异源复核：Codex
- 生产代码改动：**0**

## 1. 起因

对 M-06 的复核（见 `2026-08-29-a6-m06-approval-chain-reverification-v0.1.0.md`）发现
A6 的 M-14「8 组新旧实现并存」中已复核的 3 组里**2 组描述有误、1 组过度简化**。
按该错误比例，剩余组不得默认正确，故对剩余 4 组逐组独立复核。

复核过程中另发现 M-19 的单例口径与 M-16 的根因归属存在问题，一并登记。

## 2. M-14 剩余 4 组复核结果

| 组 | A6 0.1.0 描述 | 判定 | 正确描述 |
|---|---|---|---|
| 回放 ×3 | 「其中一套后端不存在」 | **MISMATCH** | 实为 **4 条**回放路径。0.1.0 与主审初判均漏掉**唯一被活页面调用的那条**。见 §2.1 |
| 证据模型 ×2 | 「两套，一套空」 | **PARTIAL** | 实为 **3 组表 + 1 个进程内存储**，共 4 条路径。见 §2.2 |
| 角色存储 ×3 | 「三处并存」 | **MISMATCH** | 实为 4 处；RBAC 表 **4 张**（0.1.0 只提 3 张）；前端类型与后端角色集合不一致。见 §2.3 |
| 3D 栈 ×2 | 「旧栈 9 文件不可达」 | **PARTIAL** | 9 文件不可达**计数准确**，但「两栈」这个框架不成立：旧文件引用现行组件，且「新栈」内部有 3 条在用渲染路径。见 §2.4 |

> **主审初判被复核方推翻两组：** 主审对回放与 3D 栈初判均为 SUPPORTED，
> 复核方分别判 MISMATCH 与 PARTIAL，逐条复验后**均成立，已采纳**。详见 §7。

### 2.1 回放（SUPPORTED）

| # | 实现 | 位置 | 后端 | 前端 | 存储 |
|---|---|---|---|---|---|
| 1 | `/ai/replay/{trace_id}` + 2 条 metrics | `ai_commands.py:156,226,290` | 存在 | — | `audit_events` |
| 2 | `/agent/replay/decision/{id}`、`/recalculate`、`/trace` | — | **不存在**（全仓 grep `agent/replay` 后端零命中） | `agent-v2.ts:394,426,467` | — |
| 3 | `/teaching/attempts/{attempt_id}/replay` | `teaching_roster.py:396` | 存在 | — | 时间线相关表 |
| **4** | **`GET /agent/v2/trace/{trace_id}/events`** | `agent_v2.py:193` | 存在 | **`AgentWorkbenchPage.tsx:302` 实际调用** | **进程内 `orchestrator_v2._event_history`** |

**第 4 条是 A6 0.1.0 与主审初判都漏掉的，且它是四条里唯一被活页面真正消费的。**
其后端实现 `orchestrator_v2.get_trace_events(trace_id)` 读的是进程内列表（见 §3.2）。

> **后果：** 工作台上用户看得见的 trace 回放数据**存在进程内存里，重启即丢**。
> 这不是"内部实现细节"，是**用户可见功能的数据持久性缺陷**。

另有 `replay_checkpoints` 表（`agent_runtime.py:118`），A6 已登记其无应用写入路径。

```bash
grep -rn "replay" --include='*.py' r-mos-backend/app/api/ | grep "@router"
grep -rn "agent/replay" --include='*.py' r-mos-backend/app/     # 零命中
grep -rn "replay" --include='*.ts' r-mos-frontend/src/ | grep -E "client\.|apiClient"
```

**结论：A6 描述准确。** 第 2 套即「后端不存在」的那套，同时也是 M-09 十五条悬空调用中的 4 条。

### 2.2 证据模型（MISMATCH——说少了）

A6 写「证据模型×2（一套空）」。实际有 **4 条独立路径**：

| # | 路径 | 存储 | 写入者 |
|---|---|---|---|
| 1 | `evidence_bundles` + `evidence_items` | 数据库 | `EvidenceEngine`（`evidence_engine.py:57,62` `db.add` + `commit`） |
| 2 | `evidence_links` | 数据库 | `EvidenceEngine`（`evidence_engine.py:209`） |
| 3 | `evidence_cards` | 数据库 | `timeline.py:65` 定义 |
| 4 | **`evidence_enforcer` 进程内单例** | **进程内存** | `POST /evidence/collect` 端点直写 |

第 4 条是 A6 完全未识别的一条：`agent_evidence.py` 的三条端点
（`/evidence/status/{step_id}`、`POST /evidence/collect`、`/evidence/can-proceed/{step_id}`）
背后**不是数据库**，而是 `app/services/evidence_enforcement.py:251` 的模块级单例
`evidence_enforcer = EvidenceEnforcer()`，其状态存在两个实例字典中：

```python
self._evidence_requirements: Dict[str, List[EvidenceRequirement]] = {}   # :41
self._collected_evidence: Dict[str, Set[str]] = {}                       # :42
self._collected_evidence[step_id].add(evidence_id)                       # :67  ← 跨请求累积
```

该文件**全文零 `db` 引用**（`grep -n "db" 结果为空`）。

> **后果：** 「证据齐备才能继续」这道门禁的判定依据存在进程内存中，
> **重启即丢、多实例不一致**。这与 M-06 的审批内存队列是**同一模式**。

### 2.3 角色存储（PARTIAL——数少了）

A6 写「角色三处并存」。实际至少 4 处，且 RBAC 表数写少了：

| # | 处 | 位置 |
|---|---|---|
| 1 | `users.role` 列 | `models/user.py:25`，`default="student"` |
| 2 | RBAC 表 **4 张**（A6 只提 3 张） | `models/rbac.py:12,22,38,53` → `roles`、`permissions`、`user_roles`、**`role_permissions`** |
| 3 | 后端散落字符串 | A4/A6 已登记 |
| 4 | **前端 `UserRole` 类型** | `store/authStore.ts:7` = `'student' \| 'teacher' \| 'admin'`，**不含 `auditor`** |

第 4 处与后端不一致：迁移
`20260207_2130_9d8c7b6a5e4f_add_approvals_table_and_links.py:129-130`
把 `approvals:grant`/`reject` 赋给 `admin` 与 `auditor`，而前端类型系统不承认 `auditor`。

### 2.4 3D 栈（SUPPORTED）

用**独立方法**验证：从 `src/main.tsx` 出发做 import 图的传递闭包（脚本见 §5），
而非 A1 使用的字符串匹配。

```
入口=1  可达=181  总文件=195(已排除 .test./.d.ts/__tests__)  不可达=17
Viewer3D 不可达 10 个 | 其他不可达 7 个
```

A1 的「旧 3D 栈 9 文件不可达」+「前端 8 个不可达模块」= **17**，与本次独立计算的
10 + 7 = **17 完全一致**。差异仅在 `useRobotDataManifest.ts` 归入哪个桶
（A1 归「其他」，本次按目录归「Viewer3D」）——**属分类边界差异，非计数错误**。

**计数部分：A6/A1 准确。** 但异源复核指出「×2 两栈」这个**框架本身不成立**，复验后成立：

1. **旧文件不是闭合集合**：`Atom01Viewer.tsx:12` 引用 `Atom01Interactive`，
   而后者在生产中可达（`adjudication/ui/useSOPSceneSync.ts:2` 使用其 `PART_METADATA`）。
   即「旧栈」依赖「现行组件」，两者不是并列的两套。
2. **「新栈」内部至少 3 条在用渲染路径**：通用/监控走 `ManifestDrivenRenderer`（缺 manifest 退回 `RobotGLBViewer`）；
   SOP 维保走 `RuntimeAssetPreview`/`InteractiveManifestViewer`/`Atom01Interactive` 三分支；
   教学尝试页直接用 `InteractiveManifestViewer`。

**结论：判定 PARTIAL。** 正确表述应为
「**9 个旧文件在生产入口不可达（应删）**，但它们不构成独立旧栈；现行渲染本身有多条活跃路径待收口」。

> 附带收获：该可达性图**以完全不同的方法独立复现了 `pages/admin/ApprovalQueuePage.tsx` 不可达**，
> 交叉验证了 M-06 复核的核心事实。

## 3. M-19 单例口径：A6 的「8 个持可变状态」至少漏 3 个

### 3.1 方法

第一次尝试用「类体内出现 dict/list/set 字面量赋值」判定，得 30 个——**过报**，
因为它把配置字典、提示词模板、策略规则表都算了进去。**该结果已废弃，不作为结论。**

改用更贴语义的判据：**模块级单例，且其类在 `__init__` 之外修改 `self.<attr>`**
（含 `self.x = ...`、`self.x[...] = ...`、`self.x.append/add/update/pop(...)`），
即真正跨请求累积的状态。

### 3.2 结果

命中 **17 个**。A6 名单的 8 个中命中 7 个（`long_term_memory` 未命中——其写入委托给数据库，
本方法不认，属正常）。**未在 A6 名单中、但持真实业务状态的有 3 个：**

| 单例 | 状态字段 | 跨请求写入点 | 支撑的对外端点 | 是否有数据库 |
|---|---|---|---|---|
| `evidence_enforcer` | `_evidence_requirements`、`_collected_evidence` | `evidence_enforcement.py:67` `.add()` | `/evidence/status`、`POST /evidence/collect`、`/evidence/can-proceed` | **无** |
| `orchestrator` | `task_state: Dict[str, Any]` | `agent_service.py:139` 按 `user_id` 写 | agent 任务状态查询（`:127,287` 读） | **无** |
| `orchestrator_v2` | `_event_history: List` | `orchestrator_v2.py:595` `.append()` | **`GET /agent/v2/trace/{trace_id}/events`（`agent_v2.py:193`）→ `AgentWorkbenchPage.tsx:302` 实际调用** | **无** |

其余命中项中，`intent_engine`、`llm_risk_scorer`、`resource_parser`、`policy_matrix`
的写入点均为 `set_*` 配置方法，属运行期可调配置而非每请求累积；
`llm_router._clients` 属客户端缓存。**这些是否计入「有状态」取决于口径，本文件不主张。**

> **口径声明（吸取交接文档 §8「统计数字必须带口径」）：**
> 本节主张的是「A6 的 8 个名单**漏掉了 3 个持真实业务状态的单例**」，
> **不主张**「应为 17 个」或「应为 30 个」。后两个数字都依赖未声明的分类口径。

### 3.3 对 M-19 的影响

M-19 当前为 P2，理由是「单实例部署约束」。补入这 3 个后，其后果不止于部署约束：

- `evidence_enforcer` → **证据门禁**的判定依据在内存，重启即丢
- `orchestrator.task_state` → **任务状态**在内存，重启即丢
- `orchestrator_v2._event_history` → **trace 事件历史**在内存，重启即丢

**建议：M-19 的严重度需重新评估**，因为它现在直接影响三类业务数据的持久性，
而不只是"能不能横向扩展"。是否升级由董事会裁定。

## 4. 对 M-16 的根因订正

A6 的 M-16 把 `replay_checkpoints`、`decision_records`、`sop_audit_logs` 等
9 张无写入路径的表归因为「**定义先行、实现未跟上**」。

`orchestrator_v2._event_history` 的存在说明：**至少一部分表为空不是因为功能没实现，
而是因为数据被写进了进程内存、从未落库**。

这两个根因的**修复方式完全不同**：
- 「未实现」→ 需要新建写入路径
- 「写进了内存」→ 需要把已有写入改为落库，功能逻辑已存在

**建议：M-16 的受影响实例应按此二分重新分类**，否则改造计划会把已实现的逻辑当作待新建。
本次未逐表分类（超出订正轮范围），登记为 A6 0.1.1 的遗留项。

## 5. 复现脚本

两个脚本写在审计工作目录之外（scratchpad），**未污染被审工作区**：

- `reach.py`：前端 import 图传递闭包，从 `src/main.tsx` 出发，输出不可达文件清单
- `singletons2.py`：AST 扫描 `app/`，找出模块级单例中「类在 `__init__` 之外修改 `self` 属性」者，
  并与 A6 的 8 个名单对照

两脚本均只读，运行解释器为 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`
（`reach.py` 无第三方依赖，用系统 python3 亦可）。

## 6. 异源复核（Codex，订正轮 2）

| 项 | 内容 |
|---|---|
| 方式 | 只读沙箱，工作目录为被审工作区；禁止改动、禁止跑测试、禁止访问主审临时目录、禁止数据库 |
| 复核后仓库状态 | 复核方自查报告：仅观察到 A6 报告被重命名为 v0.1.1 及两份未跟踪审计文件（均为主审所写），**本次未写入或修改任何文件** |
| 判定 | 4 组：MISMATCH 2、PARTIAL 2、SUPPORTED 0 |
| 与主审初判的差异 | **2 组不同**（回放、3D 栈），主审初判均为 SUPPORTED |
| 处置 | **2 组差异逐条复验后全部采纳**，主审初判被推翻 |

| 组 | 主审初判 | 复核方 | 复验结果 |
|---|---|---|---|
| 回放 | SUPPORTED | **MISMATCH** | **复核方对**。漏掉第 4 条 `GET /agent/v2/trace/{id}/events`，且它是唯一被活页面调用的。已核 `agent_v2.py:193` 与 `AgentWorkbenchPage.tsx:302` |
| 3D 栈 | SUPPORTED | **PARTIAL** | **复核方对**。计数准确但「两栈」框架不成立，已核 `Atom01Viewer.tsx:12` → `Atom01Interactive` → `useSOPSceneSync.ts:2` 生产可达 |
| 证据模型 | MISMATCH | PARTIAL | 事实一致，仅严重度标签不同，**采纳复核方标签** |
| 角色存储 | PARTIAL | MISMATCH | 事实一致，仅严重度标签不同，**采纳复核方标签** |

### 6.1 主审在本轮的错误

主审对回放组只核到「后端有几条路由 + 前端有几条悬空调用」，
**没有核「哪条路由被活页面实际调用」**，因此漏掉了第 4 条——
而那恰恰是唯一在跑的一条，也恰恰是暴露进程内状态的那条。

> **教训：清点并存实现时，「有几套」和「哪套在跑」是两个必须分别回答的问题。**
> 只答前者会漏掉正在生产中承载用户功能的那套。
> 这与订正轮 1 的教训（设施齐全 ≠ 路径接通）是同一根源的两个面向。

## 7. 待并入 A6 0.1.1 的订正项

| # | 订正项 | 依据 |
|---|---|---|
| 8 | M-14 证据模型由「×2」改为「3 组表 + 1 个进程内存储」 | §2.2 |
| 9 | M-14 角色存储：RBAC 表 3 张→4 张；补前端类型为第 4 处且不一致 | §2.3 |
| 10 | M-14 回放、3D 栈两组标注「已独立复核，描述准确」 | §2.1、§2.4 |
| 11 | M-19 补 3 个持业务状态的单例，并提请重估严重度 | §3 |
| 12 | M-16 根因二分（未实现 vs 写进内存），登记逐表分类为遗留项 | §4 |

（第 1~7 项见 M-06 证据文件 §8。）
