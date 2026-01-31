# 运行与排障手册

## Phase2 基线入口（唯一事实源）

按以下顺序查阅并以其为准（顺序不可改）：
1) `docs/testing/TEST_REPORT.md`
2) `docs/testing/TEST_PLAN.md`
3) `docs/ops/RUNBOOK.md`
4) `docs/adr/ADR.md`
5) `DEVELOPMENT_LOG.md`

## Phase2 基线运行入口（唯一启动/排障入口）

固定路径与环境（必须原样）：
- worktree：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0`
- 后端：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend`
- 前端：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-frontend`
- 数据库：`DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
- Python 必须在 `.venv` 内运行：`source /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend/.venv/bin/activate`
- 代理硬约束：V2rayN `10808`
- 本机 HTTP 必须使用：`curl --noproxy 127.0.0.1,localhost ...`

端口策略（Phase2 验收）：
- 后端默认端口 `8000`，若 `EPERM` 则使用 `18000`
- 前端当前可验收端口 `55173`，若占用/受限则记录替代端口（如 `3000`/`3100`）
- 实际使用端口必须写入 `docs/testing/TEST_REPORT.md`

唯一验收脚本入口：
```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh
```

## Postgres 可用性探测与连接选择

1) 探测命令（按顺序执行并记录输出）
- `psql --version`
- `pg_isready -h localhost -p 5432`
- `lsof -nP -iTCP:5432 -sTCP:LISTEN`
- `psql -h localhost -p 5432 -U postgres -d postgres -c "select 1;"`

2) 选择规则
- 若以上命令中 `psql ... select 1` 成功：使用本机 Postgres
  - 示例：`DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
- 若 `psql` 连接失败：使用 Docker 启动 Postgres 后再设置 `DATABASE_URL`
  - 参见本节后续“Docker 启动方式”

3) Docker 启动方式（本机不可用时）
- `docker run --name rmos-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=rmos_dev -p 5432:5432 -d postgres:16`
- 启动后使用：`DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rmos_dev`

4) 配置落地
- 将连接串写入 `.env`（参考 `r-mos-backend/.env.example`）

## 一键迁移/种子/重置命令

- 迁移：`make migrate`
- 种子：`make seed-demo`
- 重置：`make reset-db`

使用说明：
- 需先设置 `DATABASE_URL`（示例：`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`）
- `make reset-db` 仅用于本地开发环境

## 一键启动与开发命令

- 后端：`make dev-backend`
- 前端：`make dev-frontend`
- 联合启动：`make dev`

说明：
- `make dev` 会同时启动后端与前端，请在独立终端观察日志
- 若前端依赖未安装，请先处理“前端依赖安装故障”章节

## 一键 Phase1 E2E（真实 HTTP：127.0.0.1:8000）

运行命令（单条命令完成迁移、种子、真实 HTTP 验收与报告追加）：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh
```

脚本行为说明：
- 强制使用 `DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
- 所有 `curl` 请求均带 `--noproxy 127.0.0.1,localhost`
- 会自动追加验收证据到 `docs/testing/TEST_REPORT.md`
- 若未检测到后端，会尝试在后台启动 `uvicorn`（日志：`logs/phase1-e2e-backend.log`）

常见失败与定位：
- 端口 8000 无法监听或被占用：
  - `lsof -nP -iTCP:8000 -sTCP:LISTEN`
  - `python3 -m http.server 8000 --bind 127.0.0.1`
  - `cd r-mos-backend && DATABASE_URL=... .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000`
- 数据库不可用或连接失败：
  - `pg_isready -h localhost -p 5432`
  - `psql -h localhost -p 5432 -U postgres -d postgres -c "select 1;"`
- 代理干扰本地请求：
  - `env | grep -i proxy`
  - 脚本会主动 `unset HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`，但仍建议在本机终端直接运行

## 保持系统代理开启情况下的前端依赖安装与构建（已验证可用）

按以下顺序执行（命令需原样）：
- `cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-frontend`
- `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm install`
- `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm run build`

输出证据要点（本机已验证）：
```bash
pwd
/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-frontend

npm install
up to date in 409ms

