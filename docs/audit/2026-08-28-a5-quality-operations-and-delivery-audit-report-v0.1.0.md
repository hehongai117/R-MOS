# A5 质量、运行与交付能力审计报告

- 版本：0.1.0
- 日期：2026-08-28
- 状态：**Ready for Board Review**（异源复核已完成，3 条 MISMATCH 已关闭、6 个独立发现已并入；等待董事会确认）
- 阶段：A5（董事会方向指令 0.2.0 §A5）
- 被审对象：整个 R-MOS 项目
- 现状基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 上游输入：[A1（0.1.1）](./2026-08-26-a1-system-function-and-asset-inventory-v0.1.1.md)、[A2](./2026-08-27-a2-user-roles-and-business-closure-audit-report-v0.1.0.md)、[A3](./2026-08-27-a3-current-architecture-and-data-boundaries-v0.1.0.md)、[A4（提交 `cef83be2`）](./2026-08-28-a4-security-control-and-realtime-audit-report-v0.1.0.md)
- 主审：Claude｜异源复核：Codex
- 生产代码改动：**0**

## 1. 执行摘要

A5 回答「现有证据能证明什么，系统能否稳定交付」。

**测试体系比前几个阶段的印象要好，这点必须先讲清楚。** 后端 `tests/` 下 743 个测试函数共
**2468 条断言，每函数中位数 3 条**；无 `assert` 的函数 21 个（其中 18 个用 `pytest.raises` 表达预期，**真正零断言的只有 3 个**）；全部只断 `status_code` 的浅断言 49 个。
这不是一个"假绿"的测试套件。CI 也不是摆设：4 个 workflow 中 `backend-ci` 起真实
`postgres:16` 服务并执行 **`alembic upgrade head` + `alembic check`**（后者能检出模型与迁移的漂移），
PG 专属门禁与 `tests/e2e/` 在**真 PostgreSQL** 上单独跑；`integration-ci` 真实启动 uvicorn、
轮询 `/api/v1/health` 就绪、无论成败都上传后端日志；`frontend-ci` 有
`tsc --noEmit` + `eslint --max-warnings 0` + vitest + 覆盖率 + 构建五道关。

**但"测试证明了什么"要按边界说清楚：**

1. **主测试套件跑在内存 SQLite 上，且不执行迁移。** `tests/conftest.py` 用
   `sqlite+aiosqlite:///:memory:`，建表用 `Base.metadata.create_all`，**38 个 alembic 迁移在主套件中从不执行**。
   这是**已知且有文档说明的取舍**——`backend-ci` 内的注释写明原因是 asyncpg 跨事件循环问题（Linux 必现），
   并注明属 P2-1 测试体系升级范围。方言盲区由「真 PG 上跑 e2e」这一步部分补偿，
   但**业务逻辑主体从未在 PostgreSQL 上被验证过**。
2. **授权与对象归属测试是成体系的——主审两次判错，此处为最终修正。**
   代码库对归属违规**返回 404 而非 403**（不泄露对象存在性，是更好的做法），
   主审前两稿只检索 `403`，因此完整漏掉了专门的边界测试文件。实际情况：
   - `tests/e2e/test_object_ownership_boundary.py`：学生 B 用**自己的合法令牌**读学生 A 的
     资料／训练／任务／报告／事件／会话／反馈并断言 404（参数化覆盖多条路径模板）；
     另有 `test_cross_school_teacher_read_returns_404`（**跨校隔离**）、
     `test_legacy_task_without_owner_is_denied`、
     `test_feedback_role_query_param_cannot_grant_teacher_view`（**查询参数提权防护**），
     以及 `test_student_can_read_own_data`、`test_same_school_teacher_can_read_student` 两条正向边界。
   - `tests/unit/test_teaching_identity_boundary.py`：伪造 `X-RMOS-Role`／`X-User-ID`、省略角色头均不得放宽范围。
   - `tests/unit/test_authz_guard_api.py`、`tests/e2e/test_e2e_cross_role_access.py`、
     `tests/unit/test_agent_authz.py`、`tests/unit/test_auth_boundary.py`、红队批次 `test_redteam_batch_j003_api.py`。
   - 拒绝类断言合计：**28 处 `== 403` + 72 处 `== 404`（分布在 15 个文件）**。

   **仍然成立的缺口**：这些测试集中在**读路径**（跨用户读→404）。A4 点名的高危**写**端点中，
   `DELETE /sops/{id}`、`POST /maintenance/drafts/{id}/approve`、`POST /adapter/inject-fault`
   所在文件既无 403 也无归属边界用例。

   > **主审自查与复核修正（两次）：** 初稿写「没有任何一条测试覆盖越权访问」——错，
   > 该结论从 A4 门禁 G3 对三个端点的观察被错误推广到全仓。自查后改为「存在但点状」——
   > **仍然过轻**，因为检索只用了 `403`，漏掉了整个以 404 表达归属拒绝的测试体系（异源复核指出）。
   > **A4 报告 §9 G3 的「没有一条测试尝试越权访问」同样错误**，已登记为 A4 待修订项（见 §10）。

