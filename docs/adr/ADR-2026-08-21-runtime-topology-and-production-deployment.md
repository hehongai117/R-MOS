# ADR-2026-08-21：运行拓扑与生产部署

- 状态：**Accepted**（2026-08-21）；**J 相关部分保持 BLOCKED，见第 8 节**
- 覆盖发现：`DEP-101`、`DEP-102`、`DEP-103`、`DEP-104`、`DEP-105`
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md` 的 G6、`docs/plans/2026-08-10-rmos-single-school-five-robot-deployment-rollback-v0.1.0.md` 的 `REL-BLOCK-01`
- 落地阶段：Phase 4（静态部分）；真实演练属 Phase 6，本 ADR 不解除任何生产阻断

## 背景

**只有开发编排，误用于生产会绕过全部门禁。**

`docker-compose.yml`（仓库根）当前状态：

- 顶层 `version: "3.8"`（已过时，`docker compose config` 会告警）。
- 默认口令写死在文件里：`POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}`、`SECRET_KEY: ${SECRET_KEY:-dev-only-change-me}`、`MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-rmos-minio-secret}`。
- `DEBUG: "${DEBUG:-true}"`——默认调试模式。
- `LLM_ENABLE_MOCK_FALLBACK: "true"` **硬编码，连环境变量都不接受**，无法在部署时关闭。
- `CORS_ORIGINS: '["http://localhost", "http://localhost:3000"]`——**缺少 AGENTS.md §1.5 规定的固定地址 `http://127.0.0.1:55173`**。经全仓检索，`55173` 只出现在 `AGENTS.md:46` 一处；`app/core/config.py:22-27` 的默认 CORS 列表同样不含它。该固定约束目前**只靠未被 Git 跟踪的本地 `.env` 维持**。
- PostgreSQL（5432）与 MinIO（9000/9001）端口直接映射到宿主。
- `backend` 服务**没有 healthcheck**；`frontend` 只写 `depends_on: - backend`，不带 `condition`，因此后端容器一启动前端就对外服务。
- 卷只挂了 `./r-mos-backend/data/robot-assets`——**训练证据目录没有卷**。

`app/core/config.py:80-87` 的 `validate_production()` 只在 `DEBUG=false` 时执行，且只检查两项：`SECRET_KEY != "dev-only-change-me"` 与 `DATABASE_URL` 不含 `sqlite`。不检查默认数据库口令、CORS、模拟回退、S3 凭据、TLS。

`docker-compose.production.yml` 与 `scripts/release/{preflight,backup,deploy,rollback,verify}.sh` **均不存在**（`r-mos-backend/scripts/` 下现有 23 个文件，全部是 seed / 回归 / 验证类脚本，无发布脚本）。部署与回滚计划已明确禁止把当前 `docker-compose.yml` 直接用于学校生产。

**双进程会拆分全部进程内状态。**

`r-mos-backend/Dockerfile:15` 固定 `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]`。而后端 `app/` 下共有 **62 个模块级单例，分布在 61 个文件**，包括但不限于 `websocket_manager.py:227` 的 `manager`、`approval_queue.py:225` 的 `approval_queue`、`agent_service.py:291` 的 `orchestrator`、`evidence_enforcement.py:251` 的 `evidence_enforcer`、`policy_matrix.py:334` 的 `policy_matrix`、`preflight_check.py:435` 的 `preflight_check_service`、`app/services/analysis/worker.py:98` 的 `analysis_worker`，以及 `app/adapters/factory.py:56` 的 `AdapterFactory._instance` 类变量。请求落到不同 worker 时看到的是两套互不可见的状态。

**启动没有迁移与就绪门禁。**

`main.py:38-73` 的 lifespan 只做三件事：`validate_production()`（仅 DEBUG=false 时）、`AdapterFactory.get_adapter()`、`asyncio.create_task(analysis_worker.start())`。**不执行 Alembic，不做迁移契约校验，不检查数据库连通性。** `app/core/database.py:52-76` 的 `create_all` 明确只供开发/测试且启动时未被调用。

