# R-MOS Phase 3 续作交接（新窗口）

- 版本：0.1.0
- 日期：2026-08-25
- 交接状态：READY
- 适用范围：在新对话窗口继续 Phase 3 第 4–6 批，直至 Phase 3 收口
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`
- 前序交接：`docs/handover/2026-08-21-phase2-phase6-handover-v0.1.0.md`（Phase 2–6 总体框架，仍然有效）

## 1. 精确恢复点

| 项目 | 值 |
|---|---|
| 主仓库 | `/Users/xuhehong/Desktop/r-mos` |
| **接手工作区** | `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime` |
| **接手分支** | `audit/phase3-auth-control-realtime` |
| **接手提交** | `d18dc5c09d55160d8a7bc146a17707dfc61d76ab` |
| 工作区状态 | 干净 |
| 远端 | **未推送**；未经用户许可不得 push、不得合并 |

阶段链（每阶段从上一阶段最终提交建立独立工作区）：

```
09ec02a1  codex/architecture-audit-phase1     Phase 1 审查
361eaac8  audit/phase2-security-architecture  Phase 2 ADR + 修复矩阵
d18dc5c0  audit/phase3-auth-control-realtime  Phase 3 第 1–3 批  ← 从这里继续
```

Phase 3 分支上的 6 个提交：

```
341dc20c  默认拒绝网关 + 公开白名单
b26b86a2  记录 P3-1 结果与白名单待决问题
44ed15f7  /auth/logout 加入白名单
c26eb183  网关落地后的测试恢复（73/154）
6aba328e  教学域服务端身份（AUTH-104）
d18dc5c0  资产边界 + 登录限流 + 邮箱脱敏
```

## 2. 新窗口必读顺序

1. `AGENTS.md`（第 0 节状态快照已更新到本交接）
2. `docs/testing/ACCEPTANCE_CHARTER.md`
3. **本文件**
4. `docs/audit/2026-08-21-phase2-remediation-matrix-v0.1.0.md`（29 项修复矩阵，含逐项关闭标准）
5. `docs/plans/2026-08-21-rmos-phase3-auth-control-realtime.md`（Phase 3 六批计划）
6. `docs/adr/ADR-2026-08-21-authn-default-deny-and-object-ownership.md`（已 Accepted）
7. `docs/adr/ADR-2026-08-21-robot-binding-and-adapter-registry.md`（已 Accepted，**P3-4/P3-5/P3-6 的依据**）
8. `docs/testing/TEST_REPORT.md`、`docs-archive/DEVELOPMENT_LOG.md` 的 2026-08-22 至 2026-08-25 条目

## 3. 已完成（Phase 3 第 1–3 批）

**实测基线：** 该分支起点 `361eaac8` 上后端全量 `825 passed`；当前 `d18dc5c0` 上 **`956 passed, 0 failed, 0 error in 68.81s`**。

| 批次 | 内容 | 关键实测 |
|---|---|---|
| P3-1 | 默认拒绝网关 + 公开白名单 | 收集器反转后实现前 **103 failed**（= 扣除白名单后可匿名访问的路由-方法组合数）；实现后该文件 179 passed |
| P3-2a | 测试恢复（机械部分） | 全量 154 failed → 81 failed |
| P3-2b | 教学域服务端身份（AUTH-104） | 新规格测试实现前 6 failed / 1 passed；实现后 7 passed；全量转 **934 passed** |
| P3-3 | 资产边界 / 登录限流 / 邮箱脱敏 | 分别 11 / 9 / 9 passed；全量 **956 passed** |

**落地的机制：**

- `app/core/public_routes.py`：7 条公开白名单（用户 2026-08-21 签字 6 条，2026-08-22 追加 `/auth/logout`）
- `app/services/authz_guard.py`：`enforce_authenticated` 网关（挂在 `main.py` 的 `include_router` 上，与端点是否声明依赖无关）；`get_current_actor` 请求级缓存；`ActorContext` 增加 `account_role`（`users.role`）与 `school_name`
- `app/services/access_control.py`：审计操作者只取 `request.state.actor`
- `app/api/v1/endpoints/teaching_roster.py`：6 个端点 10 处身份头全部移除，角色判断改白名单式
- `app/api/v1/endpoints/robots.py`：`_get_visible_robot_or_404` + 3 个资产端点接认证与可见性校验
- `app/services/login_throttle.py`：5 次 / 15 分钟窗口 / 15 分钟锁定，按 (账号, 来源 IP)
- `app/api/v1/endpoints/schools.py`：`_mask_email` 公开教师列表脱敏

**新增的门禁测试（接手后不要削弱它们）：**

| 文件 | 作用 |
|---|---|
| `tests/unit/test_auth_boundary.py` | 全路由参数化：非白名单路由匿名必须 401（收集器已反转，**不得**改回"跳过无认证依赖的路由"） |
| `tests/unit/test_auth_boundary_gate.py` | 白名单钉死 + 生产代码身份头零读取 + 探测器自检 |
| `tests/unit/test_teaching_identity_boundary.py` | 伪造/省略身份头零影响、跨对象 404/403、审计主体等于令牌主体、邮箱脱敏 |
| `tests/unit/test_robot_asset_boundary.py` | 资产匿名 401、跨教师 404、正向可见性 |
| `tests/unit/test_login_throttle.py` | 限流窗口/锁定/清零/不永久锁定/不泄漏账号存在性 |

## 4. 未完成与已知问题（**接手第一件事就是读这一节**）

### 4.1 已知回归：3D 网格加载被打断（最高优先）

`@react-three/drei` 的 `useGLTF` **直接 fetch，不走 `apiClient`、不带令牌**。默认拒绝网关生效后，3D 网格加载返回 401。

- 受影响调用点：`r-mos-frontend/src/components/Viewer3D/InteractiveManifestViewer.tsx:239`、`Atom01AssemblyRenderer.tsx:156`、`RuntimeAssetPreview.tsx:124`
- **修法已有现成先例**：`RuntimeAssetPreview.tsx:63` 已在用"带令牌取回 blob → `URL.createObjectURL` → 交给加载器"的写法，照抄即可
- **不要**为此新开匿名资产路由：`RobotVisibility` 只有 `PRIVATE` / `SHARED`（`app/models/robot_model.py:8-11`），**不存在面向匿名的公开档**，`SHARED` 意为"对已认证用户可见"
- 该修复**必须做浏览器实测**，不能只靠单测与构建

### 4.2 AUTH-101～105 均为 IN_PROGRESS，**未正式关闭**

软件侧实现与定向门禁都已落地，但：

- 浏览器主流程实测未做
- 4.1 的 3D 回归未修
- **4.5 的对象归属大面积缺失**（`AUTH-101` 的归属半边）
- **4.6 的资产拒绝无审计**（`AUTH-103`）

关闭判定放在 Phase 3 收口，须连同浏览器实测一并给结论。**不得因为"全量绿"就宣布关闭。**

### 4.5 已实测确认：认证已关但**对象归属大面积缺失**（与 4.1 同为最高优先）

默认拒绝网关只解决了「匿名」。**认证通过之后，大量接口不比较调用者与目标对象的归属。**

**硬证据（一次性只读探针，内存 SQLite + TestClient，未连真实库）：**

```
acting_as=student_B(id=3)   target=student_A(id=2)
  GET /api/v1/students/2/profile              -> 200   可跨学生读取
  GET /api/v1/students/2/weak-steps           -> 200   可跨学生读取
  GET /api/v1/training/users/2/sessions       -> 200   可跨学生读取
  匿名对照 GET /api/v1/students/2/profile      -> 401   （网关本身生效）
