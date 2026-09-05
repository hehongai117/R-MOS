# B-ASIS 到当前 HEAD 漂移复比报告（AG-04／AG-05）v0.1.0

- 日期：2026-09-05
- 历史事实基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 当前复比 HEAD：`a0b47c10f7dfbd438e52baf3bce6fe172c96cdb8`
- 当前分支：`audit/phase3-auth-control-realtime`
- 取证工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 主干阶段／任务：`S0｜统一现状`／`RMOS-S0-001`
- 主干对应关系：本报告为 S0-01 的“当前基线与当前问题清单”提供 AG-04／AG-05 复比输入，不宣布 S0 完成
- 任务性质：只读取证；除本报告外未改生产代码、配置或历史审计报告；未提交、未推送、未写数据库

## 0. 结论先行

1. **A1～A6 的历史结论没有被本报告倒改。** 本报告只说明这些结论能否继续描述当前 HEAD。
2. 当前 HEAD 相对 B-ASIS 已有 **63 个提交、186 个文件变化、+22,114／-1,540 行**。A1、A2、A3、A4、A5 的多个精确分母已经失效，A6 的 26 个问题编号仍可作为历史问题目录，但不能继续沿用旧状态分布。
3. 明确改善包括：HTTP 路由由 181 降至 168；写操作由 94 降至 87；可比对象／作者保护由 10/94 提升到 37/87；两个 WebSocket 均已在握手前认证，按用户发送不再全量广播；旧 adapter 入口及旧内存审批队列接口已删除；CI 重复 `env` 已修复；迁移由 38 增至 40；后端用例总量由 971 增至 995。
4. 明确恶化或新增失效有三组，均以 **🔴 CHANGED_WORSE** 标识：
   - 前端调用后端不存在的字面量契约由历史登记 15 条变为当前实测 21 条，其中 3 条是删除后端任务接口但遗留前端调用造成的新漂移；另 3 条是 B-ASIS 当时已存在但漏记，属于历史枚举不完整。
   - `OrchestratorV2` 新增 `_trace_owner_user_ids` 进程内所有者状态，扩大了 M-19 的进程内状态面。
   - 当前实现、测试、配置与历史审计分母已形成大范围漂移，M-24 的“文档、指纹和实现漂移”风险在当前 HEAD 上更强。
5. 三个原高危代表项中，“任意登录用户可打分”和“任意登录用户可删任意 SOP”已不成立；“任意登录用户可批准维保草稿”已收紧为教师／管理员且作者不得自批，但**仍未看到学校／租户范围校验**，不能关闭该风险。
6. 后端按指定命令实际得到 **992 passed、3 failed**。3 项失败均在连接 `::1:5432` 时被沙箱以 `PermissionError: Operation not permitted` 阻断，属于已知环境限制；当前测试集合共 995 项，但本报告不把未在本环境通过的 3 项写成 PASS。前端实际为 **518 passed、2 skipped**。
7. 本报告足以作为 AG-04／AG-05 的定向重开输入，**不等于 AG-04／AG-05 已关闭，也不等于 A1～A6 已重新批准**。

## 1. 口径与判定规则

| 标记 | 含义 |
|---|---|
| `UNCHANGED` | 当前实测与 B-ASIS 断言相同，或根因仍完整成立。 |
| `🟢 CHANGED_IMPROVED` | 当前实测已变化，且变化方向减少了原风险；历史事实仍保留。 |
| `🔴 CHANGED_WORSE` | 当前实测出现回归、新暴露面或更强漂移；需优先重开。 |
| `NO_LONGER_APPLICABLE` | 原对象／入口／实现已删除，原断言不能再描述当前 HEAD；删除不代表历史结论错误。 |

测量约束：

- HTTP 路由由加载后的真实 `main:app` 枚举 `fastapi.routing.APIRoute`，按方法与完整挂载路径统计；没有解析装饰器字符串。
- WebSocket 由真实应用枚举 `APIWebSocketRoute`。
- 写入口守卫由 AST 读取真实端点函数体中的 `Call` 节点；docstring 内出现的名字不计入。`DELETE /sops/{id}` 当前的 `ensure_write_owner()` 位于函数体真实调用节点中。
- 表同时以 `__tablename__` 静态枚举和 `Base.metadata.tables` 运行时枚举复核；迁移同时枚举真实版本文件和 Alembic revision graph。
- 前端调用以 TypeScript AST 中可确定的 HTTP 动词与字面量路径为分母；动态拼装且无法静态归一的调用不猜。
- “当前 HEAD”以本报告落笔前的 `a0b47c10` 为准。全量测试运行期间 HEAD 为其父提交 `616db22a`；随后外部并发过程新增的 `a0b47c10` 只改治理／交接文档。`git diff 616db22a..a0b47c10 -- r-mos-backend r-mos-frontend .github` 为空，因此本次前后端测试覆盖的程序与当前 HEAD 完全相同。

## 2. AG-04 环境指纹

### 2.1 Git 与差集

