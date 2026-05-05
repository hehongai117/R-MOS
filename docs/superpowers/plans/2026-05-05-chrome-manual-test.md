# R-MOS 产品化 Chrome 手动测试计划

> **For agentic workers:** 使用 chrome-devtools MCP 工具逐步执行本测试计划。每个 Task 是一个独立测试场景，每个 Step 是一个原子操作 + 验证断言。截图记录关键状态。

**Goal:** 使用 Chrome 浏览器端到端验证 14 个产品化 Task 的全部功能，覆盖三种角色（student/teacher/admin）的完整用户旅程。

**前置条件:**
- 后端运行在 `http://localhost:8000`（启动命令: `cd r-mos-backend && source venv/bin/activate && python main.py`）
- 前端运行在 `http://localhost:5173`（启动命令: `cd r-mos-frontend && npm run dev`）
- 数据库已初始化并运行种子数据（`cd r-mos-backend && python scripts/seed_acceptance_users.py && python scripts/seed_demo_data.py && python scripts/seed_fault_sops.py`）

**测试账号:**

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 学生 A | student_a@rmos.test | Student@123 |
| 学生 B | student_b@rmos.test | Student@123 |
| 教师 | teacher1@rmos.test | Teacher@123 |
| 管理员 | admin@rmos.test | Admin@123 |

---

## Task 1: 后端 API 端点冒烟验证

**覆盖产品化 Task:** 1 (生产配置), 2 (学生任务 API), 3 (场景 API), 4 (AI 助手 API)

**目的:** 在浏览器介入前，先通过直接 HTTP 请求确认所有新后端端点可用。

- [ ] **Step 1: 验证 /health 端点**

在 Chrome 中打开 `http://localhost:8000/api/v1/health`

验证:
- 页面返回 JSON
- 包含 `"status": "ok"` 或类似健康检查字段
- HTTP 状态码 200

- [ ] **Step 2: 验证 /student/tasks 端点**

在 Chrome 中打开 `http://localhost:8000/api/v1/student/tasks?student_id=1`

验证:
- 返回 JSON，包含 `items`, `total`, `pending_count`, `in_progress_count`, `completed_count` 字段
- `items` 是数组（可能为空）
- `total` 是整数
- HTTP 状态码 200

- [ ] **Step 3: 验证 /student/tasks 参数校验**

在 Chrome 中打开 `http://localhost:8000/api/v1/student/tasks`（不带 student_id）

验证:
- HTTP 状态码 422
- 返回包含 `ValidationError` 或 `VALIDATION_ERROR` 的 JSON
- 错误信息指出 `student_id` 缺失

- [ ] **Step 4: 验证 /scenarios 端点**

在 Chrome 中打开 `http://localhost:8000/api/v1/scenarios`

验证:
- 返回 JSON，包含 `items` 和 `total` 字段
- `items` 是数组，每项包含 `id`, `fault_type`, `sop_id`, `difficulty`, `priority`
- 如果种子数据已加载，应返回至少 1 条场景

- [ ] **Step 5: 验证 /scenarios 难度筛选**

在 Chrome 中打开 `http://localhost:8000/api/v1/scenarios?difficulty=beginner`

验证:
- 返回的 `items` 中所有项的 `difficulty` 字段均为 `"beginner"`
- 如果无匹配数据，`items` 为空数组，`total` 为 0

- [ ] **Step 6: 验证 /ai-assistant/chat 端点**

使用 Chrome DevTools Console 发送 POST 请求:

```javascript
fetch('http://localhost:8000/api/v1/ai-assistant/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '什么是轴承？' })
}).then(r => r.json()).then(console.log)
```

验证:
- 返回包含 `reply` 和 `hint_level_used` 字段
- `reply` 是非空字符串（可能是 LLM 回复或降级回复: "抱歉，AI 助手暂时不可用..."）
- `hint_level_used` 为 3（默认值）

- [ ] **Step 7: 验证 /ai-assistant/chat hint_level 参数**

