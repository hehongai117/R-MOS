# R-MOS 前端改造实施方案

> **执行模型** GPT-5.3-codex  
> **改造策略** 架构补齐 + 视觉统一 + 信息架构重组，不推倒业务逻辑  
> **总工期** 6 周 · 三期交付  
> **技术方向** Ant Design（数据组件保留）+ shadcn/ui + Tailwind CSS  
> **修订版本** 2026-03-06（接口/鉴权对齐 + ADR补齐 + 已完成项去重）

---

## 模型选择说明

> ✅ 已验证：本节为执行模型说明，与当前代码库无冲突，保留原文。

**代码实现全程使用 Codex（GPT-5.3）；Minimax 仅用于文案校对，不参与代码提交。**

| 能力维度 | Minimax 2.5 | GPT-5.3-codex |
|---------|------------|---------------|
| 组件代码生成 | 风格不稳定 | 强，Tailwind+shadcn 训练数据充足 |
| 跨文件上下文理解 | 弱，容易丢失依赖关系 | 强，能理解整个组件树 |
| 「只改视觉不动逻辑」类约束 | 经常越界修改 | 指令理解准确 |
| TypeScript 类型 | 频繁生成 `any` | 类型推断严格 |
| 设计还原 | 一般 | 给参考风格能准确还原 |

**Minimax 在本次改造中只做一件事**：给 Codex 生成的组件补充中文注释和文案校对，不写代码。

---

## 0) 本轮对齐修订（2026-03-06）

> 本节用于修正“接口/鉴权假设偏差”和“已完成项重复施工”问题。

### 已完成项（本方案去重，不再重复实施）

> ✅ 已验证：以下项目已在当前仓库存在或已闭环，保留原文。

- [x] 前端 CI 已存在：`.github/workflows/frontend-ci.yml`
- [x] Node 版本基线已存在：仓库根 `.nvmrc=22`
- [x] T-06 前端核心组件补测已闭环（当前实测：`npm test` = `20 passed`，`npm run build` = PASS）

### 接口与鉴权对齐原则

1. 鉴权以 `/api/v1/auth/login` 返回体为准：`access_token`/`refresh_token`/`role`/`default_route`，不再假设 JWT payload 可解码。
2. 角色首页以后端 `default_route` 为准：student=`/workbench/training`，teacher=`/workbench/teaching`，admin=`/admin/console`。
3. 前端只使用仓库中已存在的后端路由；不存在接口必须标记为 `BACKLOG/TBD`，不得在方案中写“已实现”。
4. 鉴权迁移必须兼容旧键：当前 `src/components/Viewer3D/hooks/useRobotData.ts` 仍读取 `localStorage('access_token')`，且本方案禁止改 3D 文件，因此 P1-04 必须保留 legacy key 镜像。

### Step 1：接口对照结果

| 方案接口 | 实际后端实现 | 对照结果 |
|------|------|------|
| `POST /api/v1/auth/login` | `auth.py:113`，返回 `access_token` / `refresh_token` / `role` / `default_route` / `welcome_summary` / `unfinished_session` | ✅ 已验证 |
| `POST /api/v1/auth/refresh` | `auth.py:201` | ✅ 已验证 |
| `POST /api/v1/auth/logout` | `auth.py:236` | ✅ 已验证 |
| `GET /api/v1/agent/preference` | `agent.py:1825` | ✅ 已验证 |
| `PUT /api/v1/agent/preference/guidance-mode` | `agent.py:1847` | ✅ 已验证 |
| `GET /api/v1/students/{user_id}/profile` | `training.py:727` | ✅ 已验证 |
| `GET /api/v1/students/{user_id}/weak-steps` | `training.py:757` | ✅ 已验证 |
| `GET /api/v1/training/sessions/{session_id}/detail` | `training.py:305` | ✅ 已验证 |
| `GET /api/v1/classes` | `teaching.py:148` | ✅ 已验证 |
| `GET /api/v1/assignments` | `teaching.py:344` | ✅ 已验证 |
| `GET /api/v1/assignments/{assignment_id}/attempts` | `teaching.py:402` | ✅ 已验证 |
| `GET /api/v1/attempts/{attempt_id}` | `teaching.py:416` | ✅ 已验证 |
| `GET /api/v1/attempts/{attempt_id}/evidence` | `teaching.py:794` | ✅ 已验证 |
| `GET /api/v1/attempts/{attempt_id}/diagnosis` | `teaching.py:813` | ✅ 已验证 |
| `GET /api/v1/admin/users?limit=200` | `admin.py:23` | ✅ 已验证 |
| `GET /api/v1/ai/approvals?status=pending&limit=5` | `approvals.py:46` | ✅ 已验证 |
| `GET /api/v1/agent/metrics` | `agent.py:1514` | ✅ 已验证 |
| `GET /api/v1/agent/monitor/health` | `agent.py:1609` | ✅ 已验证 |
| `GET /api/v1/agent/monitor/metrics` | `agent.py:1616` | ✅ 已验证 |
| `GET /api/v1/agent/monitor/alerts?limit=5` | `agent.py:1647` | ✅ 已验证 |
| `GET /api/v1/health` | `health.py:30` | ✅ 已验证 |
| `WS /ws/robot/status` | `websocket.py:13`，服务端推送 `telemetry`，并发送 `ping` 心跳 | ✅ 已验证 |
| `GET /api/v1/training/users/{user_id}/sessions` | `training.py:599` | ⚠️ 已修正：原方案误判为缺失接口，实际已存在 |
| `GET /api/v1/training/users/{user_id}/active-session` | `training.py:632` | ⚠️ 已修正：原方案遗漏，可用于断点续训 |
| `GET /api/v1/agent/metrics/reports?limit=10` | `agent.py:1579` | ⚠️ 已修正：原方案遗漏，AdminDashboard 趋势应优先使用 |
| `GET /api/v1/agent/monitor/metrics/history?limit=100` | `agent.py:1630` | ⚠️ 已修正：原方案遗漏，系统监控趋势应优先使用 |
| `GET /api/v1/ai/approvals/{id}` / `POST /api/v1/ai/approvals/{id}/grant` / `POST /api/v1/ai/approvals/{id}/reject` | `approvals.py:127` / `173` / `280` | ⚠️ 已修正：原方案只写列表接口，审批操作接口需一并纳入 |
| 教师发送提示接口 | 当前代码库未找到公开路由 | ❌ 后端待实现 |

### Step 2：识别到的错误假设

#### 鉴权机制类

- ~~前端可以通过 JWT payload 解码得到 role~~  
  ⚠️ 已修正：`/api/v1/auth/login` 和 `/api/v1/auth/refresh` 返回的是 opaque token；`role` 与 `default_route` 直接来自响应体。
- ~~只需要规划 login 接口即可完成鉴权改造~~  
  ⚠️ 已修正：完整鉴权生命周期还包括 `POST /api/v1/auth/refresh` 与 `POST /api/v1/auth/logout`，且当前前端仍有 legacy `access_token` 读取点。
- ~~用户信息可以直接从 token 中恢复~~  
  ⚠️ 已修正：当前只能从登录邮箱、本地持久化和 `GET /api/v1/agent/preference` 补齐最小用户上下文。

#### 接口路径类

- ~~StudentSkillsPage 的按用户训练历史接口不存在~~  
  ⚠️ 已修正：实际存在 `GET /api/v1/training/users/{user_id}/sessions`。
- ~~TeacherMonitorPage 可直接用 attempts 数据展示学生姓名、当前步骤、已用时间、attempt_count~~  
  ⚠️ 已修正：`AssignmentAttemptResponse` 实际字段只有 `studentId / status / score / attemptIndex / taskId / createdAt / updatedAt`，不含姓名、当前步骤、已用时间、`attempt_count`。
- ~~AdminDashboard 的“趋势”可以直接由 `/api/v1/agent/metrics` 提供~~  
  ⚠️ 已修正：`/api/v1/agent/metrics` 仅返回当前快照；趋势应使用 `/api/v1/agent/metrics/reports` 或 `/api/v1/agent/monitor/metrics/history`。
- ~~ApprovalQueuePage 只需要把旧 helper 路径换掉即可~~  
  ⚠️ 已修正：不仅路径从 `/agent/approval/*` 漂移到 `/ai/approvals*`，返回 payload 结构也不同，页面列定义需要同步调整。

