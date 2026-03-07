# R-MOS 用户核心流程改造实施方案
> **版本** V0.2-IMPL · **日期** 2026-03-04  
> **范围** 仅覆盖补充方案 V0.2（用户核心流程）· V1.0 已完成开发，不在本文档范围内  
> **总工期** 10 周 · **两阶段** Phase 1（第 1-6 周）→ Phase 2（第 7-10 周）

---

## 阅读说明

```
三级任务结构：
  主任务   UF-01            可分配给小组的功能模块
  子任务   UF-01-a          可分配给个人的工作包（1-3天）
  原子任务 UF-01-a-1        可直接执行的最小开发单元（半天~1天）

标记约定：
  🔴 阻塞   当前子阶段必须完成，后续任务依赖它
  🟡 并行   可与其他任务并行开展
  ✅ 复用   直接复用 V1.0 已有能力，无需重新开发
```

---

## 全局概览

| Phase | 周期 | 主任务数 | 核心目标 |
|-------|------|---------|---------|
| **Phase 1** | 第 1-6 周 | 7 个（UF-01 ~ UF-07） | 用户主流程全线上线：身份识别 → 需求理解 → 项目生成 → 工作台四联动 → 训练执行 |
| **Phase 2** | 第 7-10 周 | 5 个（UF-08 ~ UF-12） | 教学闭环：提交 → AI 反馈 → 记忆写入 → 技能成长可视化 → 教师监控台 |

### 与 V1.0 的接口约定（已可直接调用）

| V1.0 能力 | 本方案调用方式 |
|-----------|--------------|
| `LLMRouter.complete()` | 项目生成、反馈生成、欢迎摘要均通过此接口 |
| `KnowledgeHub.search()` | 项目生成双路检索的路 A |
| `MemoryHub` 三层记忆 | 项目生成双路检索的路 B；训练后记忆写入 |
| `require_permission` 鉴权 | 所有新增接口直接注入，无需自行实现 |
| `audit_events` 写入 | 新服务产生的关键行为均写入，沿用现有结构 |
| `conversation_turns` 表 | 训练对话直接写入，无需新建 |

---

## Phase 1 · 用户主流程（第 1-6 周）

> **阶段目标**：学员从登录到完成一次完整训练执行（不含提交反馈），全流程跑通。  
> **阶段验收**：学员登录后自动路由到训练工作台；说出需求后 10s 内生成训练项目；工作台四面板 3s 内完成初始化；步骤切换 3D/工具联动延迟 < 200ms；中断后可续训。

---

### UF-01 · 角色数据模型与登录路由
> 🔴 阻塞任务，其余所有任务依赖角色体系  
> **负责**：后端 + 前端 · **工时**：3 天

**验收标准**：
- 三种角色（student / teacher / admin）登录后自动跳转到各自默认工作台
- 越权访问页面时自动重定向，并显示「无权限」提示
- `classes` / `class_members` 表迁移成功，现有用户默认 `role='student'`

---

#### UF-01-a · 数据库迁移
> 🔴 先行，其他子任务依赖此表结构

- [ ] **UF-01-a-1** `users` 表新增四个字段：`role VARCHAR(20) DEFAULT 'student'` / `teacher_id UUID` / `class_id UUID` / `hint_level INTEGER DEFAULT 3`
- [ ] **UF-01-a-2** 新建 `classes` 表：`class_id UUID PK` / `name VARCHAR(100)` / `teacher_id UUID FK → users` / `created_at TIMESTAMP`
- [ ] **UF-01-a-3** 新建 `class_members` 表：`(class_id UUID FK, user_id UUID FK)` 复合主键 + `joined_at TIMESTAMP`
- [ ] **UF-01-a-4** 编写 Alembic 迁移脚本，在 staging 执行，确认现有用户均获得默认值 `role='student'`

#### UF-01-b · 角色管理接口
> 🟡 可与 UF-01-c 并行

- [ ] **UF-01-b-1** `POST /api/v1/admin/users/{user_id}/role`：更新用户角色，仅 admin 可调用，写 `audit_event`（type='role_change'）
- [ ] **UF-01-b-2** `GET /api/v1/classes`：教师查自己名下班级；admin 查全部；支持分页
- [ ] **UF-01-b-3** `POST /api/v1/classes`：创建班级（teacher / admin 权限）
- [ ] **UF-01-b-4** `POST /api/v1/classes/{class_id}/members`：批量添加学员到班级，去重处理

#### UF-01-c · 前端路由与权限守卫
> 🟡 可与 UF-01-b 并行

- [ ] **UF-01-c-1** 登录接口响应体新增 `role` 和 `default_route` 字段（后端改动）
- [ ] **UF-01-c-2** 前端登录成功后，根据 `default_route` 自动跳转：`student` → `/workbench/training`，`teacher` → `/workbench/teaching`，`admin` → `/admin/console`
- [ ] **UF-01-c-3** 路由守卫：检测当前 token 中的 `role`，无权限访问的路由自动重定向到本角色默认工作台
- [ ] **UF-01-c-4** 全局搜索前端代码中的角色硬编码（`isAdmin` / `role === 'admin'`），统一改为读取 token payload 的 `role` 字段

---

### UF-02 · 会话初始化与 Agent 角色策略
> 🔴 阻塞，UF-03 / UF-04 的 LLM 行为依赖此配置  
> **负责**：后端 · **工时**：4 天 · **依赖**：UF-01