3. **A1 记录的两处缺陷在本基线仍然存在**：前端 8 个无测试声明的 `.test.ts`（vitest 不收集）、
   后端 `schemas/tests/` 下 7 个不在 `testpaths` 内的文件。

**运行与交付侧的缺口更明确：**

| 能力 | 现状 |
|---|---|
| 依赖漏洞扫描 | **无**（无 pip-audit／safety／npm audit／dependabot） |
| 外部监控／APM | **无**（无 Sentry／Prometheus／OpenTelemetry） |
| 日志 | 写本地 `logs/app_YYYYMMDD.log`（按日期滚动），**compose 未挂载该目录** |
| 备份 | **无脚本、无演练** |
| 恢复／回滚 | 有计划文档，但该文档**自述**「真实回滚演练未执行」「没有正式监控、告警、备份、恢复和版本回滚脚本」 |
| 密钥治理 | ✅ `validate_production()` 在 `DEBUG=False` 时拦截默认密钥与 SQLite URL，且**确实在 `main.py` 中被调用**；`.env` 未被跟踪 |

**交付裁决维持不变：** E1 FAIL、E2／E3／E4 BLOCKED、生产启用 BLOCKED、`REL-BLOCK-01` 未清零。

**M-AUD-08（运行证据无隐含空白）：** 本批未申请也未获批受控 E2 环境，
因此全部运行能力按 §7 逐项标记为 `E2_NOT_COLLECTED` 或 `E2_BLOCKED`，无一项留空。
按 §A5 规则，**这不表示运行、恢复或交付能力通过**；A6 的相关维度只能写 UNKNOWN/BLOCKED。

**本批未执行测试套件、未启动长驻服务、未连真机，验证等级上限 E1。**

## 2. 方法与口径

| 项 | 内容 |
|---|---|
| 测试质量 | AST 遍历 `tests/**/test_*.py`，统计每个 `test_` 函数的 `assert` 数、`pytest.raises`、mock 用量、skip 标记；「浅断言」定义为**全部断言都只检查 `status_code`** |
| 测试基座 | 读 `tests/conftest.py` 的引擎构造与建表方式 |
| CI | 逐个读 `.github/workflows/*.yml` 的 services、env、run 步骤 |
| 运行与部署 | `docker-compose.yml`、两个 `Dockerfile`、`app/core/logging.py`、`app/core/config.py` |
| 交付证据 | `docs/testing/TEST_REPORT.md`、`docs/testing/ACCEPTANCE_CHARTER.md`、回滚计划文档 |
| 未做的事 | **未执行任何测试套件**（避免副作用与耗时）、未启动长驻服务、未连真机、未申请 E2 环境 |

**方法局限：**
1. 测试质量是**静态**指标。断言数多不等于断言对；`assert response.status_code == 200` 计 1 条断言，
   但证明力远低于对返回内容的结构性断言。本批只能区分"有无断言"与"是否只断状态码"，
   **不能评价断言是否切题**。
2. 未执行测试意味着**本批不产生任何新的 PASS/FAIL 结论**，只核对既有记录的可追溯性。
3. CI 的实际运行历史（哪些 workflow 真的在跑、通过率如何）需要 GitHub Actions 运行记录，
   本批只读了配置文件，**未核实 CI 的实际执行情况**——标记为 UNKNOWN。

## 3. 测试可信度（表 1）

