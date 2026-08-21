# R-MOS Phase 4 执行计划：证据、AI 与运行环境

- 版本：0.1.0
- 日期：2026-08-21
- 状态：Planned（**Phase 2 产物；进入 Phase 4 需 Phase 3 完成并由用户另行批准**）
- 范围：`EVID-101`～`EVID-105`、`AI-101`～`AI-105`、`DEP-101`～`DEP-104` 的静态实现部分、`DEP-105` 的本地准备（共 15 项）
- 依据：`docs/audit/2026-08-21-phase2-remediation-matrix-v0.1.0.md`、ADR-EVID、ADR-AI、ADR-RUNTIME
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md`

## 0. 进入条件

1. Phase 3 已完成并由用户确认。
2. ADR-EVID、ADR-AI、ADR-RUNTIME 的"待确认事项"已逐条确认，状态转为 Accepted。其中三项是硬阻塞：
   - ADR-EVID：存储命名空间口径（方案 A 泛化 `FileStorageBase` 首参）；SOP 产品行为变更（改 SOP = 发新版本）。
   - ADR-AI：删除 `tests/regression/test_p0_bugs_2026_07.py:241` 这条 `regression` 标记用例（`pytest.ini:11` 定义为"永不放松"）。
   - ADR-RUNTIME：**待定 J 未答复时，DEP-101 与 DEP-104 不得关闭**，但其余部分可推进。
3. 从已确认的 Phase 3 最终提交建立独立工作区与分支。
4. 现场核对 Python 环境，输出 Read-first Checkpoint。

## 1. 纪律

与 Phase 3 相同（先写失败测试、逐批留痕、只对实际运行范围下结论、检查 `knowledge_store.json`、不擅自 push）。额外两条：

- **不得用本地恢复演练替代 `DR-01` 至 `DR-06` 的真实演练。**
- **不得把 `DEP-105` 的本地准备写成风险已关闭。** 不连接真机，不启用生产，AI 直接真机动作保持 0。

## 2. 七个批次

### P4-1｜证据存在性、归属、类型与内容完整性

**覆盖：** EVID-101、EVID-102、EVID-103

**先写的失败测试**
- 不存在、其他用户、其他会话、其他步骤、未封存、哈希不一致的证据包均不能判 PASS；有效证据只能被正确会话步骤使用。
- 跨会话同名 `step_id` 并行不互相污染；伪类型、伪编号、重启前后、其他用户证据均不满足当前步骤。
- 修改任一事件载荷、快照传感器值或底层文件后校验必须失败；伪造 URI/哈希不能创建封存包；跨学校与跨会话读取被拒绝。

**实现**
- Alembic 迁移 1：`evidence_bundles` 加 `owner_user_id` / `school_name` / `task_id` / `session_id` / `step_id` / `sop_version_id`；`evidence_items` 加 `verified_at`。先全部可空 → 回填 → 加约束。存量推不出归属的置 `is_legacy_evidence=True`。
- `evidence_service.py:27-59,91-131`：创建时通过 `get_storage()` 读真实字节重算 `content_hash`，不符即拒绝；`bundle_hash` 的 manifest 增加服务端复核后哈希 + 任务/机器人/会话/步骤/SOP 版本。
- `evidence_engine.py:141-157`：manifest 从"只含 summary"扩展到覆盖事件载荷与快照内容的稳定摘要。
- `workbench_execution_service.py:133-135`：`has_evidence = bool(evidence_bundle_id)` 改为同事务加载 + 六项校验。**保留 `:235-241` 的会话归属校验这一正向边界。**
- `evidence_enforcement.py`：进程内门禁不再作为裁决来源。注意 `collect_evidence`（63-77）只存 `evidence_id` 却在 `validate_step_completion`（79-102）当类型比较，两处必须一并修正。
- `evidence.py:14,25,35` 三个入口接认证与归属（沿用 Phase 3 的 `raise_read_access_denied` / `raise_write_access_denied`）。

**通过条件（EVID-GATE 第一部分）**
- 伪造、跨对象、损坏、未封存证据通过 **0 次**（对应 `AC-04` / `T-04-E` 的"500 组完成成功 0 次"）。
- 迁移升级与回滚各演练一次并核对回填计数。
- **存量 legacy 证据不补内容复核**（原始字节可能已不可达），显式标注"未经服务端内容复核"且不得用于新判定。

> 可复用：`workbench_execution_service.py:53-64` 的上传路径**已经在服务端对真实字节算 sha256**，缺的只是复核环节与存储抽象。`tests/test_storage.py` 的双实现参数化范式可直接扩展到证据路径。

### P4-2｜SOP 不可变版本与报告生成门禁

**覆盖：** EVID-104、EVID-105

**先写的失败测试**
- 关键步骤无证据 / 证据损坏 / 归属错误时任务不能完成、不能判 PASS；非关键缺失按明确策略降级并在报告中显示为"证据缺口"。
- 停用或发布新版本后，旧任务报告仍能完整回放原步骤、版本与哈希。
- 对已被任务引用的 SOP 版本执行物理删除，在数据库层被阻断。

**实现**
- Alembic 迁移 2：建 `sop_versions`（`sop_id` / `version_label` / `published_at` / `published_by` / `content_hash` / `steps_snapshot` / `is_active`）；`tasks` 加 `sop_version_id`（`ondelete="RESTRICT"`）；`sops` 加 `is_archived`。为每个现存 SOP 生成初始版本并回填。
- `sop_service.py:126-204`：`delete_sop(force=True)` 不再置空 `tasks.sop_id`、不再删 `SOPStep`；语义改为"归档并停用"。
- `app/schemas/task.py:53-58` 的 `StepExecutionRequest` 增加可选证据引用字段；证据要求由 `sop_steps.is_critical`（`app/models/sop.py:61`）在服务端声明。
- `task_service.py:188-211` 的快照失败不阻断行为保留，但必须落一条可见的"证据缺口"记录。
- `scoring_service.py:42-142` 在存在证据缺口时不得输出"通过"结论。

**通过条件（EVID-GATE 第二部分）**
- 0 条证据时完成成功 **0 次**（`AC-04` / `T-04-B`）；六类记录引用同一 attempt 的一致性不被破坏（`AC-05` / `T-05-N`）。
- `tests/unit/test_evidence_engine.py:60-82` 一类"无证据也能完成"的特征化测试已改写。
- **回滚约束写入发布手册：** 迁移 2 上线后若需回滚，必须先导出 `sop_versions` 全表，否则丢失已发布的新版本内容。

### P4-3｜AI 未知动作默认拒绝与服务端身份

**覆盖：** AI-102、AI-103

**先写的失败测试**
- 未知动作、缺规则动作、需审批动作均不能进入模块执行；批准前副作用次数 0，拒绝或过期后始终 0。
- 伪造 `user_id` 不改变任何运行时或审计主体；删除客户端 `side_effects` 仍不能绕过写工具审批；未知/未发布工具被拒绝并审计。

**实现**
- `policy_matrix.py:212-221` 默认分支 `allowed=True` → `allowed=False`，理由 `no_matching_policy_rule` 并写审计。
- `orchestrator_v2.py:351-433`：`requires_approval=True` 时持久化命令并进入等待状态，不分发模块。规划与执行的动作类型分别登记策略规则（`:124-128` 的 `execute-task` → `plan-task` 映射保留）。
- `agent.py:144-281`：`Command.actor_user_id` 改取 `ActorContext.user_id`；客户端 `user_id` 忽略并在审计 `request_meta` 记录差异；`Command.risk_level` 写入（列已存在）。
- 工具名解析到已发布技能版本；风险与副作用由服务端登记表决定。

**通过条件（AI-GATE 第一部分）**
- 未知动作默认拒绝；写操作风险不低于 medium。

> 可复用：`app/api/v1/endpoints/skills.py:65` 已有 `_validate_publish_risk` / `RISK_LEVEL_ORDER` / `CRITICAL_SIDE_EFFECT_KEYWORDS`，其中"未知风险等级即拒绝"正是本批要的范式，错误码命名可对齐。`app/models/skill_registry.py:11` 的 Skill 表已有 `evidence_requirements` / `approval_workflow` / `policy_rules` 三个 JSON 列，目前只被按 id 查询、从不用于运行时裁决——正是服务端技能风险登记表的现成载体，**不需要新建表**。

### P4-4｜审批绑定执行、禁止自批、审计失败阻断

**覆盖：** AI-101、AI-105

**先写的失败测试**
- 普通 Agent 用户、请求创建者本人、伪造 `approved_by` 均不能批准；审批重启后仍存在；状态变化有同一 `trace_id` 与审计事件。
- 人为使审计写入失败后，批准与所有写副作用必须为 **0**；拒绝仍能在可靠介质中找到真实 `resource_id`；恢复后可重放且不重复执行。

**实现**
- Alembic 迁移 3（ADR-AI D1a）：`approvals` 增加 `resource_type` / `resource_id` / `action` / `priority` / `expires_at`；`command_id` / `tool_call_id` 放开为可空（与资源三元组至少一组非空，服务层约束）。过期惰性判定，不引入后台定时任务。**同批删除死表 `approval_records` / `decision_records`**（`app/models/agent_runtime.py:63-113`，全仓无活跃读写），避免三套审批模型并存。
- `approval_service.py:56-68` 加自批拒绝（`created_by_user_id` 与 `decided_by_user_id` 两列已存在）；`approvals.py:173-278` 的 grant/reject 补角色守卫（复用 `require_permission(..., required_role=...)`）。
- `audit_event_service.py:58-66` 的 `log_event` 增加 `strict: bool = False`；`strict=True` 时不吞异常。安全关键路径与审计同事务；`log_event` 内部 `commit()` 移除，由调用方事务边界统一提交（**须一次性排查全部调用点**）。
- `approvals.py:200-241` 的"先改状态执行、后补审计"顺序反转。
- 拒绝路径审计不可用时降级到独立日志通道并计入可观测指标，拒绝本身仍生效。

**通过条件（AI-GATE 第二部分）**
- 学生自批、伪造批准发送 **0 次**（`AC-02` / `T-02-E`）；审计失败时写副作用 **0 次**（`DR-05` 的软件侧）。
- **可用性代价已确认接受**：审计库故障期间安全关键写入不可用。本批单独提交、单独回归。

> 可复用：`app/services/access_control.py:37` 是全仓 38 处审计写入的唯一收敛入口，且已被 `tests/unit/test_deny_audit_entrypoint_gate.py` 的门禁测试锁定为单一入口——AI-105 的改动集中在两个包装器与 `log_event`，**不需要新增服务或装饰器**。

### P4-5｜引用真实性与证据持久化

**覆盖：** AI-104、DEP-104 的持久化部分

**先写的失败测试**
- 随机 UUID、其他用户、其他课程、已撤销引用均不能进入 `hits`/`citations`；有效引用可由同一用户回放。
- 重建后端容器后训练证据 100% 可读且哈希一致。

**实现**
- `tool_executor.py:187-215`：生成 citations/hits 前批量查询并应用对象级访问过滤。抽取 `ai_commands.py:100-153` 的实现为 helper——它是仓库里唯一"引用 ID → 查库 → 校验归属 → deny 审计 → 404 掩蔽"的正确实现；**抽取时须一并修正其 `owner_user_id` 为空即放行的缺口，并按决策 K 补 school 维度**。`:78-95` 的 UUID 正则保留为前置快速失败。
- `workbench_execution_service.py:38` 的 `self.storage_root` 本地路径下线，改走 `get_storage()`。按 ADR-EVID D5 方案 A 把 `FileStorageBase` 首参从 `robot_model_id: int` 泛化为命名空间标识（改动集中在 `file_storage.py:36-72` 与 `s3_storage.py`）。`content_uri` 从 `local://training-evidence/...` 改为存储后端可解析的统一形式。
- 存量本地证据文件一次性迁移到对象存储并核对哈希。