`/api/v1/health`（`app/api/v1/endpoints/health.py:30-85`）**只检查适配器**，不检查数据库、对象存储或迁移版本；且尽管 docstring 写"503: 服务异常"，函数**从未设置 HTTP 状态码**——`overall_status` 为 `"unhealthy"` 时仍返回 **200**。发布系统无法据此判断是否放量或回滚。

**训练证据未持久化。**

`app/services/training/workbench_execution_service.py:38` 把证据写入 `<backend>/storage/training-evidence`，该目录在 `docker-compose.yml:57-58` 的卷列表中不存在。重建后端容器即丢失，而数据库仍保留引用。

**依赖风险未分类。**

Phase 1 的 `npm install` 报告当前完整依赖树 18 个已知风险（5 moderate、11 high、2 critical）。在线明细因外发依赖清单未获授权而未执行，因此不知道高等级项是否只在开发工具链，还是会进入生产产物。

**基础设施现状：** `r-mos-frontend/nginx.conf` 只有 `listen 80` 与两条 `proxy_pass http://backend:8000`，**无 TLS、无限流**。`Makefile` 有 11 个 target（`migrate`、`seed-demo`、`reset-db`、`dev-backend`、`dev-frontend`、`dev`、`test-backend`、`test-frontend`、`lint-backend`、`lint-frontend`、`clean`），全部面向开发。

## 决策

### D1：锁定单进程单实例

后端在生产以 **1 个 Uvicorn worker、1 个应用实例**运行。`Dockerfile:15` 的 `--workers 2` 改为 `--workers 1`。

理由：62 个进程内单例中，至少适配器、WebSocket 连接表、审批（下线前）、幂等缓存、证据门禁、分析 worker 六类持有请求间共享状态。把它们全部迁到共享介质需要引入 Redis 或等价服务，属于新外部依赖与大范围重构；而单校五台机器人的负载完全在单进程能力内。**不引入 Redis。**

在本 ADR 显式登记该约束及其解除条件：

- 约束：生产部署必须保证同一时刻只有一个后端应用实例持有 `robot_model_id` 的控制所有权（与 ADR-robot-binding D2 一致）。
- 解除条件（未来若需水平扩展）：先把上述六类状态迁到有一致性约束的共享介质，并为每台机器人建立唯一控制所有权租约，然后另立 ADR。**在此之前，多副本部署一律视为配置错误。**
- 落地保障：生产编排不提供 `replicas`；发布前检查脚本断言 worker 数为 1。

### D2：生产编排与开发编排彻底分离

新增 `docker-compose.production.yml`，与开发编排不共用：

- **零默认口令。** 所有密钥、口令、S3 凭据只接受外部注入，缺失即启动失败，不提供 `:-default` 回退。
- `DEBUG=false` 固定；`LLM_ENABLE_MOCK_FALLBACK=false` 固定且可配置（当前的硬编码 `"true"` 必须改成变量）。
- `CORS_ORIGINS` 由部署方显式给出。同时把 `http://127.0.0.1:55173` 写进 `app/core/config.py` 的默认列表与 `.env.example`，使 AGENTS.md §1.5 的固定约束不再只依赖未跟踪的本地 `.env`。
- 数据库与对象存储端口**不映射到宿主**，只在内部网络暴露。
- 镜像使用不可变 tag（提交 SHA 或版本号），**禁止 `latest` 与浮动 tag**。
- 容器以非 root 用户运行。

`app/core/config.py` 的 `validate_production()` 扩展为完整必填清单：SECRET_KEY 非默认、DATABASE_URL 非 sqlite 且非默认口令、CORS 非空且不含通配、`LLM_ENABLE_MOCK_FALLBACK=false`、`STORAGE_BACKEND` 与对应凭据齐备。任一不满足即启动失败。

`.env.example` 只放占位符，不放任何可用值。

### D3：迁移与就绪门禁