```

复现方式：注册同校教师 1 名 + 学生 2 名，用学生 B 的**真实令牌**请求学生 A 的编号。

**静态核对（已逐条验证，非推断）：**

- `app/api/v1/endpoints/tasks.py:154-157` 的 `get_task_report` 签名只有 `(task_id, db)`，**连 `actor` 参数都没有**。
- `app/api/v1/endpoints/training.py:112-115` 的 `get_session_detail` 同样只有 `(session_id, db)`。
- **`actor.school_name` 在全仓的使用点为 0**（`rg -c 'actor\.school_name' app/` → 0）。ADR-AUTHN D4 的跨校维度只落了载体（P3-2b 加进 `ActorContext`），**没有任何消费方**，因此当前**没有一处能证明跨校访问会被拒绝**。

**这意味着：**

- `AUTH-101` 的「认证」半边已闭合，「对象归属」半边（其最小修复方向明确要求"用认证身份做学生、教师、学校和资源归属校验"）**远未闭合**。对应 `AC-06` / `T-06-E` 的"越权成功 0 次、404 率 100%"目前**不可能达成**。
- 这不是本次改造引入的回归——这些路由改造前是**匿名**可读，现在至少要登录。但**绝不能**据此认为 AUTH-101 可以关闭。

**建议的下一批（优先级高于 P3-4）：** 以 `docs/plans/2026-08-21-rmos-phase3-auth-control-realtime.md` 的 P3-2 口径新开一批「对象归属」，先写失败测试（跨学生 / 跨教师 / 跨校各一组），再逐路由补校验。可复用的正确实现：`app/services/access_control.py` 的 `raise_read_access_denied` / `raise_write_access_denied`（自带拒绝审计与真实资源编号）。

### 4.6 本次改造自身的两处已确认缺陷

| 缺陷 | 位置 | 说明 |
|---|---|---|
| 资产越权拒绝**不写审计** | `robots.py` 的 `_get_visible_robot_or_404` | 用的是 `raise HTTPException(404)`，没走 `raise_read_access_denied`。G1 要求任何拒绝都必须留带真实资源编号的审计。**AUTH-103 因此也不能关闭。** |
| 限流为「先查后写」，非原子 | `app/services/login_throttle.py` | `locked_seconds_remaining` 与 `record_failure` 之间没有互斥，高并发下可能多放行若干次尝试。**尚未实测复现**，属代码形态可疑，需并发专项测试取事实后再判。 |

### 4.3 Phase 3 剩余批次（未开始）

| 批次 | 覆盖 | 依据 |
|---|---|---|
| P3-4 | `CTRL-101`、`CTRL-102`、`CTRL-103` —— 机器人不可变绑定、适配器按机器人隔离、现场检查默认阻断 | ADR-ROBOT D1/D2/D3/D4 |
| P3-5 | `CTRL-104`、`CTRL-105` —— 统一停止通道、并发复现（**20 轮 × 5 并发**，先取事实再决定是否修） | ADR-ROBOT D6/D7 |
| P3-6 | `RT-101`～`RT-104` —— WebSocket 认证与隔离 | ADR-ROBOT D5 |

P3-4 带一个 Alembic 迁移（三表加 `robot_model_id` + `tasks.user_id` 收紧，合并为同一个迁移，`down_revision = "20260817_sop_three_phase"`）。**执行前必须核对 `SELECT id, brand, model_name FROM robot_models WHERE id=1` 确为 ATOM-01。**

### 4.4 本阶段发现、但**刻意未在本阶段修**的既有问题

这些都不是本次改造引入的，单独立项，不要顺手改：

| 编号 | 问题 | 为什么没在本阶段修 |
|---|---|---|
| 两套角色系统 | 注册只写 `users.role`，**全仓无生产代码写 `UserRole`**（只有 seed 脚本写），故 `ActorContext.roles`（RBAC）对正常注册用户恒为空 —— `robots.py:41` 的 `_require_teacher_or_admin` 会拒绝所有自助注册的教师 | 合并两者等于改变"谁能管机器人"，是独立的权限决策 |
| `get_robot` 口径不一致 | `robots.py:150` 对无权访问返回 **403** 且不认 `owner_teacher_id`；本阶段新写的 `_get_visible_robot_or_404` 返回 **404** 且认 owner。G1 要求越权读 404 | 改 `get_robot` 会波及既有测试，属独立对齐工作 |
| ADR-AUTHN D3 措辞 | 该处写"公开入口校验 `visibility=public`"，但该枚举值不存在 | 需按 §4.1 的事实修订 ADR 文本 |
| 8 个假裁决测试 | `r-mos-frontend/src/adjudication/__tests__/` 下 8 个 `.test.ts` 不是 vitest 测试 | CLAUDE.md 标注"勿顺手修，是否重写待决策"，**须用户拍板** |

## 5. 待用户决策（未答复前不得自行推定）

| 编号 | 事项 | 影响 |
|---|---|---|
| D-1 | **3D 查看器修复是否现在做**（需启动前后端 8000 / 55173 做浏览器实测；按 `AGENTS.md` §1.4 启动服务前须先报备） | 决定 Phase 3 能否收口 |
| D-2 | `critical` 级别的多人确认阈值（两名教师 or 一名管理员） | ADR-AI D4；属 Phase 4，不挡 Phase 3 |
| D-3 | 待定项 **J**（现场部署形态 / TLS 终结方 / 备份目标 / RTO-RPO） | `DEP-101`、`DEP-104` 未答复前不得关闭 |
| D-4 | 依赖清单外发 npm 的授权 | `DEP-105` 未授权则保持未关闭，E1 不得提升 |
| D-5 | `CTRL-105` 若 20×5 并发未复现，是否接受"未复现、风险接受" | Phase 5 关闭条件 |
| D-6 | 8 个假裁决测试是否重写 | 见 §4.4 |

## 6. 关于 Codex 的使用记录（重要：**不要把它的输出当成已完成的复核**）

2026-08-25 用 `codex exec -s read-only` 起过三次辅助任务：

1. **对抗性访问控制复核（第一次）** —— 因措辞（"找出绕过方法"）被 OpenAI 安全过滤判为网络安全风险中止，退出码 1，**无结论**。
2. **改用防御性措辞重跑** —— 产出了完整复核意见，裁决为「不通过，需修复后复核」。
3. **全路由归属校验普查** —— 产出了逐路由普查表，核心结论：180 条路由中约 110 条只有「登录/角色」检查、无对象归属；跨校比较 0 处。

**这些输出没有被直接采信。** 其中的关键结论已由接手方（本窗口）独立复核：§4.5 的跨学生读取由一次性探针取得硬证据；`actor.school_name` 使用点为 0 由 `rg` 直接确认；§4.6 的资产拒绝无审计由代码构造直接确认。**未经复核的部分（如限流并发竞态）已标注为"尚未实测复现"，不得当作既成事实。**

**Phase 3 第 1–3 批的全部实现与测试结论均不依赖任何 Codex 输出**，实测命令与结果见 `docs-archive/DEVELOPMENT_LOG.md`。

若新窗口要继续用 Codex：
- 复核类任务用**防御性措辞**（"复核这些防护是否成立"），不要写"找绕过"。
- 一律 `-s read-only`，并从**工作区根目录**运行（曾因 cwd 设成 `r-mos-backend` 导致沙箱无可写临时目录而失败）。
- Codex 的任何结论都必须由接手方独立复核后才能写进报告。

## 7. 固定运行规则（沿用，不得放宽）

1. Python 只用 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv`，每次任务**现场核对**解释器与依赖，不得预填为已就绪。
2. 后端测试命令（工作目录必须是本工作区的 `r-mos-backend`）：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m dotenv \
  -f /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env run -- \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest
```

3. **每次全量测试后检查并恢复 `r-mos-backend/data/knowledge_store.json`**（会被测试改写生成编号与时间）。
4. 先写失败测试、确认它是红的，再最小实现。每批第一个提交只含测试。
5. 只对实际运行的范围下结论；跑定向测试就只说定向结论，不得外推为全量或链路通过。
6. `DATABASE_URL` 不得擅改；CORS 保留 `http://127.0.0.1:55173`；本机 HTTP 用 `curl --noproxy 127.0.0.1,localhost`。
7. 需要启动服务前先说明要起哪些服务与端口。
8. 不得未经许可 push、合并、操作真机、联网跑依赖审计。
9. 每批结束输出 `git diff --name-only` + 关键差异 + 可复制命令 + 真实结果，并按八字段追加 `docs-archive/DEVELOPMENT_LOG.md`；影响验收时同步 `docs/testing/TEST_REPORT.md`。

## 8. 裁决状态（未变）

| 对象 | 状态 |
|---|---|
| 29 项发现 | 5 项 IN_PROGRESS（AUTH-101～105，**未关闭**），24 项 NOT_STARTED |
| E1 软件安全与主链路 | **FAIL** |
| E2 预生产 / E3 真机 / E4 课堂 | **BLOCKED** |
| 生产启用 | **BLOCKED** |
| `REL-BLOCK-01` | **生效中**，未清零 |
| DR-01 至 DR-06 | 未全部真实执行 |
| AI 直接真机动作 | 必须保持 0 |