```javascript
fetch('http://localhost:8000/api/v1/ai-assistant/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: '这个步骤怎么做？',
    sop_title: '左膝关节轴承更换',
    current_step_index: 2,
    current_step_description: '确认 M3 内六角扳手、轴承拔取器、润滑脂就位',
    hint_level: 1
  })
}).then(r => r.json()).then(console.log)
```

验证:
- `hint_level_used` 为 1
- `reply` 是非空字符串

- [ ] **Step 8: 验证 /ai-assistant/chat 请求校验**

```javascript
fetch('http://localhost:8000/api/v1/ai-assistant/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '' })
}).then(r => { console.log('status:', r.status); return r.json() }).then(console.log)
```

验证:
- HTTP 状态码 422（message 不能为空）

- [ ] **Step 9: 验证 OpenAPI 文档可访问**

在 Chrome 中打开 `http://localhost:8000/docs`

验证:
- Swagger UI 正常加载
- 能看到 `/student/tasks`、`/scenarios`、`/ai-assistant/chat` 三个新端点
- 端点分组标签包含 `student`、`scenarios`、`ai-assistant`

- [ ] **Step 10: 截图记录**

截取 Swagger UI 页面截图，确认新端点可见。

---

## Task 2: 学生注册与登录流程

**覆盖产品化 Task:** 13 (路由整合与默认首页)

**目的:** 验证新用户注册、登录、默认跳转到 /dashboard 的完整流程。

- [ ] **Step 1: 打开登录页**

在 Chrome 中打开 `http://localhost:5173`

验证:
- 未登录状态下自动跳转到 `/login`
- 显示 R-MOS 登录界面
- 有邮箱和密码输入框
- 有"登录"按钮
- 有"注册"链接

- [ ] **Step 2: 测试错误登录**

输入:
- 邮箱: `wrong@test.com`
- 密码: `WrongPass123`

点击登录。

验证:
- 显示错误提示（"邮箱或密码错误" 或 toast 提示）
- 停留在登录页面
- 未跳转

- [ ] **Step 3: 学生账号登录**

输入:
- 邮箱: `student_a@rmos.test`
- 密码: `Student@123`

点击登录。

验证:
- 登录成功
- 页面跳转（可能到 `/workbench/training` 或 `/dashboard`，取决于后端 default_route 配置）
- 左侧侧边栏出现

- [ ] **Step 4: 验证 localStorage 存储**

在 Chrome DevTools Console 执行:

```javascript
console.log('token:', localStorage.getItem('rmos_access_token')?.substring(0, 20));
console.log('role:', localStorage.getItem('rmos_role'));
console.log('route:', localStorage.getItem('rmos_default_route'));
```

验证:
- `rmos_access_token` 非空
- `rmos_role` 为 `"student"`
- `rmos_default_route` 有值

- [ ] **Step 5: 手动导航到 /dashboard**

在地址栏输入 `http://localhost:5173/dashboard` 并回车。

验证:
- 页面显示"学习进度"标题
- 说明学生可以访问 dashboard 路由

- [ ] **Step 6: 截图记录**

截取登录成功后的页面和 dashboard 页面。

---

## Task 3: 学生导航结构验证

**覆盖产品化 Task:** 5 (前端导航分层调整)

**目的:** 验证学生侧边栏导航的分层结构（练习中心 / 维保操作 / 学习成长 / 进阶工具）。

- [ ] **Step 1: 确认学生已登录**

确认当前以 student_a 身份登录。如未登录，先登录。

- [ ] **Step 2: 验证"练习中心"分组**

查看左侧侧边栏。

验证:
- 看到"练习中心"分组标题
- 包含 3 个菜单项: "学习进度"、"我的任务"、"自主练习"
- 各项有对应图标

- [ ] **Step 3: 验证"维保操作"分组**

验证:
- 看到"维保操作"分组标题
- 包含 2 个菜单项: "实时监控"、"维保练习"

- [ ] **Step 4: 验证"学习成长"分组**