| 项 | 当前实测 |
|---|---|
| 工作区 | `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime` |
| 分支 | `audit/phase3-auth-control-realtime` |
| HEAD | `a0b47c10f7dfbd438e52baf3bce6fe172c96cdb8` |
| 上游 | `origin/audit/phase3-auth-control-realtime`，当前本地领先 1 个文档提交 |
| 取证前工作树 | 干净；本报告写入后仅应新增本报告 |
| B-ASIS → HEAD 提交数 | 63 |
| B-ASIS → HEAD 文件数 | 186 |
| B-ASIS → HEAD 行数 | 22,114 insertions、1,540 deletions |
| 生产树同父提交差异 | `616db22a..a0b47c10` 在 `r-mos-backend/`、`r-mos-frontend/`、`.github/` 下无差异 |

复现命令：

```bash
git branch --show-current
git rev-parse HEAD
git status --short --branch
git rev-list --count 29d2a5889e3b320a3e777e3d8c19efbbe31c0294..HEAD
git diff --shortstat 29d2a5889e3b320a3e777e3d8c19efbbe31c0294..HEAD
git diff --name-only 29d2a5889e3b320a3e777e3d8c19efbbe31c0294..HEAD | wc -l
git diff --name-only 616db22a..a0b47c10 -- r-mos-backend r-mos-frontend .github
```

### 2.2 Python、Node 与依赖

| 项 | 当前实测 |
|---|---|
| Python 解释器 | `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python` |
| Python | 3.13.13 |
| pytest | 9.0.3 |
| `requirements.txt` | 623 bytes；SHA-256 `a0d75483af9a9a6f4761d7202d8969ac8151ba4c7f75698e9fdd6e8663a97439` |
| `pip freeze` | 84 行；排序后 SHA-256 `98a8839c2b45355860b2bb52b9a77c17466b1c19434aa5c8da6f3f60103daa9e` |
| Node | v20.19.2 |
| npm | 10.8.2 |
| 顶层 Node 依赖 | 53 项；`npm ls --depth=0` 退出 0 |
| 锁文件 | 仅 `r-mos-frontend/package-lock.json`；447,698 bytes；SHA-256 `87888972373b95eb1a94aad1f56855eb2bf762c8c143009d8b41380ed79bf412` |

`pip` 的缓存目录不可写警告不影响冻结输出；没有安装、升级或删除任何依赖。

### 2.3 实际测试结果

| 套件 | 命令与结果 | 判定 |
|---|---|---|
| 后端全量 | 用户指定命令原样执行；`992 passed, 3 failed in 83.27s` | **环境受限**：3 项均因沙箱禁止连接 `::1:5432`；不得写成 995 PASS |
| 高风险定向 | 打分、SOP 删除、维保审批、WebSocket 定向／订阅、审批门禁；`23 passed in 2.46s` | PASS（仅覆盖这些定向行为） |
| 前端全量 | `npm test`；70 个文件，`518 passed, 2 skipped`，13.42s | PASS（2 项明确跳过） |

后端失败的三项为：

1. `tests/unit/test_audit_query_index_gate.py::test_audit_query_indexes_exist`
2. `tests/unit/test_audit_query_index_gate.py::test_audit_trace_query_explain_uses_trace_index`
3. `tests/unit/test_skill_registry_migration_gate.py::test_skill_registry_migration_gate`

三者关键错误均为连接 `::1:5432` 时 `PermissionError: [Errno 1] Operation not permitted`。这是环境限制，不是本次发现的产品缺陷；也不能据此确认两项新迁移已在真实数据库应用。

## 3. A1 逐项复比：系统功能与资产分母

历史量化来源主要见 `2026-08-26-a1-dual-source-diff-v0.1.0.md:47-57,77-99`；A1 v0.2.1 已把部分全量断言降级并要求重开，不应把历史数字当作当前事实。

| 原断言 | 当前实测 | 判定 | 证据／说明 |
|---|---:|---|---|
| 181 个 HTTP `APIRoute`；另有 2 个 WS；框架路由合计后 `app.routes=187` | 168 个 HTTP（167 个 `/api/v1` + 根路径 `/`）；2 个 WS；4 个文档框架路由；`app.routes=174` | 🟢 `CHANGED_IMPROVED` | 真实 `main:app` 枚举；13 个 HTTP 净减少来自删除 5 个 adapter 入口和 8 个旧内存任务／审批入口。历史 181／187 不再适用于 HEAD。 |
| 65 张业务表，数据库另有 `alembic_version` | 静态 65、`Base.metadata` 65，差集为空 | `UNCHANGED` | 双源表定义仍为 65。实时数据库表数因沙箱无法连接，单列为不可测。 |
| 38 个迁移文件／38 个图节点／单一 head | 40 个迁移文件／40 个图节点／单一 head `20260904_m02_ownership` | 🟢 `CHANGED_IMPROVED` | 文件与 Alembic revision graph 双源一致；新增所有权字段与回填迁移。是否已应用到现场库不可测。 |
| 前端路由 26 条 | 26 条 JSX 路由声明 | `UNCHANGED` | TypeScript AST 枚举 `Route path`。 |
| 前端非测试 TS/TSX 195 个 | 排除 `.d.ts` 后 195 个 | `UNCHANGED` | 文件枚举。 |
| 后端 `main.py + app` 231 个模块 | 230 个 | 🟢 `CHANGED_IMPROVED` | `app` 229 + `main.py`；删除 adapter 端点模块后净少 1。 |
| 后端 123 个测试文件／971 个收集用例 | `tests/` 下 131 个测试文件；本次套件共 995 项（992 通过 + 3 环境失败） | 🟢 `CHANGED_IMPROVED` | 用例集合净增 24；不能用当前沙箱结果声称 995 全通过。 |
| `schemas/tests` 下 7 个测试文件未被主套件收集 | 仍有 7 个 | `UNCHANGED` | 文件枚举；未纳入当前主套件。 |
| 前端 78 个 `.test.ts(x)`，70 文件／518 用例被 Vitest 收集；8 个伪测试 | 仍为 78 个 `.test.ts(x)`；实际 70 文件、518 通过、2 跳过；8 个非收集伪测试仍在 | `UNCHANGED` | 文件枚举 + `npm test`。 |