**验收标准**：
- 学生登录后看到包含上次训练成果和今日推荐的个性化欢迎摘要
- 教师登录后看到班级近 7 天训练统计概况
- 同一问题：学生收到引导式回复（不直接给答案），教师收到完整分析回复

---

#### UF-02-a · SessionInitializer 服务
> 🔴 先行

- [ ] **UF-02-a-1** 新建 `services/identity/session_initializer.py`，定义 `initialize_session(user_id) -> SessionContext` 方法，登录成功后自动触发
- [ ] **UF-02-a-2** **学生路径**：调用 `MemoryHub.get_profile(user_id)` 获取技能画像 → 构建欢迎 prompt（含上次训练结果 + 薄弱点提示 + 今日推荐方向）→ `LLMRouter.complete()` 生成 2-3 句欢迎摘要
- [ ] **UF-02-a-3** **教师路径**：查询名下所有班级近 7 天训练统计（完成数 / 平均分 / 失败率最高的步骤）→ 规则拼接班级概况摘要，不调用 LLM
- [ ] **UF-02-a-4** **管理员路径**：返回系统健康摘要（在线用户数 / 当日训练任务数 / 未处理告警数），规则生成
- [ ] **UF-02-a-5** `SessionContext` 对象存入 Redis（key: `session:{user_id}`，TTL 8h），后续每次请求读取而非重新查询

#### UF-02-b · AgentPolicyFactory
> 🟡 可与 UF-02-a 并行

- [ ] **UF-02-b-1** 新建 `services/identity/agent_policy_factory.py`，`build(role, memory) -> AgentConfig`
- [ ] **UF-02-b-2** `student` 配置项：`guidance_mode=True` / `hint_level=user.hint_level(1-5)` / `difficulty_cap=skill_level+1` / `show_answers=False`
- [ ] **UF-02-b-3** `teacher` 配置项：`observe_mode=True` / `can_override_verdict=True` / `show_full_analysis=True`
- [ ] **UF-02-b-4** `admin` 配置项：`management_mode=True` / `audit_access=True`
- [ ] **UF-02-b-5** `AgentConfig` 随 `SessionContext` 一起存入 Redis，每次 LLM 调用时自动注入系统提示

#### UF-02-c · 角色差异化系统提示
> 🟡 依赖 UF-02-b

- [ ] **UF-02-c-1** 在 `PromptTemplateEngine`（V1.0 已有）的系统提示区块末尾，根据 `agent_config` 动态注入角色策略：学生模式附加「引导用户思考，不要直接给出答案或正确数值」；教师模式附加「直接给出完整分析和参考答案」
- [ ] **UF-02-c-2** `hint_level` 映射到提示细度：`1`=只确认操作结果 / `3`=给出操作要点 / `5`=逐步骤详细引导
- [ ] **UF-02-c-3** 高难度步骤门控：Agent 响应前检查 `skill_level >= step.required_level`，不满足时拒绝并给出前置训练建议，不允许强行继续
- [ ] **UF-02-c-4** 数据权限边界：学生查询他人数据时，Agent 层返回明确拒绝（不仅 API 层），教师查询学员数据时后端校验归属关系（`class_members` 表）

---

### UF-03 · 训练需求意图识别（专项扩展）
> 🟡 可与 UF-02 并行开展，UF-04 依赖本任务  
> **负责**：后端 · **工时**：3 天 · **依赖**：UF-01（技能等级数据）

**验收标准**：
- 5 种训练意图类型识别准确率 ≥ 90%（20 条标注测试样本）
- 参数缺失时 Agent 主动追问，不猜测

---

#### UF-03-a · 五类训练意图定义

- [ ] **UF-03-a-1** 在 V1.0 `IntentEngine` 的意图枚举中新增训练专项类型：`TRAINING_NEW` / `TRAINING_WEAKNESS` / `TRAINING_CERT` / `TRAINING_ASSIGNED` / `TRAINING_EXPLORE`
- [ ] **UF-03-a-2** 训练意图识别成功后，直接路由到 `ProjectGenerator`（UF-04），跳过普通对话分发逻辑

#### UF-03-b · 各类意图参数提取逻辑

- [ ] **UF-03-b-1** `TRAINING_NEW`：LLM 提取 `brand` / `model` / `category`，任一缺失时 Agent 追问，全部获取后才触发生成
- [ ] **UF-03-b-2** `TRAINING_WEAKNESS`：不需用户指定步骤，自动从 `student_weak_steps` 表（UF-10 建立）读取 Top3 薄弱步骤；表不存在时降级为 `TRAINING_NEW` 并提示「暂无历史薄弱记录，已切换为全新训练」
- [ ] **UF-03-b-3** `TRAINING_CERT`：提取目标等级（L1/L2/L3）和维保类别；校验前置认证是否已完成，未完成时告知缺失条件
- [ ] **UF-03-b-4** `TRAINING_ASSIGNED`：提取任务 ID，查 `assignments` 表验证任务存在、归属当前用户、未过期
- [ ] **UF-03-b-5** `TRAINING_EXPLORE`：只需提取维保类别，生成无严格裁决的轻量引导式项目

#### UF-03-c · 测试样本与评测

- [ ] **UF-03-c-1** 整理 20 条训练意图标注样本：每种类型至少 3 条，含边界情况（如拼写变体、口语化表达、多意图混合）
- [ ] **UF-03-c-2** 将样本集成到 V1.0 已有评测脚本，输出五类意图的精确率/召回率报告
- [ ] **UF-03-c-3** 准确率不达标时分析失败样本，补充 few-shot 示例或调整 prompt，直到达标

