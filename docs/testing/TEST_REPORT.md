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

### DEF-003：attempt 已完成但 evidence 仍返回 404

- 复现现象（真实 HTTP）：
  - `GET /api/v1/attempts/{id}` 显示 `status=completed` 且 `taskId` 存在
  - `GET /api/v1/tasks/{task_id}/report` 返回 `200`
  - `GET /api/v1/attempts/{id}/evidence` 返回 `404`（`证据关联不存在`）
- 根因判定：
  - `EvidenceEngine._create_link` 仅在 `task.assignment_id` 存在时才尝试绑定 attempt
  - `teaching` 证据端点在缺少 `EvidenceLink` 时直接 `404`
- 修复策略（最小改动，保持解耦）：
  - `EvidenceEngine`：
    - 去除对 `task.assignment_id` 的硬依赖
    - `_find_attempt` 加 `limit(1)`，避免多行异常
    - 支持 `preferred_attempt_id`，确保绑定到当前 attempt
  - `/api/v1/attempts/{id}/evidence`：
    - 当缺少 `EvidenceLink` 且 `attempt.task_id` 存在时，现场生成 bundle+link 再返回
- 回归证据：
  - 运行：`cd r-mos-backend && bash scripts/run_phase1_e2e.sh`
  - 结果：新增的 “Phase1 P0 自动验收” 段落中，`evidence` 返回 `200` 且 `summary` 含关键字段

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

### Phase1 P0 自动验收（2026-01-27T07:41:27Z）

- 提交：`44ba784`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`6`，student_id=`1`，task_id=`1`，attempt_id=`11`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-27T07:41:27.347269Z",
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
    "id": 11,
    "assignmentId": 6,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-27T07:41:27.387784",
    "updatedAt": "2026-01-27T07:41:27.387786"
}
```

**evidence**
```json
{
    "bundleId": "aa1ae361-cde5-4cf2-a07b-115f86fb800b",
    "taskId": 1,
    "attemptId": 11,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 130,
        "final_score": 100,
        "is_passed": true
    }
}
```

### Phase1 P0 自动验收（2026-01-27T08:02:54Z）

- 提交：`eb4ce99`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`8`，student_id=`1`，task_id=`1`，attempt_id=`12`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-27T08:02:53.866051Z",
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

### Phase1 UI 冒烟通过（2026-01-27）

- 前端地址：`http://localhost:3000`
- 验证路径：`/teaching/attempts/13/evidence`
- 关键标识：
  - attempt_id：`13`
  - task_id：`4`
  - evidence_bundle_id：`f10cb301-ab38-4f19-98db-dfe0db638f1a`
- 关键结果（UI 可见）：
  - `task_status=completed`
  - `total_steps=2`
  - `error_count=0`
  - `final_score=100`
  - `is_passed=true`
- 结论：
  - UI 端“查看证据摘要”路径已验证通过，未再出现 `404`

**attempt**
```json
{
    "id": 12,
    "assignmentId": 8,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-27T08:02:53.888537",
    "updatedAt": "2026-01-27T08:02:53.888538"
}
```

**evidence**
```json
{
    "bundleId": "26979603-b24f-4d3f-aa07-cdcfa40304f5",
    "taskId": 1,
    "attemptId": 12,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 138,
        "final_score": 100,
        "is_passed": true
    }
}
```

### Phase1 P0 自动验收（2026-01-30T08:51:16Z）

- 提交：`ce7483a`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`9`，student_id=`1`，task_id=`1`，attempt_id=`14`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-30T08:51:15.749530Z",
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
    "id": 14,
    "assignmentId": 9,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-30T08:51:15.792143",
    "updatedAt": "2026-01-30T08:51:15.792145"
}
```

**evidence**
```json
{
    "bundleId": "261e4d76-2b3b-4fff-b2a6-47f3de445c5b",
    "taskId": 1,
    "attemptId": 14,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 142,
        "final_score": 100,
        "is_passed": true
    }
}
```

## Phase2 P0 诊断报告验收（2026-01-30）

### 脚本定位

- 脚本路径：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend/scripts/run_phase1_e2e.sh`

### 端口监听判定与限制