## 4. A2 逐项复比：前后端闭环

历史量化来源见 `2026-08-27-a2-flow-linkage-v0.1.0.md:21-27,53-54,145`。

| 原断言 | 当前实测 | 判定 | 证据／说明 |
|---|---:|---|---|
| 27 个前端文件、117 组字面量方法／路径 | 21 个文件、112 组 | 🟢 `CHANGED_IMPROVED` | TypeScript AST 字面量调用枚举；旧实现删除使调用面收缩，但不是业务闭环已经完成的证据。 |
| 对 182 条后端路由：94 条动词命中、5 条仅路径命中、83 条完全无前端调用 | 当前 167 条 `/api/v1` HTTP 操作中，91 条有同动词前端字面量调用，76 条无调用 | 🟢 `CHANGED_IMPROVED` | 当前比较按真实完整路由 + AST 字面量调用；旧 94／83 分母失效。动态调用不猜，因此不与旧“仅路径命中”强行拼接。 |
| 94 条写操作，51 条有前端入口、43 条没有 | 87 条写操作，48 条有前端入口、39 条没有；覆盖率 54.3% → 55.2% | 🟢 `CHANGED_IMPROVED` | 真实 `APIRoute` 分母。改善很小，且主要来自删除入口，不能写成业务闭环通过。 |
| 11 个端点域完全没有写前端 | 10 个：`admin`、`assessments`、`evidence`、`fault_cases`、`incidents`、`maintenance`、`observations`、`skills`、`teaching`、`training` | `NO_LONGER_APPLICABLE` | adapter 域整体删除使数量少 1；其余 10 个仍在，教学／训练闭环根因未消失。 |
| 前端调用后端不存在 15 条 | 当前 21 条 | 🔴 **`CHANGED_WORSE`** | 当前全量清单见附录 A。18 条属于旧范围：历史登记 15 条 + B-ASIS 已存在但漏记 3 条；另有 3 条为删除后端 `/agent/v2/task*` 后遗留的前端调用。 |

新增的 3 条漂移为：

- `POST /agent/v2/task/create` — `r-mos-frontend/src/api/agent-v2.ts:226`
- `POST /agent/v2/task/{}/transition` — `r-mos-frontend/src/api/agent-v2.ts:248`
- `GET /agent/v2/task/{}` — `r-mos-frontend/src/api/agent-v2.ts:262`

`git show B-ASIS:r-mos-backend/app/api/v1/endpoints/agent_v2.py` 可证明这三条在 B-ASIS 存在；当前真实应用中不存在。因此这是后端删除未同步清理前端的真实回归。

## 5. A3 逐项复比：架构与数据边界

历史量化来源见 `2026-08-27-a3-architecture-evidence-v0.1.0.md:20-52,129-133`。A3 v0.2.0 已明确暂停“35 个／8 个”等未保存原始脚本的全量数字。

| 原断言 | 当前实测 | 判定 | 证据／说明 |
|---|---:|---|---|
| 分层模块：services 115、models 40、api 39、schemas 18、core 11、adapters 5、other 2 | 115／40／38／18／11／5／2 | 🟢 `CHANGED_IMPROVED` | 仅 api 净少 1，来自 adapter 端点模块删除。 |
| 顶层实例化 74 = 36 路由 + 3 常量 + 35 业务单例 | 72 = 35 路由 + 3 常量 + 34 业务单例 | 🟢 `CHANGED_IMPROVED` | 复用历史“顶层构造调用赋值”规则重算；路由和业务单例各少 1。精确“可变单例”数仍不可同口径复现。 |
| 独立 `approval_queue` 是进程内字典，5 个接口不落库 | `app/services/approval_queue.py` 不存在，应用引用为 0，相关 5 个接口连同 3 个旧内存任务接口已删除 | `NO_LONGER_APPLICABLE` | 原具体实现已整体删除。注意 `knowledge_governance._approval_requests` 等其他进程内状态仍存在，不能外推为“所有内存审批状态均消失”。 |
| 15 张表无应用写入：9 张完全无写入 + 6 张仅脚本写入 | 15 = 9 + 6，名单完全相同 | `UNCHANGED` | ORM 导入别名解析 + 构造／update／delete AST 枚举。 |
| 16 张表由 API 端点直接写入 | 16 张，名单完全相同 | `UNCHANGED` | 当前直写名单仍含 `approvals`、`commands`、`ai_tool_calls`、`robot_sop_drafts` 等。 |
| `services/` 根目录 35 个文件未归组 | 35 | `UNCHANGED` | 文件枚举。 |
| 仅 1 组循环依赖 | 当前重建图识别到 2 组；第二组 `app.services.memory ↔ app.services.memory.training_memory_writer` 在 B-ASIS 已存在 | `NO_LONGER_APPLICABLE` | 这不是改造新增回归，而是历史枚举漏项；原脚本未保存，不能把“1→2”解释为 HEAD 漂移。A3 应重开循环依赖口径。 |
| 各层跨层边的精确数字 | 当前重建为 229 模块、648 条导入边；因原提取脚本未保存，部分相对导入归一规则无法证明完全同口径 | `NO_LONGER_APPLICABLE` | 当前数字可作新基线候选，不可直接写成历史边数的精确增减。 |