| Test_ID | 声称证明 | 实际执行分支 | 数据 | 断言路径 | 假绿风险 | 可支持结论 |
|---|---|---|---|---|---|---|
| **T-01** | 后端主套件（971 用例／743 函数） | 本地与 CI 均**裸跑**：内存 SQLite + `create_all` | 每测试自建 | 2468 条断言，中位数 3 | **中**：方言盲区（SQLite≠PG）、迁移未执行 | 业务逻辑在 SQLite 语义下自洽；**不能证明 PostgreSQL 上可用** |
| **T-02** | PG 专属门禁（`test_audit_query_index_gate`、`test_skill_registry_migration_gate`） | CI 中在真 `postgres:16` 上跑 | 真实迁移后的库 | 索引存在性 + 执行计划 | 低 | 审计索引与技能注册迁移在 PG 上成立 |
| **T-03** | `alembic upgrade head` + **`alembic check`** | CI 真 PG | — | 迁移可应用 + 无模型漂移 | 低 | **迁移链在 PG 上可用且与模型一致**——这是主套件缺口的关键补偿 |
| **T-04** | `tests/e2e/` on PostgreSQL | CI 独立 `rmos_e2e` 库，per-test drop/create_all | 真 PG | 端到端流程 | 低 | 注释明写「消除 SQLite 方言盲区」；覆盖面限于 e2e 用例 |
| **T-05** | 前端 vitest（70 文件／518 用例） | CI：`tsc --noEmit` → `eslint --max-warnings 0` → vitest → coverage → build | jsdom + mock | — | 中：重度 mock | 组件与逻辑单元自洽 |
| **T-06** | `integration-ci` 真起服务 | uvicorn + `/api/v1/health` 轮询 + 日志 artifact | 真 PG | 健康就绪 | 低 | **进程能起来、健康端点可达**——目前最接近"可运行"的证据 |
| **T-07** | `e2e-browser-ci`（Playwright） | 真 PG + preflight 脚本 + 浏览器 | 真 PG | 浏览器流程 | 低 | 浏览器路径可达（本批未核实实际运行历史） |
| **T-08** | 前端 `adjudication/__tests__/` 8 个 `.test.ts` | **不被 vitest 收集** | — | **无 `describe`／`it`** | **高（空转）** | **零证明力**；A1 已登记，本批复核仍存在 |
| **T-09** | `r-mos-backend/schemas/tests/` 7 个 `test_*.py` | **不在 pytest `testpaths` 内，从未收集** | — | — | **高（空转）** | **零证明力**；A1 已登记 |
| **T-10** | 越权/对象归属测试 | **成体系**：`test_object_ownership_boundary.py`（跨学生/跨校读→404、遗留无主任务拒绝、查询参数提权防护、两条正向边界）+ `test_teaching_identity_boundary.py`（伪造角色头/用户ID）+ 跨角色 e2e + 红队批次 | 多身份夹具（两学生 + 同校/跨校教师） | **28 处 `403` + 72 处 `404`**（15 文件） | 低（读路径）／**高（写路径）** | 可证明**读路径**的对象归属与跨校隔离成立；**写路径**的高危端点（`sops` 删除、维保审批、故障注入）无对应用例 → 这部分仍是 UNKNOWN |
| **T-11** | 无直接断言的测试 | 执行但无 `assert` 语句的函数 **21 个**，其中 18 个用 `pytest.raises` 表达预期（有效断言），**真正无任何断言的 3 个** | — | 无 | **高**（仅那 3 个） | 3 个分别在 `tests/e2e/test_agent_execute.py::test_execute_response_schema`、`tests/test_robot_service.py::test_file_size_ok`、`tests/test_storage.py::test_delete_missing_is_noop` |
| **T-12** | 浅断言测试（49 个） | 只断 `status_code` | — | 仅状态码 | 中 | 只能证明"未 500"，不证明返回内容正确 |

**总体判断：测试套件本身不是假绿，但它的证明边界比表面数字窄。**
「971 passed」在报告里出现时，应当同时说明：跑在 SQLite 上、不含迁移、不含授权验证。

## 4. 运行与部署（表 2）

