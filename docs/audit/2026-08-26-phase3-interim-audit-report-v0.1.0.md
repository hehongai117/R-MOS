# R-MOS Phase 3 中期审查报告（代码冻结点）

- 版本：0.1.0
- 日期：2026-08-26
- 状态：**Active**（Phase 3 进行中，本报告是用户下令冻结代码后的中期结论）
- 报告提交：`audit/phase3-auth-control-realtime` @ 本报告所在提交（**未 push、未合并**）
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`
- 前序材料：`docs/audit/2026-08-21-phase1-six-chain-review-v0.1.0.md`（29 项发现）、`docs/audit/2026-08-21-phase2-remediation-matrix-v0.1.0.md`（修复矩阵）

## 0. 本报告是什么、不是什么

**是：** 对 Phase 0 至 Phase 3 当前状态的一次核对，全部结论由本人在本机实际执行命令取得，不引用他人报告中的数字。

**不是：** 不是 Phase 3 的完成报告（Phase 3 未完成）；不是任何一项发现的关闭裁决；不是 E1 至 E4 的验收。

**证据等级：** 本报告全部结论为 **E1**（当前静态代码、配置、自动化测试与本机一次性只读探针），外加一次**本机开发环境的浏览器验证**（不等于 E2）。**没有** E2 预生产、E3 真机、E4 课堂证据。

## 1. 阶段边界与代码冻结的事实核对

用户要求确认「审查阶段是否动过代码」。实测：

```bash
git diff --name-only 213775c6^..09ec02a1 | grep -cE '^(r-mos-backend/app|r-mos-frontend/src|r-mos-backend/main.py)'   # → 0
git diff --name-only 09ec02a1..361eaac8  | grep -cE '^(r-mos-backend/app|r-mos-frontend/src|r-mos-backend/main.py)'   # → 0
```

| 阶段 | 定位（依据 Phase 2–6 交接文档 §7） | 应用代码改动 |
|---|---|---|
| Phase 0 | 章程与事实源登记 | **0 个文件** ✅ |
| Phase 1 | 六链路只读审查 | **0 个文件** ✅ |
| Phase 2 | 安全架构与修复规格，「本阶段默认不改应用代码」 | **0 个文件** ✅ |
| Phase 3 | **AUTH/CTRL/RT 基础修复**，「以失败测试先行，修复身份边界……」 | **有**（按设计） |

**结论：审查阶段（0–2）的代码冻结被严格遵守。** Phase 3 按其定义就是修复阶段，不是审查阶段。

Phase 3 的代码改动分两段：

- **本报告作者接手之前**（`361eaac8..08a637b2`，上一窗口）：9 个应用文件 —— `auth.py`、`robots.py`、`schools.py`、`teaching_roster.py`、`core/public_routes.py`、`services/access_control.py`、`services/authz_guard.py`、`services/login_throttle.py`、`main.py`。
- **本轮**（`08a637b2..HEAD`）：21 个应用文件（前端 17 + 后端 4），见第 3 节。

自本报告起，**代码冻结生效**，不再新增修复。

## 2. 当前测试基线（本人实测）

| 范围 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `python -m dotenv -f <主工作区 .env> run -- python -m pytest -q` | **971 tests，进度条 `F`=0 / `E`=0，退出码 0** |
| 前端全量 | `npx vitest run` | **70 files，518 passed / 2 skipped** |
| 前端构建 | `npm run build` | `✓ built`，退出码 0 |
| 前端类型 | `npx tsc --noEmit` | 无输出，退出码 0 |

后端基线演进：Phase 1 起点 `825` → P3-1～P3-3 收口 `956` → 本轮 `971`（+15 为本轮新增的对象归属门禁）。

**测试副作用：** `r-mos-backend/data/knowledge_store.json` 每次全量后被改写，已核对并恢复，与批次开始前备份**逐字节一致**（sha256 `6d00252d…0475f`）。

> **后端全量绿 ≠ 任何一项发现已关闭。** 现有测试不覆盖本报告第 5 节列出的越权面。

## 3. Phase 3 已完成的批次与实测证据

| 批次 | 内容 | 实测 |
|---|---|---|
| P3-1 | 默认拒绝网关 + 公开白名单（7 条） | 收集器反转后实现前 103 failed；实现后该文件 179 passed |
| P3-2a | 网关落地后的测试恢复 | 全量 154 failed → 81 failed |
| P3-2b | 教学域服务端身份（AUTH-104 的身份头面） | 定向 7 passed；全量转 934 |
| P3-3 | 机器人资产边界 / 登录限流 / 教师邮箱脱敏 | 分别 11 / 9 / 9 passed；全量 956 |
| **P3-3b** | **3D 资产带令牌加载**（修复网关引入的 401 回归） | 门禁 7 passed；**浏览器实测**：`/3d-viewer` 与 `/maintenance` 的 `/api/v1/robots/*` 请求 **26 条全 200、401 数为 0**，`.glb` 24 条全 200，全页 4xx/5xx 为 0，模型渲染正常 |
| **P3-2c** | **对象归属校验第一刀**（8 条路由） | 实现前 12 failed / 3 passed；实现后 15 passed；全量 971 |

P3-3b 与 P3-2c 为本轮完成。浏览器实测前以「匿名资产 401 / 带令牌 200」探针自证被测对象是**已启用网关**的本工作区代码，排除了用旧后端产生假绿的风险。

## 4. 29 项发现的当前状态

| 分类 | 数量 | 状态 |
|---|---|---|
| `AUTH-101`～`AUTH-105` | 5 | **IN_PROGRESS，一项都未关闭** |
| `CTRL-101`～`CTRL-105` | 5 | NOT_STARTED |
| `RT-101`～`RT-104` | 4 | NOT_STARTED |
| `EVID-101`～`EVID-105` | 5 | NOT_STARTED |
| `AI-101`～`AI-105` | 5 | NOT_STARTED |
| `DEP-101`～`DEP-105` | 5 | NOT_STARTED |

**AUTH 五项逐项不关闭的理由（全部为实测事实）：**

- **`AUTH-101`（P0）**：认证半边已闭合（默认拒绝网关），**归属半边远未闭合**。本轮只覆盖 8 条路由。全仓 `app/api/v1/endpoints/` 下 **180 条路由中 122 条**在函数签名层面拿不到调用者身份（AST 普查，本轮修复后复测）。`AC-06`/`T-06-E` 的「越权成功 0 次、404 率 100%」不成立。
- **`AUTH-102`**：边界测试已反转并覆盖全路由（178 条参数化），但它只断言**匿名 401**，不断言归属，故不能随 AUTH-101 一起关闭。
- **`AUTH-103`**：资产可见性已收紧，但 `robots.py` 的 `_get_visible_robot_or_404` 仍用裸 `HTTPException(404)`、**不写拒绝审计**，违反 G1「任何拒绝都必须留带真实资源编号的审计」。
- **`AUTH-104`**：`teaching_roster.py` 的 10 处身份头已移除，但该文件 **21 条路由中仍有 15 条没有任何调用者身份**，其中包含写操作（见第 5 节 N-01/N-02）。身份头问题解决 ≠ 教学域授权解决。
- **`AUTH-105`**：限流已落地（5 次/15 分钟窗口/15 分钟锁定），但为进程内状态，多副本部署失效；且尚未做并发竞态的实测（交接文档标注为「代码形态可疑、未复现」，本轮**未验证**，不得当作已确认或已排除）。

## 5. 本轮新发现（不计入原 29 项，单独登记）

编号规则沿用 `AUTH-SCHOOLS-PII` 的先例：Phase 2/3 取证新发现的暴露面单独跟踪。

### N-01（**P0，已实证**）｜任何已登录学生可篡改任意作业尝试的状态与分数

`app/api/v1/endpoints/teaching_roster.py:708` 的 `update_attempt_status` 与 `:727` 的 `grade_attempt` 函数签名只有 `(attempt_id, request, db)` —— **没有 `actor`、没有角色判断、没有归属校验**。

**一次性只读探针硬证据**（内存 SQLite + TestClient，未连真实库，未改仓库文件）：

```
教师 id=1   学生A id=2（尝试所有者）   学生B id=3   attempt_id=1

匿名  POST /api/v1/attempts/1/grade            -> 401     （网关本身生效）
学生B PATCH /api/v1/attempts/1 {"status":"completed"}  -> 200  status=completed
学生B POST  /api/v1/attempts/1/grade {"score":100}     -> 200  score=100.0

数据库最终状态: score=100.0  status=graded
```

即：**学生用自己的合法令牌，把别人的作业分数改成了 100 并落库。** 按 G1，越权写必须返回 403 并记录带真实资源编号的审计；当前两者皆无。

对教培产品而言这是成绩可篡改，影响 `AC-04`/`AC-05` 的成绩与报告一致性，也使 G2「任意有副作用的动作须走审批」不成立。

### N-02（P1，已实证）｜学生可执行教学域写操作

同一探针：`POST /api/v1/classes` 以学生令牌调用返回 **201**（成功创建班级）。`teaching_roster.py` 中 `create_class`、`create_course`、`enroll_student`、`create_attempt`、`create_evidence_card` 等写入口同样无角色门。

### N-03（P1，已确认）｜训练反馈的视角由客户端查询参数决定

`app/api/v1/endpoints/training.py:506` 的 `role: str = Query(default="student", pattern="^(student|teacher)$")`，`:549` 据此选择 `FeedbackRole.TEACHER`。与 `AUTH-104` 的伪造身份头同类：**权限相关的视角不得由客户端输入决定**。

本轮为其写了门禁用例 `test_feedback_role_query_param_cannot_grant_teacher_view`，但**该用例当前空转通过**（测试会话无 `TrainingSubmission`，端点在读 `role` 前先 404），**不构成该参数已受控的证据**。测试文件内已如实标注。

### N-04（P1，已确认）｜assessments 域 11 条路由无归属维度且无人调用

`app/api/v1/endpoints/assessments.py` 共 11 条路由，**全部**没有调用者身份。数据模型 `AssessmentProvider` / `ExternalAssessment`（`app/models/assessment.py`）**没有 owner、student、school 中的任何一个字段**，因此当前**不存在可比较的归属维度**——要做归属校验必须先加租户列（数据结构变更 + 迁移 + ADR）。

消费方普查：`r-mos-frontend/src` 零引用，`r-mos-backend/tests` 零引用。即这是一组**无人调用、但任何已登录用户都能命中**的活 HTTP 面，可创建、撤销（`/revoke`）、申诉（`/dispute`）、恢复（`/reinstate`）外部评估记录。

**用户已裁决：直接删除。** 因代码冻结，该删除**已批准、待执行**，见第 8 节。

### N-05（P2，已确认）｜两套角色系统导致 `list_tasks` 的特权判断恒不成立

`app/api/v1/endpoints/tasks.py:128`：`is_privileged = bool({"teacher", "admin"} & actor.roles)`。

而 `actor.roles` 来自 RBAC 表 `user_roles`，**生产代码从不写入该表**（`grep -rn "UserRole(" app/` 在排除模型定义后无命中；只有 `scripts/seed_acceptance_users.py`、`scripts/seed_demo_full.py` 会写）。因此对所有**正常注册**的教师，`actor.roles` 恒为空集，`is_privileged` 恒为 `False`，教师在维保报告列表页只能看到自己的任务。

这是**功能缺陷**（教师看不到学生任务）与**授权口径不一致**（同仓 `robots.py` 与本轮新增的 `ownership.py` 都改用 `account_role`）并存。合并两套角色系统属独立权限决策，须用户拍板，本轮未动。

### N-06（P2）｜3D 资产加载无令牌刷新重试

P3-3b 的 `useAuthedGLTF` 在创建 `GLTFLoader` 时注入一次 Bearer 令牌。`apiClient` 有 401 刷新重试，`GLTFLoader` 没有。access token 在长时间停留 3D 页时过期，后续 mesh 加载失败需重进页面。属本轮引入的已知边界，已在开发记录中标注为未做。

### N-07（文档，已修）｜审查索引曾为过期事实源

`docs/audit/README.md` 是 `AGENTS.md` 第 0 节点名的「架构审查基线」。核对时它仍写「阶段 = Phase 1 六链路审查完成」「生产代码改动 = 无」，而 Phase 2 已完成、Phase 3 已改 5 批生产代码。已于提交 `6cb81ada` 刷新。

## 6. 对既有材料的事实更正

本轮核对中发现**前序文档存在两处与代码不符**，已在对应文档内更正：

1. **交接文档 §4.1 的 3D 回归范围不准确**：原列 3 个受影响调用点，其中 `RuntimeAssetPreview.tsx:124` **不受影响**（它接收的是 `apiClient` 取回后生成的 blob URL，是该文档自己称的「先例」本身）；实际受影响面为 **11 个文件 + 1 处裸 `fetch`**，原文漏列 `ManifestDrivenRenderer`、`Atom01Model`、`atom01/InteractiveLinkMesh`、`atom01/SubPartsGroup`、`ModelPreloader`（3 处 preload）与 `hooks/useAtom01AssemblyData.ts`。
2. **归属缺失的规模数字**：交接文档引用的外部普查为「约 110 条」，本人 AST 全量普查为**修复前 130 条 / 修复后 122 条**（分母 180，含 7 条白名单公开路由）。报告以本人实测为准。

## 7. 当前裁决（未变）

| 对象 | 裁决 | 依据 |
|---|---|---|
| E1 软件安全与主链路 | **FAIL** | 第 4、5 节的越权面仍然成立 |
| E2 预生产非功能 | **BLOCKED** | 无预生产环境与演练证据 |
| E3 真机安全 | **BLOCKED** | 未连接真机；`ROBOT_MODE` 保持模拟 |
| E4 课堂试点 | **BLOCKED** | 20 场课堂未执行 |
| 生产启用 | **BLOCKED** | `REL-BLOCK-01` 未清零 |
| `DR-01` 至 `DR-06` | 未全部真实执行 | — |
| AI 直接真机动作 | 保持 **0** | — |

**本轮的 5 批修复没有提升任何一项验收状态。** 修复使部分越权面收窄，但 N-01 的成绩篡改属新确认的 P0，E1 的 FAIL 判定因此更加牢固而非松动。

## 8. 待用户决策

| 编号 | 事项 | 状态 |
|---|---|---|
| D-1 | 3D 修复与浏览器实测 | ✅ 已批准并完成 |
| **D-7** | **删除 assessments 域 11 条路由**（N-04） | **已批准，因冻结待执行**。执行范围：删除 `app/api/v1/endpoints/assessments.py`、其路由注册、相关 schema；`app/models/assessment.py` 是否一并删除需另行确认（涉及数据表） |
| D-8 | Phase 3 是否继续推进修复，还是就此转入报告/交接 | **待答复**（本报告即为决策依据） |
| D-9 | 两套角色系统是否合并（N-05） | 待答复；属独立权限决策 |
| D-2 | `critical` 多人确认阈值 | 待答复（属 Phase 4，不挡 Phase 3） |
| D-3 | 待定项 J（部署形态 / TLS / 备份 / RTO-RPO） | 待答复；`DEP-101`、`DEP-104` 不得关闭 |
| D-4 | 依赖清单外发 npm 授权 | 待答复；未授权则 `DEP-105` 保持未关闭 |
| D-5 | `CTRL-105` 未复现时是否接受风险 | 待答复；**建议先在 PostgreSQL 上复跑**，SQLite 的写锁语义会掩盖竞态 |
| D-6 | 8 个假裁决测试是否重写 | 待答复 |

## 9. 如果继续修复，建议的优先级

按实测严重性，而非原计划顺序：

1. **N-01 / N-02（教学域写操作无授权）** —— 成绩可篡改，P0，且修复面集中在 `teaching_roster.py` 一个文件。
2. **`AUTH-103` 的资产拒绝审计** —— 两行改动，`_get_visible_robot_or_404` 改走 `raise_read_access_denied`。
3. **N-03（`role` 查询参数）** —— 需先补一条带 `TrainingSubmission` 的用例让门禁真跑到分支。
4. 继续扩大归属覆盖：`agent_*`、`maintenance.py`、`sops.py`、`fault_cases.py`。
5. 原计划的 P3-4（机器人绑定与适配器隔离，带 Alembic 迁移）、P3-5（停止通道与并发复现）、P3-6（WebSocket 认证与隔离）。

## 10. 本报告没有做的事

- 没有关闭任何一项发现。
- 没有提升 E1 至 E4 或解除任何生产阻断。
- 没有执行 N-04 的删除（冻结中）。
- 没有验证 `AUTH-105` 的并发竞态、没有跑 `CTRL-105` 的 20×5 并发。
- 没有做 E2 预生产、E3 真机、E4 课堂的任何验证。
- 没有联网、没有跑依赖审计、没有操作真机、没有 push、没有合并。