## 6. A4 逐项复比：安全、控制与实时通道

历史报告 v0.2.0 已将 94／84／46 等精确分母暂停；本节用当前真实应用和 AST 重新建立当前分母，不反推修改历史事实。历史写操作 94／归属 10 见 `2026-08-28-a4-security-evidence-v0.1.0.md:253-254`。

| 原断言 | 当前实测 | 判定 | 证据／说明 |
|---|---:|---|---|
| 安全矩阵 187 行（181 HTTP + 2 WS + 4 框架入口） | 当前同口径 174 行（168 HTTP + 2 WS + 4 框架入口） | 🟢 `CHANGED_IMPROVED` | 真实应用枚举；当前安全矩阵必须按 174 重开。 |
| 94 条写操作仅 10 条有对象归属校验（10.6%，报告取整 10%） | 87 条写操作；27 条调用标准对象／作者守卫，另有原有 10 条 robots／onboarding 内联保护，合计可比 37/87（42.5%） | 🟢 `CHANGED_IMPROVED` | AST 只计算函数体真实 `Call`；标准调用为 `ensure_write_owner` 24、`ensure_reviewer_not_author` 2、`ensure_teacher_scope_over_student` 1。旧 10 条逐函数复核仍在，且不与这 27 条重叠。另有 18 条只做权限守卫、10 条角色写守卫，不冒充对象归属。 |
| 多个写入口不接收身份 | 当前 87 条写入口中 83 条有身份；4 条无身份的是公开认证流程（register/login/refresh/logout） | 🟢 `CHANGED_IMPROVED` | 真实依赖图 + AST；“有身份”不等于“对象范围正确”。 |
| 任意登录用户可给任意作业打分 | 当前调用 `ensure_teacher_scope_over_student`；学生自评、范围外教师均被拒绝 | 🟢 `CHANGED_IMPROVED` | `teaching_roster.py:827-843`；定向用例通过。 |
| 任意登录用户可删任意 SOP；历史守卫只写在 docstring | 当前 `ensure_write_owner` 是函数体真实调用 | 🟢 `CHANGED_IMPROVED` | `sops.py:232-245`；AST 与定向用例均通过。 |
| 任意登录用户可批准任意维保草稿 | 当前只允许教师／管理员，且作者本人不得审批或拒绝 | 🟢 `CHANGED_IMPROVED` | `maintenance.py:188-215,220-243`；非作者教师可批准、管理员作者被拒绝的定向用例通过。**残余：函数体未见学校／租户范围守卫，跨校非作者教师风险仍需 A4 重开。** |
| 两个 WebSocket 零认证、无对象过滤；`send_to_user` 实为全量广播 | 两个 WS 都在 `accept` 前认证；带 robot_id 路由先做机器人可见性检查；连接登记 user_id；`send_to_user` 仅选择该 user_id | 🟢 `CHANGED_IMPROVED` | `websocket.py:41-132,155-182`、`websocket_manager.py:315-351`；定向运行 23 项包含匿名拒绝、机器人订阅授权与用户定向投递。当前单全局 adapter 仍不能按 robot_id 过滤不同遥测源。 |
| M-04：默认拒绝只覆盖 `/api/v1`，生产文档／OpenAPI 暴露 | `DEBUG=false` 真实加载时文档路由为 0；根路径仍在 `/api/v1` 网关外 | 🟢 `CHANGED_IMPROVED` | 生产文档暴露已修；“默认拒绝只包 API 前缀”的结构事实仍部分成立，需按根路径和未来前缀外入口重开。 |
| M-05：adapter 入口无端点级鉴权 | adapter 端点模块与 5 条路由已删除 | `NO_LONGER_APPLICABLE` | 删除是当前状态变化，不倒改 B-ASIS 风险。 |
| M-06：持久化审批不在真实执行路径，另有零消费者内存队列 | 旧内存队列已删除；持久化 `Command → AIToolCall → Approval` 门禁进入执行链，审批前阻断、批准后才进入执行 stub | 🟢 `CHANGED_IMPROVED` | `approvals.py:173-245,280-347` 与 `test_approval_gate.py`。仍是 write stub，未执行外部真实副作用，不能关闭 M-06。 |
| M-07：机器人适配器契约无产品级运动控制／急停 | `BaseRobotAdapter` 仍只有连接、状态、故障注入／清除等接口，没有运动命令或产品级急停契约 | `UNCHANGED` | `app/adapters/base.py:16-154`；mock 内的 `emergency_stop` 动作不等于抽象契约和真机急停门禁。 |
| M-13：角色多源并存，auditor 可审批 | `actor.roles` 与 `account_role` 仍并存；审批仍允许 admin 或 auditor | `UNCHANGED` | `approvals.py:26-27,173-198,280-305`。维保作者不得自批是局部改善，未消除角色事实源与审计员审批职责问题。 |