---

### UF-04 · 训练项目生成器（ProjectGenerator）
> 🔴 核心交付，UF-05 工作台直接依赖本任务输出  
> **负责**：全栈 · **工时**：6 天 · **依赖**：UF-03 / UF-06（会话表结构）

**验收标准**：
- 生成的 TrainingProject 包含完整 `steps[]` / `tools_checklist[]` / `verdict_config` / `robot`
- 薄弱步骤（从记忆读取）自动出现在生成项目中
- 生成总耗时 < 10s（含双路检索 + LLM 调用）
- 知识库无该型号数据时，返回明确提示而非生成空步骤

---

#### UF-04-a · 双路融合检索

- [ ] **UF-04-a-1** 新建 `services/training/project_generator.py`
- [ ] **UF-04-a-2** **路 A（知识库）**：调用 `KnowledgeHub.search(query=intent.description, filters={brand, model, category}, top_k=10)`，返回匹配 SOP 步骤 + 技术规格 + 历史故障案例
- [ ] **UF-04-a-3** **路 B（个人记忆）**：调用 `MemoryHub.get_student_profile(user_id)`，获取 `skill_level` / `weak_steps(Top3)` / `completed_tasks`（避免重复）/ `avg_duration`
- [ ] **UF-04-a-4** 若路 A 返回 `insufficient_data`（chunk 数 < 5），直接终止并返回错误：`{ error: "knowledge_missing", hint: "请先在知识库上传 {brand} {model} 的技术手册" }`
- [ ] **UF-04-a-5** 将两路结果合并为统一 `GenerationContext` 对象，注入生成 prompt

#### UF-04-b · LLM 项目生成

- [ ] **UF-04-b-1** 设计项目生成 prompt，约束条件注入：`max_steps=20` / `difficulty_cap=skill_level+1` / `emphasize_weak=weak_steps[:3]` / `estimated_time=60min` / `avoid_repeated=completed_tasks`
- [ ] **UF-04-b-2** 要求 LLM 强制输出 TrainingProject JSON 结构（复用 V1.0 `PromptTemplateEngine` 的强制 JSON 输出机制）
- [ ] **UF-04-b-3** 实现 `TrainingProject.parse(raw_json)`：必填字段校验（steps 非空 / robot 非空 / tools_checklist 非空），校验失败抛出带原因的异常
- [ ] **UF-04-b-4** 降级策略：LLM 解析失败时，从知识库直接加载评分最高的匹配 SOP 作为训练项目，告知用户「已为您选取最相近的标准训练方案」

#### UF-04-c · 项目合规检查

- [ ] **UF-04-c-1** 步骤引用检查：每个 step 必须含 `ref_ids`，无引用的步骤自动标注 `"⚠ 依据待补充"`，不阻断生成
- [ ] **UF-04-c-2** 安全步骤自动补全：检查步骤列表是否包含「安全确认」类步骤，缺失时在 step[0] 之前自动插入安全检查步骤（从知识库检索通用安全规范 chunk）
- [ ] **UF-04-c-3** `verdict_config` 生成规则：`TRAINING_CERT` 意图 → `mode='strict'`（无提示）；`TRAINING_EXPLORE` 意图 → `mode='guided'`（无裁决）；其余默认 `mode='normal'`

#### UF-04-d · 生成接口与流式响应

- [ ] **UF-04-d-1** 新建接口 `POST /api/v1/training/projects/generate`，请求体：`{ intent: TrainingIntent, user_id }`，响应：`TrainingProject`
- [ ] **UF-04-d-2** 接口支持 SSE 流式响应，阶段性推送状态：`"检索知识库中…"` → `"分析历史记录…"` → `"生成训练步骤…"` → `"完成"`
- [ ] **UF-04-d-3** 前端收到完整 `TrainingProject` 对象后触发 `WorkbenchOrchestrator.init(project)`（UF-05）

---

### UF-05 · 工作台编排器（WorkbenchOrchestrator）
> 🔴 核心交付，工作台四面板联动的协调中枢  
> **负责**：前端 · **工时**：6 天 · **依赖**：UF-04

**验收标准**：
- 收到 TrainingProject 后 3s 内四面板完成初始化
- 步骤切换后工具面板高亮 + 3D 模型聚焦更新延迟 < 200ms
- 关键工具全部「已确认」前，裁决提交按钮保持锁定
- 任意工具标记「异常」时，Agent 自动响应并给出处理建议

---

#### UF-05-a · 全局状态（WorkbenchStore）

- [ ] **UF-05-a-1** 新建 `WorkbenchStore`（全局状态管理，Zustand 或 Redux），字段：`project` / `currentStepIndex` / `sessionId` / `mode` / `toolsStatus(Map<toolId, status>)` / `verdictState`
- [ ] **UF-05-a-2** 实现 `WorkbenchOrchestrator.init(project: TrainingProject)` 主入口，接收生成器输出并驱动四面板初始化
- [ ] **UF-05-a-3** 初始化完成后路由跳转至 `/workbench/training`，并调用 `agentAPI.notifyWorkbenchReady(project.project_id)`，触发 Agent 推送首步引导

#### UF-05-b · 四面板并行初始化