- 端口占用检查：`lsof -nP -iTCP:8000 -sTCP:LISTEN` 无输出
- 监听失败：`uvicorn main:app --host 127.0.0.1 --port 8000` 报 `Errno 1` / `operation not permitted`
- 对照端口：`uvicorn main:app --host 127.0.0.1 --port 18000` 可正常监听（环境并非全面禁止 listen，疑似 8000 受限）
- 前端 dev 监听失败：`npm run dev` 报 `EPERM`（见 `/tmp/vite-dev.log`）

### Phase1 回归脚本（用于“不破 Phase1”）

- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 结果：脚本执行完成并追加报告，但末尾 `curl` 访问 `127.0.0.1:8000` 失败（与 8000 监听受限一致）

### Phase2 API 证据（无端口条件下的替代验收）

- 诊断服务单测：`pytest tests/unit/test_diagnosis_service.py -q` 通过
  - 覆盖规则：`R-DIAG-001/002/003` 与 `R-DIAG-000`
  - 覆盖字段：`diagnosis_code`、`rule_id`、`severity`、`findings`、`recommendations`
  - 覆盖幂等：同一 attempt 多次请求一致
- 诊断接口单测：`pytest tests/unit/test_teaching_api.py -q` 通过
  - 覆盖 `GET /api/v1/attempts/{attempt_id}/diagnosis` 返回 `200`
  - 覆盖 fallback：无 `evidence_link` 仍返回 `200` 且 `source_refs.attempt_evidence_id` 有值

### Phase2 P0 真实运行验收（后端）

- backend_port=`8000` 探针：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/openapi.json` 状态码 `200`
- attempt_id=`16`（来源：`scripts/run_phase1_e2e.sh` 产物）
- diagnosis：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/diagnosis` 状态码 `200`
  - 关键字段（与响应字段对照）：
    - report_version=`v1`（响应字段 `reportVersion`）
    - diagnosis_code=`OK`（响应字段 `diagnosisCode`）
    - rule_id=`R-DIAG-000`（响应字段 `ruleId`）
    - severity=`LOW`
    - source_refs.attempt_evidence_id=`10`（响应字段 `sourceRefs.attemptEvidenceId`）
```json
{
  "reportVersion": "v1",
  "attemptId": 16,
  "diagnosisCode": "OK",
  "ruleId": "R-DIAG-000",
  "severity": "LOW",
  "findings": [],
  "recommendations": [],
  "sourceRefs": {
    "attemptEvidenceId": 10
  }
}
```
- evidence：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/evidence` 状态码 `200`
  - 关键字段：
```json
{
  "attemptId": 16,
  "summary": {
    "total_steps": 2,
    "skip_count": 0,
    "error_count": 0,
    "duration_ms": 133
  }
}
```
- 前端阻塞：`npm run dev` listen `EPERM` / `Operation not permitted`，已尝试端口 `3000` / `3100` / `18000`

### 前端 listen EPERM 排查矩阵与结论

**尝试矩阵**
- python3 简易服务器：`python3 -m http.server 18000` 报 `PermissionError: [Errno 1] Operation not permitted`
- python3 高位端口：`python3 -m http.server 45173` 报 `PermissionError: [Errno 1] Operation not permitted`
- Node 高位端口：`node -e "http.createServer(...).listen(45173,'127.0.0.1')"` 报 `EPERM`
- Vite dev（host=127.0.0.1）：`npm run dev -- --host 127.0.0.1 --port 3000` 报 `EPERM`
- Vite dev（host=127.0.0.1）：`npm run dev -- --host 127.0.0.1 --port 3100` 报 `EPERM`
- Vite dev（host=0.0.0.0）：`npm run dev -- --host 0.0.0.0 --port 55173` 报 `EPERM`

**根因判断（策略/权限）**
- 新进程 listen 被环境策略阻止（`EPERM` / `Operation not permitted` 在 Python/Node/Vite 均复现）。
- 但后端现有进程可监听 `127.0.0.1:8000` 且 `curl --noproxy` 返回 `200`，说明非全局禁止网络。

**最终可行方案**
- 当前环境无法恢复前端 listen，UI 冒烟需在允许 listen 的本机执行。
- 复现步骤（需解除策略/权限后执行）：
  - `cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-frontend`
  - `npm run dev -- --host 127.0.0.1 --port 3000`
  - `curl --noproxy 127.0.0.1,localhost http://127.0.0.1:3000/ | head`

### Phase2 阶段3 前端 listen EPERM 根因调查（不可交付 UI）