## 7. A5 逐项复比：质量、运行与交付

历史静态统计见 `2026-08-28-a5-quality-evidence-v0.1.0.md:19-33,142-158`。

| 原断言 | 当前实测 | 判定 | 证据／说明 |
|---|---:|---|---|
| 743 个 `test_` 函数、2,468 个 assert、中位 3、均值 3.3 | 776 个函数、2,535 个 assert、中位 3、均值 3.267 | 🟢 `CHANGED_IMPROVED` | 同类 AST 静态计数；函数与断言总量增加，但数量不等于证明质量。 |
| 21 个无 assert，其中 18 个 `pytest.raises`，真正零断言 3 | 21／18／3，且 3 个函数名单相同 | `UNCHANGED` | AST 复测。 |
| 49 个仅状态码浅断言 | 58 个 | 🔴 **`CHANGED_WORSE`** | 同类 AST 规则下增加 9 个；新增测试量上升的同时浅断言也上升，A5 需复核新增测试的断言深度。 |
| 含 skip 字样 18，实际 skip 机制出现 6 次 | 18／6 | `UNCHANGED` | AST／词法双检。 |
| 重度 mock（≥5）函数 34 | 当前无法同口径确认 | `NO_LONGER_APPLICABLE` | 历史 mock 计数脚本未保存；当前重建规则与历史正则归一方式不一致，拒绝发布伪精确增减。 |
| 主套件 971 用例，基座主要使用 SQLite `create_all`，不经过 38 个迁移 | 当前 995 项；主基座仍保留 SQLite `create_all`，另有 3 个真 PG 门禁本环境因 `::1:5432` 被阻断；迁移现为 40 | 🟢 `CHANGED_IMPROVED` | 用例和 PG 门禁增加，但本环境没有取得迁移执行 PASS，证明边界仍窄于总数量。 |
| `integration-ci` 两个同级 `env:`，后块覆盖前块使 `DEBUG` 丢失 | job 仅一个 `env`，同时含 `DEBUG` 和 `DATABASE_URL`；重复键扫描为 0 | 🟢 `CHANGED_IMPROVED` | `.github/workflows/integration-ci.yml:34-40`。配置缺陷已修；真实远程 CI 运行仍未取证。 |
| 健康体可返回 `unhealthy`，HTTP 仍为 200 | 依赖断开模拟下 payload 仍为 `unhealthy`，路由未声明非 200 状态 | `UNCHANGED` | `health.py:30-82`；M-11 未修。 |
| 无备份恢复演练、外部监控、真机／浏览器正式验收等证据 | 本任务未找到可把这些历史 UNKNOWN／BLOCKED 改为 PASS 的新正式证据 | `UNCHANGED` | 静态材料存在不等于运行验收；详见“无法测量”。 |

## 8. A6 的 26 项问题：当前状态复比

历史唯一问题表与严重度见 `2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md:11-49`。下表只给**当前技术事实变化**，不替代正式问题状态裁定，也不重算 P0／P1／P2。

