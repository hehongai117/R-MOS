# 测试计划

## 阶段一回归矩阵（任务1-任务6）

> 说明：所有用例优先使用 `python r-mos-backend/scripts/seed_teaching_demo.py --reset` 生成教学演示数据。  
> 说明：需要 `assignment_id`、`class_id` 的场景，以脚本输出为准。  
> 说明：需要 `attempt_id` 的场景，先执行以下命令创建尝试并记录返回的 `id`：  
> `curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts -H "Content-Type: application/json" -d '{"studentId": {student_id}}'`

### 任务1（数据模型与迁移）

- 用例编号：T1-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}
    ```
  - 可选界面：`/teaching/assignments`
  - 期望结果（关键字段+状态码）：
    - `200`，包含 `id`、`classId`、`title`、`sopId`
  - 标签：P0

- 用例编号：T1-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/classes/{class_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，`metadata` 为对象
  - 标签：P1

### 任务2（数据结构与字段输出）

- 用例编号：T2-01
  - 角色：学生
  - 前置数据/种子命令：无
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/guidance-policies \
      -H "Content-Type: application/json" \
      -d '{"name": "练习模式", "baseMode": "teaching"}'
    ```
  - 期望结果（关键字段+状态码）：
    - `201`，包含 `baseMode`、`allowGhostHand`、`allowHintButton`、`showErrorDetails`、`maxRetryCount`
  - 标签：P0

- 用例编号：T2-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，包含 `diagnosisCode`、`pathScore`、`evidenceQualityScore`（允许为空）
  - 标签：P1

### 任务3（教学服务层与状态流转）

- 用例编号：T3-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts \
      -H "Content-Type: application/json" \
      -d '{"studentId": {student_id}}'
    curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts \
      -H "Content-Type: application/json" \
      -d '{"studentId": {student_id}}'
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `201`，第二次 `attemptIndex = 第一次 + 1`
  - 标签：P0

- 用例编号：T3-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "completed"}'
    curl -X POST http://localhost:8000/api/v1/attempts/{attempt_id}/grade \
      -H "Content-Type: application/json" \
      -d '{"score": 95}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第一步 `200`，`status = completed`
    - 第二步 `200`，`status = graded`，`score` 有值
  - 标签：P0

- 用例编号：T3-03
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "graded"}'
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "completed"}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第二步 `409`，错误码 `INVALID_ATTEMPT_STATUS_TRANSITION`
  - 标签：P1

### 任务4（教学接口与错误处理）

- 用例编号：T4-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，返回数组，元素包含 `id`、`classId`、`title`
  - 标签：P0

- 用例编号：T4-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/enrollments \
      -H "Content-Type: application/json" \
      -d '{"classId": {class_id}, "studentId": {student_id}}'
    curl -X POST http://localhost:8000/api/v1/enrollments \
      -H "Content-Type: application/json" \
      -d '{"classId": {class_id}, "studentId": {student_id}}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第二次 `409`，错误码 `ALREADY_ENROLLED`
  - 标签：P0

- 用例编号：T4-03
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}/attempts
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，元素包含 `attemptIndex`、`status`
  - 标签：P1

### 任务5（证据引擎与证据关联）

- 用例编号：T5-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/start
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/step \
      -H "Content-Type: application/json" \
      -d '{"step_index": 1, "action": "inspect"}'
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/step \
      -H "Content-Type: application/json" \
      -d '{"step_index": 2, "action": "execute"}'
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 第四步 `200`，`summary` 包含 `total_steps`、`skip_count`、`error_count`、`duration_ms`
  - 标签：P0

- 用例编号：T5-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - `404`
  - 标签：P1

- 用例编号：T5-03
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，`evidenceBundleId` 不为空
  - 标签：P1

- 用例编号：T5-04
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/tasks/{task_id}/report
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 第一步 `200`
    - 第二步 `200`，且 `summary` 包含 `total_steps`、`error_count`、`skip_count`、`duration_ms`
  - 标签：P0

### 任务6（教学前端最小闭环）

- 用例编号：T6-01
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}/attempts
    ```
  - 可选界面：`/teaching/assignments`
  - 期望结果（关键字段+状态码）：
    - `200`，出现尝试列表，包含 `attemptIndex` 与 `status`
  - 标签：P0

- 用例编号：T6-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 可选界面：`/teaching/attempts/{attempt_id}/evidence`
  - 期望结果（关键字段+状态码）：
    - `200`，页面显示 `summary` 关键字段（`duration_ms` 等）
  - 标签：P1

### 任务8（默认 Postgres 迁移与契约校验）

- 用例编号：T8-01
  - 角色：开发
  - 前置数据/种子命令：`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
  - 接口验收（curl）：
    ```bash
    make migrate
    ```
  - 期望结果（关键字段+状态码）：
    - 命令成功完成，无报错
  - 标签：P0