- 结论：UI 未恢复，策略/权限阻止新进程 listen（Python/Node/Vite 复现 `EPERM` / `Operation not permitted`）。
- 复现矩阵（含错误码）：
  - `python3 -m http.server 18000` → `PermissionError: [Errno 1] Operation not permitted`
  - `python3 -m http.server 45173` → `PermissionError: [Errno 1] Operation not permitted`
  - `node -e "http.createServer(...).listen(45173,'127.0.0.1')"` → `EPERM`
  - `npm run dev -- --host 127.0.0.1 --port 3000` → `EPERM`
  - `npm run dev -- --host 127.0.0.1 --port 3100` → `EPERM`
  - `npm run dev -- --host 0.0.0.0 --port 55173` → `EPERM`
- 影响面：前端 dev server 无法启动；UI 冒烟不可在此环境完成。
- 下一步入口：参考 `README.md` 的“端口策略（Phase2 验收）”与“环境探针（验收前必做）”段落。

#### 补充：前端 dev server 已恢复（127.0.0.1:55173）

- 补充时间：2026-01-30
- frontend_port=`55173`（Vite v5.4.21）
- 探针：`curl --noproxy 127.0.0.1,localhost -I http://127.0.0.1:55173/` 返回 `200`
- UI 冒烟：`http://127.0.0.1:55173/teaching/attempts/17/diagnosis` 可打开，字段可见
- 结论更正：此前 `EPERM` 结论在当时成立，但当前已解除

### 本次会话证据索引

- attempt_id=`16`
- 后端探针（200）：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/openapi.json`
- diagnosis：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/diagnosis`
- evidence：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/evidence`
- frontend_port=`55173` 探针（200）+ UI 冒烟通过

### Phase2 P0 UI 冒烟（前端 55173 + 后端 8000）

- frontend_port=`55173`（Vite v5.4.21）
- backend_port=`8000`
- completed_attempt_id=`17`（status=`completed`）
- CORS 规避：前端 API 改为相对路径 `/api/v1`，Vite proxy 转发到 `http://127.0.0.1:8000`，控制台无 CORS 拦截
- 前端探针：`curl --noproxy 127.0.0.1,localhost -I http://127.0.0.1:55173/` 返回 `200`
- 后端旁证：
  - diagnosis：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/17/diagnosis` 返回 `200`
  - evidence：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/17/evidence` 返回 `200`
  - 关键字段（diagnosis）：
```json
{
  "reportVersion": "v1",
  "attemptId": 17,
  "diagnosisCode": "OK",
  "ruleId": "R-DIAG-000",
  "severity": "LOW",
  "sourceRefs": {
    "attemptEvidenceId": 11
  }
}
```
  - 关键字段（evidence）：
```json
{
  "attemptId": 17,
  "summary": {
    "task_status": "completed",
    "total_steps": 2,
    "skip_count": 0,
    "error_count": 0,
    "duration_ms": 135
  }
}
```
- UI 冒烟（诊断页）：`http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - 可见字段：diagnosis_code=`OK`、severity=`LOW`、rule_id=`R-DIAG-000`
  - findings 列表可见（空态“暂无诊断发现”）
  - recommendations 列表可见（空态“暂无建议”）
- UI 回归（证据页）：`http://127.0.0.1:55173/teaching/attempts/17/evidence` 可打开，摘要字段可见

### Phase2 P1 验收证据（占位扩展点 + 教师文案）

- frontend_port=`55173`
- backend_port=`8000`
- attempt_id=`17`
- 端口监听（lsof）：
```text
COMMAND   PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
Python  89703 xuhehong 11u  IPv4 0x40c63fe75dde09de 0t0 TCP 127.0.0.1:8000 (LISTEN)
COMMAND  PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node    90141 xuhehong 22u  IPv4 0xaf2030067a625d43 0t0 TCP 127.0.0.1:55173 (LISTEN)
```
- openapi 探针：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/openapi.json` 返回 `HTTP/1.1 200 OK`，`x-trace-id: b18e61f7`
- diagnosis：`curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/17/diagnosis` 返回 `HTTP/1.1 200 OK`
  - 关键字段（占位扩展点为 `[]`）：
```json
{"reportVersion":"v1","attemptId":17,"diagnosisCode":"OK","ruleId":"R-DIAG-000","severity":"LOW","findings":[],"recommendations":[],"stepDiagnoses":[],"factors":[],"attachments":[],"generatedAt":"2026-01-31T04:05:27.382297","sourceRefs":{"attemptEvidenceId":11}}
```
- UI 冒烟：`http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - diagnosis_code=无异常（OK）
  - severity=低（LOW）
  - rule_id=R-DIAG-000
  - findings=无
  - recommendations=无
  - 证据关联=11