| Ops_ID | 配置来源 | 默认值 | 密钥 | 监控 | 备份 | 恢复 | 当前证据等级 |
|---|---|---|---|---|---|---|---|
| **O-01** 应用配置 | `app/core/config.py`（pydantic-settings）+ `.env` | `DEBUG=False`、`SECRET_KEY="dev-only-change-me"`、`STORAGE_BACKEND=local` | ✅ `validate_production()` 拦截默认密钥与 SQLite URL，**已在 `main.py` 调用**；`.env` 未被 git 跟踪 | — | — | — | E1 |
| **O-02** 容器编排 | `docker-compose.yml` | 4 服务（postgres:16-alpine、backend、frontend、minio），**无 replicas** | 环境变量占位，默认值为 `changeme`／`dev-only-change-me` | 无 | `pgdata`／`miniodata` 卷 | — | E1 |
| **O-03** 日志 | `app/core/logging.py` | `LOG_LEVEL=INFO`，`FileHandler → logs/app_{YYYYMMDD}.log`（文档字符串误写为 `app.log`） | — | **无集中采集** | **compose 未挂载 `logs/`** | 容器重建后日志丢失 | E1 |
| **O-04** 监控／告警 | — | — | — | **无 Sentry／Prometheus／OpenTelemetry** | — | — | **E2_NOT_COLLECTED** |
| **O-05** 依赖治理 | `requirements.txt`（25 项）、`package.json`（26 prod + 27 dev） | — | — | **无 pip-audit／safety／npm audit／dependabot** | — | — | E1（清单存在，**无漏洞扫描**） |
| **O-06** 备份 | — | — | — | — | **无脚本、无演练** | — | **E2_NOT_COLLECTED** |
| **O-07** 恢复／回滚 | `docs/plans/2026-08-10-…-deployment-rollback-v0.1.0.md` | — | — | — | — | 文档**自述**「真实回滚演练未执行」「没有正式监控、告警、备份、恢复和版本回滚脚本」 | **E2_BLOCKED**（文档为 E0，演练未做） |
| **O-08** 升级 | alembic 迁移链（38 个，单 head） | — | — | — | — | CI 验证 `upgrade head` + `check`；**无降级演练** | E1（升级），**E2_NOT_COLLECTED**（降级） |
| **O-09** 断网／降级 | 代码中有 LLM `mock_fallback`、pgvector SAVEPOINT 隔离 | `LLM_ENABLE_MOCK_FALLBACK=true` | — | — | — | **无断网演练证据** | **E2_NOT_COLLECTED** |
| **O-10** 预生产环境 | — | — | — | — | — | — | **E2_BLOCKED**（环境不存在） |
| **O-11** 真机 | `ROBOT_MODE=simulation`，适配器只有 Mock 实现 | simulation | — | — | — | — | **E3 BLOCKED**（A2／A4：无控制、无急停） |
| **O-12** 课堂 | — | — | — | — | — | — | **E4 BLOCKED** |

## 5. 交付证据（表 3）

| Gate_ID | 要求等级 | 当前证据 | 判定 | 缺口 |
|---|---|---|---|---|
| **G-E1 软件与主链路** | E1 | 自动测试通过，但 Phase 1 已确认反证 | **FAIL** | A4 新增 15 项安全发现，缺口扩大 |
| **G-E2 预生产非功能** | E2 | 无预生产环境、无性能/断网/恢复演练 | **BLOCKED** | 全部 |
| **G-E3 真机安全** | E3 | 无真机、适配器无控制与急停能力 | **BLOCKED** | 全部 |
| **G-E4 课堂试点** | E4 | 无试点记录 | **BLOCKED** | 全部 |
| **G-REL 生产启用** | 全部 | `REL-BLOCK-01` 未清零 | **BLOCKED** | 依赖上述全部 |
| **G-DOC 文档门禁** | E0/E1 | `TEST_REPORT.md` 自带「只记录能绑定到具体提交和环境的实际结果」规则，HISTORICAL 快照单列 | **PASS** | 仅文档门禁，不代表应用验收 |
| **G-CI CI 配置完备性** | E1 | 4 个 workflow 覆盖后端（含真 PG 迁移与门禁）、集成、浏览器 e2e、前端五道关 | **PASS（配置层）** | **CI 实际运行历史未核实 → UNKNOWN** |

### 5.1 退出门禁「每项 PASS 可追溯」的核对

