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
