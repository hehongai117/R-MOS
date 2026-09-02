# A0 获批只读指纹探针结果

- 版本：0.1.0
- 执行日期：2026-09-02
- 结果固化时间：2026-09-02 16:32 CST
- 工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 分支：`audit/phase3-auth-control-realtime`
- 探针输入提交：`986a2a9b89a2558c6560f04d6675a850e5d8bfd0`
- 授权依据：[A0 前置事项董事会确认记录](2026-09-02-a0-board-preconditions-confirmation-v0.1.0.md)
- 探针定义：[A0 至 R0 前置动作包](2026-09-02-a0-pre-r0-human-and-probe-action-pack-v0.1.0.md)
- 结果：PASS（只限四项只读探针及前后复比；不构成应用验收、A0 批准或 R1 放行）

## 1. 输入、边界与前置快照

标准 Python 为 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`，现场版本 Python 3.13.13；pytest 9.0.3、SQLAlchemy 2.0.49、asyncpg 0.31.0。Node 为 v20.19.2，npm 为 10.8.2。`npm ls --all --json` 退出码 0，完整安装树摘要为 `712d753e188fd8332651f635b6b265d8f059db4df5e548b448a5ca95a7315385`，与 B-ASIS 历史指纹相同；`--parseable` 当前列出 707 个安装路径，该计数口径不等于历史证据的 1,695 个依赖出现节点。数据库配置只从主工作区 `.env` 解析，只有目标精确等于 `postgresql+asyncpg://…@localhost:5432/rmos` 才允许连接；没有记录口令。

执行前工作区干净，HEAD 为上述提交；`55173` 未监听，临时目录 `/tmp/rmos-a0-fe-981670d4` 不存在。关键摘要如下：

| 对象 | 执行前 SHA-256 |
|---|---|
| `r-mos-backend/data/knowledge_store.json` | `6d00252d03194ba0a67948a0e9b48beff0b4ca6418198bd9ab55b35b15c0475f` |
| `r-mos-backend/requirements.txt` | `a0d75483af9a9a6f4761d7202d8969ac8151ba4c7f75698e9fdd6e8663a97439` |
| `r-mos-frontend/package-lock.json` | `87888972373b95eb1a94aad1f56855eb2bf762c8c143009d8b41380ed79bf412` |
| 主工作区 `.env` | `348c2191e008c543fda7b87f002a316af09ec24852931fd5bec24065b9083495` |
| `data`、`storage`、`public` 路径与大小清单 | `e3b72016b212a8b7371f95ff690a203176c2faf0246918995a72180d4dd6843e` |
| `logs` 路径与大小清单 | `dc3f7425c520b07e91aad5dcecdc614b6ea8d55359a353a0352bbf320fa2588e` |

## 2. P-A0-PROC-01｜本机监听与容器映射

执行命令：

```bash
lsof -nP -iTCP:8000 -iTCP:3000 -iTCP:55173 -sTCP:LISTEN
docker ps --no-trunc --format '{{.ID}}|{{.Image}}|{{.Ports}}|{{.Names}}'
```

最终复核时间为 2026-09-02 16:31:46 CST，两条命令组成的复核批次退出码 0。结果：

- `8000`、`55173` 没有监听者；
- `3000` 由 Docker Desktop 后端进程监听，对应容器为 `openmaic`，镜像 `deploy-openmaic`，映射 `0.0.0.0:3000->3000/tcp`；
- 另有 Judge0 测试容器；其服务端映射 `2358`，数据库和 Redis 没有映射到宿主机；
- 当前本机已检查入口中未发现 R-MOS 监听或 R-MOS 容器。该事实不能外推为外部环境没有部署，外部部署继续 `UNKNOWN`。

首次在受限环境读取 Docker socket 被拒绝；保留该错误后，按已批准的相同只读命令在允许读取 Docker 元数据的环境重试成功。没有启动、停止或进入任何容器。

## 3. P-A0-DB-01｜数据库指纹

执行命令：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-09-02-a0-approved-fingerprint-probes.py db \
  --env-file /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