验证:
- 看到"学习成长"分组标题
- 包含 3 个菜单项: "维保报告"、"我的技能"、"3D 展示"

- [ ] **Step 5: 验证"进阶工具"分组**

验证:
- 看到"进阶工具"分组标题
- 包含 1 个菜单项: "AI 诊断工作台"

- [ ] **Step 6: 验证旧的分组已移除**

验证:
- 不存在"维保流程"分组
- 不存在"工具"分组
- 总共只有 4 个分组

- [ ] **Step 7: 逐项点击导航验证路由**

依次点击每个导航项:

| 菜单项 | 预期 URL | 预期页面 |
|--------|----------|----------|
| 学习进度 | /dashboard | 显示"学习进度"标题 + 4 张统计卡片 |
| 我的任务 | /my-tasks | 显示"我的任务"标题 + Tab 筛选 |
| 自主练习 | /scenarios | 显示"自主练习"标题 + 难度 Tab |
| 实时监控 | /monitor | 监控页面加载 |
| 维保练习 | /maintenance | SOP 维保页面加载 |
| 维保报告 | /reports | 报告页面加载 |
| 我的技能 | /student/skills | 技能页面加载 |
| 3D 展示 | /atom01 | 3D 展示页面加载 |
| AI 诊断工作台 | /agent/workbench | 工作台页面加载 |

每项验证:
- 点击后 URL 正确变化
- 对应页面加载无白屏/报错
- 导航项高亮状态正确（当前页面的项有蓝色高亮）

- [ ] **Step 8: 截图记录**

截取完整侧边栏展示，显示 4 个分组结构。

---

## Task 4: 学习进度仪表盘页面 (DashboardPage)

**覆盖产品化 Task:** 6 (学习进度仪表盘)

**目的:** 验证 DashboardPage 的数据展示、统计卡片、空状态处理。

- [ ] **Step 1: 导航到 Dashboard**

点击侧边栏"学习进度"。

验证:
- URL 为 `/dashboard`
- 页面标题为"学习进度"
- 标题前有图标

- [ ] **Step 2: 验证 4 张统计卡片结构**

验证页面显示 4 张卡片:

| 卡片 | 标题 | 图标颜色 | 预期值 |
|------|------|----------|--------|
| 卡片 1 | 总任务数 | 灰色靶心 | 数字（0 或更多） |
| 卡片 2 | 进行中 | 黄色时钟 | 黄色数字 |
| 卡片 3 | 已完成 | 绿色对勾 | 绿色数字 |
| 卡片 4 | 完成率 | 蓝色图表 | 百分比 + 进度条 |

- [ ] **Step 3: 验证 API 调用**

打开 Chrome DevTools > Network 面板。刷新页面。

验证:
- 看到 `GET /api/v1/student/tasks?student_id=...&limit=1` 请求
- 请求状态 200
- 响应 JSON 包含 `total`, `in_progress_count`, `completed_count`

- [ ] **Step 4: 验证数据一致性**

将 API 响应中的 `total`, `in_progress_count`, `completed_count` 与页面卡片上的数字对比。

验证:
- 总任务数 = API 返回的 `total`
- 进行中 = API 返回的 `in_progress_count`
- 已完成 = API 返回的 `completed_count`
- 完成率 = `completed_count / total * 100`（四舍五入取整），若 total=0 则显示 0%

- [ ] **Step 5: 验证完成率进度条**

验证:
- 进度条在"完成率"卡片数字下方
- 进度条宽度与百分比一致（0% 时为空条，100% 时为满条）

- [ ] **Step 6: 验证技能雷达区域**

验证:
- 4 张统计卡片下方有"技能雷达"卡片
- 显示占位文字: "完成更多练习任务后，技能雷达图将在此显示你的五维能力分布。"

- [ ] **Step 7: 截图记录**

截取 DashboardPage 完整页面。

---

## Task 5: 我的任务页面 (MyTasksPage)

**覆盖产品化 Task:** 7 (MyTasksPage 补全)

**目的:** 验证任务列表、Tab 筛选、空状态、加载动画。