- [ ] **UF-05-b-1** **步骤面板（StepPanel）**：渲染 `project.steps`，高亮 `steps[0]`，顶部展示进度条（当前步/总步数）
- [ ] **UF-05-b-2** **工具面板（ToolPanel）**：渲染 `project.tools_checklist`，`is_critical=true` 的工具置顶显示，所有工具初始状态为 `PENDING`（待确认）
- [ ] **UF-05-b-3** **3D 模型面板（ModelPanel）**：调用 `window.__agent3DCommand({ action: "load", asset_id: project.robot.asset_id })`，加载完成后调用 `window.__agent3DCommand({ action: "highlight", parts: steps[0].model_highlight })`（复用 V1.0 已建立的 3D 接口，不改渲染层）
- [ ] **UF-05-b-4** **裁决面板（VerdictPanel）**：加载 `project.verdict_config`，提交按钮初始为锁定状态（`disabled=true`），等待工具确认解锁
- [ ] **UF-05-b-5** 用 `Promise.all` 并行触发四面板；设置 5s 超时保护：超时后已加载面板正常展示，未加载面板显示「加载超时，点击重试」

#### UF-05-c · 步骤切换四联动

- [ ] **UF-05-c-1** 实现 `onStepChange(stepIndex: number)` 统一联动函数：更新 `store.currentStepIndex` → 工具面板高亮当前步骤所需工具 → 3D 面板更新高亮部件 → 裁决面板重置为初始状态
- [ ] **UF-05-c-2** 更新 `window.__robotState`（V1.0 已建立的只读对象）：步骤切换时写入 `{ current_step_id, highlighted_parts, snapshot_at }`，防抖 200ms
- [ ] **UF-05-c-3** 步骤切换后防抖 200ms 通知 Agent（`agentAPI.notifyStepChange(step)`），避免快速翻步骤时频繁触发 LLM 调用
- [ ] **UF-05-c-4** 已通过的步骤在步骤面板显示绿色勾，已失败（超重试次数）的步骤显示红色叉，当前步骤高亮

#### UF-05-d · 工具确认状态机

- [ ] **UF-05-d-1** 工具面板每个工具条目展示：工具名称 / 规格 / 数量 / `is_critical` 标识（关键工具显示红色星标）+ 三个操作按钮（✅ 已确认 / ⚠️ 标记异常 / ○ 暂不处理）
- [ ] **UF-05-d-2** 工具状态流转：`PENDING → CONFIRMED`（已确认）/ `PENDING → ABNORMAL`（标记异常）
- [ ] **UF-05-d-3** 解锁裁决提交按钮的条件：当前步骤所有 `is_critical=true` 的工具状态均为 `CONFIRMED`
- [ ] **UF-05-d-4** 任意工具标记 `ABNORMAL` 时，自动触发 Agent 对话：优先推荐知识库中记录的替代工具，无替代时提示联系主管，同时在工具面板显示橙色警告角标
- [ ] **UF-05-d-5** 工具确认操作实时持久化：每次状态变更调用 `PATCH /api/v1/training/sessions/{session_id}/steps/{step_id}/tools`，写入 `session_step_records.tools_confirmed` JSONB

---

### UF-06 · 训练会话状态机 + 中断续训
> 🔴 先行，UF-04 / UF-05 / UF-07 均依赖此表结构  
> **负责**：后端 · **工时**：4 天 · **依赖**：UF-01

**验收标准**：
- 训练中途关闭浏览器，重新登录后步骤进度和工具确认状态完整恢复
- 四种会话状态（ACTIVE / PAUSED / SUBMITTED / ABANDONED）均可正常流转

---

#### UF-06-a · 数据库建表

- [ ] **UF-06-a-1** 新建 `training_sessions` 表：
  ```
  session_id      UUID PK
  project_id      UUID NOT NULL        -- 关联生成的 TrainingProject（存 JSON 快照）
  user_id         UUID FK → users
  status          VARCHAR(20)          -- ACTIVE / PAUSED / SUBMITTED / ABANDONED / EXPIRED
  current_step    INTEGER DEFAULT 0
  project_snapshot JSONB               -- 完整 TrainingProject JSON，防止后续知识库变更影响进行中训练
  started_at      TIMESTAMP
  paused_at       TIMESTAMP
  submitted_at    TIMESTAMP
  total_duration  INTEGER              -- 实际用时（秒，暂停期间不计）
  score           NUMERIC(5,2)
  submit_type     VARCHAR(20)          -- manual / timeout / teacher / abandoned
  ab_group        VARCHAR(10)          -- A/B 测试分组（llm / baseline）
  ```
- [ ] **UF-06-a-2** 新建 `session_step_records` 表：
  ```
  record_id       UUID PK
  session_id      UUID FK → training_sessions
  step_id         VARCHAR(50)
  step_index      INTEGER
  status          VARCHAR(20)          -- PENDING / IN_PROGRESS / PASS / FAIL / SKIP
  attempt_count   INTEGER DEFAULT 0
  tools_confirmed JSONB                -- [{ tool_id, status, confirmed_at }]
  evidence        JSONB                -- { input_value, photo_url, notes }
  verdict_result  JSONB                -- { rule_result, llm_explanation, ref_ids }
  duration_sec    INTEGER
  started_at      TIMESTAMP
  completed_at    TIMESTAMP
  ```
- [ ] **UF-06-a-3** 运行 Alembic 迁移，在 staging 验证

#### UF-06-b · 会话状态机服务