- 用例编号：T8-02
  - 角色：开发
  - 前置数据/种子命令：`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
  - 接口验收（curl）：
    ```bash
    make seed-demo
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `作业`、`任务`、`学生` 信息
  - 标签：P0

- 用例编号：T8-03
  - 角色：开发
  - 前置数据/种子命令：`ALLOW_BOOTSTRAP=1`
  - 接口验收（curl）：
    ```bash
    ALLOW_BOOTSTRAP=1 DATABASE_URL=sqlite+aiosqlite:////tmp/rmos_demo.db \\
      r-mos-backend/.venv/bin/python r-mos-backend/scripts/seed_teaching_demo.py --bootstrap --reset
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `作业` 与 `任务`，允许使用临时库
  - 标签：P1

### 任务9（前端环境治理与一键启动）

- 用例编号：T9-01
  - 角色：开发
  - 前置数据/种子命令：无
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/docs
    ```
  - 操作步骤（命令）：
    ```bash
    cd r-mos-frontend
    npm install
    ```
  - 期望结果（关键字段+状态码）：
    - `npm install` 成功完成，无 `EPERM`
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T9-02
  - 角色：开发
  - 前置数据/种子命令：`make migrate && make seed-demo`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 操作步骤（命令）：
    ```bash
    make dev
    ```
  - 期望结果（关键字段+状态码）：
    - 后端与前端均启动成功
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T9-03
  - 角色：学生
  - 前置数据/种子命令：`make seed-demo`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 可选界面：`/teaching/assignments` → `/teaching/attempts/{attempt_id}` → `/teaching/attempts/{attempt_id}/evidence`
  - 期望结果（关键字段+状态码）：
    - `200`，`summary` 包含 `total_steps`、`error_count`、`duration_ms`
  - 标签：P0

### 任务10（前端路径修正与代理分流安装构建）

- 用例编号：T10-01
  - 角色：开发
  - 前置数据/种子命令：系统代理保持开启
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/docs
    ```
  - 操作步骤（命令）：
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm install
    ```
  - 期望结果（关键字段+状态码）：
    - `npm install` 成功完成
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T10-02
  - 角色：开发
  - 前置数据/种子命令：已完成 T10-01
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 操作步骤（命令）：
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm run build
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `vite` 构建完成信息
    - 生成 `dist` 目录
    - 若出现 `chunk` 大小超过 `500 kB` 的警告，不判失败
    - `curl` 返回 `200`
  - 标签：P0

### Phase1 UI 冒烟

- 用例编号：UI-01（PASS）
  - 角色：学生/教师
  - 前置数据/种子命令：
    ```bash
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    make migrate
    make seed-demo
    make dev-backend
    make dev-frontend
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/tasks/4/report
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/13/evidence
    ```
  - UI 路径验收：
    - 打开 `http://localhost:3000/teaching/attempts/13/evidence`
  - 期望结果（关键字段+状态码）：
    - 接口：两次请求均为 `200`
    - 界面：显示 `task_status=completed`、`total_steps=2`、`error_count=0`、`final_score=100`、`is_passed=true`
  - 标签：P0

### 任务11（诊断报告 P0）

- 用例编号：T11-01
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 error_count > 0，且 skip_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_ERROR_OCCURRED`
    - `rule_id=R-DIAG-001`
    - `severity=HIGH`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-02（No match / R-DIAG-000）
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 error_count=0、skip_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=OK`
    - `rule_id=R-DIAG-000`
    - `severity=LOW`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-03
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 skip_count > 0，且 error_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_STEP_SKIPPED`
    - `rule_id=R-DIAG-002`
    - `severity=MEDIUM`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-04
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 duration_ms > 5000，且 error_count=0、skip_count=0
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_TOO_SLOW`
    - `rule_id=R-DIAG-003`
    - `severity=LOW`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-05（规则不触发样例）
  - 角色：教师
  - 前置数据/种子命令：复用 T11-02 的 attempt（error_count=0、skip_count=0、duration_ms<=5000）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - 未触发 R-DIAG-001/002/003（落入 R-DIAG-000）
  - 标签：P0

- 用例编号：T11-06（fallback 兜底）
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，且不存在 evidence_link（允许触发兜底生成）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `source_refs.attempt_evidence_id` 非空
  - 标签：P0

- 用例编号：T11-07（并发一致性）
  - 角色：教师
  - 前置数据/种子命令：任一教学 attempt（输入源不变）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - 三次均 `200`
    - 三次 `diagnosis_code` 一致
  - 标签：P0

### 任务12（环境阻塞与验收收口）