- **发布前显式执行迁移**：`scripts/release/deploy.sh` 在启动应用前运行 `alembic upgrade head` 并校验结果，**不在 lifespan 里跑迁移**（单实例下可行，但会让回滚与重启语义复杂化）。
- **新增 `/api/v1/readyz`**，与现有 `/health` 分工：
  - `/health`：存活探针，保持现状语义（适配器 + 系统），继续返回 200。
  - `/readyz`：就绪门禁，检查数据库连通、`alembic_version` 等于代码期望的 head、对象存储可读写、关键契约表存在。任一失败返回 **503**（真正设置 HTTP 状态码）。
- 顺带修正 `/health` 的 docstring 与实现不一致：要么按 docstring 在 unhealthy 时返回 503，要么删掉 docstring 里的 503 说明。选前者。
- `docker-compose.production.yml` 给 backend 配 healthcheck 指向 `/readyz`；frontend 的 `depends_on` 改为 `condition: service_healthy`。

### D4：持久化与备份恢复

- 训练证据改走 `get_storage()`（见 ADR-evidence D5），落到对象存储；生产编排为对象存储与数据库分别配置持久卷。
- 新增五个发布脚本（部署与回滚计划已列出但当前不存在）：`scripts/release/preflight.sh`、`backup.sh`、`deploy.sh`、`rollback.sh`、`verify.sh`。
- `preflight.sh` 至少断言：worker 数为 1、镜像 tag 非浮动、必填生产变量齐备、迁移可达 head、`/readyz` 通过。
- 备份覆盖：PostgreSQL 全量 + 对象存储（机器人资产 + 训练证据）。
- **DR-01 至 DR-06 的真实演练属 Phase 6。** 本 ADR 只交付脚本与手册；Phase 4 允许在本地隔离环境做工具可用性演练，**该演练不得记为 DR 通过，`REL-BLOCK-01` 保持生效**。

### D5：DEP-105 分两步，本阶段只做本地准备

Phase 4 只做不联网的部分：

- 整理 `r-mos-frontend/package.json` 的 `dependencies` 与 `devDependencies` 分界，确认哪些包会进入生产构建产物。
- 记录 `package-lock.json` 的 `lockfileVersion` 与直接依赖树。
- 起草联网核查申请：说明要发送什么（依赖清单元数据）、发给谁（npm registry）、用途（漏洞明细）。

**Phase 4 不运行 `npm audit`、不外发依赖清单、不执行任何自动修复。** 在线明细核查须用户明确授权后于 Phase 5 执行。未取得明细前 `DEP-105` 保持未关闭，E1 不得提升。

### D6：nginx 与 TLS

`r-mos-frontend/nginx.conf` 当前无 TLS 无限流。生产配置的具体形态取决于待定项 J（见下），因此本 ADR 只固定两条不依赖 J 的要求：

- 生产环境必须关闭 FastAPI 的 `/docs` 与 `/openapi.json`（`main.py` 按 `DEBUG` 开关）。
- 登录限流以 ADR-authn D5 的应用层实现为准；nginx 层限流作为可选纵深防御，**不作为 AUTH-GATE 的通过依据**（nginx 层限流不写应用审计）。

## 备选

1. **保留 `--workers 2`，把状态迁到 Redis。** 引入新外部服务需 ADR、增加运维面与故障模式，且 62 个单例的排查成本远超单校场景收益。已由用户决策排除。
2. **在 lifespan 里跑 `alembic upgrade head`。** 单实例下可行，但会把"迁移失败"与"应用启动失败"混为一谈，回滚时也无法先迁移后启动。放弃。
3. **复用 `/health` 做就绪探针。** `/health` 已被现有客户端与文档当作存活探针使用，改变其语义与状态码会影响既有集成。新增 `/readyz` 更干净。
4. **用一份 compose + profiles 区分开发生产。** 默认值仍然写在同一文件里，误用风险不消除。放弃。
5. **Phase 4 就跑 `npm audit` 拿明细。** 会把依赖清单发送到外部服务，未获授权。明确拒绝。

## 影响