#### WebSocket类

- ~~存在班级级 WebSocket 频道或 class-specific 路径~~  
  ⚠️ 已修正：当前唯一公开路径是 `WS /ws/robot/status`。
- ~~TeacherMonitorPage 可以直接消费 `step_warning` 等班级事件~~  
  ⚠️ 已修正：当前 WebSocket 公开行为是 `telemetry` 推送 + `ping` 心跳，且客户端 `pong` 仍未被 endpoint 正式转交给 manager；班级级事件未暴露。
- ~~websocket_manager 已经实现频道映射~~  
  ⚠️ 已修正：`broadcast_to_channel()` / `send_to_user()` 当前仍是“向所有连接广播”的简化实现。

#### 工具链类

- ~~前端 CI 位于 `r-mos-frontend/.github/workflows/frontend-ci.yml`~~  
  ⚠️ 已修正：实际文件位于仓库根 `.github/workflows/frontend-ci.yml`，无需重复新建。
- ~~Node 版本文件位于 `r-mos-frontend/.nvmrc`~~  
  ⚠️ 已修正：实际文件位于仓库根 `.nvmrc`，当前值为 `22`。
- ~~ADR 目录位于 `r-mos-frontend/docs/adr/`~~  
  ⚠️ 已修正：实际 ADR 目录位于仓库根 `docs/adr/`。

#### 其他类

- ~~StudentSkillsPage 可以把后端 profile / weak-step / session 数据直接喂给现有三个训练组件~~  
  ⚠️ 已修正：当前组件 props 与后端字段结构并非一一对应，需要页面内 adapter 或组件契约调整。
- ~~TrainingWorkbenchPage 可以直接复用现有 `ABNORMAL` 工具状态~~  
  ⚠️ 已修正：当前 `workbenchStore` 枚举是 `PENDING | CONFIRMED | ANOMALY`。

### 子任务对齐矩阵（执行前必读）

| 子任务 | 状态 | 当前仓库对齐结论 | 最小验证 |
|------|------|------------------|---------|
| `P1-01` tokens/theme | `DONE` | 仅涉及 `src/styles/`，无接口依赖 | `npm run build` |
| `P1-02` Tailwind 映射 | `DONE` | 仅配置层，需保持 AntD 现有主题共存 | `npm run build` |
| `P1-03` shadcn 初始化 | `DONE WITH ADR` | 依赖新增已由 `ADR-FE-REDESIGN-001` 覆盖 | `npm run build` |
| `P1-04` 鉴权体系 | `DONE WITH COMPAT` | 必须对齐 `/auth/login` 返回体，并兼容旧 `access_token`/`refresh_token` 键 | `npm test -- ProtectedRoute` + `npm run build` |
| `P1-05` 角色布局 | `DONE` | 菜单路径必须使用 canonical route：`/workbench/teaching`、`/admin/console` | `npm run build` |
| `P1-06` 路由重组 | `DONE` | `/admin/console` 对应 `P2-06`，`/teacher/monitor` 和 `/admin/dashboard` 仅保留别名 | `npm run build` |
| `P2-01` 通用组件 | `DONE` | 已落地 `PageHeader / DataCard / StatusBadge / SectionCard / EmptyState` 并统一 export | `npm run build` |
| `P2-02` AgentWorkbench | `DONE` | 已完成左右双栏、轨迹抽屉视觉重构；`user_id` 硬编码留到 `P3-02` 统一处理 | `npm run build` |
| `P2-03` TrainingWorkbench | `DONE WITH STORE EXTENSION` | 已增量扩展 `workbenchStore` 且保持现有 API 兼容，工作台接入真实活跃会话与步骤详情 | `npm test` + `npm run build` |
| `P2-04` StudentSkills | `DONE WITH CONTRACT ADAPTER` | 已完成 profile / weak-step / session 三类字段适配，并接入真实训练历史接口 | `npm run build` |
| `P2-05` TeacherMonitor | `DONE WITH BACKLOG GUARDRAILS` | 已并入 `src/teaching/` 域，严格按现有 attempts/WS 边界实现，教师提示仍保留为后端 BACKLOG | `npm run build` |
| `P2-06` AdminDashboard | `DONE WITH HISTORY ADDITIONS` | 已接入 users/approvals/metrics/reports/monitor/history/alerts/health 并 30 秒自动刷新 | `npm run build` |
| `P2-07` SOPMaintenance | `DONE` | 已补入工作台式标题区与步骤导航外壳，保留现有 3D 渲染组合与逻辑 | `npm run build` |
| `P3-01` 批量视觉统一 | `READY WITH EXCEPTIONS` | `EvidencePage`、`ApprovalQueuePage`、`LLMMetricsPage` 不是纯视觉，需先做 API 对齐 | `npm run build` |
| `P3-02` 残余 TODO/API 对齐 | `READY` | 除 TODO 外，还需处理审批页旧 helper 路由漂移 | `npm run build` |
| `P3-03` 样式清理 | `READY` | 使用 `rg` 检查引用，避免删错 | `npm run build` |
| `P3-04` 联调 | `READY` | 验收预期必须改成 canonical route 和真实接口能力 | `npx tsc --noEmit` + `npm test` + `npm run build` |
| `P3-05` CI 基线复核 | `DONE` | 已存在 `.github/workflows/frontend-ci.yml` 和 `.nvmrc=22` | `npx tsc --noEmit` + `npm test` + `npm run build` |

---

## 设计方向

> ✅ 已验证：本章为视觉方向定义，与当前代码库契约无冲突，保留原文。

### 风格定义：工业控制台 · 精密仪器美学

R-MOS 是机器人维保操作系统，用户是工程师和技术教师。
设计语言传达**精密、可信、高效**，而非消费级 App 的轻松感。

```
风格关键词：Industrial Precision Dark

背景层级：深灰阶渐进（不用纯黑）
  #0a0a0f → #13131a → #1c1c27 → #252535

主色：冷蓝 #2D7DD2
强调色：琥珀 #F4A261（警告/高亮）/ 青绿 #2EC4B6（通过/健康）/ 红 #E63946（危险）

字体：
  JetBrains Mono → 所有数值、代码、ID、时间戳
  Inter           → 所有 UI 文字、标题、说明

卡片风格：玻璃拟态（backdrop-filter blur + 半透明背景 + 细边框）
边框：1px rgba(255,255,255,0.08~0.18)，有层次感
动效：克制，仅状态变化时触发，150ms ease-out，不做无意义装饰动画
信息密度：中高密度，工程师不需要大留白，但层次必须清晰
```

### 与现状的差异

| 现在 | 改后 |
|------|------|
| Ant Design 默认深色，偏蓝灰 | 自定义深灰底，质感更强 |
| 大量 inline style，风格不统一 | Tailwind + CSS 变量，全局统一 |
| 菜单 11 项平铺，无角色区分 | 按角色分三个视图，菜单精简 |
| 顶部硬编码 `Test Admin` | 真实用户信息 + 角色徽标 |
| 白底卡片（深色主题下突兀） | 半透明玻璃卡片，融入背景 |
| 无鉴权，无登录页 | 完整鉴权上下文 + 角色路由守卫 |

---

## 技术栈变更

> ✅ 已验证：新增依赖与保留栈方向合理；ADR 入口已存在于 `docs/adr/ADR-FE-REDESIGN-001.md`。

### 新增

```bash
# 依赖变更前置：先落 ADR（docs/adr/ADR-FE-REDESIGN-001.md）

# Tailwind CSS（Vite 5 原生支持）
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn/ui（按需安装）
npx shadcn@latest init

# 图标
npm install lucide-react

# 字体
npm install @fontsource/jetbrains-mono @fontsource/inter

# 动效
npm install motion

# Toast 通知
npx shadcn@latest add sonner
```

> ADR 覆盖范围必须显式包含：`tailwindcss`、`postcss`、`autoprefixer`、`shadcn/ui`、`sonner`、`lucide-react`、`@fontsource/*`、`motion`。

### 保留不动

```
Ant Design 5          Table / Form / DatePicker / Modal 等数据组件
react-router-dom 6    路由结构保留，只重组层级
zustand               状态管理保留，新增 authStore
axios                 请求层保留，补充 token 拦截器
three / @react-three  3D 层完全不动
```

### 目录结构变更