```

初次受限执行因本机套接字权限被拒，退出失败且没有采用其结果；按批准范围重试后退出码 0。探针开始与结束时各执行一次，结果逐字段一致；16:32:04 CST 又以同一命令复核一次，退出码 0，结果仍一致。完整脱敏结果保存在 [数据库原始 JSON](2026-09-02-a0-db-fingerprint-v0.1.0.json)，文件 SHA-256 为 `bb89966b5e2f16a5506badbfbf79df04444110030dd384bbb5e4cd8392984d79`。

已验证事实：

| 字段 | 结果 |
|---|---|
| 目标 | `postgresql+asyncpg` / `localhost:5432/rmos` |
| 事务 | `READ ONLY` |
| PostgreSQL | `14.17 (Homebrew)` |
| 扩展 | `plpgsql 1.0`、`vector 0.8.2` |
| Alembic 头 | `20260817_sop_three_phase` |
| public 表 | 66 个，含 65 个业务表和 `alembic_version` |
| schema-only dump | 163,098 bytes，`pg_dump` 退出码 0，SHA-256 `2cc629832af8447313c3a0dbcdc63ec6faabedb2461b7205fcd1051c0a9e647a` |

探针没有读取业务行、执行迁移或写 SQL。连接本身可能进入 PostgreSQL 连接日志，这是预先声明的非数据副作用。

## 4. P-A0-ROUTE-01｜运行时路由注册表

执行命令：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-09-02-a0-approved-fingerprint-probes.py routes \
  --env-file /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
```

命令退出码 0；16:32:13–16:32:14 CST 复核仍为同一结果。完整清单保存在 [运行时路由原始 JSON](2026-09-02-a0-runtime-route-fingerprint-v0.1.0.json)，文件 SHA-256 为 `c1b41b0035fec0bfd86fe3ab877681043cd53b202022afde79c8bd05ec2d8c94`；规范化路由清单 SHA-256 为 `db018c34dfcc8be267255c2a3f0b3a4cf8978fc9b2da16e9ed935a85ec166d88`。

- 共 182 条：176 条业务 HTTP、2 条 WebSocket、4 条框架文档/OpenAPI 路由；
- 176 + 2 与当前静态装饰器分母一致；4 条框架路由解释了运行表比业务分母多出的差集；
- 应用文件日志在导入前禁用；lifespan 未执行；没有启动监听端口。

## 5. P-A0-FE-01｜前端构建与公开入口

构建命令：

```bash
cd r-mos-frontend
npm exec vite -- build --outDir /tmp/rmos-a0-fe-981670d4
npm run preview -- --host 127.0.0.1 --port 55173 --strictPort \
  --outDir /tmp/rmos-a0-fe-981670d4
curl --noproxy 127.0.0.1,localhost -fsS -i http://127.0.0.1:55173/
curl --noproxy 127.0.0.1,localhost -fsS -i http://127.0.0.1:55173/login
curl --noproxy 127.0.0.1,localhost -fsS -i http://127.0.0.1:55173/register
```

结果：

- Vite 5.4.21 构建退出码 0，6,316 个模块完成转换，用时 8.68 秒；
- 临时构建含 955 个文件、1,041,019,110 bytes；只有 caniuse 数据陈旧和大块文件提示，没有构建失败；
- 预览只监听 `127.0.0.1:55173`；`/`、`/login`、`/register` 三次请求均退出码 0、HTTP 200、返回同一前端 HTML 入口；
- 没有登录、调用业务 API、启动后端或连接数据库；
- 预览进程通过其准确受管会话发送 Ctrl-C 停止，因信号结束报告退出码 1；随后确认 `55173` 已无监听；
- 精确临时目录 `/tmp/rmos-a0-fe-981670d4` 已删除且确认不存在。该目录只含本次生成物，删除不可恢复但可由同一构建命令重建。

首次在受限环境绑定回环端口被拒；保留错误后，按批准范围重试成功。原动作包预览命令遗漏 `--outDir`，会让 Vite 读取默认 `dist`，不能证明请求来自本次临时构建；执行时增加该参数，原获批动作包保持原文不覆盖，本文件保存实际可复现命令和订正说明。这里执行的是 Vite 构建，不是完整 TypeScript 检查，因此只证明当前 Vite 构建入口，不写成前端全量验收。

## 6. 后置复比与边界

全部探针和清理完成后：

- 探针输入提交仍为 `986a2a9b89a2558c6560f04d6675a850e5d8bfd0`，在新增本证据前工作区恢复干净；
- 第 1 节六项摘要与执行前逐项相同；
- 数据库探针前后输出相同；
- `55173` 无监听，临时构建目录不存在；
- 没有观察到应用、测试、依赖、配置、迁移、数据库 schema、关键数据、资产或日志变化。

本结果把 A0 当前数据库、当前运行路由、本机进程和前端公开入口从 `UNKNOWN` 推进为上述受限事实，但不提供外部部署、登录业务链、生产、恢复、真机、课堂或 E2/E3/E4 证据。后续 A1～A6 仍须以各自开始时的快照复比，不能把这一次 A0 快照当成后续阶段结果。