`TEST_REPORT.md` 现有 PASS 条目均记录了提交号与判定范围，例如
「Phase 3 第 2c 批：提交 `c7ad217a`；定向 15 passed；后端全量 971 tests / 0 failed（退出码 0）」，
并明确标注「只覆盖 8 条路由；全仓约 115 条路由仍无归属校验，`AUTH-101` 不关闭」。
**该文件的记录纪律满足本门禁要求**：有提交、有命令、有关键输出、有范围限定。

需降级的项：**CI 的实际执行历史**（哪些 workflow 真的跑过、结果如何）本批未核实，
按门禁规则记为 **UNKNOWN**，不得作为 PASS 依据。

## 6. 受控 E2 采集清单（表 4，M-AUD-08）

**本批未申请受控 E2 环境**，全部运行能力按下表标记，无一项留空：

| Evidence_ID | 能力 | 现有证据 | 等价环境申请 | 批准状态 | 状态标记 | A6/R1 限制 |
|---|---|---|---|---|---|---|
| **EV-01** | 服务可启动与健康就绪 | `integration-ci` 起 uvicorn + health 轮询（配置层证据） | 建议：单机 compose 全栈拉起 | 未申请 | **E2_NOT_COLLECTED** | A6 运行维度 UNKNOWN |
| **EV-02** | 迁移升级 | CI `alembic upgrade head` + `check`（配置层） | 建议：在等价库上跑一次并留原始输出 | 未申请 | **E2_NOT_COLLECTED** | 同上 |
| **EV-03** | 迁移降级／回滚 | 无 | 建议：`downgrade` 演练 | 未申请 | **E2_NOT_COLLECTED** | A6 回滚维度 BLOCKED |
| **EV-04** | 备份与恢复 | 无脚本、无演练 | 建议：pg_dump/restore 演练 + RTO/RPO 实测 | 未申请 | **E2_NOT_COLLECTED** | A6 恢复维度 BLOCKED |
| **EV-05** | 断网与依赖失效降级 | 代码有 LLM mock fallback、pgvector SAVEPOINT 隔离 | 建议：断开 LLM/对象存储后观察降级 | 未申请 | **E2_NOT_COLLECTED** | A6 韧性维度 UNKNOWN |
| **EV-06** | 性能与并发 | 有 Lighthouse／WS 探针脚本（未入 package.json），基线文档为 HISTORICAL | 建议：等价环境重采 | 未申请 | **E2_HISTORICAL** | 旧基线不得用作当前结论 |
| **EV-07** | 浏览器端到端 | `e2e-browser-ci` 配置存在；`TEST_REPORT` 记有一次 P3-3b 浏览器实测 PASS（提交 `70e9c078`） | 建议：在当前基线重跑 | 未申请 | **E2_HISTORICAL** | 限于该提交与该场景 |
| **EV-08** | 监控与告警 | 无 | 建议：接入后采集 | 未申请 | **E2_NOT_COLLECTED** | A6 可观测性维度 BLOCKED |
| **EV-09** | 真机安全 | 无真机；适配器无控制与急停 | — | 环境不可得 | **E2_BLOCKED**（E3 层面） | A6 真机维度 BLOCKED |
| **EV-10** | 课堂试点 | 无 | — | 环境不可得 | **E2_BLOCKED**（E4 层面） | A6 交付维度 BLOCKED |

**M-AUD-08 达标：** 10 项运行能力全部有明确状态标记，无隐含空白。

## 7. 关键发现