### Phase2 P2 验收证据（步骤诊断下钻）

- 失败证据（stepDiagnoses=[]）：
  - diagnosis：`curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/17/diagnosis`
  - 关键片段：
```json
{"reportVersion":"v1","attemptId":17,"diagnosisCode":"OK","ruleId":"R-DIAG-000","severity":"LOW","findings":[],"recommendations":[],"stepDiagnoses":[],"factors":[],"attachments":[],"generatedAt":"2026-01-31T10:18:50.984463","sourceRefs":{"attemptEvidenceId":11}}
```
- 修复证据（长度=2，对齐 total_steps）：
  - diagnosis：`curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/17/diagnosis` 返回 `HTTP/1.1 200 OK`
  - 关键片段：
```json
{"reportVersion":"v1","attemptId":17,"diagnosisCode":"OK","ruleId":"R-DIAG-000","severity":"LOW","findings":[],"recommendations":[],"stepDiagnoses":[{"stepIndex":1,"stepDiagnosisCode":"OK","severity":"LOW","findings":[],"recommendations":[],"ruleId":"R-DIAG-S-000","sourceRefs":{"stepId":null,"snapshotId":null}},{"stepIndex":2,"stepDiagnosisCode":"OK","severity":"LOW","findings":[],"recommendations":[],"ruleId":"R-DIAG-S-000","sourceRefs":{"stepId":null,"snapshotId":null}}],"factors":[],"attachments":[],"generatedAt":"2026-01-31T10:33:33.227817","sourceRefs":{"attemptEvidenceId":11}}
```
  - evidence：`curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/17/evidence` 返回 `HTTP/1.1 200 OK`
  - 关键片段（对齐 total_steps=2）：
```json
{"bundleId":"03c0089e-46fb-44f3-aab0-9d469ad150c6","taskId":1,"attemptId":17,"summary":{"task_id":1,"task_status":"completed","total_events":6,"snapshot_count":2,"total_steps":2,"skip_count":0,"error_count":0,"duration_ms":135,"final_score":100,"is_passed":true}}
```
- UI 冒烟：`http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - “步骤诊断”区块可见且可展开：是
  - 显示 2 步（与 summary.total_steps=2 一致）：是
  - 每步 severity 标签可见（低/LOW 映射为“低”）：是
  - 每步展开后 findings/recommendations 为空时显示“无”：是
  - 当前页可见示例：步骤1/步骤2 均显示“低”“无异常”（与 stepDiagnosisCode=OK 一致）

### 前端交付证据（无法 listen 的替代路径）

- 构建命令：`npm run build`
- 结果：构建通过，出现 `chunk` 体积告警但不影响结果

### 日志落点

- 后端失败日志：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend/logs/uvicorn-dev.log`
- 前端失败日志：`/tmp/vite-dev.log`

### Phase1 P0 自动验收（2026-01-30T12:23:36Z）

- 提交：`c140d2e`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`10`，student_id=`1`，task_id=`1`，attempt_id=`15`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-30T12:23:35.973189Z",
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
    "id": 15,
    "assignmentId": 10,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-30T12:23:35.999429",
    "updatedAt": "2026-01-30T12:23:35.999430"
}
```

**evidence**
```json
{
    "bundleId": "6a0c7772-874f-4f27-94c7-ea525160c127",
    "taskId": 1,
    "attemptId": 15,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 137,
        "final_score": 100,
        "is_passed": true
    }
}
```

### Phase1 P0 自动验收（2026-01-30T12:37:30Z）

- 提交：`c140d2e`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`11`，student_id=`1`，task_id=`1`，attempt_id=`16`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-30T12:37:30.068149Z",
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
    "id": 16,
    "assignmentId": 11,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-30T12:37:30.090497",
    "updatedAt": "2026-01-30T12:37:30.090498"
}
```

**evidence**
```json
{
    "bundleId": "59ef9925-c639-4a50-948f-7297b394ba36",
    "taskId": 1,
    "attemptId": 16,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 133,
        "final_score": 100,
        "is_passed": true
    }
}
```

### Phase1 P0 自动验收（2026-01-30T14:38:05Z）

