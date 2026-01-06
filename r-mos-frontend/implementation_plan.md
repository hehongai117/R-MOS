# R-MOS 前端开发计划（修订版）

## 0. 技术选型确认

| 维度 | 选型 | 版本 | 理由 |
|-----|------|------|------|
| 框架 | **React** | 18+ | 拆包D强制要求，函数式组件+Hooks |
| 语言 | **TypeScript** | 5+ | 严格模式，与后端类型对齐 |
| 状态管理 | **Zustand** | 4+ | 轻量、简洁，拆包D推荐 |
| UI组件库 | **Ant Design** | 5+ | 中文生态好、企业级组件 |
| HTTP客户端 | **Axios** | 1+ | 拦截器、类型支持良好 |
| WebSocket | **原生API** | - | 封装 useWebSocket Hook |
| 3D渲染 | **Three.js + R3F** | - | 机器人可视化 |
| 路由 | **React Router** | 6+ | Data Router模式 |
| 构建 | **Vite** | 5+ | 快速HMR、ESBuild |
| 样式 | **Ant Design 内置 + CSS Modules** | - | 默认使用 Less |

> [!IMPORTANT]
> 拆包D文档已明确技术栈，本计划遵循该规范。

---

## 1. 现有代码盘点

**目录**: `/Users/xuhehong/Desktop/r-mos/r-mos-frontend/src`

| 目录/文件 | 现状 | 需操作 |
|----------|------|--------|
| `src/api/` | 存在，含1个子项 | 需验证 `client.ts` |
| `src/components/` | 存在，含3个子项 | 需补充 Layout/通用组件 |
| `src/hooks/` | 存在，含1个子项 | 需验证 `useWebSocket.ts` |
| `src/pages/` | 存在，含4个子项 | 需补充完整页面 |
| `src/store/` | 存在，含1个子项 | 需验证 Zustand stores |
| `src/types/` | ❌ 缺失 | 需创建 |
| `src/utils/` | ❌ 缺失 | 需创建 |
| `package.json` | ❓ 未确认 | 需验证依赖 |
| `vite.config.ts` | ❓ 未确认 | 需验证代理配置 |
| `tsconfig.json` | ❓ 未确认 | 需验证严格模式 |

---

## 2. 开发阶段规划

### Phase 1: 项目验证与补全 [P0]

| 任务ID | 文件 | 功能 | 状态 |
|--------|-----|------|------|
| F1.1 | `package.json` | 验证依赖完整性，补充缺失 | 待验证 |
| F1.2 | `tsconfig.json` | 验证严格模式配置 | 待验证 |
| F1.3 | `vite.config.ts` | 验证代理配置 `/api/v1 -> :8000` | 待验证 |
| F1.4 | `index.html` | 验证存在 | 待验证 |
| F1.5 | `.env.example` | 创建环境变量模板 | 缺失 |
| F1.6 | `src/main.tsx` | 验证应用入口 | 待验证 |
| F1.7 | `src/App.tsx` | 验证路由配置 | 待验证 |

---

### Phase 2: 类型定义 [P0]

> [!WARNING]
> 必须与后端 Schema 完全对齐，下方列出对照表。

| 任务ID | 文件 | 后端对应 | 关键类型 |
|--------|-----|----------|---------|
| F2.1 | `src/types/sop.ts` | `schemas/sop.py` | `SOP`, `SOPStep`, `SOPListItem` |
| F2.2 | `src/types/task.ts` | `schemas/task.py` | `Task`, `TaskStatus`, `StepExecutionRequest/Response` |
| F2.3 | `src/types/robot.ts` | `adapters/schemas.py` | `JointState`, `SensorData`, `TelemetryMessage` |
| F2.4 | `src/types/fault.ts` | `schemas/fault.py` | `FaultCase`, `FaultCaseListItem` |
| F2.5 | `src/types/api.ts` | `core/exceptions.py` | `ErrorResponse`, `PaginatedResponse` |
| F2.6 | `src/types/report.ts` | `schemas/report.py` | `TaskReport`, `ScoreBreakdown`, `StepScore` |

**后端 Schema 对齐检查清单**:

