# Phase1 验收测试报告（P0 端到端）

## 环境信息

- 验收提交：`280878d`
- 数据库连接（脱敏）：`postgresql+asyncpg://postgres@localhost:5432/postgres`
- 执行目录：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0`
- 关键命令：
  - `export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/postgres"`
  - `make migrate`
  - `make seed-demo`

## 数据迁移与种子结果

### 迁移结果

迁移命令执行成功（无报错）：

```bash
export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/postgres" && make migrate
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

### 种子结果

种子脚本执行成功，并生成可用于验收的关键 ID：

```bash
export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/postgres" && make seed-demo
✅ 教学演示数据已完成
- 班级：教学演示班级 (2)
- 课程：基础维保课程 (2)
- 作业：示例作业 (2)
- 任务：示例作业 (1)
- 学生：S001（内部编号 1）
```

本次验收使用：
- `assignment_id=2`
- `task_id=1`
- `student_id=1`

## P0 API 验收证据

> 说明：当前环境不允许后端监听端口（见“阻塞项与缺陷”），因此 API 验收采用进程内 `TestClient` 方式执行，同样覆盖实际路由与数据库读写。

### 健康检查（/api/v1/health）

健康检查返回 `200`，并确认 `adapter` 为 `up`：

```python
health_status = 200
health_body.status = "healthy"
health_body.checks.adapter.status = "up"
```

### 作业列表（/api/v1/assignments）

作业列表返回 `200`，数量为 `1`：

```python
assignments_status = 200
assignments_count = 1
```

### 尝试创建与证据摘要

为规避已知缺陷（见下文），本次采用“先清理执行痕迹与历史 attempt，再创建新 attempt 并完成任务”的方式生成证据。

关键输出如下：

```python
{
  "assignment_id": 2,
  "task_id": 1,
  "attempt_id": 5,
  "evidence_bundle_id": "0232d334-67aa-4bb9-af1d-eff104368546",
  "summary": {
    "total_steps": 2,
    "error_count": 0,
    "duration_ms": 118,
    "task_status": "completed"
  }
}
```

随后通过路由读取证据摘要（/api/v1/attempts/5/evidence），返回 `200` 且字段齐全：

```python
attempt_evidence_status = 200
attempt_evidence_body.bundleId = "0232d334-67aa-4bb9-af1d-eff104368546"
attempt_evidence_body.taskId = 1
attempt_evidence_body.attemptId = 5
attempt_evidence_body.summary.total_steps = 2
attempt_evidence_body.summary.error_count = 0
attempt_evidence_body.summary.duration_ms = 118
```

## P0 UI 验收记录

### 前端启动结果

前端开发服务器可以启动并对外提供访问地址：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm run dev
VITE v5.4.21  ready in 86 ms
➜  Local:   http://localhost:3000/
```

### UI 闭环路径验证结论

- 目标路径：`/teaching/assignments → /teaching/attempts/:id → /teaching/attempts/:id/evidence`
- 受阻原因：后端无法监听端口，前端无法完成真实 API 交互
- 结论：UI 闭环在本环境下“路径存在但无法完成真实端到端联调”

## 阻塞项与缺陷记录

### BLOCK-001：后端监听在后台进程中被阻塞

- 环境说明：受限沙箱（Codex CLI 执行环境）
- 现象归纳：
  - 前台运行 `uvicorn` 可以监听端口
  - 使用 `nohup ... &` 后台启动时，绑定端口失败并报 `operation not permitted`
- 复现命令（后台失败）：
  - `cd r-mos-backend && DATABASE_URL=... nohup .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 > ../logs/dev-backend-background.log 2>&1 &`
- 关键报错（后台失败日志）：

```text
ERROR: [Errno 1] error while attempting to bind on address ('127.0.0.1', 8000): operation not permitted
```

- 对照证据（用于排除“端口被占用/系统禁止监听”）：
  - 端口占用检查为空：
    - `lsof -nP -iTCP:8000 -sTCP:LISTEN`
  - 标准库临时服务可监听：
    - `python3 -m http.server 8000 --bind 127.0.0.1`
  - `uvicorn` 前台可启动：
    - `cd r-mos-backend && DATABASE_URL=... .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000`

- 证据位置：
  - `logs/dev-backend-background.log`
  - `logs/dev-backend.log`
  - `logs/dev-backend-3001.log`

### DEF-001：TaskService.start_task 在 Postgres 下状态类型不一致

- 现象：`task.status` 为字符串时，`task.status.value` 抛出异常
- 关键报错：

```text
AttributeError: 'str' object has no attribute 'value'
```

- 本次处置：验收脚本内将 `task.status` 显式转换为 `TaskStatus`
- 影响：真实运行时存在潜在崩溃风险，建议后续在 `TaskService` 内部做统一归一化

### DEF-002：EvidenceEngine._find_attempt 在多 attempt 场景下抛出 MultipleResultsFound

- 现象：同一 `task_id` 存在多个未 `abandoned` 的 attempt 时崩溃
- 关键报错：

```text
sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required
```

- 本次处置：验收脚本内先将历史 attempt 标记为 `abandoned`
- 影响：真实教学场景下可能触发证据生成失败，建议后续将查询改为“排序 + limit 1”

## 验收结论（当前环境）

- 数据迁移：通过
- 教学种子：通过
- API 路由：通过（进程内验证）
- UI 闭环联调：受 BLOCK-001 阻塞

建议在本机真实终端完成最终端到端复核：

```bash
export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/postgres"
make migrate
make seed-demo
make dev-backend
make dev-frontend
```

### Phase1 P0 自动验收（2026-01-27T06:36:45Z）

- 提交：`6ddeaa0`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`5`，student_id=`1`，task_id=`1`，attempt_id=`8`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-27T06:36:44.804655Z",
    "version": "2.2.0",
    "checks": {
        "adapter": {
            "status": "up",
            "message": "Adapter\u5df2\u8fde\u63a5",
            "details": {
                "type": "MockRobotAdapter",
                "robot_id": "mock_robot_001",
                "model": "MOCK_HUMANOID_V1"
            }
        },
        "system": {
            "status": "up",
            "message": "\u7cfb\u7edf\u8fd0\u884c\u6b63\u5e38",
            "details": null
        }
    }
}
```

**attempt**
```json
{
    "id": 8,
    "assignmentId": 5,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-27T06:36:44.827991",
    "updatedAt": "2026-01-27T06:36:44.827994"
}
```

**evidence**
```json
{
    "bundleId": "e7fb52e1-7028-448b-957e-f07113dd1ad5",
    "taskId": 1,
    "attemptId": 8,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 136,
        "final_score": 100,
        "is_passed": true
    }
}
```