```
src/
├── styles/
│   ├── tokens.css          【新建】设计令牌
│   ├── theme.ts            【修改】与 tokens.css 对齐
│   └── index.css           【修改】引入 Tailwind，清理冗余
│
├── components/
│   ├── ui/                 【新建】shadcn/ui 组件
│   ├── common/             【扩展】业务通用组件
│   ├── Layout/
│   │   ├── AppLayout.tsx   【重写】三角色布局分支
│   │   ├── StudentLayout.tsx    【新建】
│   │   ├── TeacherLayout.tsx    【新建】
│   │   └── AdminLayout.tsx      【新建】
│   └── auth/
│       ├── AuthContext.tsx      【新建】
│       └── ProtectedRoute.tsx   【改为真实使用】
│
├── store/
│   ├── authStore.ts        【新建】用户身份 / role / token
│   └── workbenchStore.ts   【增量扩展】训练工作台编排状态（保持现有接口兼容）
│
├── teaching/
│   └── pages/              【扩展】教师域页面（复用现有 teaching store/api）
│
└── pages/
    ├── student/            【新建】学生专属页面
    └── admin/              【保留并整合】
```

---

## 三期总览

```
P1  第1-2周   地基：设计令牌 + 鉴权 + 布局重组     不动页面内容，风险低
P2  第3-4周   核心页面改造（8个）                   改视觉不改逻辑，风险中
P3  第5-6周   剩余页面 + 清理 + 联调 + CI           收尾，风险低
```

---

## P1 · 地基建设（第 1-2 周）

> 本期结束：应用可正常运行，视觉上与现在相似，但架构已正确。
> 所有「改页面内容之前必须做的」工作全部在本期完成。

---

### P1-01 · 设计令牌系统（tokens.css）

> ✅ 已验证：本节为纯样式层改造，不依赖后端契约，保留原文。
> ✅ 2026-03-06 已完成：`tokens.css`、`index.css`、`theme.ts` 已按新令牌体系落地。

**Codex 指令：**

```
【全局约束】改造过程中：不改业务逻辑 / 不改3D层 / 不改测试文件 /
新样式用Tailwind / 不写新CSS文件 / 不写inline style（动态计算值除外）

任务：在 r-mos-frontend/src/styles/ 下新建 tokens.css，
建立完整的 CSS 变量设计令牌系统：

颜色：
  背景 --bg-base/#0a0a0f  --bg-surface/#13131a  --bg-elevated/#1c1c27  --bg-overlay/#252535
  主色 --color-primary/#2D7DD2  --color-primary-hover/#3d8de2  --color-primary-muted/rgba(45,125,210,0.15)
  强调 --color-amber/#F4A261  --color-green/#2EC4B6  --color-red/#E63946
  文字 --text-primary/#e8edf4  --text-secondary/#8b95a5  --text-muted/#4a5568
  边框 --border-subtle/rgba(255,255,255,0.06)  --border-default/rgba(255,255,255,0.10)  --border-strong/rgba(255,255,255,0.18)

间距（4px基准）：--space-1(4px) 到 --space-16(64px)

圆角：--radius-sm/4px  --radius-md/8px  --radius-lg/12px  --radius-xl/16px

阴影（带 primary 色微光）：--shadow-sm  --shadow-md  --shadow-lg

动效：--duration-fast/100ms  --duration-base/150ms  --duration-slow/300ms
      --ease-base/cubic-bezier(0.4,0,0.2,1)

字体：--font-mono/'JetBrains Mono',monospace  --font-sans/'Inter',system-ui,sans-serif

同步修改 src/styles/index.css：
  顶部加 @import './tokens.css'
  加 @tailwind base/components/utilities
  body 应用 bg-base 背景色和 text-primary 文字色
  加 @fontsource/jetbrains-mono 和 @fontsource/inter 的 import

同步修改 src/styles/theme.ts（Ant Design 主题）：
  colorPrimary → #2D7DD2
  colorBgContainer → #1c1c27
  colorBgElevated → #252535
  colorBorder → rgba(255,255,255,0.10)
  与 tokens.css 颜色值完全对齐

完成后运行 npm run dev，截图确认背景变为深灰色。
```

---

### P1-02 · Tailwind 配置

> ✅ 已验证：本节为纯配置改造，不依赖后端契约，保留原文。
> ✅ 2026-03-06 已完成：`tailwind.config.js`、`postcss.config.js` 与工具类映射已接入。

**Codex 指令：**

```
【全局约束同 P1-01】

任务：修改 r-mos-frontend/tailwind.config.js：

1. content: ['./src/**/*.{ts,tsx}']

2. theme.extend.colors 将 tokens.css 变量映射为 Tailwind 工具类：
   bg: { base/surface/elevated/overlay }
   primary: { DEFAULT/hover/muted }
   amber / success / danger
   text: { primary/secondary/muted }
   border: { subtle/default/strong }

3. theme.extend.fontFamily:
   mono: ['JetBrains Mono', 'monospace']
   sans: ['Inter', 'system-ui', 'sans-serif']

4. theme.extend.borderRadius 映射 --radius-* 变量

5. theme.extend.boxShadow 映射 --shadow-* 变量

6. 在 src/styles/index.css 的 @layer utilities 中添加自定义工具类：
   .glass-card {
     backdrop-filter: blur(12px);
     background: rgba(28, 28, 39, 0.8);
     border: 1px solid var(--border-subtle);
   }
   .text-data { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
   .status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
```

---

### P1-03 · shadcn/ui 安装初始化

> ✅ 已验证：本节与当前仓库方向一致；新增依赖已被 ADR 覆盖。
> ✅ 2026-03-06 已完成：基础依赖、`components.json`、`src/components/ui/` 基线组件与 `npm run build` 验证已完成。

**Codex 指令：**

```
【全局约束同 P1-01】

任务：在 r-mos-frontend 目录下：

1. 运行 npx shadcn@latest init
   配置：Style=Default / BaseColor=Slate / CSS variables=Yes / 目录=src/components/ui

2. 安装组件：
   npx shadcn@latest add button card badge tooltip
   npx shadcn@latest add dropdown-menu separator scroll-area
   npx shadcn@latest add avatar progress tabs input textarea sonner

3. 修改 src/components/ui/ 下所有文件：
   将 shadcn 默认的 --background/--foreground 等变量
   替换为我们 tokens.css 中对应的变量名

4. 运行 npm run build，确认无报错，报告构建结果。
```

---

### P1-04 · 鉴权上下文

> ⚠️ 已修正：本节需要补齐 auth 生命周期接口与 legacy token 兼容说明。
> ✅ 2026-03-06 已完成：`authStore`、`AuthProvider`、`axios refresh/logout` 流程与 `ProtectedRoute` 已接入。

**Codex 指令：**

```
【全局约束同 P1-01】

任务：建立完整鉴权体系，共4个文件：

【1】新建 src/store/authStore.ts（zustand）
状态：
  user: { user_id?, email?, role:'student'|'teacher'|'admin', guidance_mode?, welcome_summary?, unfinished_session? } | null
  accessToken: string | null
  refreshToken: string | null
  isLoading: boolean

方法：
  login(credentials:{email,password})
    → POST /api/v1/auth/login
    → 成功：读取 access_token / refresh_token / role / default_route
    → 持久化：
       localStorage('rmos_access_token')
       localStorage('rmos_refresh_token')
       localStorage('rmos_role')
       localStorage('rmos_default_route')
       localStorage('rmos_user_email')
    → 兼容镜像（仅迁移期保留，因 Viewer3D hook 仍读取旧键）：
       localStorage('access_token')
       localStorage('refresh_token')
    → 可选：调用 GET /api/v1/agent/preference 回填 user_id / guidance_mode
    → ✅ 已验证：登录响应还包含 `welcome_summary` / `unfinished_session`，可直接缓存供首页和断点续训提示使用
    → 失败：抛出错误信息
  logout() → 清空 store + 清空上述 localStorage 键和 legacy key
  initFromStorage()
    → 依次读取：
       localStorage('rmos_access_token')
       localStorage('rmos_refresh_token')
       localStorage('rmos_role')
       localStorage('rmos_default_route')
    → 若新键不存在，兼容读取 legacy localStorage('access_token'/'refresh_token') 并迁移写回 rmos_* 键
    → 不做 atob 解析（token 为 opaque string）
    → 启动后探测一次 GET /api/v1/agent/preference，成功则补齐 user_id / guidance_mode
    → 用户显示名优先级：已知 full_name（若后续接口提供） > localStorage('rmos_user_email') > 登录邮箱
    → 若 401/403 则调用 logout()

【2】新建 src/components/auth/AuthContext.tsx
React Context Provider，应用启动时调用 authStore.initFromStorage()

【3】修改 src/api/client.ts（现有 axios 实例）
请求拦截器：自动附加 Authorization: Bearer {token}（从 authStore 读取）
响应拦截器：
  - 请求返回 401 时，若存在 `rmos_refresh_token`（或 legacy `refresh_token`）且该请求尚未重试过：
    1. POST /api/v1/auth/refresh
    2. 用响应体中的 `access_token` / `refresh_token` / `role` / `default_route` 更新 store 与 localStorage
    3. 重放原请求一次（仅一次）
  - 若 refresh 失败、无 refresh_token，或重放后仍为 401：
    1. 可选调用 POST /api/v1/auth/logout
    2. 执行 logout() 并跳转 /login
⚠️ 已修正：`refresh_token` 需与本地 `rmos_refresh_token` / legacy `refresh_token` 同步维护，不允许再使用“401 直接 logout”简化流程。

【4】修改 src/components/auth/ProtectedRoute.tsx（改为真实使用）
Props: { allowedRoles?: string[] }
从 authStore 读取 user
未登录 → 重定向 /login
role 不在 allowedRoles 中 → 重定向到 localStorage('rmos_default_route')
同步更新 src/components/auth/__tests__/ProtectedRoute.test.tsx 预期路由与存储键。

注意：后端 token 不是 JWT，不允许使用 atob/jwt-decode 推断身份。
```

