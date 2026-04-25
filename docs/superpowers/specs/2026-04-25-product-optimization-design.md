# R-MOS 产品化优化设计

> 从 Demo 到产品：维保教学培训平台

## 1. 产品定位

R-MOS 是一个面向机器人维保培训场景的教学平台。核心练习流程（发现故障 → AI诊断 → 3D引导维保 → 生成报告）是学生练习的载体，教学管理围绕这个流程展开。

## 2. 角色与核心场景

| 角色 | 核心场景 | 入口页 |
|------|---------|--------|
| 学员 | 接受任务/自主练习 → 监控发现故障 → AI诊断 → 3D维保执行 → 查看报告 → 技能成长 | 我的任务 |
| 教师 | 创建练习任务 → 监控学生进度 → 查看报告与评分 → 管理SOP与学员 | 班级监控台 |
| 管理员 | 系统概览 + 教师全部权限 + 用户管理 | 系统概览 |

## 3. 核心练习流程

```
任务入口（教师布置 / AI推荐场景）
  → 实时监控（发现异常关节）
    → AI诊断工作台（确认故障、获得诊断和SOP推荐）
      → 维保练习工作台（3D引导 + AI辅助 + 步骤执行 + 证据采集）
        → 维保报告（评分、证据链、改进建议）
          → 技能画像更新
```

两种练习入口：
- **教师布置任务**：教师选择故障场景 + SOP + 截止时间，学员在任务列表中领取
- **AI辅助自主练习**：学员从场景库选择，AI全程引导（诊断提示、操作指引、纠错反馈）

## 4. 导航结构

### 学员导航

```
练习中心
  ├─ 我的任务          (MyTasksPage - 新增)
  ├─ 自主练习          (ScenarioPickerPage - 新增)

维保流程
  ├─ 实时监控          (MonitorPage - 保留)
  ├─ AI 诊断工作台      (AgentWorkbenchPage - 保留)
  ├─ 维保练习工作台     (SOPMaintenancePage - 合并改造)

学习成长
  ├─ 维保报告          (ReportPage - 改造为列表+详情)
  ├─ 我的技能          (StudentSkillsPage - 保留)

工具
  ├─ 3D 展示           (Atom01DemoPage - 保留)
```

### 教师导航

```
教学管理
  ├─ 班级监控台        (TeacherMonitorPage - 保留)
  ├─ 作业管理          (TeachingAssignmentsPage - 扩展为练习任务发布)
  ├─ 学员档案          (TeacherStudentsPage - 保留)

SOP & 工具
  ├─ SOP 管理          (SOPListPage - 保留)
  ├─ 3D 展示           (保留)
  ├─ 实时监控          (保留)

记录
  ├─ 维保报告          (查看所有学员报告)
  ├─ 知识库            (KnowledgePage - 管理机器人资料/SOP文档/维保数据)
```

### 管理员导航

```
概览
  ├─ 系统概览          (AdminDashboardPage - 精简指标)

(+ 教师全部导航)

平台管理
  ├─ 用户管理          (复用学员档案扩展)
  ├─ 知识库            (保留)
```

## 5. 删除的页面（17个）

| 页面 | 文件 | 原因 |
|------|------|------|
| AI 助手 | AIChatPage.tsx | 与诊断工作台重复 |
| 信念追踪 | BeliefTrackerPage.tsx | 调试工具 |
| 诊断详情 | DiagnosisPage.tsx | 诊断在Agent工作台完成 |
| 证据查看 | EvidencePage.tsx | 证据内嵌到练习流程 |
| 事件列表 | IncidentListPage.tsx | 运维功能 |
| 评估状态 | AssessmentStatusPage.tsx | 底层状态展示 |
| 任务执行 | TaskExecutionPage.tsx | 被统一工作台取代 |
| 执行回放 | ReplayPage.tsx | Phase 2 |
| 维保草稿 | MaintenanceProjectDraftPage.tsx | 过于复杂 |
| SOP检查器 | SOPMaintenanceInspectorPage.tsx | 碎片化功能 |
| 训练工作台 | TrainingWorkbenchPage.tsx | 合并进维保工作台 |
| 验收看板 | AcceptanceDashboardPage.tsx | 开发工具 |
| 补偿方案 | CompensationPage.tsx | 运维功能 |
| Feature Flag | FeatureFlagPage.tsx | 开发工具 |
| LLM 指标 | LLMMetricsPage.tsx | 开发工具 |
| 故障管理 | FaultManagePage.tsx | 运维功能 |
| 数据管理 | SeedDataPage.tsx | 开发工具 |

## 6. 新增页面（2个）