- [ ] **UF-06-b-1** 新建 `services/training/session_service.py`，实现状态流转方法：
  - `create_session(user_id, project) -> session_id`：创建新会话，存储 project_snapshot
  - `update_step(session_id, step_record)`：写入步骤操作记录（checkpoint）
  - `pause(session_id)`：状态 → PAUSED，记录 paused_at
  - `resume(session_id)`：状态 → ACTIVE，累加已暂停时长到 total_duration
  - `expire_stale()`：定时任务，将超过 48h 未操作的 ACTIVE 会话标记为 EXPIRED
- [ ] **UF-06-b-2** 每步操作完成后自动 checkpoint：写 `session_step_records`（不等待用户主动提交）
- [ ] **UF-06-b-3** 新建接口 `GET /api/v1/training/sessions/{session_id}`：返回会话当前状态和所有步骤记录，供工作台恢复使用

#### UF-06-c · 中断续训

- [ ] **UF-06-c-1** 登录后检测当前用户是否存在 `status=ACTIVE AND started_at > now() - interval '24 hours'` 的历史会话
- [ ] **UF-06-c-2** 有未完成会话时，登录响应体附带 `unfinished_session: { session_id, project_title, current_step, total_steps, started_at }`；前端展示「继续上次训练」提示卡（可关闭）
- [ ] **UF-06-c-3** 用户选择续训：前端调用 `GET /api/v1/training/sessions/{session_id}` 获取 checkpoint 数据，`WorkbenchOrchestrator.resume(session)` 恢复工作台状态（步骤进度 + 工具确认记录 + 已用时间显示）
- [ ] **UF-06-c-4** 用户选择放弃：调用 `PATCH /api/v1/training/sessions/{session_id}/abandon`，状态 → ABANDONED，已完成步骤记录保留（供 UF-11 记忆写入使用）

---

### UF-07 · 教师实时监控基础
> 🟡 Phase 1 基础版，复杂可视化延到 UF-12  
> **负责**：后端 + 前端 · **工时**：3 天 · **依赖**：UF-06

**验收标准**：
- 教师在教学管理台可看到名下学员的实时训练状态（训练中 / 空闲 / 已提交）
- 学员步骤失败超过 3 次时，教师台收到推送通知（延迟 < 5s）

---

#### UF-07-a · 实时状态推送（WebSocket）

- [ ] **UF-07-a-1** 建立 WebSocket 频道：`/ws/class/{class_id}`，教师登录后自动订阅名下所有班级频道
- [ ] **UF-07-a-2** 训练会话状态变更时（步骤完成 / 步骤失败 / 会话提交）发布事件到对应频道
- [ ] **UF-07-a-3** 学员步骤 `attempt_count >= 3` 时，发布 `{ type: "step_warning", user_id, step_id, attempt_count }` 预警事件到教师频道

#### UF-07-b · 教学管理台基础视图

- [ ] **UF-07-b-1** 教师默认工作台 `/workbench/teaching`：展示名下所有学员列表，每行显示：姓名 / 当前状态（训练中 🟡 / 空闲 ⚪ / 已提交 ✅）/ 当前步骤 / 已用时间
- [ ] **UF-07-b-2** 步骤失败预警：学员条目出现橙色预警标识，点击可查看失败详情
- [ ] **UF-07-b-3** 教师介入：点击学员条目旁「发送提示」按钮，输入文字后推送到该学员工作台 Agent 对话框（标注「教师提示」，区分于 Agent 自动回复）

---

## Phase 2 · 教学闭环（第 7-10 周）

> **阶段目标**：训练提交后完成完整闭环：AI 生成多维反馈 → 数据写入个人技能记忆 → 记忆驱动下次推荐。  
> **阶段验收**：四种提交触发方式均可测试；AI 反馈有用性评分 ≥ 4/5（30 名学员）；提交后次日登录可看到更新的技能画像；教师监控台实时数据正确。

---

### UF-08 · 训练提交机制（四种触发）
> 🔴 阻塞，UF-09 反馈生成依赖提交包  
> **负责**：全栈 · **工时**：4 天 · **依赖**：UF-06

**验收标准**：
- 四种提交触发方式（主动 / 超时 / 教师强制 / 放弃）均可独立触发和测试
- 提交包 `TrainingSubmission` 所有必填字段完整，可正确传入反馈生成器

---

#### UF-08-a · SubmissionService

- [ ] **UF-08-a-1** 新建 `services/training/submission_service.py`
- [ ] **UF-08-a-2** `submit_manual(session_id, user_id)`：检查未完成步骤数 → 有则返回提示（「还有 N 步未完成，确认提交？」）→ 用户确认后打包提交包 → 触发反馈生成
- [ ] **UF-08-a-3** `submit_timeout(session_id)`：由定时任务调用，检查 `total_duration > project_snapshot.verdict_config.time_limit`，自动打包，状态标注 `submit_type='timeout'`
- [ ] **UF-08-a-4** `submit_by_teacher(session_id, teacher_id)`：验证 teacher_id 对该学员有管辖权（`class_members` 表）→ 打包提交，写 `submitted_by=teacher_id` → 推送通知给学员
- [ ] **UF-08-a-5** `abandon(session_id)`：状态 → ABANDONED，已完成步骤记录**保留**，写入 `submit_type='abandoned'`，不触发完整反馈（只写简短放弃记录到记忆）

#### UF-08-b · 提交包打包