| 发现 | 事实 | 证据 |
|---|---|---|
| **A5-F-01** | 后端主测试套件跑在**内存 SQLite** 且**不执行迁移**（`create_all`）；这是有文档说明的已知取舍（asyncpg 跨事件循环，属 P2-1 范围），方言盲区由「真 PG 上跑 e2e」部分补偿 | `tests/conftest.py`、`backend-ci.yml` 注释 |
| **A5-F-02** | **CI 是实质性的**：真 PG + `alembic upgrade head` + **`alembic check`**（模型漂移检测）+ PG 门禁 + PG 上 e2e + 前端五道关 + integration 真起服务 | 4 个 workflow |
| **A5-F-03** | 测试断言质量**不差**：743 函数 / 2468 断言 / 中位数 3；零断言仅 3 个 | AST 统计 |
| **A5-F-04** | 但 **49 个函数只断 `status_code`**，只能证明"未 500" | AST 统计 |
| **A5-F-05** | 授权与对象归属测试**成体系**（专门的 `test_object_ownership_boundary.py`：跨学生/跨校读→404、提权防护、正向边界；28×403 + 72×404）；**但集中在读路径**，A4 点名的高危写端点无对应用例。主审两稿结论（「完全不存在」→「点状」）**均被推翻**，根因是只检索 403 而该库用 404 表达归属拒绝 | `test_object_ownership_boundary.py`；`grep -rn "== 404" tests/` |
| **A5-F-06** | A1 记录的 8 个前端伪测试与 7 个后端未收集测试文件**在本基线仍然存在** | 复核 A1 结论 |
| **A5-F-07** | **无依赖漏洞扫描**：无 pip-audit／safety／npm audit／dependabot | `.github/` 检索 |
| **A5-F-08** | **无外部监控／APM** | 依赖与代码检索 |
| **A5-F-09** | 日志写本地 `logs/app_{YYYYMMDD}.log`，**compose 未挂载该目录** —— 与 A3 的 `knowledge_store.json` 同一类问题 | `logging.py:50` + compose |
| **A5-F-10** | **备份无脚本、无演练；回滚有计划文档但自述"演练未执行"** | 回滚计划文档自述 |
| **A5-F-11** | 密钥治理**做得对**：`validate_production()` 拦默认密钥与 SQLite URL，且确实被调用；`.env` 未跟踪 | `config.py:80`、`main.py:55` |
| **A5-F-12** | **CI 实际运行历史未核实**，配置完备不等于持续在跑 —— 记为 UNKNOWN | 本批未查 Actions 记录 |
| **A5-F-13** | **`integration-ci` 很可能根本跑不起来**：该 job 有**两个 `env:` 块**，第一个含 `DEBUG: "true"` 并附注释说明「CI 无 .env，DEBUG 默认 False 会触发 `validate_production` 拒启」，**第二个块（`DATABASE_URL`）按 YAML 规则静默覆盖了它**。解析后 `job.env` 只剩 `DATABASE_URL`，`DEBUG` 丢失 → 后端启动即被 `validate_production()` 拒绝 → 健康轮询 45 次全败 | YAML 解析：`job.env = {'DATABASE_URL': ...}`（异源复核独立发现） |
| **A5-F-14** | **`/api/v1/health` 从不返回 503**：内部判定 `overall_status = "unhealthy"` 后仍 `return HealthCheckResponse(...)`（HTTP 200），文档字符串却写着「503: 服务异常」；且不检查数据库与对象存储。CI 的 `curl -fsS` 因此**无法识别依赖异常** | `health.py:66,72,80`（异源复核独立发现） |
| **A5-F-15** | **真 PG 上的 e2e 并未验证迁移后的表结构**：`tests/e2e/conftest.py` 仍用 `drop_all`/`create_all` 按模型建表，且用的是与迁移检查**不同的数据库**（`rmos_e2e` vs `rmos_ci`）。即「迁移可用」与「e2e 通过」是两条互不相交的证据链 | 异源复核独立发现 |
| **A5-F-16** | **浏览器 e2e 不是合并前门禁**：`e2e-browser-ci` 只在进入主分支后或手工触发；**没有任何 workflow 由 `docker-compose.yml` 变更触发**；4 个 workflow 中**无容器构建、发布或部署步骤** | 异源复核独立发现 |
| **A5-F-17** | **容器交付风险**：两个 `Dockerfile` 都**无 `.dockerignore`**、**未切换低权限 `USER`**（以 root 运行）；后端 `COPY . .` 会把本地未跟踪文件（如 `.env`、`logs/`）带进镜像；部分基础镜像用可变标签 | 异源复核独立发现 |
| **A5-F-18** | **后端 CI 无任何静态检查**：无 ruff／flake8／mypy／pyright／pylint／black／isort／bandit；而前端有 `tsc --noEmit` + `eslint --max-warnings 0` 两道 | 异源复核独立发现 |

## 8. 退出门禁自评