- **部署契约变更：** 新增生产编排与五个发布脚本；镜像启动参数变更；新增 `/readyz` 端点。
- **配置：** `validate_production()` 必填项增加，现有开发 `.env` 不受影响（`DEBUG=true` 时不触发）。
- **代码：** `Dockerfile` 一行；`config.py` 校验扩展与 CORS 默认值；`health.py` 状态码修正 + 新端点；`main.py` 的 `/docs` 开关。
- **数据：** 无结构迁移。持久化改动随 ADR-evidence D5 一并落地。
- **不影响：** 认证、机器人绑定、证据、AI 语义。
- **不改变的裁决：** 本 ADR 全部落地后，E2/E3/E4 仍为 BLOCKED，`REL-BLOCK-01` 仍生效，生产启用仍需 Phase 6 的真实演练与用户批准。

## 迁移策略

无数据库迁移。按此顺序落地，每步可独立验证：

1. `Dockerfile` 改单 worker + 非 root；`config.py` 补 CORS 默认与生产必填校验。
2. `/readyz` 新增 + `/health` 状态码修正 + `/docs` 生产关闭。
3. `docker-compose.production.yml` + `.env.example` 占位符化。
4. 五个发布脚本 + 备份恢复手册。
5. 本地隔离环境做一次工具可用性演练（**不计入 DR**）。

存量部署（如有）从开发编排迁到生产编排时，需先导出数据库与对象存储，再以新编排导入并核对计数。

## 回滚策略

- 全部为文件与配置改动，`git revert` 即可。
- `docker-compose.production.yml` 为新增文件，删除即回到只有开发编排的状态。
- `/readyz` 为新增端点，删除不影响既有客户端；但 `/health` 的状态码修正会影响把 200 当作"总是可用"的调用方，回滚前需确认无此类依赖。
- 回滚后 DEP 链路重新变为 FAIL。

## 8. 待定项 J：生产部署目标形态（用户暂无答案，写为 BLOCKED）

用户已确认本项**暂时待定**。以下四个问题在得到答案前无法定稿，本 ADR 相关部分保持 BLOCKED：

| 编号 | 问题 | 被卡住的设计点 |
|---|---|---|
| J-1 | 学校现场是单机 docker-compose，还是有 K8s / 其他编排 | D1 的"单实例"保障手段（compose 无 replicas vs K8s 需显式 `replicas: 1` + 反亲和）；D3 的 healthcheck 形式 |
| J-2 | TLS 由谁终结（Nginx 自签 / 学校统一证书 / 上游网关） | D6 的 nginx 生产配置；CORS 与 Cookie 的 secure 属性；WebSocket 是 `ws://` 还是 `wss://`（影响 ADR-robot-binding D5 的令牌传递风险评估） |
| J-3 | 备份目标是本地磁盘、学校 NAS，还是外部对象存储 | D4 的 `backup.sh` 目标与保留策略；异地恢复是否可行 |
| J-4 | RTO / RPO 目标值 | D4 的备份频率；DR-01～DR-06 的通过阈值 |

**处理方式：** Phase 4 先落地不依赖 J 的部分（D1、D2 除 CORS 具体值外、D3、D4 的脚本骨架与数据库备份、D5）。J 相关部分在 `scripts/release/*` 中留显式 TODO 与失败退出，**不写默认值、不做假设**。J 得到答案前：

- `DEP-101` 不得关闭（生产编排未完整定稿）。
- `DEP-104` 不得关闭（备份目标未定，恢复演练无法设计）。
- E2 保持 BLOCKED。

## 9. 已确认决议（2026-08-21）

1. **`/health` 在 unhealthy 时改返 503**：定案执行。经核实当前无任何生产监控或编排集成依赖该端点；唯一受影响的是 `docs/testing/TEST_PLAN.md` 的 API-02（当前断言 200），在同批同步更新。
2. **`--workers 1` 的性能背书**：定为 Phase 4 的强制工作项而非可选项——用现有 `r-mos-backend/scripts/backend_stress_test.py` 取一次单进程基线并记录，**不得仅凭推断把 DEP-102 写成关闭**。

除第 8 节的待定项 J 外，本 ADR 无其他阻塞项。