| ID | 历史根因摘要 | 当前复比 | 判定 | 定向重开要点 |
|---|---|---|---|---|
| M-01 | 写入口缺身份／归属 | 87 写入口；83 有身份；可比对象／作者保护 37 | 🟢 `CHANGED_IMPROVED` | 用 87 分母重建全表；对其余入口逐项区分“无需对象”“只有角色”“缺对象范围”。 |
| M-02 | 业务身份未绑定认证身份 | 多批入口已改用服务端 actor，代表性负向测试增加 | 🟢 `CHANGED_IMPROVED` | 对所有请求体／查询参数中的 user、student、teacher 身份做全量语义复核；不能用“83 有身份”替代绑定证明。 |
| M-03 | WS 无认证、对象过滤、用户维度 | 握手前认证、机器人可见性、用户定向均已实现并定向通过 | 🟢 `CHANGED_IMPROVED` | 重开后验证双用户、双机器人；单 adapter 下 robot_id 数据源过滤仍未实现。 |
| M-04 | API 前缀外入口未被默认拒绝覆盖 | 生产文档路由已关闭；根路径仍在网关外 | 🟢 `CHANGED_IMPROVED` | 以 `DEBUG=false` 的全部 `app.routes` 重建公开白名单。 |
| M-05 | adapter 入口无鉴权 | 入口已删除 | `NO_LONGER_APPLICABLE` | 确认删除为正式产品决策并做无残留消费者检查。 |
| M-06 | 审批不在真实执行链且双实现 | 旧内存队列删除；持久化审批接入执行链；真实副作用仍为 stub | 🟢 `CHANGED_IMPROVED` | 从请求、审批、执行、审计到真实受控副作用做隔离验证。 |
| M-07 | 无运动控制／急停契约 | 抽象适配器仍无该契约 | `UNCHANGED` | 保持 E3 阻断；先定安全契约。 |
| M-08 | 教学／训练写能力无前端闭环 | 仍有 10 个域没有写前端，teaching／training 在内 | `UNCHANGED` | 用当前 87 写入口重做角色流程和浏览器闭环。 |
| M-09 | 前后端契约漂移 | 当前 21 条前端悬空；3 条为本次改造新增 | 🔴 **`CHANGED_WORSE`** | 优先处理 `/agent/v2/task*` 三条新漂移，再复核 18 条存量。 |
| M-10 | CI 重复配置覆盖 DEBUG | 配置重复键已修 | 🟢 `CHANGED_IMPROVED` | 取得当前提交真实 CI 记录后才可正式关闭。 |
| M-11 | unhealthy 仍返回 HTTP 200 | 仍成立 | `UNCHANGED` | 做依赖故障、状态码和编排行为测试。 |
| M-12 | 租户隔离主要在读路径 | 多个读写入口新增归属字段／守卫；维保审批仍未见学校范围校验 | 🟢 `CHANGED_IMPROVED` | 建立学校维度的读写负向全矩阵，不以单对象 owner 代替 tenant。 |
| M-13 | 角色多源、职责分离失效 | 维保作者自批已拦截；auditor 仍可批准／拒绝，角色事实源仍多处 | `UNCHANGED` | 分开复核局部职责分离和系统角色事实源。 |
| M-14 | 新旧实现并存 | 旧内存任务／审批接口删除，重复面缩小；其他 replay／metrics／evidence 分组仍在 | 🟢 `CHANGED_IMPROVED` | 逐组冻结保留／删除及消费者，不能因一组删除关闭全部。 |
| M-15 | 运行期本地文件未纳入持久卷 | 未见生产持久卷闭环的新运行证据 | `UNCHANGED` | 容器重建与数据保持演练；测试污染修复不等于生产卷问题修复。 |
| M-16 | 定义先行与内存代替落库混合 | 旧 approval_queue 删除；15 张无应用写入表名单不变，其他内存状态仍在 | 🟢 `CHANGED_IMPROVED` | 按每张表／状态源重新二分，不作整体关闭。 |
| M-17 | 测试证明边界窄于数量 | 用例增至 995，安全负向测试增加；3 个 PG 门禁在本环境未运行成功，SQLite 基座仍在 | 🟢 `CHANGED_IMPROVED` | 在可连 PG 环境补跑 3 门禁，并重审 58 个浅断言函数。 |
| M-18a | 备份、恢复、回滚缺失 | 无新的正式恢复／回滚演练证据 | `UNCHANGED` | 继续 BLOCKED，不能用文档代替演练。 |
| M-18b | 监控、告警、依赖治理缺失 | 无新的等价环境运行证据 | `UNCHANGED` | 采集监控、告警送达和依赖治理证据。 |
| M-19 | 业务状态驻留进程内 | 原进程内状态仍在；新增 `_trace_owner_user_ids` 保存 trace 所有者 | 🔴 **`CHANGED_WORSE`** | 重新盘点全部进程内业务状态，并做重启、并发、多进程验证；新映射当前重启后会丢失并拒绝普通用户访问旧 trace。 |
| M-20 | 容器权限／构建上下文未收敛 | 未见足以改变根因的新可运行证据 | `UNCHANGED` | 镜像内容、运行用户与供应链检查。 |
| M-21 | CI 门禁覆盖不完整 | M-10 配置已修；其他门禁与远程执行证据仍不完整 | 🟢 `CHANGED_IMPROVED` | 以当前 HEAD 的真实工作流记录重开，分开配置存在与运行成功。 |
| M-22 | 任务终态写入责任未收口 | 本次无完整 UI→终态运行证据改变该结论 | `UNCHANGED` | 执行完整流程并核对唯一终态写入者。 |
| M-23 | 知识批准后未形成检索底料 | 本次无批准→切块→检索完整证据 | `UNCHANGED` | 做全链路运行验证。 |
| M-24 | 文档、指纹、实现漂移 | B-ASIS 到 HEAD 已 63 提交、186 文件；多个核心分母和状态变化 | 🔴 **`CHANGED_WORSE`** | 本报告作为新基线输入；重开后建立自动漂移检查。 |
| M-25 | 模块责任／目录边界模糊 | `services/` 根目录仍 35 文件；边界根因未消失 | `UNCHANGED` | R1 决策后再冻结目标边界。 |

### 8.1 A6 数量结论怎么处理

- “26 个唯一 Master_ID”作为**历史问题目录数量**仍为 `UNCHANGED`。
- 历史严重度分布 `P0=8、P1=11、P2=7` 是 B-ASIS 的治理事实，不在本报告中重算。
- 当前技术状态已经不是“原 26 项全部维持原 OPEN／REVERIFY／DISPUTED 含义”：至少 M-05 已 `NO_LONGER_APPLICABLE`，M-01／02／03／04／06／10／12／14／16／17／21 有不同程度改善，M-09／19／24 变差。
- 所以 A6 必须定向重开这些行并重新裁定，不能由本报告直接改写历史台账。

## 9. A1～A6 需要定向重开的具体条目

### A1

1. 用 168 HTTP + 2 WS + 4 框架入口重建当前入口分母和全量资产表。
2. 用 40 个迁移、65 个模型表重建迁移／数据库对照；在可连 PG 环境确认实际 head 与 66 张含版本表的真实库表。
3. 更新后端模块、测试文件、995 项用例分母；保留 7 个未收集后端测试和 8 个前端伪测试的历史／当前区分。

### A2