| 页面 | 文件 | 说明 |
|------|------|------|
| 我的任务 | MyTasksPage.tsx | 学员任务列表：教师布置的 + 自主练习的，显示状态/得分/时间 |
| 场景选择 | ScenarioPickerPage.tsx | 故障场景库：按难度/类型筛选，AI推荐适合当前水平的场景 |

## 7. 核心改造点

### 7.1 去除 DEMO_MODE

**删除：**
- `VITE_DEMO_MODE` 环境变量和 `config/demoMode.ts`
- 所有 `if (DEMO_MODE)` 分支代码（MonitorPage、AgentWorkbenchPage、SOPPlayerAdjudicated、ReportPage、AppLayout）
- `DEMO_NAV` 导航配置
- 后端 `demo.py` 端点
- `mock_provider.py` 中的 hardcoded 响应
- sessionStorage 拼装报告逻辑
- 前端 `api/demo.ts`

**替代方案：** 教师创建练习任务时选择故障场景，后端调用 `adapter.inject_fault()` 注入故障，走真实 API。

### 7.2 合并工作台

将 TrainingWorkbenchPage 的能力整合进 SOPMaintenancePage：

| 来自训练工作台 | 整合方式 |
|--------------|---------|
| AI 对话辅助 | 维保工作台右侧加 AI 对话面板 |
| 证据上传 | 步骤执行时内嵌证据采集 |
| 工具确认 | 复用维保工作台已有的 ToolSelector |
| 步骤评分/verdict | 复用 SOPPlayerAdjudicated 的评判逻辑 |
| 会话管理（计时、暂停） | 新增会话层包装 |

合并后删除 TrainingWorkbenchPage 及其 Zustand store (workbenchStore)。

### 7.3 练习任务系统

- 教师通过「作业管理」发布练习任务（故障场景 + SOP + 截止时间）
- 学员在「我的任务」看到任务列表，点击开始 → 后端注入故障 → 跳转监控页
- 自主练习：学员从场景库选择 → AI推荐 → 同样流程
- 完成后自动生成报告、更新技能画像

### 7.4 报告页改造

- 去掉 sessionStorage mock 数据，全部从后端 API 获取
- 增加报告列表页（学员看自己的，教师看全部学员的）
- 报告详情保持现有结构（诊断摘要、前后对比、证据链、评分）

### 7.5 监控页改造

- 去掉"触发故障演示"按钮和引导 banner
- 故障由练习任务后端自动注入
- 学员进入监控页时看到已注入的故障，点击告警卡片进入诊断

### 7.6 后端精简

**删除的端点和服务：**
- `endpoints/demo.py` 全部端点
- `services/llm/mock_provider.py` hardcoded 响应
- `services/belief_state.py` + agent.py 中 belief 相关路由
- `services/compensation_planner.py` + compensation 相关路由
- `services/decision_recalculator.py` + replay 相关路由
- `services/acceptance_metrics.py` + metrics 相关路由
- `services/feature_flag.py` + feature flag 相关路由
- `services/system_monitor.py` 中的高级告警（保留基础健康检查）
- 对应的前端 admin 页面 API 客户端

**保留的核心后端：**
- Auth 认证全链路
- Task 任务管理
- SOP 管理
- Training 训练会话/评分/反馈
- Teaching 教学管理
- Agent 诊断（coach + diagnoser）
- Knowledge 知识库
- Evidence 证据采集
- Scoring 评分引擎
- Adapter 故障注入 + WebSocket 遥测
- LLM 路由（先用 mock provider 结构，后续接真实 LLM）

## 8. 统一模式下的数据流

```
教师创建任务
  → DB: practice_task (fault_scenario, sop_id, deadline)
  
学员开始任务
  → 后端: adapter.inject_fault(scenario.fault_code, scenario.joint)
  → 后端: 创建 training_session
  → 前端: 跳转 /monitor
  
学员在监控页发现故障
  → 点击告警卡片
  → 前端: 跳转 /agent/workbench?fault=X&joint=Y&session=S

AI诊断
  → 后端: diagnoser_agent.diagnose() (走 LLM 或 mock provider)
  → 返回诊断结果 + SOP推荐
  → 前端: 点击"开始维保"跳转 /maintenance?sop=X&session=S

维保执行
  → SOPPlayerAdjudicated 逐步执行
  → 每步采集证据、AI辅助
  → 完成后: 后端生成报告 + 更新技能画像
  → 前端: 跳转 /reports/:sessionId

报告查看
  → 后端 API 返回完整报告数据
  → 技能画像自动更新
```

## 9. 不在本次范围

以下功能暂不实现，后续按需加入：
- 真实 LLM 接入（当前用 mock provider 结构占位）
- 执行回放功能
- 多机器人型号支持
- 实时硬件对接（Gazebo / 真实机器人适配器）
- 高级审批流程
- 补偿/回滚机制