- [ ] **Step 1: 导航到我的任务**

点击侧边栏"我的任务"。

验证:
- URL 为 `/my-tasks`
- 页面标题为"我的任务"
- 标题前有剪贴板图标

- [ ] **Step 2: 验证 Tab 筛选器**

验证:
- 标题下方显示 Tab 组: "全部"、"进行中"、"已完成"
- 默认选中"全部"

- [ ] **Step 3: 验证 API 调用**

打开 Network 面板，观察请求。

验证:
- 发出 `GET /api/v1/student/tasks?student_id=...&limit=50` 请求
- 状态 200

- [ ] **Step 4: 验证空状态（无任务时）**

如果该学生没有任务记录:

验证:
- 显示"暂无任务记录，开始一次练习吧！"文字
- 下方有"去练习"按钮（带播放图标）

- [ ] **Step 5: 测试"去练习"按钮导航**

点击"去练习"按钮。

验证:
- 跳转到 `/scenarios`（自主练习页面）

- [ ] **Step 6: 返回我的任务测试 Tab 切换**

返回 `/my-tasks`，依次点击各 Tab:

| Tab | 预期行为 |
|-----|----------|
| 全部 | API 不带 status 参数，显示所有任务 |
| 进行中 | API 带 `status=in_progress`，仅显示进行中任务 |
| 已完成 | API 带 `status=completed`，仅显示已完成任务 |

在 Network 面板验证每次 Tab 切换是否发出了正确的 API 请求。

- [ ] **Step 7: 验证加载骨架屏**

刷新页面时快速观察（或在 Network 面板中 throttle 到 Slow 3G）。

验证:
- 数据加载期间显示 3 个动画骨架卡片（pulse 动画）
- 数据加载完成后骨架卡片消失，显示真实数据或空状态

- [ ] **Step 8: 验证任务卡片内容（如有任务数据）**

如果有任务数据，验证每张任务卡片:
- 显示任务名称（粗体）
- 显示状态 Badge（进行中=蓝色默认，已完成=绿色成功，已放弃=红色）
- 显示 SOP 名称（如有）
- 显示故障类型（如有）
- 显示开始日期
- 右侧有对应颜色的状态图标

- [ ] **Step 9: 截图记录**

截取 MyTasksPage 空状态和有数据状态（如有）。

---

## Task 6: 自主练习页面 (ScenarioPickerPage)

**覆盖产品化 Task:** 8 (ScenarioPickerPage 补全)

**目的:** 验证场景列表、难度筛选、场景卡片、开始练习导航。

- [ ] **Step 1: 导航到自主练习**

点击侧边栏"自主练习"。

验证:
- URL 为 `/scenarios`
- 页面标题为"自主练习"
- 标题前有哑铃图标

- [ ] **Step 2: 验证引导提示卡片**

验证:
- 标题下方有蓝色背景的提示卡片
- 内容: "选择一个故障场景开始练习，AI 助手会在练习过程中为你提供帮助。"
- 左侧有 Sparkles 图标

- [ ] **Step 3: 验证难度 Tab 筛选器**

验证:
- 显示 4 个 Tab: "全部"、"入门"、"进阶"、"高级"
- 默认选中"全部"

- [ ] **Step 4: 验证 API 调用**

打开 Network 面板，观察请求。

验证:
- 默认 Tab "全部": 发出 `GET /api/v1/scenarios` 请求（无 difficulty 参数）
- 状态 200

- [ ] **Step 5: 测试难度筛选**

依次点击各 Tab:

| Tab | 预期 API 请求 |
|-----|--------------|
| 入门 | `GET /api/v1/scenarios?difficulty=beginner` |
| 进阶 | `GET /api/v1/scenarios?difficulty=intermediate` |
| 高级 | `GET /api/v1/scenarios?difficulty=advanced` |
| 全部 | `GET /api/v1/scenarios`（无 difficulty） |

在 Network 面板验证每次切换的请求参数正确。

- [ ] **Step 6: 验证空状态**

如果某个难度下无场景:

验证:
- 显示"暂无可用的练习场景。教师配置故障场景后将显示在此处。"

- [ ] **Step 7: 验证场景卡片内容（如有数据）**

如果有场景数据，验证场景卡片:
- 网格布局（3 列 @ 大屏, 2 列 @ 中屏, 1 列 @ 小屏）
- 每张卡片包含:
  - 场景标题（SOP 标题或故障类型）
  - 难度 Badge（入门=默认蓝, 进阶=绿色, 高级=红色）
  - 故障类型文字
  - "开始练习"按钮（带播放图标，占满卡片宽度）
- 鼠标悬停时卡片边框变色、有阴影

- [ ] **Step 8: 测试"开始练习"导航**

点击某个场景的"开始练习"按钮。

验证:
- 跳转到 `/maintenance?sop_id=<该场景的sop_id>`
- 维保练习页面加载

- [ ] **Step 9: 验证加载骨架屏**

Network 面板设置 Slow 3G，刷新页面。

验证:
- 加载时显示 3 个骨架卡片（网格布局 + pulse 动画）
- 加载完成后替换为真实卡片

- [ ] **Step 10: 截图记录**

截取 ScenarioPickerPage 含场景卡片的页面和空状态页面。

---

## Task 7: AI 助手浮窗组件

**覆盖产品化 Task:** 9 (AI 助手前端浮窗), 10 (集成到 SOPPlayer)

**目的:** 验证 AI 助手 FAB 按钮、浮窗打开/关闭、消息发送/接收、SOPPlayer 集成。

- [ ] **Step 1: 导航到维保练习页面**

点击侧边栏"维保练习"或从场景选择进入。

验证:
- URL 为 `/maintenance` 或 `/maintenance?sop_id=...`
- 维保练习页面加载

- [ ] **Step 2: 验证 AI 助手 FAB 按钮**

验证:
- 页面右下角（fixed position）显示一个圆形蓝色按钮
- 按钮上有 Bot 机器人图标
- 按钮大小约 48x48px

- [ ] **Step 3: 点击 FAB 打开浮窗**

点击右下角的 AI 助手按钮。

验证:
- FAB 按钮消失
- 出现一个 360x480px 的浮窗面板
- 浮窗位于右下角（fixed position）
- 浮窗有标题栏: "AI 助手" + Bot 图标
- 标题栏右侧有最小化和关闭按钮
- 中间消息区域显示: "有问题随时问我，我会根据当前步骤为你提供帮助。"
- 底部有输入框 + 发送按钮

- [ ] **Step 4: 测试发送消息**

在输入框中输入"什么是轴承？"，点击发送按钮（或按 Enter）。

验证:
- 输入框清空
- 消息区域出现用户消息气泡（蓝色背景，右对齐）
- 消息内容为"什么是轴承？"
- 用户气泡左侧有 User 头像圆圈
- 出现"思考中..."加载提示（Bot 图标 pulse 动画）

- [ ] **Step 5: 验证 AI 回复**

等待 AI 回复（或降级回复）。

验证:
- "思考中..."消失
- 出现 AI 回复气泡（灰色背景，左对齐）
- AI 气泡左侧有 Bot 头像圆圈
- 回复内容为非空文字（可能是 LLM 回复或降级回复 "抱歉，AI 助手暂时不可用..."）

- [ ] **Step 6: 验证 API 调用**

在 Network 面板检查:

验证:
- 发出 `POST /api/v1/ai-assistant/chat` 请求
- 请求 body 包含 `message: "什么是轴承？"`
- 请求 body 包含 `history` 数组
- 响应状态 200
- 响应包含 `reply` 和 `hint_level_used`

- [ ] **Step 7: 测试多轮对话**

继续发送第二条消息: "怎么更换它？"

验证:
- 消息区域依次显示: 用户问题1 → AI 回复1 → 用户问题2 → AI 回复2
- API 请求的 `history` 字段包含之前的对话记录
- 消息区域自动滚动到底部

- [ ] **Step 8: 测试空消息防护**