---

### P1-05 · 角色分层布局

> ✅ 已验证：本节的 canonical route 规划已与 `default_route` 对齐，保留原文。
> ✅ 2026-03-06 已完成：`AppLayout` 已切换为三角色侧栏壳体与用户区。

**Codex 指令：**

```
【全局约束同 P1-01】

任务：重写布局系统，实现三角色差异化导航。

【AppLayout.tsx 改造】
从 authStore 读取 role，渲染对应 Layout 组件：
  student  → <StudentLayout />
  teacher  → <TeacherLayout />
  admin    → <AdminLayout />
  null     → <Navigate to="/login" />

【三个 Layout 共用的视觉规范】
整体：flex h-screen，背景 bg-base
侧边栏：bg-surface，宽 220px，fixed 高度，flex flex-col
  - 顶部 Logo 区：56px，border-b border-border-subtle，显示产品名
  - 菜单区：flex-1，overflow-y-auto
  - 底部用户区：56px，border-t border-border-subtle，显示用户名+角色徽标+退出按钮
菜单项：px-3 py-2.5，rounded-md，flex items-center gap-3
  - 默认：text-text-secondary，hover:bg-elevated hover:text-primary
  - 激活：bg-primary-muted text-primary，左侧 3px primary 实线边框条
  - 图标：Lucide 图标，18px
顶部栏（无独立 Header，合并到侧边栏顶部）
内容区：flex-1 overflow-auto p-6，背景 bg-base

不使用 Ant Design Layout/Sider/Menu，改用 Tailwind div + shadcn 组件

【StudentLayout.tsx 菜单项（4项）】
  训练工作台  /workbench/training    Lucide: Dumbbell
  我的技能    /student/skills        Lucide: BarChart3
  知识库      /knowledge             Lucide: BookOpen
  AI 助手     /ai-chat               Lucide: MessageSquare
角色徽标：蓝色 Badge「学员」
底部用户信息：优先显示 full_name；当前阶段若无用户资料接口，回退显示邮箱

【TeacherLayout.tsx 菜单项（5项）】
  班级监控台  /workbench/teaching    Lucide: Monitor
  作业管理    /teaching/assignments  Lucide: ClipboardList
  学员档案    /teacher/students      Lucide: Users
  SOP 管理    /sops                  Lucide: FileText
  知识库      /knowledge             Lucide: BookOpen
角色徽标：绿色 Badge「教师」
说明：当前登录返回体不含 class_name，P1 不要求在侧栏底部展示班级名称

【AdminLayout.tsx 菜单项（7项）】
  系统概览    /admin/console         Lucide: LayoutDashboard
  知识库      /knowledge             Lucide: BookOpen
  审批队列    /admin/approvals       Lucide: CheckSquare
  验收看板    /admin/acceptance      Lucide: BarChart2
  LLM 指标    /admin/llm-metrics     Lucide: Cpu
  故障管理    /admin/faults          Lucide: AlertTriangle
  数据管理    /admin/seed-data       Lucide: Database
角色徽标：红色 Badge「管理员」
```

---

### P1-06 · 路由重组 + 登录页

> ✅ 已验证：本节路由重组方向与后端 `default_route` 一致，保留原文。
> ✅ 2026-03-06 已完成：`LoginPage`、新路由树、P1 占位页和 `AuthProvider` 顶层包裹已落地。

**Codex 指令：**

```
【全局约束同 P1-01】

任务一：新建 src/pages/LoginPage.tsx

UI 要求：
- 整页背景 bg-base，垂直水平居中
- glass-card 卡片，宽 400px，p-8，rounded-xl
- 卡片顶部：大号 R-MOS 文字（font-mono text-2xl text-primary）
  + 副标题「机器人维护操作系统」（text-sm text-muted）
- 表单：shadcn Input（邮箱+密码），shadcn Button（全宽，primary）
- 按钮 loading 状态：禁用 + 显示 spinner
- 卡片底部：版本号和环境标识（text-xs text-muted，右对齐）
- 登录成功后根据后端返回的 `default_route` 跳转
  （当前已验证的映射为：student → `/workbench/training`，teacher → `/workbench/teaching`，admin → `/admin/console`）

任务二：重写 src/App.tsx 路由结构

新结构：
  /login                          → <LoginPage />（无需鉴权）
  /                               → <AppLayout />（需登录）
    index                         → 根据后端返回并持久化的 `default_route` 重定向到各自首页
    /workbench/training           → <TrainingWorkbenchPage />（P2-03 新建，P1 阶段用占位页）
    /student/skills               → <StudentSkillsPage />（P2-04 新建，P1 阶段用占位页）
    /workbench/teaching           → <TeacherMonitorPage />（P2-05 新建，位于 src/teaching/pages，P1 阶段用占位页）
    /teacher/monitor              → <Navigate to="/workbench/teaching" />（兼容别名）
    /teacher/students             → <TeacherStudentsPage />（位于 src/teaching/pages，占位页）
    /admin/console                → <AdminDashboardPage />（P2-06 新建，P1 阶段用占位页）
    /admin/dashboard              → <Navigate to="/admin/console" />（兼容别名）
    
    以下路由保持原样，只是挂到新结构下：
    /sops / /knowledge / /ai-chat / /monitor
    /maintenance / /atom01
    /teaching/assignments 和子路由
    /agent/workbench / /agent/replay
    /admin/approvals / /admin/acceptance / /admin/llm-metrics
    /admin/faults / /admin/seed-data
    /incidents / /evidence / /assessments / /reports / /reports/:taskId
    /diagnosis/:taskId / /tasks/:taskId

P1 阶段新路由的占位页：用一个简单的 div 显示「页面建设中，将在 P2 完成」，
不用花时间实现，P2 阶段会替换。

任务三：修改 src/App.tsx 顶层结构
在 <BrowserRouter> 外包裹 <AuthProvider>
```

**P1 验收标准：**
- [x] `npm run build` 无报错
- [ ] 访问任意路由重定向到 `/login`，登录页视觉正确
- [ ] student / teacher / admin 三种角色登录后按后端 `default_route` 跳转
- [ ] 三种角色的侧边栏菜单项各自正确
- [ ] 角色徽标、用户标识（full_name 或邮箱回退）正确显示
- [ ] 刷新后登录状态保持
- [ ] 退出登录后跳转 `/login` 且 `rmos_*` / legacy token 键均已清空

---

## P2 · 核心页面改造（第 3-4 周）

> **核心约束**：只改视觉层，不改业务逻辑。
> 每个页面改完立即运行 `npm run dev` 验证功能正常。

---

### P2-01 · 通用组件库

> ✅ 已验证：本节为组件抽象规划，与当前接口契约无冲突，保留原文。

**Codex 指令：**

