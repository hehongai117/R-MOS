# ADR-2026-08-21：证据完整性与 SOP 版本化

- 状态：**Accepted**（2026-08-21 用户确认存储命名空间口径与 SOP 产品行为变更）
- 覆盖发现：`EVID-101`、`EVID-102`、`EVID-103`、`EVID-104`、`EVID-105`
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md` 的 G3
- 落地阶段：Phase 4（本 ADR 不改代码）

## 背景

验收章程 G3 要求"引用和证据必须由服务端验证存在、完整且调用者可访问""证据、步骤结果、评分快照和报告必须属于同一训练或任务对象"。当前四条都不成立。

**证据对象没有归属。**

`app/models/evidence.py:12-27` 的 `evidence_bundles` 字段为：`id`(String64 主键)、`bundle_type`、`bundle_hash`、`bundle_hash_algo`、`observed_time_start/end`、`ingest_time`、`is_sealed`、`sealed_at`、`human_summary`、`machine_tags`。**没有 owner、school、task/session/step 任何归属字段。** `evidence_items`（30-45 行）有 `bundle_id` 外键与 `content_uri`/`content_hash`/`size_bytes`，同样没有到任务或步骤的关联。

**"封存"只封存声明值。**

`app/services/evidence_service.py:46-58` 的 `_compute_bundle_hash` 对 `_bundle_manifest(bundle)` 做 sha256，而 manifest 的每一项（`content_uri`、`content_hash`、`size_bytes`…）都直接来自客户端提交的 `EvidenceBundleCreate`。创建时不读取内容、不验证 URI 可达、不重算内容哈希，随后即可写 `is_sealed=True`。

`app/services/evidence_engine.py:141-157` 为任务自动生成的哈希，manifest 只含 `task_id`、`bundle_type`、时间与 `summary`；而 `summary`（`_build_summary`，116-140 行）只是 `total_events`、`snapshot_count`、`total_steps`、`skip_count`、`error_count`、`duration_ms`、`final_score`、`is_passed` 等计数与分数。**事件载荷、传感器值、快照内容都不在哈希覆盖范围内**——同一组计数可以对应完全不同的真实过程。

**步骤判定只看编号是否非空。**

`app/services/training/workbench_execution_service.py:133-135`：

```python
has_evidence = bool(evidence_bundle_id)
passed = has_evidence and not missing_critical and not anomaly_ids
```

不查证据包是否存在、是否属于当前用户/会话/步骤，也不复核内容哈希。Phase 1 探针提交数据库中不存在的 `bundle-does-not-exist` 后仍得到 `verdict=PASS`。

正向边界须保留：同文件 `submit_step` 第一行即 `session = await self._get_owned_session(user_id, session_id)`，会话归属校验是有效的；缺口只在证据对象本身。

**旧证据门禁是进程内字典且忽略类型。**

`app/services/evidence_enforcement.py:50-52` 用 `self._collected_evidence: Dict[str, Set[str]]` 保存状态，**只以 `step_id` 为键**，无任务、会话、用户或学校范围，重启即丢失，同名步骤跨会话共享。`collect_evidence`（63-77 行）只执行 `self._collected_evidence[step_id].add(evidence_id)`，**完全忽略 `evidence_type` 参数**；而 `validate_step_completion`（79-102 行）却把该集合里的值当类型比较：`any(ev_type == req.evidence_type for ev_type in collected)`。因此只要提交一个恰好等于类型名的 `evidence_id` 就能满足门禁。`app/api/v1/endpoints/agent_evidence.py:25-32` 的 `/evidence/collect` 虽有 `require_permission("agent:execute")`，但接受任意客户端编号与类型且不查真实证据。

**任务无证据即可完成并评分。**

`app/schemas/task.py:53-58` 的 `StepExecutionRequest` 只有 `step_index`、`action`、`parameters`、`notes`，**没有证据字段**。`app/services/task_service.py:93-304` 只检查顺序与步骤严重度，快照失败在 188-211 行明确不阻断。`app/services/scoring_service.py:42-142` 按跳步、错误、超时、异常快照评分，不要求步骤证据存在。`tests/unit/test_evidence_engine.py:60-82` 用两个无证据的 `StepExecutionRequest` 完成任务并断言自动生成证据包——该测试通过本身即为当前行为的证据。

**SOP 可被物理删除。**

`app/models/sop.py:25` 的 `version = Column(String(20), nullable=True)` 只是一个可编辑字符串，没有发布快照或不可变版本实体。`app/services/sop_service.py:126-204` 的 `delete_sop(force=True)` 会把关联任务的 `sop_id` 置 `None`、删除全部 `SOPStep`、删除 SOP 主记录。`app/models/task.py:43-49` 的外键本就是 `ondelete="SET NULL"`。历史任务因此失去当时执行的步骤、限制与版本。

**可复用的既有资产：**

- `app/services/storage/file_storage.py:32-73` 的 `FileStorageBase` 已定义 `upload / download / delete / list_files / exists / open_stream / get_public_url / materialize / materialize_dir`；`app/services/storage/__init__.py:9-21` 的 `get_storage()` 是全仓唯一实例化入口，按 `settings.STORAGE_BACKEND` 返回 `LocalFileStorage` 或 `S3FileStorage`。`tests/test_storage.py` 已对双实现参数化双跑，是可复用的契约测试范式。
- `workbench_execution_service.py:53-64` 的上传路径**已经在服务端对真实字节计算 sha256**（`hashlib.sha256(content).hexdigest()`）。缺口不在哈希算法，而在它把文件写到 `self.storage_root`（`:38`，即 `<backend>/storage/training-evidence`）这个绕过存储抽象的本地目录，且写入后没有任何环节再复核。

## 决策

### D1：证据包补齐归属与内容真实性

`evidence_bundles` 增加：`owner_user_id`（外键 `users.id`，非空）、`school_name`（String，与 `users.school_name` 口径一致，见 ADR-authn D4）、`task_id`（外键，可空）、`session_id`（String，可空）、`step_id`（String，可空）、`sop_version_id`（外键，见 D4，可空）。至少 `task_id` 与 `session_id` 之一非空，由服务层约束。

`evidence_items` 增加 `verified_at`（TZDateTime，可空）：服务端读取真实字节复核 `content_hash` 通过后才写入。

所有证据读写走 ADR-authn D3 的归属校验；越权读 404、越权写 403，均落真实 `resource_id` 审计。

### D2：封存必须覆盖真实内容

- 创建证据包时，服务端对每个 item 通过 `get_storage()` 读取真实字节重算 `content_hash`；URI 不可达、哈希不符、`size_bytes` 不符一律拒绝创建，**不得**先落库再补验。
- `bundle_hash` 的 manifest 增加每个 item 的**服务端复核后**哈希，以及 `task_id`、`robot_model_id`、`session_id`、`step_id`、`sop_version_id`。
- `evidence_engine._compute_bundle_hash` 的 manifest 从"只含 summary"扩展为额外覆盖事件载荷与快照内容的稳定摘要（对 `events` 与 `snapshots` 按主键排序后逐条哈希，再哈希该列表）。
- `is_sealed=True` 后禁止任何字段修改，服务层拒绝并写审计。

### D3：步骤判定与任务完成的证据门禁

- `workbench_execution_service.submit_step` 的 `has_evidence = bool(evidence_bundle_id)` 改为：在同一事务内加载证据包，校验存在、`owner_user_id == 当前 actor`、`session_id`/`step_id` 匹配、`is_sealed=True`、内容哈希一致、未被撤销。任一不满足 → `verdict=FAIL`，理由具体到失败项。
- `StepExecutionRequest` 增加可选证据引用字段；SOP 步骤按 `sop_steps.is_critical`（`app/models/sop.py:61`）声明服务端证据要求：**关键步骤缺有效证据不得判 PASS，任务不得完成**。
- 允许降级的遥测缺失（如快照采集失败）必须在报告中显式标为"证据缺口"，**不得**等同完整通过。`task_service.py:188-211` 的不阻断行为保留，但必须落一条可见的缺口记录。
- `scoring_service` 在存在证据缺口时不得输出"通过"结论；具体扣分规则随实现确定。

### D4：SOP 不可变发布版本

新增 `sop_versions` 表：`id`、`sop_id`（外键）、`version_label`、`published_at`、`published_by`、`content_hash`、`steps_snapshot`（JSON，完整步骤快照）、`is_active`。

- SOP 发布即生成一个不可变版本；发布后 `steps_snapshot` 与 `content_hash` 禁止修改。
- `tasks` 增加 `sop_version_id`（外键，`ondelete="RESTRICT"`），任务绑定具体版本而非可变的 `sops` 行。
- `delete_sop` 的物理删除下线：改为软删除（`sops` 增加 `is_archived`）。已被任何任务引用的版本内容**不允许删除**，由 `ondelete="RESTRICT"` 在数据库层兜底。`force=true` 参数保留但语义改为"归档并停用"，不再置空 `tasks.sop_id`。
- 教师修改已发布 SOP 的产品行为变为"发布新版本"；旧任务报告继续回放旧版本快照。

### D5：训练证据走存储抽象

`workbench_execution_service.py:38` 的 `self.storage_root` 本地路径下线，改用 `get_storage()`。

**已知接口摩擦：** `FileStorageBase` 的全部方法首参是 `robot_model_id: int`（`file_storage.py:36-72`），语义是"机器人资产命名空间"。训练证据不属于任何机器人资产目录。两个可选口径：

- **方案 A（推荐）：** 把首参泛化为命名空间标识，`robot_model_id` 成为其中一类。改动集中在 `file_storage.py` 与 `s3_storage.py` 的签名与 `_robot_dir` 实现，调用方按名传参基本不受影响。
- **方案 B：** 保持签名不变，训练证据复用 ADR-robot-binding 引入的 `robot_model_id` 作为命名空间（训练必然绑定机器人）。零改动，但会把训练证据放进机器人资产目录树下，语义混淆且与备份粒度不一致。

采用方案 A。`content_uri` 从 `local://training-evidence/...` 改为存储后端可解析的统一形式。