- 用例编号：T12-UI-01（前端 listen EPERM 复现）
  - 角色：教师
  - 前置数据/种子命令：无
  - 接口验收（命令）：
    ```bash
    python3 -m http.server 18000
    npm run dev -- --host 127.0.0.1 --port 3000
    npm run dev -- --host 127.0.0.1 --port 3100
    npm run dev -- --host 0.0.0.0 --port 55173
    ```
  - 期望结果（关键字段+状态码）：
    - 均报 `EPERM` / `Operation not permitted`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 阶段3 前端 listen EPERM 根因调查（不可交付 UI）`
  - 标签：P0

- 用例编号：T12-UI-02（UI 冒烟：诊断页 completed attempt）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - 期望结果（关键字段可见）：
    - diagnosis_code、severity、rule_id 可见
    - findings、recommendations 列表可见（允许空态）
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P0 UI 冒烟（前端 55173 + 后端 8000）`
  - 标签：P0

- 用例编号：T12-API-01（Phase2 P0 后端诊断与证据 200）
  - 角色：教师
  - 前置数据/种子命令：Phase1 e2e 产物 attempt_id=`16`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/diagnosis
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `200`
    - diagnosis 含 `reportVersion`、`diagnosisCode`、`ruleId`、`severity`、`sourceRefs.attemptEvidenceId`
    - evidence 含 `summary`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P0 真实运行验收（后端）`
  - 标签：P0

### 任务13（Phase2 P1 占位扩展点与教师文案）

- 用例编号：T13-API-01（DiagnosisReport v1 占位扩展点字段返回）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`；backend_port=`8000`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/17/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `stepDiagnoses`、`factors`、`attachments` 均为 `[]`
    - `reportVersion`、`attemptId`、`diagnosisCode`、`ruleId`、`severity` 存在
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P1 验收证据（占位扩展点 + 教师文案）`
  - 标签：P1

- 用例编号：T13-UI-01（诊断页教师文案与空态）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`；frontend_port=`55173`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - 期望结果（关键字段可见）：
    - diagnosis_code 显示教师文案“无异常”
    - severity 显示教师文案“低”
    - findings 空态显示“无”
    - recommendations 空态显示“无”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P1 验收证据（占位扩展点 + 教师文案）`
  - 标签：P1

### 任务14（Phase2 P2 步骤诊断下钻）

- 用例编号：T14-API-01（stepDiagnoses 长度与字段）（PASS）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`22`；backend_port=`8000`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/22/evidence
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/22/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `200`
    - evidence `summary.total_steps=2`
    - diagnosis `stepDiagnoses` 长度=2，且包含 `stepIndex`、`stepDiagnosisCode`、`severity`、`ruleId`、`findings`、`recommendations`、`sourceRefs`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `主目录回归验收（Phase2 基线冻结）`
  - 标签：P2

- 用例编号：T14-UI-01（步骤诊断区块下钻）（PASS）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`22`；frontend_port=`55173`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/22/diagnosis`
  - 期望结果（关键字段可见）：
    - “步骤诊断”区块可见且可展开
    - 显示 2 步（与 summary.total_steps=2 一致）
    - 每步 severity 标签可见（低）
    - 每步展开后 findings/recommendations 空态显示“无”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `主目录回归验收（Phase2 基线冻结）`
  - 标签：P2

### 任务15（Phase3 Step 1 规则真实触发闭环）

- 用例编号：T15-RULE-01（R-DIAG-001 error_count）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`23`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case error
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/23/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.error_count>=1`、`summary.total_steps` 可见
    - diagnosis：`200` 且 `ruleId=R-DIAG-001`、`diagnosisCode=E_ERROR_OCCURRED`、`severity=HIGH`
    - UI：教师文案显示“存在错误步骤”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

- 用例编号：T15-RULE-02（R-DIAG-002 skip_count）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`24`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case skip
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/24/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.skip_count>=1`、`summary.total_steps` 可见
    - diagnosis：`200` 且 `ruleId=R-DIAG-002`、`diagnosisCode=E_STEP_SKIPPED`、`severity=MEDIUM`
    - UI：教师文案显示“存在跳过步骤”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

- 用例编号：T15-RULE-03（R-DIAG-003 duration_ms）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`25`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case slow
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/25/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.duration_ms>5000`、`summary.total_steps` 可见（已知口径差异需在报告标注）
    - diagnosis：`200` 且 `ruleId=R-DIAG-003`、`diagnosisCode=E_TOO_SLOW`、`severity=LOW`
    - UI：教师文案显示“步骤耗时偏长”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

### 任务16（Phase3 Step2 触发步骤定位）

- 用例编号：T16-STEPDIAG-01（R-DIAG-001 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`23`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/23/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “该步骤存在错误”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3

- 用例编号：T16-STEPDIAG-02（R-DIAG-002 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`24`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/24/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “该步骤被跳过”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3

- 用例编号：T16-STEPDIAG-03（R-DIAG-003 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`25`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/25/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “步骤耗时偏长”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3
