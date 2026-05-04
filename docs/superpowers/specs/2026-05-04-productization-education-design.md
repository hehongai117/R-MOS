# R-MOS 院校教培产品化设计

> 日期: 2026-05-04
> 状态: Approved
> 目标: 将 R-MOS 从技术 Demo 转为可交付院校教培产品

## 背景与约束

### 目标市场
院校教培（职业院校、技工学校），非工业运维。

### 四项关键决策

1. **学习路径**: SOP 引导练习（初学）→ 场景驱动（进阶），渐进式解锁
2. **机器人连接**: 纯数字孪生优先，部分院校按需接实机
3. **AI 交互模式**: 嵌入式 AI 助手（初学阶段）→ 完整 Agent 工作台（进阶阶段）
4. **实施策略**: 方案 A 渐进式精简，不做大重构，快速达到可交付状态

---

## 第一部分：保留模块

### 核心引擎层（无需改动）

| 模块 | 说明 |
|------|------|
| 3D 数字孪生 (Viewer3D) | ATOM-01 机器人，364 GLB 资产，23 DOF |
| SOP 裁决执行引擎 | 7 种约束类型 + evidence 验证 |
| Mock Robot Adapter | 重命名为"仿真模式" |
| 五维技能画像 | Safety/Procedure/Precision/Efficiency/Tools |
| WebSocket 遥测 (5Hz) | 实时数据流 |
| JWT + RBAC 认证 | 教师/学生角色 |

### 训练系统（小幅调整）

| 模块 | 说明 |
|------|------|
| Training Session 状态机 | active→paused→submitted |
| Project Generator | AI 生成练习项目 |
| Submission + Feedback | 提交 + AI 反馈 |
| Skill Profile Service | 训练记忆 + 画像更新 |

### 教学管理

| 模块 | 说明 |
|------|------|
| 教师监控面板 | 实时查看学生状态 |
| 学生管理 | 班级、教师-学生关系 |
| Evidence 系统 | SHA-256 封存，操作追溯 |

---

## 第二部分：删除/精简模块

### 直接删除（从 UI 导航移除，代码保留不删）

| 模块 | 原因 |
|------|------|
| Incident Service (事件管理) | 工业运维概念，教学不需要 |
| Observation Service (观测记录) | 工业巡检用，evidence 系统替代 |
| External Assessment API | 院校内部闭环，无需外部对接 |
| Approval Queue (审批队列) | 工业安全审批流，教师直接监控即可 |
| Knowledge Governance (知识治理) | 过度设计，保留简单 CRUD |
| Policy Engine 复杂规则 | risk_level/policy_decision 等，教学不需要多级审批 |

### 降级为"进阶功能"

| 模块 | 处理方式 |
|------|----------|
| Agent Workbench 完整版 | 从主导航降为"进阶工具"，初学者不可见 |
| Fault Diagnosis 自主诊断 | 进阶阶段开放，初学阶段由 SOP 引导 |
| Multi-Agent 协调 | UI 入口隐藏，场景驱动阶段再开放 |

### 精简复杂度

| 模块 | 调整 |
|------|------|
| LLM Router | 保留 3 级 fallback，简化配置，默认 Mock 开箱即用 |
| Commands 表扩展字段 | DB 保留但 UI 不展示 |
| Intent Recognition | 简化为教学常见意图（练习/帮助/提交） |

---

## 第三部分：新增模块

### P0 — 首批交付（必须有）

#### 1. 嵌入式 AI 助手

- **位置**: SOP 练习页面右侧浮窗
- **功能**: 学生可随时提问，根据当前 SOP 步骤上下文回答
- **提示深度**: 由 `hint_level` 控制（1=只给方向，2=关键提示，3=详细步骤）
- **后端**: 复用 LLM Router，新增 `/api/v1/ai-assistant/chat` 端点
- **前端**: `<AIAssistantPanel>` 组件，悬浮在 SOPPlayer 右侧

#### 2. 学习进度仪表盘

- **学生端**: 已完成/进行中任务数、五维雷达图、历史趋势折线图
- **教师端**: 班级整体进度、落后学生预警、维度分布
- **数据源**: 复用 skill_profile + training_session 数据
- **路由**: `/dashboard`（替代当前默认首页）

#### 3. MyTasksPage 补全

- **内容**: 待完成任务列表、任务状态标签、快速进入练习按钮
- **数据源**: task_executions 表 + training_sessions
- **筛选**: 按状态（待开始/进行中/已完成）、按故障类型

#### 4. 生产配置

- **环境变量**: `DEBUG`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ROBOT_MODE`, `LLM_*`
- **文件**: `.env.example` + `.env.production` 模板
- **启动校验**: 生产模式下 SECRET_KEY 非空检查

#### 5. Docker 部署方案

- **docker-compose.yml**: frontend(nginx) + backend(uvicorn) + postgres
- **最低配置**: 4C8G 单机
- **数据卷**: GLB 资产、上传文件、数据库持久化
- **院校 IT 操作**: `docker compose up -d` 即可

### P1 — 第二批交付

#### 6. 场景库 (ScenarioPickerPage)

- 按难度/故障类型筛选练习场景
- 教师可自定义场景参数
- 与 fault_sop_mappings 表联动

#### 7. 学习路径编排

- 教师为班级配置学习顺序
- SOP 练习完成度 → 解锁场景驱动的条件规则
- 前端: 教师设置页 + 学生端进度条

#### 8. 练习报告导出

- PDF 格式，含操作记录、得分、AI 反馈、五维雷达图
- 学生/教师均可导出
- 后端生成（WeasyPrint 或 reportlab）

#### 9. 实机对接配置界面

- Robot Adapter 工厂模式已有
- 新增管理页面：选择"仿真模式/实机模式"
- 实机模式需配置 IP、端口、协议

### P2 — 客户反馈后决定

| 候选模块 | 触发条件 |
|----------|----------|
| 班级对比/排行 | 客户需要竞争机制 |
| 自定义 SOP 编辑器 | 客户需要自建 SOP |
| Agent Workbench 开放 | 进阶学生需求明确 |
| 多机器人型号支持 | 客户有不同型号机器人 |

---

## 第四部分：配置与工程化

### 配置治理

| 项目 | 当前 | 目标 |
|------|------|------|
| DEBUG | 硬编码 `True` | 环境变量，生产 `False` |
| 数据库 | SQLite | 开发 SQLite / 生产 PostgreSQL |
| CORS | `allow_origins=["*"]` | 白名单，环境变量 |
| Secret Key | 硬编码 | 环境变量，启动校验 |
| LLM Keys | 代码内 | `.env`，缺失自动降级 Mock |
| Robot Mode | 代码判断 | `ROBOT_MODE=simulation|physical` |

### 前端导航调整

| 调整 | 说明 |
|------|------|
| 默认首页 | → 学习进度仪表盘 |
| 导航分层 | "基础练习" / "进阶工具" 两级 |
| 空页面 | 补全或从导航移除 |

### 代码清理

| 项目 | 处理 |
|------|------|
| console.log | 移除或条件日志 |
| API 错误格式 | 统一 `{code, message, data}` |
| 未使用 import | 清理 TS 警告 |
| 中文错误提示 | 统一格式（预留 i18n） |

---

## 交付节奏

```
P0 完成 → 首批院校试用 → 收集反馈 → P1 补齐 → P2 按需迭代
```

## 技术栈不变

- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- Frontend: React + TypeScript + Vite + Zustand
- 3D: React Three Fiber + GLB
- AI: LLM Router (DeepSeek → MiniMax → Mock)
- Deploy: Docker Compose