## 备选

1. **只加归属字段，不做服务端哈希复核。** 能挡住跨对象引用，挡不住"声明一个假哈希"。G3 要求"完整"，不满足。放弃。
2. **保留 `evidence_enforcement.py` 的进程内门禁，只补 scope 键。** 进程内状态在重启后丢失，且与 ADR-runtime 的单进程决策绑死；证据裁决必须可持久追溯。决策为**该门禁不再作为裁决来源**，退化为缓存或直接删除，裁决一律查库。
3. **SOP 用行版本号 + 软删除，不建版本表。** 无法回放当时的步骤内容（步骤本身会被改）。放弃。
4. **给 `sops` 表加 `steps_snapshot` JSON 而不建新表。** 一个 SOP 只能有一个快照，多版本共存无法表达。放弃。

## 影响

- **数据结构：** `evidence_bundles` 加 6 列、`evidence_items` 加 1 列、新建 `sop_versions` 表、`tasks` 加 `sop_version_id`、`sops` 加 `is_archived`。属于多模块影响，本 ADR 即为 AGENTS.md §6 要求的 ADR。
- **产品行为：** 教师改 SOP 的心智从"编辑"变为"发新版"；已发布 SOP 不能物理删除。**需要用户从教学角度确认。**
- **接口：** `DELETE /api/v1/sops/{sop_id}` 语义变更（`app/api/v1/endpoints/sops.py:153`）；`/api/v1/evidence-bundles` 三个入口（`evidence.py:14,25,35`）加认证与归属。
- **测试：** `tests/unit/test_evidence_engine.py:60-82` 等"无证据也能完成"的特征化测试必须改写；`tests/test_storage.py` 的双实现参数化范式扩展到证据路径。
- **存储：** 训练证据从容器内本地目录迁到对象存储，与 ADR-runtime 的持久化和备份口径一致。