```
【全局约束同 P1-01】

新建以下 5 个通用组件，统一 export 到 src/components/common/index.ts：

【PageHeader】src/components/common/PageHeader.tsx
Props: { title:string, subtitle?:string, actions?:ReactNode, breadcrumb?:string[] }
样式：mb-6 flex items-start justify-between
  左：面包屑（text-xs text-muted mb-1）+ 标题（text-xl font-semibold text-primary font-sans）+ 副标题（text-sm text-secondary mt-1）
  右：actions slot

【DataCard】src/components/common/DataCard.tsx
Props: { title:string, value:string|number, unit?:string, trend?:'up'|'down'|'flat', trendValue?:string, status?:'normal'|'warning'|'danger'|'success' }
样式：glass-card p-4 rounded-lg
  标题：text-xs text-muted uppercase tracking-wider mb-2
  数值：text-2xl font-mono font-bold text-primary
  单位：text-sm text-secondary ml-1
  trend：小箭头图标 + 数值，颜色按 status（warning=amber，danger=red，success=green）

【StatusBadge】src/components/common/StatusBadge.tsx
Props: { status:'active'|'idle'|'error'|'warning'|'success'|'pending', label?:string }
用 shadcn Badge，左侧加 status-dot
active 状态：status-dot 加 CSS 脉冲动画（animate-pulse，primary色）
颜色映射：active=primary / idle=muted / error=danger / warning=amber / success=green / pending=secondary

【SectionCard】src/components/common/SectionCard.tsx
Props: { title:string, description?:string, actions?:ReactNode, children:ReactNode, collapsible?:boolean, className?:string }
外层：glass-card rounded-xl border border-border-subtle
头部：px-5 py-4 flex items-center justify-between + border-b border-border-subtle
  标题：text-sm font-medium text-primary
  描述：text-xs text-muted ml-2
内容：p-5

【EmptyState】src/components/common/EmptyState.tsx
Props: { icon:LucideIcon, title:string, description:string, action?:{label:string, onClick:()=>void} }
居中布局，py-16
icon：text-muted，size=48
标题：text-base font-medium text-secondary mt-4
描述：text-sm text-muted mt-2
按钮（若有）：shadcn Button variant=outline，mt-6
```

---

### P2-02 · AgentWorkbenchPage 视觉改造

> ✅ 已验证：本节以视觉改造为主；`user_id` 硬编码问题已在 `P3-02` 单列处理。

**Codex 指令：**

```
【全局约束同 P1-01】
改造 src/pages/agent/AgentWorkbenchPage.tsx 视觉层，不改任何函数实现。

【整体布局】改为左右双栏：
  左侧主区（flex-1 min-w-0）：顶部 Agent 状态栏 + 消息列表 + 输入区
  右侧边栏（w-80 shrink-0）：快捷动作 + 当前任务信息
  整体：flex gap-4 h-full

【顶部 Agent 状态栏】
  用 DataCard 展示 Agent 状态：StatusBadge（在线/离线）+ 会话 ID（font-mono，可点击复制）+ 消息数
  改用 AgentStatusCapsule 组件（现有组件保留，只改外层容器）

【消息列表区】
  背景：bg-surface rounded-xl，flex-1 overflow-hidden
  内部用 shadcn ScrollArea
  用户消息气泡：ml-auto max-w-[80%]，bg-primary-muted border border-primary/20 rounded-xl p-3
  Agent 消息气泡：mr-auto max-w-[80%]，bg-elevated border border-border-subtle rounded-xl p-3
  消息中的代码块：bg-overlay font-mono text-sm p-3 rounded-md
  风险等级标签：StatusBadge（high=danger/medium=warning/low=success）
  证据需求提示：左侧 3px amber 色边框条 + bg-amber/5 背景

【输入区】
  border-t border-border-subtle p-4 bg-surface
  意图选择：shadcn Tabs 横向排列（替换现有 Select，保留 onChange 逻辑不变）
  文本输入：shadcn Textarea，深色，auto-resize，max-h-[120px]
  发送按钮：primary 色，右下角
  快捷按钮行：ghost button，flex wrap，gap-2

【右侧快捷动作】
  SectionCard 包裹，标题「快捷操作」
  6 个动作改为垂直列表：每项 flex items-center gap-3，hover:bg-elevated，cursor-pointer
  图标（Lucide）+ 标题（text-sm text-primary）+ 描述（text-xs text-muted）

【轨迹抽屉】
  保留 Drawer 逻辑，只改内部样式：
  背景 bg-surface
  时间线改为自定义：竖线 bg-border-subtle + 节点圆点（颜色按事件类型）+ 时间戳（font-mono text-xs text-muted）+ 内容

删除 src/pages/agent/AgentWorkbench.css，所有样式改 Tailwind。
```

---

### P2-03 · TrainingWorkbenchPage（新建学生训练工作台）

**Codex 指令：**

```
【全局约束同 P1-01】

新建 src/pages/student/TrainingWorkbenchPage.tsx
这是 V0.2 训练工作台的主页面，接入现有 workbenchStore。
注意：当前 src/store/workbenchStore.ts 只包含 currentStepId / toolStatusMap / verdict，
P2-03 允许在该文件内增量扩展训练工作台所需编排字段，但必须保持现有 API 兼容，
并同步更新 src/store/__tests__/WorkbenchStore.test.ts。

【整体布局】三栏 CSS Grid：
  grid-cols-[280px_1fr_300px] gap-4 h-full

【左栏：步骤面板】
  SectionCard 标题「训练步骤」，右侧显示「x/y」
  顶部 shadcn Progress 条
  步骤列表（从扩展后的 workbenchStore 步骤字段读取）：
    每项 h-14 flex items-center px-3 rounded-md cursor-pointer
    左侧状态图标：Lucide CheckCircle2(绿)/XCircle(红)/Circle(灰)
    步骤名：text-sm
    右侧用时：font-mono text-xs text-muted
    当前步骤：border-l-[3px] border-primary bg-elevated
    通过步骤：text-muted
    失败步骤：text-danger

【中栏上方：3D 模型面板（h-[60%]）】
  bg-surface rounded-xl overflow-hidden relative
  右上角浮层：两个 ghost icon button（重置视角/全屏）
  直接渲染 `src/components/Viewer3D/Atom01Viewer.tsx`，外层加 className="w-full h-full"
  不替换为 `RobotViewer` / `Atom01Interactive`，仅允许在页面外层新增布局容器和控制按钮

【中栏下方：裁决面板（h-[40%]）】
  SectionCard 标题「当前步骤操作」
  步骤指令：text-sm text-primary leading-relaxed，突出显示
  操作输入：shadcn Input
  证据上传：虚线边框 border-dashed border-border-default，文字「拖拽或点击上传证据」
  提交按钮：全宽 primary，disabled 时 shadcn Tooltip 说明「请先确认所有关键工具」
  裁决结果卡：通过=border-l-4 border-success bg-success/5 / 失败=border-l-4 border-danger bg-danger/5
    内含 LLM 解释折叠区（默认折叠，chevron 展开）

【右栏上方：工具面板（flex-1）】
  SectionCard 标题「工具清单」右侧显示「确认 x/y」
  工具列表（从扩展后的 workbenchStore 工具状态字段读取）：
    每项 flex items-center justify-between px-3 py-2.5
    左侧：is_critical → 红色 status-dot / 普通 → 灰色 status-dot
    工具名（text-sm）+ 规格（text-xs text-muted）
    右侧三按钮：
      ✓ CONFIRMED → success色 CheckCircle2
      ⚠ ANOMALY → amber色 AlertTriangle
      ○ PENDING → muted色 Circle
    CONFIRMED 行：bg-success/5
    ANOMALY 行：bg-amber/5 + 下方展示 Agent 建议文字（text-xs text-amber）

【右栏下方：Agent 对话（h-[300px]）】
  SectionCard 标题「AI 助手」
  消息列表（最近5条）：shadcn ScrollArea
  教师提示消息：border-l-2 border-success bg-success/5 + 「教师提示」小标签
  底部单行输入：shadcn Input + 发送按钮（icon）

数据加载：
  workbenchStore 若无训练项目数据（用户直接访问此页面），显示 EmptyState
  图标 Dumbbell + 标题「还没有训练项目」+ 按钮「去 AI 工作台创建训练」（跳转 /ai-chat）
```

---