**通过条件**
- 伪引用命中 **0 条**（`AC-04`）。
- `tests/test_storage.py` 的双实现参数化契约测试在泛化后仍绿。

### P4-6｜生产配置、就绪门禁与发布脚本

**覆盖：** DEP-101、DEP-102、DEP-103、DEP-104 的脚本部分

**先写的失败测试**
- 干净环境缺任一生产必填变量时启动必须失败。
- 静态门禁：默认口令、`latest` 浮动 tag、`DEBUG=true`、模拟回退、错误 CORS 命中 **0 次**；worker 数为 1。
- 分别用空库、上一版库、故意缺字段的库启动：前两者按迁移策略成功，缺契约时 `/readyz` 返回 **503** 且不放量；重复执行不产生副作用。

**实现**
- `Dockerfile:15` `--workers 2` → `--workers 1`；容器改非 root 运行。
- `config.py:80-87` 的 `validate_production()` 扩展为完整必填清单（SECRET_KEY 非默认、DATABASE_URL 非 sqlite 且非默认口令、CORS 非空且不含通配、`LLM_ENABLE_MOCK_FALLBACK=false`、存储凭据齐备）。
- 把 `http://127.0.0.1:55173` 写入 `config.py:22-27` 默认 CORS 与 `.env.example`——该固定约束（`AGENTS.md:46`）目前**全仓只出现在 AGENTS.md 一处**，只靠未跟踪的本地 `.env` 维持。
- 新增 `/api/v1/readyz`（检查数据库连通、`alembic_version` 等于代码期望 head、对象存储可读写、关键契约表存在，失败返回 503）。修正 `/health` 的 docstring 与实现不一致：`overall_status="unhealthy"` 时真正返回 503（**同步更新 `docs/testing/TEST_PLAN.md` 的 API-02，其当前断言 200**）。
- 生产环境关闭 `/docs` 与 `/openapi.json`。
- 新增 `docker-compose.production.yml`（零默认口令、`DEBUG=false`、`LLM_ENABLE_MOCK_FALLBACK` 改为可配置变量、数据库与对象存储端口不映射宿主、不可变镜像 tag、backend healthcheck 指向 `/readyz`、frontend `depends_on` 用 `condition: service_healthy`、为对象存储与数据库配持久卷）。
- `.env.example` 占位符化。
- 新增 `scripts/release/{preflight,backup,deploy,rollback,verify}.sh`。`deploy.sh` 在启动应用前执行 `alembic upgrade head` 并校验（**不放进 lifespan**）。`preflight.sh` 断言 worker=1、镜像 tag 非浮动、必填变量齐备、迁移可达 head、`/readyz` 通过。