| 门禁 | 要求 | 本报告 | 结论 |
|---|---|---|---|
| A5-G1 | 每项现有 PASS 都能追到提交、环境、命令和原始输出 | §5.1 核对：`TEST_REPORT.md` 的 PASS 条目均有提交号、命令与范围限定 | ✅ 达标 |
| A5-G2 | 无法复现的结论降级为 HISTORICAL 或 UNKNOWN | 性能基线与浏览器实测降为 `E2_HISTORICAL`；CI 运行历史降为 UNKNOWN | ✅ 达标 |
| A5-G3 | **M-AUD-08 完整** | §6 的 10 项运行能力全部标记 `E2_NOT_COLLECTED`／`E2_HISTORICAL`／`E2_BLOCKED`，无隐含空白 | ✅ 达标 |
| A5-G4 | 缺少新鲜 E2 时不得表示运行/恢复/交付通过 | §1、§6 均显式声明；E1 FAIL、E2/E3/E4 BLOCKED 维持不变 | ✅ 达标 |
| A5-G5 | 不得把「代码存在」写成「真实可用」 | 测试可信度按"可支持结论"逐条限定；CI 配置与 CI 实际运行严格区分 | ✅ 达标 |
| §5.8 | 主审与复核异源 | Codex 13 条断言复核完成，3 条 MISMATCH 全部采纳，另接受其 6 个独立发现 | ✅ 达标 |

## 9. 异源复核记录

| 项 | 内容 |
|---|---|
| 复核方 | Codex（工作目录在被审仓库之外，明令只读、**禁止执行测试套件**；其在独立只读快照上复核固定基线 `29d2a588`） |
| 复核范围 | 13 条断言（E-01~E-13），要求**两个方向都查**（是否夸大／是否遗漏或美化），并独立提出缺口 |
| 结论 | **OVERALL: MISMATCH(3)** — 10 条 AGREE（1 条带限定）、**3 条 MISMATCH**，另**独立提出 6 个主审未列出的缺口** |
| 处置 | 3 条 MISMATCH 全部复验成立并采纳；6 个独立发现全部复验属实，已列为 A5-F-13~18 |

### 9.1 MISMATCH 处置

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MM-A5-01**（E-13） | 「没有测试覆盖越权」不成立：`tests/e2e/test_object_ownership_boundary.py` 中，学生 B 用自己的合法身份读学生 A 的资料、训练、任务、报告、事件、会话、反馈并断言被拒 | **成立，且这是主审第二次在同一条上判错**。根因：该库对归属违规**返回 404 而非 403**（不泄露对象存在性），主审两稿都只检索 `403`，完整漏掉了以 404 表达拒绝的整套边界测试。复验确认该文件含跨学生读→404、**跨校教师读→404**、遗留无主任务拒绝、**查询参数提权防护**及两条正向边界；全仓 `== 404` 断言 **72 处 / 15 文件** | **采纳**。§1 第 2 点、T-10、A5-F-05 全部重写；缺口收窄为「读路径已覆盖、写路径未覆盖」 |
| **MM-A5-02**（E-03） | 无 `assert` 的函数是 21 个（把 `pytest.raises` 也算有效断言后才是 3 个）；skip 的三种口径（函数名／函数体／真正跳过）数字不同 | 成立。主审只报了「3」这一个数字，没有说明口径 | **采纳**。改为「无 `assert` 21 个，其中 18 个用 `pytest.raises`，真正零断言 3 个」 |
| **MM-A5-03**（E-08） | 日志实际文件名是按日期滚动的 `app_YYYYMMDD.log`，不是 `app.log` | 成立。主审取自 `logging.py` 的**文档字符串**（写着 `logs/app.log`），未核对实际创建语句（`logging.py:51`） | **采纳**。核心风险（未挂载）不变 |

### 9.2 复核方独立发现（主审完全未覆盖，全部复验属实）