- [ ] **UF-08-b-1** 从 `session_step_records` 聚合全部步骤记录（含证据、工具确认、裁决结果）
- [ ] **UF-08-b-2** 从 `conversation_turns` 表查询本 session 的全部对话记录（V1.0 已建立）
- [ ] **UF-08-b-3** 从前端上传 3D 模型交互日志（前端在点击提交时一并上传：`{ part_id, action, timestamp }[]`）
- [ ] **UF-08-b-4** 生成完整 `TrainingSubmission` JSON 并持久化到 `training_submissions` 表（新建）：`submission_id / session_id / user_id / submit_type / submitted_at / payload(JSONB)`

#### UF-08-c · 前端提交入口

- [ ] **UF-08-c-1** 工作台底部常驻「提交训练」按钮：有未完成步骤时显示橙色+步骤数提示，全部完成后显示绿色
- [ ] **UF-08-c-2** 点击提交时：若有未完成步骤，弹出确认弹窗「还有 N 步未完成，确认提交当前进度？」，用户确认后上传交互日志并调用提交接口
- [ ] **UF-08-c-3** 超时自动提交：工作台顶部显示剩余时间倒计时，最后 5 分钟变红色，归零时显示「训练已超时，正在自动提交…」并锁定操作

---

### UF-09 · 多维 AI 反馈生成
> 🔴 核心交付  
> **负责**：后端 + 前端 · **工时**：5 天 · **依赖**：UF-08 / UF-10（技能画像）

**验收标准**：
- 反馈报告 7 个维度数据完整生成
- 学生/教师视角报告内容正确分离（教学诊断仅教师可见）
- 30 名学员测评：反馈有用性均分 ≥ 4/5

---

#### UF-09-a · FeedbackGenerator 服务

- [ ] **UF-09-a-1** 新建 `services/training/feedback_generator.py`，入口方法 `generate(submission: TrainingSubmission, role: str) -> TrainingFeedback`
- [ ] **UF-09-a-2** **综合评分**（规则计算，不调用 LLM）：`总分 = 步骤完成率×50 + 用时系数×20 + 工具规范×15 + 尝试次数系数×15`；用时系数：实际用时 ≤ 预计用时得满分，每超 10% 扣 2 分
- [ ] **UF-09-a-3** **步骤逐项分析**（LLM）：对每个 `status=FAIL` 或 `attempt_count > 1` 的步骤，调用 LLMRouter 生成原因解析 + 改进建议，注入该步骤相关知识 chunk
- [ ] **UF-09-a-4** **工具使用评价**（LLM）：分析 `tools_confirmed` 记录，评价关键工具确认规范性和异常工具处理情况
- [ ] **UF-09-a-5** **历史对比**（规则）：查询该用户历史 `training_sessions`，计算本次得分与历史均分的差值和趋势（进步/持平/退步）
- [ ] **UF-09-a-6** **个性化建议 + 下一步计划**（LLM）：基于本次薄弱点和技能画像，推荐改进方向和下次训练类型

#### UF-09-b · 双视角报告差异化

- [ ] **UF-09-b-1** 学员报告包含：综合评分 + 步骤逐项分析 + 工具使用评价 + 历史对比 + 个性化建议 + 下一步计划
- [ ] **UF-09-b-2** 教师报告增加「教学诊断」维度（LLM 生成）：该学员在班级中的相对排名百分位 + 是否建议额外辅导 + 推荐调整的 `hint_level` 值
- [ ] **UF-09-b-3** 报告生成完成后，异步触发 UF-11 记忆写入任务（不阻塞报告展示）

#### UF-09-c · 前端反馈报告页

- [ ] **UF-09-c-1** 学员提交后跳转至 `/training/feedback/{session_id}`，展示得分动画（从 0 到最终分数）+ 各维度评分卡
- [ ] **UF-09-c-2** 步骤逐项分析：可展开/折叠每步详情，失败步骤红色高亮，显示 LLM 解释和 ref_id 引用链接
- [ ] **UF-09-c-3** 历史对比：折线图展示最近 5 次训练得分趋势，本次得分用高亮点标注
- [ ] **UF-09-c-4** 教师视角：在班级管理页新增「查看学员反馈」入口，展示教学诊断模块（学员自己的页面不含此模块）

---

### UF-10 · 个人技能画像数据模型
> 🔴 先行，UF-03 / UF-04 / UF-09 / UF-11 均依赖此数据  
> **负责**：后端 · **工时**：4 天 · **依赖**：UF-01

**验收标准**：
- 训练提交后技能画像五维评分正确更新
- 薄弱步骤累计统计正确（多次失败 fail_count 递增，一次通过则 is_resolved=true）

---

#### UF-10-a · 数据库建表

- [ ] **UF-10-a-1** 新建 `student_skill_profiles` 表：
  ```
  user_id         UUID PK FK → users
  overall_level   INTEGER DEFAULT 1       -- 综合技能等级 1-5
  total_sessions  INTEGER DEFAULT 0
  total_duration  INTEGER DEFAULT 0       -- 累计训练秒数
  last_trained_at TIMESTAMP
  score_safety    NUMERIC(5,2)            -- 安全规范执行（0-100）
  score_procedure NUMERIC(5,2)            -- 步骤规范性
  score_precision NUMERIC(5,2)            -- 操作精度（力矩/间隙等数值）
  score_efficiency NUMERIC(5,2)           -- 时间效率
  score_tools     NUMERIC(5,2)            -- 工具使用规范
  cert_l1_passed  BOOLEAN DEFAULT false
  cert_l2_passed  BOOLEAN DEFAULT false
  cert_l3_eligible BOOLEAN DEFAULT false  -- 满足 L3 报考资格
  updated_at      TIMESTAMP
  ```