1. 以 167 个 `/api/v1` HTTP 操作、112 组前端字面量调用重建双向契约矩阵。
2. 更新写入口闭环为 87／48／39，并解释覆盖率改善主要来自删除而非新增 UI。
3. 将 21 条前端悬空调用完整入表；把 3 条新 `/agent/v2/task*` 回归与 3 条历史漏项分开。
4. 对仍无写前端的 10 个域做角色流程复核。

### A3

1. 更新 api 模块数 39→38、业务单例候选 35→34；停止复用无原脚本支撑的“8 个可变单例”。
2. 将旧 `approval_queue` 标为删除，同时重新盘点 `knowledge_governance`、`orchestrator_v2` 等剩余内存状态。
3. 保留“15 张无应用写入”和“16 张 API 直写”两项当前仍成立的结论。
4. 重建循环依赖与导入边提取器；明确第二组循环是 B-ASIS 漏项，不是当前新增。

### A4

1. 以 174 行重建当前安全矩阵，逐条保存身份、角色、对象、租户和拒绝审计证据。
2. 以 87 写入口重建对象保护分母；重点审查 32 个未命中统一写守卫的入口，不把公开认证入口或无对象创建入口误报为漏洞。
3. 重新裁定三项代表高危：打分已修、SOP 删除已修、维保审批部分修复但跨校范围仍待证。
4. 对两个 WS 做双用户、双机器人运行隔离；区分“订阅授权”与“按 robot_id 数据源过滤”。
5. M-04 按 `DEBUG=false` 全路由重验；M-05 按删除决定重验；M-06 延伸到真实受控副作用；M-07、M-13 保持未关闭。

### A5

1. 更新用例与静态断言分母；专项复核 58 个浅断言函数。
2. 在允许连接 PG 的环境执行当前 40 个迁移及 3 个数据库门禁，不能用本次环境失败替代产品结论。
3. 为 M-10 获取真实远程 CI 记录；为 M-11补健康非 200 行为验证。
4. 备份恢复、监控告警、容器、浏览器 E2E 和真机 E3／E4 均保持 UNKNOWN／BLOCKED，直至有运行证据。

### A6

1. 对 26 个 Master_ID 逐行吸收本报告 §8 的变化，但保留 B-ASIS 历史列不动。
2. 优先重开 **M-09、M-19、M-24** 三个 `CHANGED_WORSE`。
3. 对 M-05 走“删除后的不再适用”裁定；对各 `CHANGED_IMPROVED` 逐项决定是部分修复、待运行复核还是可关闭。
4. 等 A1～A5 新分母和运行证据冻结后再重算当前严重度与状态分布。

## 10. 无法测量／不得猜测的项目

| 项目 | 为什么无法测量 | 本报告处理 |
|---|---|---|
| 现场 PostgreSQL 实际表数、每表行数、角色数、`alembic_version` 当前值 | 沙箱禁止连接 `::1:5432`，只读连接也被 EPERM 拒绝 | 只报告模型 metadata=65、迁移文件／图=40；不声称现场库已迁移 |
| 3 个数据库门禁的功能结果 | 同一网络限制 | 记录 3 FAIL 为环境限制，不算产品缺陷，也不算 PASS |
| 真实远程 GitHub Actions | 本任务未访问外部 CI 记录 | M-10 仅证明配置修复；远程运行仍 UNKNOWN |
| 备份恢复、监控告警送达、容器重建、浏览器正式验收、真机急停／断网 | 需要等价环境、外部系统或真机；本任务禁止扩大运行范围 | 保持 UNKNOWN／BLOCKED，不用静态代码或文档代替 |
| 真实 write tool 的审批后副作用 | 当前路径仍是 stub，本任务不允许外部写操作 | 只证明门禁状态机，不证明真实副作用闭环 |
| A3 历史“8 个可变单例”与精确跨层边的同口径增减 | 历史提取脚本和原始输出未保存，A3 v0.2.0 已暂停该数字 | 发布当前候选枚举，不伪造可比差值 |
| A5 “重度 mock 34”当前同口径值 | 历史 regex／AST 归一规则未保存，重建结果无法证明同口径 | 不发布当前伪精确数 |
| 动态生成的前端 URL | 静态 AST 不能可靠还原全部运行值 | 只把可确定的 112 组字面量纳入分母；其余列 UNKNOWN |
| 当前 P0／P1／P2 新分布和正式关闭状态 | 需要 A1～A6 重开、批准与运行证据，不属于本取证报告授权 | 不重算，不代替董事会裁定 |

## 11. 复现命令与证据摘要

### 11.1 路由、表、迁移、AST 与依赖图

本次临时脚本全部位于 `/tmp`，没有写入仓库：

| 临时脚本 | SHA-256 | 用途 |
|---|---|---|
| `/tmp/rmos_drift_probe.py` | `3c307e1a89b2d2d09896b78d6461f45c47a2809de687e9355fc3df76d6dc4393` | 真实应用路由、表、迁移、模块、单例、写入者、测试 AST |
| `/tmp/rmos_frontend_api_probe.mjs` | `ce0f1efcfaca51d18580fd3fbd46e372c0c09f22fff40d99d490c48ae5057d95` | TypeScript AST 调用与前后端契约 |
| `/tmp/rmos_write_auth_scan.py` | `1887fcd2638d7c52ed12077fa77545653d107713c2c8a61473237ff706d5372e` | 真实写端点依赖图 + 函数体 Call 守卫 |

