# 运行与排障手册

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
- 临时绕开本地代理端口（仅当前终端生效）：
  - `export npm_config_proxy=`
  - `export npm_config_https_proxy=`
- 切换镜像源（`registry`，按需选择其一）：
  - `npm config set registry https://registry.npmjs.org/`
  - `npm config set registry https://registry.npmmirror.com/`
- 处理建议：确认本地代理是否运行；若需使用代理，请确保端口可连通

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

## 常用命令

- 单元测试：`r-mos-backend/.venv/bin/pytest r-mos-backend/tests/unit -v`
- 前端启动：`cd r-mos-frontend && npm run dev`
- 教学数据种子：`python r-mos-backend/scripts/seed_teaching_demo.py`
- 教学数据清理：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