### P2-04 · StudentSkillsPage（新建技能成长页）

> ⚠️ 已修正：本节的接口存在，但后端字段结构不能直接映射到现有三个训练组件。

**Codex 指令：**

```
【全局约束同 P1-01】

新建 src/pages/student/StudentSkillsPage.tsx
接入现有三个可视化组件（现在只有测试在用，本页面是它们的实际落地）：
  src/components/training/SkillRadarChart.tsx
  src/components/training/TrainingTimeline.tsx
  src/components/training/WeakStepHeatmap.tsx
注意：以上三个组件当前自带 Ant Design Card/标题/筛选器。
P2-04 默认策略是“先原样接入，不再外层重复套 SectionCard”；
若要统一外壳，需先在该子任务内抽出无壳版本，并同步更新对应 Vitest。

数据接口（后端已实现）：
  GET /api/v1/students/{user_id}/profile → 技能画像
  GET /api/v1/students/{user_id}/weak-steps → 薄弱步骤
  GET /api/v1/training/sessions/{session_id}/detail → 单会话详情（当前可用）
  ~~训练历史列表接口（按 user_id）当前未提供，标记 BACKLOG（需后端补接口）~~
  ⚠️ 已修正：实际已有 `GET /api/v1/training/users/{user_id}/sessions`，应作为训练历史时间线数据源
  ✅ 已补充：`GET /api/v1/training/users/{user_id}/active-session` 可用于页面顶部“继续未完成训练”提示
  user_id 从 authStore 读取

字段适配说明：
  ⚠️ 已修正：`SkillProfileResponse` 实际字段是 `score_safety / score_procedure / score_precision / score_efficiency / score_tools`，
  与 `SkillRadarChart` 当前 props `safety / quality / efficiency / diagnosis / collaboration` 不一一对应；
  本子任务须先在页面内做 adapter，或先调整组件维度定义。
  ⚠️ 已修正：`WeakStepResponse` 只有 `step_id / fail_count / last_failed_at / fail_tags / is_resolved`，
  不含 `stepName`，热力图标签需回退到 `step_id` 或通过本地映射补名。
  ⚠️ 已修正：`SessionResponse` 不含 `model` 字段，`TrainingTimeline` 不能继续假定“型号筛选”一定可用。

【页面布局】
PageHeader 标题「我的技能成长」副标题「技能等级 Lv.{level} · 累计训练 {total} 次」

第一行（4个 DataCard，grid-cols-4 gap-4）：
  综合等级 / 累计训练次数 / 累计训练时长（格式化为小时）/ 上次训练时间

第二行（grid-cols-5 gap-4）：
  左侧 2/5：直接接入 <SkillRadarChart />（保留组件自带 Card）
  右侧 3/5：SectionCard「技能详情」
    五个维度各一条：维度名（text-sm）+ shadcn Progress + 数值（font-mono）
    升级进度：当前等级大字（font-mono text-4xl text-primary）
    升级条件说明：text-xs text-muted，列出达成条件和当前进度

第三行：直接接入 <WeakStepHeatmap />（保留组件自带 Card）

第四行：训练历史区域接入 <TrainingTimeline />
  ~~当前训练历史列表接口缺失时：~~
  ⚠️ 已修正：训练历史接口已存在，应使用 `/api/v1/training/users/{user_id}/sessions`；
  ~~不额外添加外层型号筛选，沿用组件内现有筛选逻辑~~
  ⚠️ 已修正：由于真实接口不返回 `model`，应优先改为按 `project_id`/`submit_type` 展示，或在无模型字段时隐藏筛选。

加载状态：每个数据区独立 loading 态（Ant Design Spin），失败显示 EmptyState
```

---

### P2-05 · TeacherMonitorPage（新建班级监控台）

> ⚠️ 已修正：本节的核心路径存在，但 attempts payload 与页面想展示的信息并不完全匹配。

**Codex 指令：**

```
【全局约束同 P1-01】

新建 src/teaching/pages/TeacherMonitorPage.tsx
并入现有 teaching 域目录，复用 teaching store / api / types。

数据来源：
  GET /api/v1/classes（教师可见班级列表）
  GET /api/v1/assignments（教师先选择作业）
  GET /api/v1/assignments/{assignment_id}/attempts（按作业拉取班级尝试）
  WS /ws/robot/status（当前可用，提供全局实时状态）
  GET /api/v1/students/{user_id}/profile（点击学员后加载详情）
  authStore 当前不提供 class_id，不允许写“从 authStore 读取 class_id”
  ✅ 已补充：点击具体尝试后可使用 `GET /api/v1/attempts/{attempt_id}`、`/evidence`、`/diagnosis` 补齐详情页跳转

【整体布局】
PageHeader 标题「班级监控台」
副标题由当前所选 class + assignment 推导；若教师有多个班级/作业，头部提供 Select
顶部 3个 DataCard（grid-cols-3）：在训人数 / 今日已完成 / 失败预警

主区域：grid grid-cols-5 gap-4
  左侧学员列表（col-span-3）
  右侧学员详情（col-span-2，点击学员后展示，默认 EmptyState）

【学员列表（SectionCard）】
每个学员行（flex items-center px-4 py-3 border-b border-border-subtle cursor-pointer）：
  左侧 shadcn Avatar（优先显示姓名首字母；当前接口缺姓名时回退为 `studentId` 尾号或默认图标）
  ~~中间：姓名（text-sm font-medium）+ 技能等级徽标（StatusBadge）~~
  ~~      当前步骤（text-xs text-muted）+ 已用时间（font-mono text-xs）~~
  ⚠️ 已修正：`AssignmentAttemptResponse` 不含 `student_name / current_step / duration`；
  列表默认展示 `studentId / attemptIndex / status / updatedAt`，姓名与步骤信息需后续补充接口。
  ~~右侧：StatusBadge（训练中/空闲/已提交）+ 两个 ghost 按钮~~
  ⚠️ 已修正：按真实状态枚举映射 `in_progress / completed / graded / abandoned`。
  ~~预警行（attempt_count >= 3）：border-l-[3px] border-amber bg-amber/5~~
  ⚠️ 已修正：预警条件改为 `attemptIndex >= 3`，与实际 payload 对齐。

WebSocket：
  连接 /ws/robot/status
  ✅ 已验证：服务端当前明确推送 `telemetry` 消息，并发送 `ping` 心跳
  ⚠️ 已验证：当前 `websocket.py` 仅 `receive_text()` 并记录日志，尚未把客户端消息转交 `websocket_manager.handle_client_message()`；因此前端即使返回 `pong`，也不能视为后端已完整消费
  将全局遥测转换为页面状态提示（在线/离线/异常）
  班级级 `step_warning` 事件当前后端未提供，且不存在等价轮询接口
  可行降级仅限：每 10s 轮询 `/api/v1/assignments/{assignment_id}/attempts` 刷新 `studentId / status / score / attemptIndex / taskId / createdAt / updatedAt`
  不得将该轮询描述为“步骤级实时预警替代”；`step_warning / current_step / duration` 仍属于后端待实现 BACKLOG

【学员详情面板（SectionCard）】
  shadcn Avatar（大号）+ `studentId`（若后续补充姓名则优先显示姓名）+ 等级
  ~~当前训练进度：步骤名 + 进度条~~
  ⚠️ 已修正：当前 attempts/profile 接口不返回步骤进度；详情区先展示 `status / attemptIndex / score / taskId`
  已尝试次数：font-mono + 颜色（>3 = amber）
  主操作按钮：
    进入尝试详情 → /teaching/attempts/{attempt_id}
    查看证据 → /teaching/attempts/{attempt_id}/evidence
    查看诊断 → /teaching/attempts/{attempt_id}/diagnosis
  ~~「教师发送提示」接口当前未暴露，保留 disabled 按钮 + Tooltip，标记 BACKLOG~~
  ⚠️ 已修正：教师发送提示交互先保留 disabled 按钮 + Tooltip，文案改为“待后端接口”
  > ❌ 后端待实现：该接口当前不存在，前端开发前需先与后端确认实现计划
```

---

### P2-06 · AdminDashboardPage（新建管理员首页）

> ⚠️ 已修正：本节的核心接口存在，但“趋势”类模块必须补用历史接口，不能只依赖快照接口。

**Codex 指令：**