**后端全量绿 ≠ 任何一项发现已关闭。**

## 9. 新窗口启动提示词

```text
继续 R-MOS 的 Phase 3。先不要改代码，先汇报。

工作区：/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
分支：audit/phase3-auth-control-realtime，提交 d18dc5c0

开始时完整阅读：
1. AGENTS.md
2. docs/testing/ACCEPTANCE_CHARTER.md
3. docs/handover/2026-08-25-phase3-continuation-handover-v0.1.0.md
4. docs/audit/2026-08-21-phase2-remediation-matrix-v0.1.0.md
5. docs/plans/2026-08-21-rmos-phase3-auth-control-realtime.md
6. docs/adr/ADR-2026-08-21-robot-binding-and-adapter-registry.md

先现场确认分支、提交、工作区干净状态和 Python 环境，再向我汇报：
- 你恢复到的准确提交与后端全量实测结果（不要引用交接文档里的数字，自己跑一遍）；
- 你对 Phase 3 已完成 1-3 批、以及 3D 网格加载回归的理解；
- P3-4 的改动边界、先写的失败测试清单、迁移与回滚方案；
- 需要我确认的事项（交接文档第 5 节列了 6 条）。

我确认后再动代码。不要宣布 AUTH-101~105 已关闭，不要合并或推送，
不要把自动测试写成浏览器实测或真机通过。
```

## 10. 本次交接没有做的事

- 没有修 3D 网格加载回归（§4.1）
- 没有做浏览器实测
- 没有关闭任何一项发现
- 没有启动前端、后端、数据库或真机
- 没有联网、没有跑依赖审计
- 没有合并、没有推送