**通过条件（DEP-GATE 静态部分）**
- 上述静态门禁全部命中 0 次；`/readyz` 三种库状态行为正确。
- **DEP-101 与 DEP-104 受待定 J 阻塞，本批不得关闭。** J 相关部分在 `scripts/release/*` 中留显式 TODO 与失败退出，**不写默认值、不做假设**。
- 允许在本地隔离环境做一次工具可用性演练，**该演练不得记为 DR 通过**。
- 建议用 `r-mos-backend/scripts/backend_stress_test.py` 取一次单进程基线，不仅凭推断。

### P4-7｜DEP-105 本地准备

**覆盖：** DEP-105

**内容（无失败测试，本批不产出通过性结论）**
- 整理 `r-mos-frontend/package.json` 的 `dependencies` 与 `devDependencies` 分界，确认哪些包进入生产构建产物。
- 记录 `package-lock.json` 的 `lockfileVersion` 与直接依赖树。
- 起草联网核查申请：发送什么（依赖清单元数据）、发给谁（npm registry）、用途（漏洞明细）。

**硬约束**
- **不运行 `npm audit`、不外发依赖清单、不执行任何自动修复。**
- 在线明细核查须用户明确授权后于 Phase 5 执行。
- 未取得明细前 `DEP-105` **保持未关闭，E1 不得提升**。
- 当前已知数字（18 个风险：5 moderate、11 high、2 critical）来自 Phase 1 的 `npm install` 报告，属历史证据，不重新登记为当前结论。