| 发现 | 主审复验 | 严重度判断 |
|---|---|---|
| `integration-ci` 的 `env:` 块重复导致 `DEBUG` 丢失 | **属实且最严重**：第一个 `env` 块含 `DEBUG: "true"` 并附注释解释「不设会触发 `validate_production` 拒启」，第二个块静默覆盖。YAML 解析后 `job.env` 只剩 `DATABASE_URL`。**作者知道这个要求并写了注释，但重复键把它吃掉了** | 高——该 workflow 大概率是红的，与 A5-F-12「CI 运行历史未核实」叠加后，"CI 在跑"这一假设需重新审视 |
| `/health` 从不返回 503 | 属实：仅 `return HealthCheckResponse(...)`，无 `status_code=503`／无异常；文档字符串写着 503 | 中——CI 的就绪检查形同虚设 |
| PG 上的 e2e 用 `drop_all`/`create_all`，与迁移检查不同库 | 属实 | 中——削弱了 T-03／T-04 的联合证明力 |
| 浏览器 e2e 非合并前门禁；无 compose 触发；无构建/部署步骤 | 属实 | 中 |
| 无 `.dockerignore`、以 root 运行、`COPY . .` 可能带入未跟踪文件、可变基础镜像标签 | 属实 | 中——与 A3 的 `COPY . .` 观察同源，此处补齐了安全维度 |
| 后端 CI 无 lint／类型／安全静态检查 | 属实 | 中 |

### 9.3 方法教训

**同一条结论上判错两次，这是本轮最需要记住的事。**

1. **不要只按一种拒绝码检索授权测试。** 该库刻意用 **404** 表达归属拒绝（更安全的做法），
   而主审两稿都只搜 `403`。**检索安全测试前，应先确认这个代码库用什么状态码表达拒绝。**
   这与 A4 的教训同源——A4 是没找到项目自封装的 `ownership.py`，A5 是没找到项目的拒绝码约定。
   **两次都栽在「用通用假设去搜一个有自己约定的代码库」。**
2. **报统计数字必须带口径。** 「零断言 3 个」在不说明「是否把 `pytest.raises` 算作断言」时是误导性的。
3. **文档字符串不是事实源。** 日志文件名与 `/health` 的 503 都写在 docstring 里，实际代码都不是那样。
   **审计要读实现，不读注释。**
4. **YAML 重复键是静默的。** `integration-ci` 的 `DEBUG` 丢失没有任何报错——
   配置文件的审计应当**解析后看最终值**，而不是读源文本。

## 10. 移交下阶段的问题

| 移交项 | 承接阶段 | 说明 |
|---|---|---|
| 主套件迁 PostgreSQL（asyncpg 事件循环问题） | A6 | 已有 P2-1 范围登记，是消除方言盲区的根本手段 |
| 授权/越权测试从零建立 | A6 | A4 的 46 条无隔离写操作需要测试反证 |
| 8 个伪测试与 7 个未收集测试文件的处置 | A6 | 删除或重写，二选一 |
| 依赖漏洞扫描接入 | A6 | 当前完全空白 |
| 监控、备份、恢复、回滚脚本 | A6 | 回滚计划文档已自述缺失 |
| 日志与知识存储的持久化 | A6 | 与 A3 D-13 同类 |
| **受控 E2 环境是否申请** | **董事会** | §6 的 10 项能力当前全为 NOT_COLLECTED/BLOCKED；是否投入取决于董事会 |
| CI 实际运行历史核实 | A6 | 需要 GitHub Actions 记录，本批未覆盖 |
| **A4 报告 §9 G3 表述错误需修订** | A4 修订 | 「没有一条测试尝试越权访问」**与事实相反**：存在 `test_object_ownership_boundary.py` 等成体系的归属边界测试（28×403 + 72×404）。应改为「这三个**写**端点未见针对性越权用例；全仓读路径的对象归属与跨校隔离已有专门测试」。按 §5 重开点规则登记，待 A5 获确认后出 A4 0.1.1 |
| **`integration-ci` 的 `DEBUG` 丢失（A5-F-13）** | A6 | 单行 YAML 修复；但需先确认该 workflow 当前是否长期失败 |
| **`/health` 不返回 503（A5-F-14）** | A6 | 就绪检查失效，影响所有依赖健康探针的编排 |
| 逐端点的授权测试覆盖度盘点 | A6 | 本批只做到文件级交叉，端点级需读测试体 |

## 11. 本批产出物

| 文件 | 说明 |
|---|---|
| 本报告 | A5 主报告 |
| [A5 质量与运行证据](./evidence/2026-08-28-a5-quality-evidence-v0.1.0.md) | 测试断言统计明细、CI workflow 逐条解析、运行能力标记表 |