- [ ] **UF-10-a-2** 新建 `student_weak_steps` 表：
  ```
  user_id         UUID FK → users
  step_id         VARCHAR(50)
  sop_id          VARCHAR(50)
  fail_count      INTEGER DEFAULT 0
  last_failed_at  TIMESTAMP
  fail_tags       JSONB     -- ["tool_error","value_out_of_range","sequence_wrong"]
  is_resolved     BOOLEAN DEFAULT false   -- 最近一次训练一次通过则标记为 true
  PRIMARY KEY (user_id, step_id)
  ```
- [ ] **UF-10-a-3** 运行 Alembic 迁移；为系统中现有用户批量创建空白技能画像记录（`overall_level=1`，各维度为 NULL）

#### UF-10-b · 评分更新服务

- [ ] **UF-10-b-1** 新建 `services/memory/skill_profile_service.py`
- [ ] **UF-10-b-2** `update_scores(user_id, submission, feedback)`：调用 LLMRouter，输入（本次提交包摘要 + 反馈结果 + 当前画像），输出 `{ score_safety, score_procedure, score_precision, score_efficiency, score_tools }` JSON，更新 `student_skill_profiles`
- [ ] **UF-10-b-3** `overall_level` 升级规则（规则判断，不调用 LLM）：五维平均分 ≥ 80 AND 本等级已完成训练次数 ≥ 5 AND 最近 3 次训练均通过 → `overall_level + 1`
- [ ] **UF-10-b-4** 认证资格自动更新：`cert_l3_eligible = cert_l2_passed AND 完成 L2 及以上训练 ≥ 5 次`

---

### UF-11 · 记忆写入触发器（TrainingMemoryWriter）
> **负责**：后端 · **工时**：3 天 · **依赖**：UF-09 / UF-10

**验收标准**：
- 提交后次日登录，技能画像已更新，薄弱步骤统计正确
- 下次生成训练项目时，本次失败的步骤出现在强化列表中

---

#### UF-11-a · 异步写入管道

- [ ] **UF-11-a-1** 新建 `services/memory/training_memory_writer.py`，作为后台异步任务执行（不阻塞反馈页面展示）
- [ ] **UF-11-a-2** **Step 1 - 薄弱点更新**（优先级最高，先执行）：
  - 遍历 `submission.steps_summary`
  - `status='FAIL'`：`student_weak_steps.fail_count += 1`，更新 `last_failed_at`，合并 `fail_tags`
  - `status='PASS' AND attempt_count=1`：将对应 `step_id` 的 `is_resolved` 设为 `true`
- [ ] **UF-11-a-3** **Step 2 - 技能画像更新**：调用 `SkillProfileService.update_scores()`（UF-10-b）
- [ ] **UF-11-a-4** **Step 3 - 训练历史写入**：更新 `training_sessions.status = 'SUBMITTED'`，写入最终 `score` 和 `total_duration`
- [ ] **UF-11-a-5** **Step 4 - 对话摘要写入情景记忆**：调用 LLMRouter 将本次 `conversation_turns` 压缩为 2-3 句摘要，写入 V1.0 `MemoryHub` 的 pgvector 情景记忆层（key: `training_summary:{user_id}:{session_id}`）
- [ ] **UF-11-a-6** **Step 5 - 下次推荐预计算**：异步触发 `precompute_next_recommendation(user_id)`：基于更新后的薄弱点和技能等级，预先计算下次推荐的训练类型，缓存到 Redis（TTL 24h），供下次登录欢迎摘要直接读取

---

### UF-12 · 技能成长可视化 + 教师监控台（完整版）
> **负责**：前端 · **工时**：6 天 · **依赖**：UF-10 / UF-11

**验收标准**：
- 五维雷达图数据与 `student_skill_profiles` 数据库记录一致
- 薄弱点热图按失败频率正确渲染颜色深度
- 教师实时学员状态更新延迟 < 5s（WebSocket）
- 教师镜像视角以只读模式正确展示学员工作台状态

---

#### UF-12-a · 学员技能成长面板

- [ ] **UF-12-a-1** **五维雷达图**：基于 `student_skill_profiles` 五维评分渲染，每次训练后带动画过渡更新（旧值 → 新值），无数据时展示灰色占位图
- [ ] **UF-12-a-2** **技能等级进度条**：显示当前等级（1-5）+ 本等级已完成训练次数 + 距升级所需次数（如「还需 2 次训练可升到 Lv.3」）
- [ ] **UF-12-a-3** **薄弱点热图**：以步骤为单位展示 `student_weak_steps.fail_count`，颜色深度映射失败频率（0次=白 / 1-2次=浅红 / 3-5次=中红 / 6+次=深红），点击步骤展示失败详情弹窗（失败时间 / 失败原因标签 / 最近是否已解决）
- [ ] **UF-12-a-4** **成长时间线**：折线图展示历次 `training_sessions.score`，X 轴为时间，支持按机器人型号筛选，最近 10 次记录默认展示
- [ ] **UF-12-a-5** **认证进度卡**：展示 L1/L2/L3 认证状态（已获得 ✅ / 资格满足可报考 🟡 / 条件未达 ⚪）及各认证的达成条件进度