不输入任何内容，直接点击发送按钮。

验证:
- 不发送任何请求
- 消息区域无新消息

- [ ] **Step 9: 测试最小化/关闭**

点击浮窗标题栏的最小化按钮（Minimize2 图标）。

验证:
- 浮窗消失
- FAB 圆形按钮重新出现

再次点击 FAB 按钮打开浮窗:
- 之前的对话记录仍然保留（状态持久化在 Zustand store 中）

点击关闭按钮（X 图标）:
- 浮窗关闭
- FAB 按钮重新出现

- [ ] **Step 10: 验证 Enter 快捷键发送**

打开浮窗，输入"测试快捷键"，按 Enter 键。

验证:
- 消息发送成功
- 不会在输入框中换行

- [ ] **Step 11: 截图记录**

截取 AI 助手浮窗打开状态（含对话消息）和关闭状态（FAB 按钮）。

---

## Task 8: 教师角色导航与页面访问

**覆盖产品化 Task:** 5 (导航分层 — 教师不变)

**目的:** 验证教师角色的导航结构未被产品化改动破坏，教师专属页面可正常访问。

- [ ] **Step 1: 退出学生账号**

点击侧边栏底部的用户头像区域，在下拉菜单中点击"退出登录"。

验证:
- 跳转到登录页面
- localStorage 中 token 被清除

- [ ] **Step 2: 教师登录**

输入:
- 邮箱: `teacher1@rmos.test`
- 密码: `Teacher@123`

点击登录。

验证:
- 登录成功
- 侧边栏出现，角色 Badge 显示"教师"

- [ ] **Step 3: 验证教师导航结构**

验证侧边栏包含 3 个分组:

| 分组 | 菜单项 |
|------|--------|
| 教学管理 | 班级监控台、作业管理、学员档案 |
| SOP & 工具 | SOP 管理、3D 展示、实时监控 |
| 记录 | 维保报告、知识库 |

验证:
- 没有"练习中心"、"自主练习"等学生专属菜单
- 没有"进阶工具"分组

- [ ] **Step 4: 验证教师专属页面可访问**

逐一点击教师导航项:

| 菜单项 | 预期 URL |
|--------|----------|
| 班级监控台 | /workbench/teaching |
| 作业管理 | /teaching/assignments |
| 学员档案 | /teacher/students |
| SOP 管理 | /sops |
| 知识库 | /knowledge |

每项验证:
- 页面加载无白屏/报错
- URL 正确

- [ ] **Step 5: 验证教师无法访问学生页面**

在地址栏输入 `http://localhost:5173/dashboard`

验证:
- 被权限拦截或重定向（因为 DashboardPage 只允许 student 角色）

在地址栏输入 `http://localhost:5173/my-tasks`

验证:
- 被权限拦截或重定向

- [ ] **Step 6: 截图记录**

截取教师侧边栏完整导航。

---

## Task 9: 管理员角色导航与页面访问

**覆盖产品化 Task:** 5 (导航分层 — 管理员不变)

**目的:** 验证管理员角色的导航结构及系统概览页面。

- [ ] **Step 1: 切换到管理员账号**

退出教师账号，使用管理员账号登录:
- 邮箱: `admin@rmos.test`
- 密码: `Admin@123`

验证:
- 登录成功
- 角色 Badge 显示"管理员"

- [ ] **Step 2: 验证管理员导航结构**

验证侧边栏包含 4 个分组:

| 分组 | 菜单项 |
|------|--------|
| 概览 | 系统概览 |
| 教学管理 | 班级监控台、作业管理、学员档案 |
| SOP & 工具 | SOP 管理、3D 展示、实时监控 |
| 记录 | 维保报告、知识库 |

- [ ] **Step 3: 验证系统概览页面**

点击"系统概览"。

验证:
- URL 为 `/admin/console`
- 管理控制台页面加载

- [ ] **Step 4: 验证管理员可访问教师页面**

点击"班级监控台"、"作业管理" 等。