## 迁移策略

分两个 Alembic 迁移，避免一次改动过多表：

**迁移 1（证据归属与复核）**
1. `evidence_bundles` / `evidence_items` 加列，全部先 `nullable=True`。
2. 存量回填：能从 `evidence_engine` 生成关系推出 `task_id` 的回填；推不出的保留 NULL 并置 `is_legacy_evidence=True`。
3. `owner_user_id` 从关联任务的 `user_id` 推导；推不出的保留 NULL + legacy 标记。
4. **不**对存量证据强制补内容哈希复核（原始字节可能已不可达）；legacy 证据在报告中显式标注"未经服务端内容复核"，**不得**用于新的步骤判定。

**迁移 2（SOP 版本化）**
1. 建 `sop_versions`，为每个现存 SOP 生成一个初始版本（`version_label` 取现有 `sops.version` 或 `"1.0"`，`steps_snapshot` 取当前步骤）。
2. `tasks` 加 `sop_version_id`，按 `sop_id` 回填到该 SOP 的初始版本；`sop_id IS NULL` 的历史任务保留 NULL + legacy 标记。
3. `sops` 加 `is_archived`，默认 false。
4. 外键 `ondelete="RESTRICT"` 最后加。

两个迁移都必须在存量库上先做一次干跑并核对回填计数。

## 回滚策略

- 迁移 1 回滚：`alembic downgrade -1` 删列。存量证据数据不丢，回到"无归属"状态。
- 迁移 2 回滚：删 `sop_versions` 与 `tasks.sop_version_id`。**注意：** 若回滚前已有 SOP 走过"发新版"流程，回滚会丢失新版本内容。因此迁移 2 上线后若需回滚，必须先导出 `sop_versions` 全表。此约束写入发布手册。
- 代码改动 `git revert`。回滚后 EVID 链路重新变为 FAIL。

## 已确认决议（2026-08-21）

1. **存储命名空间**：采用方案 A——把 `FileStorageBase` 首参从 `robot_model_id: int` 泛化为通用命名空间标识。`tests/test_storage.py` 的双实现参数化契约测试随之更新，泛化后必须仍绿。
2. **SOP 产品行为变更**：用户已从教学角度确认接受——教师改已发布 SOP = 发新版本；已被任务引用的版本不可物理删除；旧任务报告继续回放旧版本快照。
3. **legacy 证据使用边界**（本 ADR 定案）：存量无归属、无内容复核的证据**仅作历史展示**，在报告中显式标注"未经服务端内容复核"，**不得用于任何新的步骤判定、评分或报告发布**。理由：这类证据的原始字节可能已不可达，无法补做复核；若允许继续参与判定，EVID-GATE 的"伪造/损坏证据通过 0 次"就无法给出结论。