#### UF-12-b · 教师监控台（完整版）

- [ ] **UF-12-b-1** **学员实时列表**（升级 UF-07-b 基础版）：增加列：本次训练项目名称 / 当前步骤 / 当前步骤用时 / 该步骤历史失败次数；状态通过 WebSocket 实时刷新
- [ ] **UF-12-b-2** **失败预警推送**：学员 `attempt_count >= 3` 时，监控台右上角弹出预警通知卡（包含学员姓名 / 失败步骤 / 已尝试次数），支持「立即介入」一键发送提示
- [ ] **UF-12-b-3** **镜像视角（只读）**：教师点击学员行的「查看工作台」按钮，以只读模式加载该学员当前工作台快照：步骤面板（步骤状态）+ 工具面板（确认状态）+ 3D 面板（当前高亮部件，通过 `window.__robotState` 读取）+ 裁决面板（最新裁决结果）；明确标注「只读模式，无法操作学员训练」
- [ ] **UF-12-b-4** **班级训练统计**：教师监控台顶部展示今日班级汇总：在训人数 / 已完成人数 / 平均得分 / 失败次数最多的 SOP 步骤（用于发现 SOP 设计问题）

---

## 数据模型新增汇总

> V1.0 已有的表不在此列，仅列本方案新建的表。

| 表名 | 阶段 | 用途 |
|------|------|------|
| `classes` | Phase 1 / UF-01 | 班级管理 |
| `class_members` | Phase 1 / UF-01 | 班级成员关系 |
| `training_sessions` | Phase 1 / UF-06 | 训练会话状态机 |
| `session_step_records` | Phase 1 / UF-06 | 每步操作 checkpoint |
| `student_skill_profiles` | Phase 2 / UF-10 | 学员五维技能画像 |
| `student_weak_steps` | Phase 2 / UF-10 | 学员薄弱步骤累计记录 |
| `training_submissions` | Phase 2 / UF-08 | 提交包持久化存储 |

---

## 新增接口汇总

| 接口 | 所属任务 | 描述 |
|------|---------|------|
| `POST /api/v1/admin/users/{user_id}/role` | UF-01 | 更新用户角色 |
| `GET /api/v1/classes` | UF-01 | 获取班级列表 |
| `POST /api/v1/classes` | UF-01 | 创建班级 |
| `POST /api/v1/classes/{class_id}/members` | UF-01 | 批量添加班级成员 |
| `POST /api/v1/training/projects/generate` | UF-04 | 生成训练项目（SSE 流式） |
| `GET /api/v1/training/sessions/{session_id}` | UF-06 | 获取会话状态与步骤记录 |
| `PATCH /api/v1/training/sessions/{session_id}/steps/{step_id}/tools` | UF-05 | 更新工具确认状态 |
| `PATCH /api/v1/training/sessions/{session_id}/abandon` | UF-06 | 放弃训练 |
| `POST /api/v1/training/sessions/{session_id}/submit` | UF-08 | 提交训练 |
| `GET /api/v1/training/feedback/{session_id}` | UF-09 | 获取 AI 反馈报告 |
| `GET /api/v1/students/{user_id}/profile` | UF-10 | 获取技能画像 |
| `GET /api/v1/students/{user_id}/weak-steps` | UF-10 | 获取薄弱步骤列表 |
| `WS /ws/class/{class_id}` | UF-07 | 教师实时监控 WebSocket |

---

## Phase 1 验收检查单

> Phase 1 结束时逐项检查，全部通过方可进入 Phase 2。

- [ ] 三种角色登录后自动路由到各自默认工作台，路由守卫生效
- [ ] 学生登录后看到包含上次训练信息的个性化欢迎摘要
- [ ] 教师登录后看到班级近 7 天训练统计概况
- [ ] 5 种训练意图类型识别准确率 ≥ 90%（20 条标注样本）
- [ ] 说出训练需求后 10s 内生成 TrainingProject，包含 steps / tools / verdict_config
- [ ] 生成的项目中包含该学员历史薄弱步骤（有记录时）
- [ ] 工作台四面板在 3s 内完成初始化
- [ ] 步骤切换后 3D 高亮和工具面板更新延迟 < 200ms
- [ ] 关键工具未全部确认时，裁决提交按钮保持锁定
- [ ] 关闭浏览器重新登录，步骤进度和工具确认状态正确恢复
- [ ] 教师监控台显示学员实时训练状态，步骤失败预警 < 5s 送达

## Phase 2 验收检查单（MVP）

- [ ] 四种提交触发方式（主动 / 超时 / 教师强制 / 放弃）均可独立测试
- [ ] AI 反馈报告 7 个维度数据完整，学生/教师视角内容正确分离
- [ ] 30 名学员测评：AI 反馈有用性均分 ≥ 4/5
- [ ] 训练提交后，技能画像五维评分和薄弱步骤记录正确更新
- [ ] 提交后次日登录，欢迎摘要包含本次训练结果和更新的推荐
- [ ] 下次生成训练项目时，本次新增的薄弱步骤出现在强化列表中
- [ ] 五维雷达图、薄弱点热图、成长时间线数据与数据库一致
- [ ] 教师镜像视角以只读模式正确展示学员工作台实时状态

---

*本文档仅覆盖补充方案 V0.2 范围，V1.0 已完成开发，直接复用其 LLMRouter / KnowledgeHub / MemoryHub / PromptTemplateEngine 等服务能力。*