```
【全局约束同 P1-01】

新建 src/pages/admin/AdminDashboardPage.tsx

数据：
  GET /api/v1/admin/users?limit=200（用户规模）
  GET /api/v1/ai/approvals?status=pending&limit=5（待审批）
  GET /api/v1/agent/metrics（LLM/验收指标）
  ✅ 已补充：GET /api/v1/agent/metrics/reports?limit=10（历史报告，用于趋势）
  GET /api/v1/agent/monitor/health（系统监控）
  GET /api/v1/agent/monitor/metrics（CPU/内存/磁盘）
  ✅ 已补充：GET /api/v1/agent/monitor/metrics/history?limit=100（系统趋势）
  GET /api/v1/agent/monitor/alerts?limit=5（近期告警）
  GET /api/v1/health（系统健康状态）
  每30秒自动刷新

【布局】
PageHeader 标题「系统概览」右侧显示「最后更新 {时间}（font-mono text-xs）」

第一行 4个 DataCard：
  用户总数（/admin/users）
  待处理审批数（/ai/approvals）
  指标通过数或通过率（/agent/metrics 推导）
  系统总体状态（/agent/monitor/health 或 /health）

第二行 grid-cols-3 gap-4：
  ~~左 2/3：SectionCard「LLM 调用趋势」~~
  ⚠️ 已修正：左 2/3 改为 SectionCard「评测指标概览 / 历史报告」；
  `/api/v1/agent/metrics` 只返回当前快照，若绘制趋势线必须改接 `/api/v1/agent/metrics/reports`
  右 1/3：SectionCard「待处理审批」
    列表展示最近5条待审批，每项 flex + 操作按钮，底部「查看全部」链接

第三行 grid-cols-2 gap-4：
  左：SectionCard「近期告警」列表（/agent/monitor/alerts）
  右：SectionCard「系统健康」
    CPU/内存/磁盘/应用：StatusBadge
    overall_status：大号状态字
    内存使用率：shadcn Progress
```

---

### P2-07 · SOPMaintenancePage 视觉改造

> ✅ 已验证：本节为纯视觉改造，不依赖后端契约，保留原文。

**Codex 指令：**

```
【全局约束同 P1-01】
改造 src/pages/SOPMaintenancePage.tsx 视觉层，不改逻辑。

改为两栏布局：
  左侧 SOP 步骤导航（w-64 shrink-0）
  右侧操作主区（flex-1）

左侧导航（bg-surface rounded-xl p-4）：
  顶部：SOP 名称（text-sm font-medium）+ 机器人型号徽标（font-mono text-xs text-primary bg-primary-muted px-2 py-0.5 rounded）
  步骤列表：与 TrainingWorkbenchPage 步骤面板风格一致
  BLOCK 步骤：右侧 Lucide Lock 图标（text-amber）
  SAFETY_HALT 步骤：右侧 Lucide ShieldAlert 图标（text-danger）

右侧主区：
  面包屑（text-xs text-muted）+ severity 徽标（StatusBadge）
  步骤指令区：SectionCard，text-sm text-primary leading-relaxed
  3D 操作区：保留 `src/pages/SOPMaintenancePage.tsx` 现有渲染组合
    `Canvas + OrbitControls + Atom01Interactive + CameraController + DisassemblyAnimation + DetailParts`
  仅允许外层新增 rounded-xl overflow-hidden 容器，不替换内部 3D 组件组合
  工具要求：SectionCard，风格与训练工作台工具面板一致
```

**P2 验收标准：**
- [x] AgentWorkbenchPage：发消息/收回复/轨迹抽屉功能正常
- [x] TrainingWorkbenchPage：扩展后的 workbenchStore 接入，步骤切换联动正常
- [x] StudentSkillsPage：雷达图/热图显示真实数据，时间线使用 `/training/users/{user_id}/sessions` 真实数据并完成字段适配
- [x] TeacherMonitorPage：全局 WebSocket 状态可见，班级列表/详情通过轮询与现有 teaching 路由联动
- [x] AdminDashboardPage：以 users/approvals/metrics/health/alerts 真实数据正确加载并自动刷新
- [x] 整体视觉风格统一：深灰底 + 玻璃卡片 + 工业蓝主色

---

## P3 · 剩余页面 + 清理 + 联调（第 5-6 周）

---

### P3-01 · 批量页面视觉统一

> ✅ 已验证：本节作为收尾样式统一方向合理；其中 API 对齐例外项已单独指出。

> 以下页面逻辑完善，只套用设计系统。每页约半天。
> 例外：`EvidencePage` / `ApprovalQueuePage` / `LLMMetricsPage` 在当前仓库中都存在接口对齐问题，不属于纯视觉；这些页面必须先完成对应 API 薄封装或 TODO 清理，再做视觉统一。

**通用 Codex 指令模板：**

```
【全局约束同 P1-01】
改造 src/pages/[页面名].tsx 视觉层，不改业务逻辑：
1. 用 PageHeader 替换现有标题区
2. 用 SectionCard 替换 Ant Design Card
3. Ant Design Table 保留，外层用 SectionCard 包裹
4. 状态标签改用 StatusBadge
5. 移除所有 inline style，改为 Tailwind
6. 深色主题下所有文字/边框/背景对比度符合 tokens.css 规范
```

| 页面 | 改造重点 | 工时 |
|------|---------|-----|
| `KnowledgePage` | 上传区虚线边框 + 文档列表 + 异步进度条 | 0.5天 |
| `AssessmentStatusPage` | 状态列表 + 筛选区 | 0.5天 |
| `IncidentListPage` | 事件列表 + 严重级别徽标 | 0.5天 |
| `EvidencePage` | 证据包列表 + 详情抽屉（接入真实API，替换 mock 数据） | 1天 |
| `ReportPage` | 评分卡片 + 步骤得分 + 历史对比 | 0.5天 |
| `ReplayPage` | 自定义时间线 + 事件卡片 | 1天 |
| `ApprovalQueuePage` | 审批列表 + 操作按钮 | 0.5天 |
| `AcceptanceDashboardPage` | 指标卡片 | 0.5天 |
| `LLMMetricsPage` | 指标表格（接入真实API，替换TODO） | 0.5天 |
| `TeachingAssignmentsPage` | 双 Tab + 作业表格 | 0.5天 |
| `TeachingDiagnosisPage` | 诊断报告卡片 | 0.5天 |
| `DiagnosisPage` | 诊断结果展示 | 0.5天 |

---

### P3-02 · 残余 TODO 处理

> ⚠️ 已修正：本节不仅处理 TODO，还需要处理真实 API payload 与现页面类型不一致的问题。

**Codex 指令：**

```
处理以下 5 项残余 TODO / API 漂移，规则：能实现的实现，不能实现的改为 BACKLOG 注释。

1. src/pages/AIChatPage.tsx
   user_id: 'current-user'
   → 改为从 authStore 读取：
   import { useAuthStore } from '@/store/authStore'
   const { user } = useAuthStore()
   user_id: user?.user_id ?? 'anonymous'

2. src/pages/agent/AgentWorkbenchPage.tsx
   user_id: 'current-user'
   → 与 AIChatPage 同步改为从 authStore 读取，禁止继续硬编码

3. src/pages/admin/LLMMetricsPage.tsx
   TODO: Call backend API when available
   → 实现真实调用：优先复用 src/api/agent-v2.ts 中的 getCurrentMetrics()
   不在页面内裸写 axios，显示加载态和错误态
   ⚠️ 已修正：真实 `/api/v1/agent/metrics` 返回 `{ metrics: MetricRecord[] }` 平铺列表，
   不是当前 mock 的 `period/metrics/generated_at` 结构；页面状态模型需一起重构

4. src/pages/TaskExecutionPage.tsx
   TODO: Integrate with Coach Agent API
   → 改写为：// BACKLOG: Integrate with Coach Agent API - pending TrainingWorkbenchPage migration
   不实现，只规范注释格式

5. src/pages/admin/ApprovalQueuePage.tsx + src/api/agent-v2.ts
   当前审批页仍调用旧的 /agent/approval/* helper，而后端真实路由是 /ai/approvals
   → 新建薄封装 src/api/approvals.ts（list / detail / grant / reject）
   → ApprovalQueuePage 与后续 AdminDashboardPage 均切到该薄封装
   ⚠️ 已修正：真实 `/api/v1/ai/approvals` 返回 `{ items, count, limit, offset }`，
   字段为 `trace_id / command_id / tool_call_id / created_by_user_id / decided_by_user_id / reason / status`，
   现有 `ApprovalRequest` 结构需同步调整
```