执行方式：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS
export DEBUG=true
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python /tmp/rmos_drift_probe.py
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python /tmp/rmos_write_auth_scan.py

cd ../r-mos-frontend
node /tmp/rmos_frontend_api_probe.mjs
```

关键输出：

```text
APIRoute=168; /api/v1 HTTP=167; write=87; WS=2; app.routes=174
tables static=65; metadata=65; migrations files=40; graph=40; heads=[20260904_m02_ownership]
write identity=83/87; unified write guard=55/87
standard object/author guard calls=27; comparable object/author protections=37/87
frontend literal method/path=112; write with frontend=48/87; dangling frontend=21
business singleton candidates=34; no-app-writer tables=15; direct-API-write tables=16
```

### 11.2 后端全量（按任务要求原样）

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS
export DEBUG=true
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest -p no:warnings
```

结果：`992 passed, 3 failed in 83.27s`；未传 `-q`，未传 `--timeout`。

### 11.3 高风险定向

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest -p no:warnings \
  tests/unit/test_api_teaching.py::test_grade_attempt_rejects_student_self_grading \
  tests/unit/test_content_ownership.py \
  tests/unit/test_robot_sop_draft_api.py::test_draft_approval_allows_non_author_teacher \
  tests/unit/test_robot_sop_draft_api.py::test_draft_approval_denies_admin_author \
  tests/unit/test_websocket_targeting.py \
  tests/e2e/test_websocket_robot_authorization.py \
  tests/unit/test_approval_gate.py
```

结果：`23 passed in 2.46s`。

### 11.4 前端

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
npm test
npm ls --depth=0
```

结果：70 个文件；`518 passed, 2 skipped`；依赖树退出 0。

## 附录 A：当前 21 条前端悬空字面量调用

| 方法 | 路径 | 前端位置 | 归类 |
|---|---|---|---|
| GET | `/agent/metrics` | `src/api/agent-v2.ts:514` | 历史存量 |
| GET | `/agent/metrics/{}` | `src/api/agent-v2.ts:522` | 历史存量 |
| GET | `/agent/metrics/reports` | `src/api/agent-v2.ts:548` | B-ASIS 已存在、历史漏记 |
| GET | `/agent/monitor/alerts` | `src/api/adminConsole.ts:77` | 历史存量 |
| GET | `/agent/monitor/health` | `src/api/adminConsole.ts:59` | 历史存量 |
| GET | `/agent/monitor/metrics` | `src/api/adminConsole.ts:64` | 历史存量 |
| GET | `/agent/monitor/metrics/history` | `src/api/adminConsole.ts:69` | 历史存量 |
| GET | `/agent/replay/decision/{}` | `src/api/agent-v2.ts:394` | 历史存量 |
| GET | `/agent/replay/recalculations` | `src/api/agent-v2.ts:442` | B-ASIS 已存在、历史漏记 |
| GET | `/agent/replay/trace/{}/decisions` | `src/api/agent-v2.ts:410` | B-ASIS 已存在、历史漏记 |
| GET | `/agent/v2/task/{}` | `src/api/agent-v2.ts:262` | **当前新增漂移** |
| PATCH | `/auth/profile` | `src/pages/UserSettingsPage.tsx:54` | 历史存量 |
| POST | `/agent/metrics/record` | `src/api/agent-v2.ts:506` | 历史存量 |
| POST | `/agent/metrics/report` | `src/api/agent-v2.ts:530` | 历史存量 |
| POST | `/agent/metrics/reset` | `src/api/agent-v2.ts:566` | 历史存量 |
| POST | `/agent/replay/decision/record` | `src/api/agent-v2.ts:383` | 历史存量 |
| POST | `/agent/replay/recalculate` | `src/api/agent-v2.ts:426` | 历史存量 |
| POST | `/agent/replay/trace` | `src/api/agent-v2.ts:467` | 历史存量 |
| POST | `/agent/v2/task/{}/transition` | `src/api/agent-v2.ts:248` | **当前新增漂移** |
| POST | `/agent/v2/task/create` | `src/api/agent-v2.ts:226` | **当前新增漂移** |
| POST | `/auth/change-password` | `src/pages/UserSettingsPage.tsx:76` | 历史存量 |

## 12. 最终判定

- **主干任务：本次工作属于 `RMOS-S0-001`，完成了 B-ASIS 到当前 HEAD 的环境、分母和问题状态漂移取证；新发现问题为 M-09 三条新增前端悬空调用与 M-19 新增进程内 trace 所有者状态。**
- **AG-04：本报告已补齐当前工作树的代码、运行环境、依赖、锁文件、路由、表、迁移和测试指纹；但实时数据库、远程 CI 与外部／真机环境仍受限，故本报告是 AG-04 的闭环输入，不自行宣告关闭。**
- **AG-05：已逐项建立 B-ASIS → 当前 HEAD 的状态变化表，并明确分开改善、恶化、不再适用和无法测量；A1～A6 均需按 §9 定向重开。**
- **优先级最高的当前回归：M-09、M-19、M-24。**
- **历史 A1～A6 报告保持原样；任何阶段状态、问题严重度或正式关闭仍须走重开与批准流程。**