验证:
- 管理员能正常访问教师可见的页面（因为权限设置为 ['teacher', 'admin']）

- [ ] **Step 5: 截图记录**

截取管理员侧边栏导航。

---

## Task 10: 用户菜单与退出登录

**目的:** 验证所有角色的用户菜单功能。

- [ ] **Step 1: 验证用户信息区域**

查看侧边栏底部用户区域。

验证:
- 显示用户头像（首字母 Fallback）
- 显示用户名称
- 显示角色 Badge

- [ ] **Step 2: 打开用户下拉菜单**

点击用户信息区域。

验证:
- 弹出下拉菜单
- 显示用户名和邮箱
- 有"个人设置"选项（带设置图标）
- 有"退出登录"选项（带 LogOut 图标）

- [ ] **Step 3: 测试个人设置导航**

点击"个人设置"。

验证:
- 跳转到 `/settings`
- 设置页面加载

- [ ] **Step 4: 测试退出登录**

重新打开下拉菜单，点击"退出登录"。

验证:
- 跳转到 `/login`
- localStorage 中 `rmos_access_token`、`rmos_role` 等被清除
- 尝试访问 `/dashboard` 被重定向回 `/login`

- [ ] **Step 5: 截图记录**

截取用户下拉菜单展开状态。

---

## Task 11: 响应式布局验证

**目的:** 验证关键页面在不同视口下的布局表现。

- [ ] **Step 1: 学生登录并导航到 Dashboard**

使用 student_a 登录，进入 `/dashboard`。

- [ ] **Step 2: 桌面宽屏 (1920x1080)**

设置浏览器视口为 1920x1080。

验证:
- Dashboard 4 张统计卡片在一行显示（4 列网格）
- 侧边栏 220px 宽度正常显示

- [ ] **Step 3: 笔记本屏 (1366x768)**

设置浏览器视口为 1366x768。

验证:
- Dashboard 4 张统计卡片在一行显示（4 列 @ lg）
- 导航和内容正常

- [ ] **Step 4: 平板宽屏 (1024x768)**

设置浏览器视口为 1024x768。

验证:
- Dashboard 统计卡片变为 2 列
- 自主练习场景卡片变为 2 列

- [ ] **Step 5: 自主练习页面响应式**

导航到 `/scenarios`。

验证各分辨率:
- 1920px: 场景卡片 3 列
- 1024px: 场景卡片 2 列
- 768px 以下: 场景卡片 1 列

- [ ] **Step 6: 截图记录**

截取 1920px 和 1024px 下的 Dashboard 和 ScenarioPicker 页面。

---

## Task 12: Network 错误处理验证

**目的:** 验证 API 不可用时各页面的容错表现。

- [ ] **Step 1: 停止后端服务**

在终端中停止后端进程（Ctrl+C）。

- [ ] **Step 2: 测试 Dashboard 容错**

导航到 `/dashboard`，刷新页面。

验证:
- 页面不白屏
- 统计数字显示 0 或 "—"（API 失败后 catch 处理）
- 无 JS 报错（检查 Console 面板）

- [ ] **Step 3: 测试 MyTasksPage 容错**

导航到 `/my-tasks`。

验证:
- 页面显示空状态: "暂无任务记录，开始一次练习吧！"
- 无白屏或 JS 崩溃

- [ ] **Step 4: 测试 ScenarioPickerPage 容错**

导航到 `/scenarios`。

验证:
- 页面显示: "暂无可用的练习场景..."
- 无白屏

- [ ] **Step 5: 测试 AI 助手容错**

导航到 `/maintenance`，打开 AI 助手浮窗，发送消息。

验证:
- 发送消息后显示错误回复: "抱歉，请求失败。请稍后重试。"
- 浮窗不崩溃

- [ ] **Step 6: 重启后端**

重新启动后端服务。

- [ ] **Step 7: 验证页面恢复**

刷新页面，验证各功能恢复正常。

- [ ] **Step 8: 截图记录**

截取后端离线时各页面的容错表现。

---