---

### P3-03 · 样式文件清理

> ✅ 已验证：本节清理动作与当前仓库习惯一致，保留原文。

**Codex 指令：**

```
执行以下清理，每步完成后运行 npm run build 确认无报错：

1. 检查 src/pages/agent/AgentWorkbench.css 是否还有引用：
   rg -n "AgentWorkbench.css" src/
   若无引用，删除该文件

2. 检查 src/pages/HomePage.css：
   rg -n "HomePage.css" src/
   若无引用，删除该文件

3. 审查 src/styles/index.css：
   删除已被 Tailwind @layer base 覆盖的冗余全局样式
   保留：@import tokens.css / @tailwind directives / 自定义动效

4. 运行 npm run build，报告最终构建产物大小
```

---

### P3-04 · 全面联调（三批次）

> ⚠️ 已修正：本节联调口径需同时验证 canonical route、WebSocket 心跳和真实 payload 映射。

**第一批：鉴权流程（发给 Codex 测试）**

```
请依次用浏览器测试以下场景并报告结果（PASS/FAIL + 实际行为）：

1. 未登录访问 /workbench/training → 预期：跳转 /login
2. student 账号登录 → 预期：跳转 /workbench/training，看到4项学生菜单
3. teacher 账号登录 → 预期：跳转 /workbench/teaching，看到5项教师菜单
4. admin 账号登录  → 预期：跳转 /admin/console，看到7项管理菜单
5. student 账号访问 /admin/console → 预期：重定向到 /workbench/training
6. 登录后刷新页面 → 预期：登录状态保持，不跳转 /login
7. 点击退出登录 → 预期：跳转 /login，localStorage 无 rmos_access_token / rmos_refresh_token
8. 兼容验证：直接访问 /teacher/monitor 或 /admin/dashboard → 预期：重定向到 canonical route
```

**第二批：核心功能回归（发给 Codex 测试）**

```
请测试以下核心功能是否正常（只报告功能问题，不报告视觉问题）：

1. AgentWorkbenchPage：输入消息发送 → AI 回复正常展示 → 消息气泡样式正确
2. TrainingWorkbenchPage：有训练项目时四面板正常渲染 → 步骤切换时3D高亮和工具面板联动
3. TeacherMonitorPage：WebSocket 连接成功 → 全局状态可见 → 轮询后的尝试列表与详情页跳转正常
4. StudentSkillsPage：雷达图/热图显示真实数据；时间线使用 `/training/users/{user_id}/sessions` 真实数据，字段不足处按适配策略降级展示
5. KnowledgePage：上传 PDF → 进度条显示 → 完成后文档出现在列表

每个功能报告：正常/异常，异常时描述具体现象。
```

**第三批：TypeScript 和构建质量**

```
依次执行并报告结果：

1. npx tsc --noEmit 2>&1 | head -80
   → 报告错误总数，逐一修复直到 0 错误

2. npx eslint src/ --ext .ts,.tsx 2>&1 | grep "error" | head -50
   → 修复所有 error 级别问题（warning 暂时保留）

3. npm run build
   → 报告：构建是否成功 / 产物总大小 / 最大单文件大小
   → 若单文件 > 1MB，分析原因并考虑代码分割
```

---

### P3-05 · 前端 CI 流水线

> ✅ 已验证：当前仓库已存在 `.github/workflows/frontend-ci.yml` 与根目录 `.nvmrc`，本节只做复核。

**Codex 指令：**

```
本项已完成，改为“基线复核”（No-op）：

1. 核查 .github/workflows/frontend-ci.yml 存在且步骤完整
2. 核查根目录 .nvmrc = 22
3. 复跑前端门禁命令：
   npx tsc --noEmit
   npx eslint src/ --ext .ts,.tsx --max-warnings 0
   npm test
   npm run build
```

---

## 给 Codex 的全局约束提示词

> **每次给 Codex 发指令时，在最前面粘贴这段话**，防止它越界修改：

```
【R-MOS 前端改造全局约束 - 每次指令必须遵守】

你正在对 R-MOS（机器人维保操作系统）前端项目进行视觉层改造。
以下约束在整个改造过程中始终有效，优先级高于任何具体指令：

❌ 绝对禁止：
  - 修改任何 API 调用函数的内部实现（可以移动调用位置，不能改函数体）
  - 修改任何 Three.js / @react-three 相关文件
  - 无关测试禁止改动；若页面行为改变，必须同步更新对应 Vitest 用例
  - 新建 .css 文件（tokens.css 和 index.css 除外，且已存在）
  - 编写 inline style（除非是动态计算的值，如 `style={{ width: \`\${pct}%\` }}`）
  - 引入任何 tokens.css 和 theme.ts 中没有定义的颜色值

✅ 样式优先级：
  1. Tailwind 工具类（首选）
  2. cn() 工具函数组合（动态类名）
  3. shadcn/ui 组件（布局/展示类）
  4. Ant Design 组件（Table/Form/DatePicker/Modal 等数据组件，保留不动）

📋 每次完成必须报告：
  - 修改/新增/删除的文件列表
  - TypeScript 类型错误（有则列出，无则说明已通过 tsc --noEmit）
  - 是否有改动业务逻辑（必须回答：有/无，有则列出具体改动）
```

---

## 完整任务清单

> ✅ 已验证：任务分期结构可保留；本轮修正聚焦各子任务的接口与契约边界。

### P1（第1-2周）基础建设
- [x] P1-01 tokens.css 设计令牌 + theme.ts 对齐
- [x] P1-02 Tailwind 配置和工具类映射
- [x] P1-03 shadcn/ui 安装初始化
- [x] P1-04 authStore + AuthContext + axios 拦截器 + ProtectedRoute 接入
- [x] P1-05 StudentLayout / TeacherLayout / AdminLayout
- [x] P1-06 路由重组 + LoginPage

### P2（第3-4周）核心页面
- [x] P2-01 通用组件库（5个组件）
- [x] P2-02 AgentWorkbenchPage 视觉改造
- [x] P2-03 TrainingWorkbenchPage 新建（四面板接入 workbenchStore）
- [x] P2-04 StudentSkillsPage 新建（三个可视化组件接入）
- [x] P2-05 TeacherMonitorPage 新建（WebSocket 实时）
- [x] P2-06 AdminDashboardPage 新建
- [x] P2-07 SOPMaintenancePage 视觉改造

### P3（第5-6周）收尾
- [ ] P3-01 批量页面视觉统一（12个页面）
- [ ] P3-02 残余 TODO 处理
- [ ] P3-03 样式文件清理
- [ ] P3-04 全面联调回归测试（三批次）
- [x] P3-05 前端 CI/.nvmrc 基线（已完成，本方案仅复核）

---

## 修正清单

- 鉴权口径：以登录/刷新响应体中的 `access_token`、`refresh_token`、`role`、`default_route` 为准；不再写成“401 直接 logout”或模糊的存储键拼接。
- 依赖与 ADR：显式补入 `lucide-react`，并要求 ADR 覆盖 `tailwindcss`、`postcss`、`autoprefixer`、`shadcn/ui`、`sonner`、`lucide-react`、`@fontsource/*`、`motion`。
- 3D 组件引用：TrainingWorkbenchPage 明确复用 `Atom01Viewer`；SOP 维护页明确保留 `SOPMaintenancePage` 现有 `Canvas + Atom01Interactive` 组合。
- WebSocket 边界：`/ws/robot/status` 当前仅可稳定视为“全局 telemetry + ping”；`pong` 尚未被后端真正消费，`step_warning` 也没有可替代的轮询接口。
- 角色跳转：登录后与根路由 index 都以后端 `default_route` 为唯一真相源，不再按前端硬编码 role 分支跳转。
- 后端待实现接口/事件：
  - `WS /ws/robot/status` 的客户端 `pong` 消费链路尚未接通
  - 班级级 `step_warning / current_step / duration` 实时事件与等价轮询接口尚未提供

*执行模型：GPT-5.3-codex（代码） + Minimax 2.5（文案校对）*  
*改造原则：视觉层替换为主；涉及接口/鉴权对齐属于必要逻辑修正；每期结束执行 `npx tsc --noEmit` + `npm test` + `npm run build` 验证*