## 3. Phase 4 完成条件

1. 本阶段定向门禁与全量自动测试通过（DEP-101、DEP-104、DEP-105 除外，三项按上文保持未关闭）。
2. 三个 Alembic 迁移的升级与回滚各演练一次并记录回填计数。
3. 恢复工具可在本地隔离环境演练。
4. `docs/testing/TEST_PLAN.md`、`docs/testing/TEST_REPORT.md`、`docs-archive/DEVELOPMENT_LOG.md` 同步。
5. **E2、E3、E4 和生产启用仍保持 BLOCKED；`REL-BLOCK-01` 未清零。**

## 4. 分工建议

| 类型 | 承担方 |
|---|---|
| 失败测试定义、门禁语义、ADR 变更、PASS/FAIL 裁决、报告回填、diff 复核 | Claude |
| 三个 Alembic 迁移脚本样板（回填逻辑由 Claude 指定） | **Codex** |
| `docker-compose.production.yml` 与五个发布脚本骨架 | **Codex** |
| 特征化测试改写（把固化不安全行为的断言改成安全目标） | **Codex**，Claude 先给出新断言 |
| `FileStorageBase` 首参泛化的机械改名 | **Codex** |
| 死表 `approval_records` / `decision_records` 删除 | **Codex** |
| DEP-105 的联网核查申请与授权沟通 | Claude → 用户 |