- 提交：`85a3619`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`13`，student_id=`1`，task_id=`1`，attempt_id=`17`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-30T14:38:05.543418Z",
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
    "id": 17,
    "assignmentId": 13,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-30T14:38:05.579705",
    "updatedAt": "2026-01-30T14:38:05.579707"
}
```

**evidence**
```json
{
    "bundleId": "03c0089e-46fb-44f3-aab0-9d469ad150c6",
    "taskId": 1,
    "attemptId": 17,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 135,
        "final_score": 100,
        "is_passed": true
    }
}
```

### Phase1 P0 自动验收（2026-01-31T11:22:32Z）

- 提交：`82897c7`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`14`，student_id=`1`，task_id=`1`，attempt_id=`20`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-31T11:22:31.779395Z",
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
    "id": 20,
    "assignmentId": 14,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-31T11:22:31.806835",
    "updatedAt": "2026-01-31T11:22:31.806838"
}
```

**evidence**
```json
{
    "bundleId": "82506fd1-c5b0-4476-8880-f85f853c5fca",
    "taskId": 1,
    "attemptId": 20,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 132,
        "final_score": 100,
        "is_passed": true
    }
}
```

### 主目录回归验收（Phase2 基线冻结）

- 本次 completed_attempt_id=`21`（替代漂移的 `17`/`20`）
- Phase2 API（diagnosis）：`curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/21/diagnosis` 返回 `HTTP/1.1 200 OK`
```json
{"reportVersion":"v1","attemptId":21,"diagnosisCode":"OK","ruleId":"R-DIAG-000","severity":"LOW","findings":[],"recommendations":[],"stepDiagnoses":[{"stepIndex":1,"stepDiagnosisCode":"OK","severity":"LOW","findings":[],"recommendations":[],"ruleId":"R-DIAG-S-000","sourceRefs":{"stepId":null,"snapshotId":null}},{"stepIndex":2,"stepDiagnosisCode":"OK","severity":"LOW","findings":[],"recommendations":[],"ruleId":"R-DIAG-S-000","sourceRefs":{"stepId":null,"snapshotId":null}}],"factors":[],"attachments":[],"generatedAt":"2026-01-31T11:32:50.166982","sourceRefs":{"attemptEvidenceId":13}}
```
- Phase2 API（evidence）：`curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/21/evidence` 返回 `HTTP/1.1 200 OK`
```json
{"bundleId":"803288ea-ea01-4805-8c20-eb57b2180bb1","taskId":1,"attemptId":21,"summary":{"task_id":1,"task_status":"completed","total_events":6,"snapshot_count":2,"total_steps":2,"skip_count":0,"error_count":0,"duration_ms":144,"final_score":100,"is_passed":true}}
```
- UI 冒烟：`http://127.0.0.1:55173/teaching/attempts/21/diagnosis`
  - “步骤诊断”区块可见且可展开：是
  - 显示 2 步：是
  - 每步 severity 标签可见：是
  - 每步展开后空态显示“无”：是
- 前端 build：`npm run build` 通过（证据可复用“前端交付证据（无法 listen 的替代路径）”段落）

### Phase1 P0 自动验收（2026-01-31T11:30:39Z）

- 提交：`82897c7`
- 命令：`cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0/r-mos-backend && bash scripts/run_phase1_e2e.sh`
- 关键 ID：assignment_id=`15`，student_id=`1`，task_id=`1`，attempt_id=`21`

**health**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-31T11:30:38.882899Z",
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
    "id": 21,
    "assignmentId": 15,
    "studentId": 1,
    "taskId": 1,
    "evidenceBundleId": null,
    "status": "in_progress",
    "score": null,
    "attemptIndex": 1,
    "diagnosisCode": null,
    "pathScore": null,
    "evidenceQualityScore": null,
    "createdAt": "2026-01-31T11:30:38.904024",
    "updatedAt": "2026-01-31T11:30:38.904026"
}
```

**evidence**
```json
{
    "bundleId": "803288ea-ea01-4805-8c20-eb57b2180bb1",
    "taskId": 1,
    "attemptId": 21,
    "summary": {
        "task_id": 1,
        "task_status": "completed",
        "total_events": 6,
        "snapshot_count": 2,
        "total_steps": 2,
        "skip_count": 0,
        "error_count": 0,
        "duration_ms": 144,
        "final_score": 100,
        "is_passed": true
    }
}
```