## Task 13: 跨角色权限隔离验证

**目的:** 确保不同角色不能越权访问他人页面。

- [ ] **Step 1: 学生尝试访问教师页面**

以 student_a 登录后，在地址栏手动输入以下 URL:

| URL | 预期行为 |
|-----|----------|
| /workbench/teaching | 被拦截/重定向 |
| /teaching/assignments | 被拦截/重定向 |
| /teacher/students | 被拦截/重定向 |
| /sops | 被拦截/重定向 |
| /knowledge | 被拦截/重定向 |
| /admin/console | 被拦截/重定向 |

验证:
- 学生无法访问教师/管理员专属页面
- 显示权限不足提示或被重定向

- [ ] **Step 2: 教师尝试访问管理员页面**

以 teacher1 登录后:

| URL | 预期行为 |
|-----|----------|
| /admin/console | 被拦截/重定向 |
| /dashboard | 被拦截/重定向（学生专属） |
| /my-tasks | 被拦截/重定向（学生专属） |
| /scenarios | 被拦截/重定向（学生专属） |

- [ ] **Step 3: 教师可访问共享页面**

| URL | 预期行为 |
|-----|----------|
| /monitor | 正常加载（所有角色可访问） |
| /atom01 | 正常加载 |
| /maintenance | 正常加载 |

- [ ] **Step 4: 截图记录**

截取权限拦截页面。

---

## Task 14: 完整学生学习旅程 E2E

**目的:** 模拟一个学生的完整使用流程，串联验证所有新功能。

- [ ] **Step 1: 登录**

以 student_a@rmos.test / Student@123 登录。

- [ ] **Step 2: 查看学习进度**

进入 Dashboard，确认统计数据加载。

- [ ] **Step 3: 查看任务列表**

导航到"我的任务"，查看任务记录（可能为空）。

- [ ] **Step 4: 浏览练习场景**

点击"去练习"（或导航到"自主练习"），浏览可用场景。

- [ ] **Step 5: 按难度筛选**

分别点击"入门"、"进阶"、"高级"Tab，验证筛选效果。

- [ ] **Step 6: 开始练习**

选择一个场景，点击"开始练习"，进入维保练习页面。

- [ ] **Step 7: 使用 AI 助手**

在维保练习页面:
1. 点击右下角 AI 助手 FAB 按钮
2. 发送问题: "这个步骤需要什么工具？"
3. 等待 AI 回复
4. 发送追问: "具体怎么操作？"
5. 最小化 AI 助手

- [ ] **Step 8: 查看其他页面**

依次访问:
- 实时监控 (/monitor)
- 维保报告 (/reports)
- 我的技能 (/student/skills)
- 3D 展示 (/atom01)
- AI 诊断工作台 (/agent/workbench)

每个页面验证:
- 页面加载无白屏
- 导航项正确高亮

- [ ] **Step 9: 退出登录**

点击退出登录，验证回到登录页。

- [ ] **Step 10: 最终截图**

截取关键步骤截图作为验收记录。

---

## Summary

| Task | 测试内容 | 覆盖产品化 Task |
|------|----------|----------------|
| 1 | 后端 API 端点冒烟 | 1, 2, 3, 4 |
| 2 | 注册登录与默认跳转 | 13 |
| 3 | 学生导航结构 | 5 |
| 4 | 学习进度仪表盘 | 6 |
| 5 | 我的任务页面 | 7 |
| 6 | 自主练习页面 | 8 |
| 7 | AI 助手浮窗 | 9, 10 |
| 8 | 教师角色导航 | 5 |
| 9 | 管理员角色导航 | 5 |
| 10 | 用户菜单退出 | — |
| 11 | 响应式布局 | 6, 8 |
| 12 | Network 错误容错 | 6, 7, 8, 9 |
| 13 | 跨角色权限隔离 | 5, 6, 7, 8 |
| 14 | 完整学生旅程 E2E | 全部 |

**总计:** 14 个测试 Task，约 100+ 个验证步骤，覆盖全部 14 个产品化 Task。
