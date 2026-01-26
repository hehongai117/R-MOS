# 测试计划

## 阶段一回归矩阵（任务1–任务6）

> 说明：所有用例优先使用 `python r-mos-backend/scripts/seed_teaching_demo.py` 生成教学演示数据；如需 SOP 基础数据，可补充执行 `python r-mos-backend/scripts/seed_data.py`。

### 任务1（数据模型与迁移）

- 用例编号：T1-01
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `POST /api/v1/classes`，body 含 `name` 与 `metadata`
    2) `GET /api/v1/classes/{id}`
  - 期望结果（关键字段+状态码）：
    - 第一步 `201`，返回 `id`、`name`、`metadata`
    - 第二步 `200`，`metadata` 为对象且字段保持
  - 标签：P0

- 用例编号：T1-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `POST /api/v1/assignments`，body 含 `classId` 与 `title`
    2) `GET /api/v1/assignments/{id}`
  - 期望结果（关键字段+状态码）：
    - 第一步 `201`，返回 `id`、`classId`、`title`
    - 第二步 `200`，`classId` 与创建一致
  - 标签：P0

### 任务2（数据结构与字段输出）

- 用例编号：T2-01
  - 前置数据/种子命令：无
  - 操作步骤（接口或界面）：
    1) `POST /api/v1/guidance-policies`
  - 期望结果（关键字段+状态码）：
    - `201`，返回字段包含 `baseMode`、`allowGhostHand`、`allowHintButton`、`showErrorDetails`、`maxRetryCount`
  - 标签：P0

- 用例编号：T2-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `POST /api/v1/assignments/{id}/attempts`
    2) `GET /api/v1/attempts/{attemptId}`
  - 期望结果（关键字段+状态码）：
    - 第一步 `201`，返回 `attemptIndex`
    - 第二步 `200`，返回 `diagnosisCode`、`pathScore`、`evidenceQualityScore`（允许为空）
  - 标签：P1

### 任务3（教学服务层与状态流转）

- 用例编号：T3-01
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 对同一 `assignmentId + studentId` 连续两次 `POST /api/v1/assignments/{id}/attempts`
  - 期望结果（关键字段+状态码）：
    - 两次均 `201`
    - 第二次 `attemptIndex = 第一次 + 1`
  - 标签：P0

- 用例编号：T3-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `PATCH /api/v1/attempts/{id}` 将状态更新到 `graded`
    2) 再次 `PATCH /api/v1/attempts/{id}` 试图改回 `completed`
  - 期望结果（关键字段+状态码）：
    - 第二步返回 `409`，错误码 `INVALID_ATTEMPT_STATUS_TRANSITION`
  - 标签：P0

### 任务4（教学接口与错误处理）

- 用例编号：T4-01
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `GET /api/v1/assignments`
  - 期望结果（关键字段+状态码）：
    - `200`，返回数组，元素包含 `id`、`classId`、`title`
  - 标签：P0

- 用例编号：T4-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `POST /api/v1/enrollments`（相同 `classId + studentId` 连续两次）
  - 期望结果（关键字段+状态码）：
    - 第二次返回 `409`，错误码 `ALREADY_ENROLLED`
  - 标签：P0

- 用例编号：T4-03
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) `GET /api/v1/assignments/{id}/attempts`
  - 期望结果（关键字段+状态码）：
    - `200`，返回数组，元素包含 `attemptIndex` 与 `status`
  - 标签：P1

### 任务5（证据引擎与证据关联）

- 用例编号：T5-01
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 创建任务并执行 `/api/v1/tasks/{id}/start`
    2) 按 SOP 步骤执行 `/api/v1/tasks/{id}/step`
    3) `GET /api/v1/attempts/{attemptId}/evidence`
  - 期望结果（关键字段+状态码）：
    - 第三步 `200`，`summary` 包含 `total_steps`、`skip_count`、`error_count`、`duration_ms`
  - 标签：P0

- 用例编号：T5-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 对未绑定任务的尝试调用 `GET /api/v1/attempts/{id}/evidence`
  - 期望结果（关键字段+状态码）：
    - `404`
  - 标签：P1

- 用例编号：T5-03
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 完成任务后 `GET /api/v1/attempts/{id}`
  - 期望结果（关键字段+状态码）：
    - `200`，`evidenceBundleId` 不为空
  - 标签：P1

### 任务6（教学前端最小闭环）

- 用例编号：T6-01
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 打开 `/teaching/assignments`
    2) 输入学生编号并点击“开始”
  - 期望结果（关键字段+状态码）：
    - 成功进入 `/teaching/attempts/{id}`
  - 标签：P0

- 用例编号：T6-02
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py`
  - 操作步骤（接口或界面）：
    1) 在尝试页启动任务并执行步骤
    2) 任务完成后点击“查看证据摘要”
  - 期望结果（关键字段+状态码）：
    - 证据页展示 `summary` 字段，包含 `duration_ms` 等关键统计
  - 标签：P0

- 用例编号：T6-03
  - 前置数据/种子命令：无
  - 操作步骤（接口或界面）：
    1) 访问 `/teaching/attempts/999999/evidence`
  - 期望结果（关键字段+状态码）：
    - 页面显示中文错误提示，包含 `404`
  - 标签：P1