```typescript
// TaskStatus 枚举值必须一一对应
enum TaskStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  PAUSED = "paused",
  COMPLETED = "completed",
  FAILED = "failed",
  TIMEOUT = "timeout"
}
```

---

### Phase 3: API层完善 [P0]

| 任务ID | 文件 | API函数 | 后端端点 |
|--------|-----|---------|---------|
| F3.1 | `src/api/client.ts` | 验证基础配置 | - |
| F3.2 | `src/api/sop.ts` | `listSOPs`, `getSOP`, `deleteSOP`, `checkDeleteImpact` | `/sops/*` |
| F3.3 | `src/api/task.ts` | `createTask`, `getTask`, `startTask`, `executeStep`, `pauseTask`, `resumeTask`, `getReport` | `/tasks/*` |
| F3.4 | `src/api/adapter.ts` | `getAdapterInfo`, `getRobotStructure`, `injectFault`, `clearFault`, `getActiveFaults` | `/adapter/*` |
| F3.5 | `src/api/fault.ts` | `listFaultCases`, `getFaultCase`, `createFaultCase`, `updateFaultCase`, `deleteFaultCase` | `/fault-cases/*` |
| F3.6 | `src/api/websocket.ts` | WebSocket连接管理 | `/ws/robot/status` |

---

### Phase 4: 布局与基础组件 [P0]

| 任务ID | 文件 | 功能 |
|--------|-----|------|
| F4.1 | `src/components/Layout/AppLayout.tsx` | 整体布局 (Header + Sider + Content) |
| F4.2 | `src/components/Layout/Navbar.tsx` | 顶部导航栏 |
| F4.3 | `src/components/Layout/Sidebar.tsx` | 左侧导航菜单 |
| F4.4 | `src/components/common/Loading.tsx` | 全局加载状态 |
| F4.5 | `src/components/common/ErrorBoundary.tsx` | 错误边界 |
| F4.6 | `src/styles/index.css` | 全局样式 + CSS变量 |

---

### Phase 5: 核心页面 [P1]

| 任务ID | 文件 | 功能 |
|--------|-----|------|
| F5.1 | `src/pages/HomePage.tsx` | 首页仪表盘 |
| F5.2 | `src/pages/SOPListPage.tsx` | SOP列表页 |
| F5.3 | `src/pages/TaskExecutionPage.tsx` | Task执行页（核心） |
| F5.4 | `src/pages/MonitorPage.tsx` | 实时监控面板 |
| F5.5 | `src/pages/ReportPage.tsx` | 报告查看页 |

---

### Phase 6: 管理功能 [P2]

| 任务ID | 文件 | 功能 |
|--------|-----|------|
| F6.1 | `src/pages/admin/FaultManagePage.tsx` | 故障案例管理 |
| F6.2 | `src/pages/admin/SeedDataPage.tsx` | 种子数据说明页 |

---

## 3. 验证方案

### 自动化验证

| 验证项 | 命令 | 预期结果 |
|-------|------|---------|
| TypeScript编译 | `npm run build` | 无类型错误 |
| 开发服务器启动 | `npm run dev` | 成功启动，无报错 |
| ESLint检查 | `npm run lint` | 无严重错误 |

### 集成验证

| 验证项 | 步骤 |
|-------|------|
| API连通性 | 1. 启动后端 `cd r-mos-backend && python main.py`<br>2. 启动前端 `cd r-mos-frontend && npm run dev`<br>3. 访问 `/sops` 页面，确认SOP列表加载 |
| WebSocket连接 | 1. 访问 `/monitor` 页面<br>2. 检查控制台 "WebSocket connected" 日志<br>3. 确认遥测数据实时更新 |

### 手动验收（用户执行）

1. **SOP列表页**：能看到SOP列表，点击"开始训练"跳转正常
2. **Task执行页**：能逐步执行，状态实时更新
3. **报告页**：任务完成后能查看评分报告

---

## 4. 执行顺序建议

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
   ↓
  验证现有代码
   ↓
  补全缺失部分
   ↓
  与后端联调测试
```

---

## User Review Required

1. **确认技术选型**：是否同意使用上述技术栈？
2. **确认执行顺序**：是否从 Phase 1（验证现有代码）开始？
3. **验证方案**：是否有其他需要补充的测试场景？