npm run build
vite v5.4.21 building for production...
✓ built in 8.89s
```

安全检查（强烈建议先做）：
- 检查：`echo $NODE_TLS_REJECT_UNAUTHORIZED`
- 排查：`env | grep -i NODE_TLS_REJECT_UNAUTHORIZED`
- 若为 `0`：说明 TLS 校验被禁用；修复：`unset NODE_TLS_REJECT_UNAUTHORIZED`
- 提示：不要长期将 `NODE_TLS_REJECT_UNAUTHORIZED` 设为 `0`

## 从零跑通教学闭环

1) 准备数据库环境
- 确认 `DATABASE_URL` 已配置（示例：`SQLite` 或本地数据库）

2) 启动后端
- 方式一：`bash r-mos-backend/scripts/run_dev.sh`
- 方式二：
  - `cd r-mos-backend`
  - `./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000`

3) 启动前端
- `cd r-mos-frontend`
- `npm install`
- `npm run dev`
  - 若出现安装失败，请先查看“前端依赖安装故障（EPERM / 127.0.0.1:10808）”

4) 生成教学演示数据
- `python r-mos-backend/scripts/seed_teaching_demo.py`

5) 跑通流程
- 打开 `/teaching/assignments`
- 学生视图点击“开始”，进入 `/teaching/attempts/{id}`
- 在尝试页启动任务并执行步骤
- 完成后点击“查看证据摘要”，进入 `/teaching/attempts/{id}/evidence`

## 常见问题定位

### 前端依赖安装故障（EPERM / 127.0.0.1:10808）
- 现象：`npm install` 连接 `127.0.0.1:10808` 失败，错误码 `EPERM`
- 诊断命令清单：
  - `npm config get registry`
  - `npm config get proxy`
  - `npm config get https-proxy`
  - `npm config get strict-ssl`
  - `npm config list`
  - `env | grep -i proxy`
  - `lsof -nP -iTCP:10808 -sTCP:LISTEN`
  - `nc -vz 127.0.0.1 10808`
- 临时绕开本地代理端口（仅当前终端生效）：
  - `export npm_config_proxy=`
  - `export npm_config_https_proxy=`
- 切换镜像源（`registry`，按需选择其一）：
  - `npm config set registry https://registry.npmjs.org/`
  - `npm config set registry https://registry.npmmirror.com/`
- 处理建议：确认本地代理是否运行；若需使用代理，请确保端口可连通

本次环境观测结果（供排障参考）：
- `npm config get registry`：曾为 `https://registry.npmmirror.com`，已尝试切换为 `https://registry.npmjs.org/`
- 项目级 `.npmrc` 已设置 `registry=https://registry.npmjs.org/`
- `npm config get proxy` / `https-proxy`：`null`
- `env | grep -i proxy`：存在 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`，指向 `127.0.0.1:10808`
- `nc -vz 127.0.0.1 10808`：返回 `Operation not permitted`
- `python`/`node` 连接本地端口与外网均出现 `Operation not permitted`
- `npm install` 失败并提示 `Exit handler never called!`，同时日志目录写入失败（`/Users/xuhehong/.npm/_logs`）
- 即便固定 `registry` 并改用项目内缓存目录，仍报 `EPERM connect 127.0.0.1:10808`

若出现 `Operation not permitted`：
- 这通常意味着当前进程网络访问被系统策略限制（不是代理未运行）
- 需要在本机真实终端或放开网络权限后再执行 `npm install`

### 409 `ALREADY_ENROLLED`
- 现象：重复报名返回 `409`
- 定位路径：
  - `r-mos-backend/app/services/teaching_service.py`
  - `r-mos-backend/app/core/exceptions.py`
- 处理建议：确认是否需要重复报名，或更换 `studentId`

### 尝试状态机非法
- 现象：`INVALID_ATTEMPT_STATUS_TRANSITION`
- 定位路径：
  - `r-mos-backend/app/services/teaching_service.py`
- 处理建议：仅允许 `in_progress → completed → graded` 或 `in_progress → abandoned`

### `/attempts/{id}/evidence` 返回 404
- 现象：证据页提示不存在
- 定位路径：
  - `r-mos-backend/app/api/v1/endpoints/teaching.py`
  - `r-mos-backend/app/services/evidence_engine.py`
- 处理建议：确认对应任务已完成，或重新执行任务触发证据生成

### `/attempts/{id}/evidence` 返回 500
- 现象：证据包缺失导致服务返回 500
- 定位路径：
  - `r-mos-backend/app/services/evidence_engine.py`
  - 数据库表 `evidence_bundles` 与 `evidence_links`
- 处理建议：检查 `evidence_links.bundle_id` 是否存在对应 `evidence_bundles.id`

## 健康检查命令

- 基础探测：`pg_isready -h localhost -p 5432`
- 最终裁决：`psql -h localhost -p 5432 -U postgres -d postgres -c "select 1;"`
- 后端可用性（示例）：`curl http://localhost:8000/docs`

说明：
- `pg_isready` 可能误判网络与权限问题，建议以 `psql ... select 1` 为准

## 常用命令

- 单元测试：`r-mos-backend/.venv/bin/pytest r-mos-backend/tests/unit -v`
- 一键启动：`make dev`（或 `make dev-backend` / `make dev-frontend`）
- 前端启动：`cd r-mos-frontend && npm run dev`
- 教学数据种子：`python r-mos-backend/scripts/seed_teaching_demo.py`
- 教学数据清理：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
