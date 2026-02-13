# R-MOS Project Manual

> 文档状态：详细说明版（基于当前主目录代码）  
> 文档时间：2026-02-04  
> 适用范围：`/Users/xuhehong/Desktop/r-mos` 当前项目快照  
> 说明：本说明书聚焦“项目基础、可实现功能、已实现功能”，用于后续深入开发前的统一认知。

---

## 1. 项目定位

R-MOS（Robot Maintenance Operating System）是一个面向人形机器人维保训练、教学闭环、过程裁决与证据沉淀的全栈系统。

它有两层基础：

1. **软件平台基础（本仓库核心）**  
   通过 `FastAPI + React + PostgreSQL` 实现 SOP 执行、任务管理、过程事件、快照、评分、证据包、教学作业与诊断报告。

2. **开源人形机器人基础（robot 资源层）**  
   仓库内 `robot/` 目录提供 Atom01 开源机器人相关资产与上游聚合快照（硬件、部署、训练、描述模块），用于数字孪生可视化与后续真实硬件对接基础。

简言之：  
**本项目当前是“可运行的维保教学与裁决平台”，并且已经具备向“数字孪生维保智能体”升级的结构基础。**

---

## 2. 项目基础

### 2.1 全栈技术基础

**后端（`r-mos-backend/`）**
- 框架：`FastAPI`
- 数据访问：`SQLAlchemy asyncio`
- 数据库：`PostgreSQL`（迁移工具 `Alembic`）
- 数据校验：`Pydantic v2`
- 实时通信：`WebSocket`（`/ws/robot/status`）
- 测试：`pytest`（当前 unit 用例 46 条）

**前端（`r-mos-frontend/`）**
- 框架：`React + TypeScript + Vite`
- UI：`Ant Design`
- 状态管理：`Zustand`
- 3D：`@react-three/fiber` + `@react-three/drei` + `three`
- API 客户端：`axios`
- 裁决测试：自定义运行器 `npm test`（`scripts/run-adjudication-tests.mjs`）

### 2.2 开源人形机器人基础（robot 目录）

`robot/README.md` 与 `robot/README_cn.md` 明确了该资源层来自全开源人形机器人体系，核心模块包括：
- `Atom01_hardware`（机械/硬件）
- `atom01_deploy`（部署/驱动）
- `atom01_train`（训练）
- `atom01_description`（URDF/描述）

在本项目中的落地现状：
- 前端已有大量模型资产：`r-mos-frontend/public/models`（`364` 个 `.glb` 文件）。
- 前端维护页和演示页已可使用 3D 模型进行交互演示与裁决流程演示。
- 后端当前默认通过 `MockRobotAdapter` 提供机器人状态与故障注入，不直接依赖真实硬件。

### 2.3 架构原则基础

从 `docs/specs/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md` 和实际代码可归纳出以下原则：

- HTTP API 统一前缀：`/api/v1`
- WebSocket 固定路径：`/ws/robot/status`
- 任务执行遵循状态机与步骤顺序约束
- 裁决优先于动画与 UI 表现
- 证据包与诊断报告围绕“可追溯、可解释”组织

---

## 3. 总体架构（当前实现）

### 3.1 后端分层

目录：`r-mos-backend/app/`

- `api/v1/endpoints/`：路由层（当前 65 个 HTTP 路由 + 1 个 WebSocket 路由）
- `services/`：业务层（任务、评分、快照、证据、教学、诊断等）
- `models/`：ORM 模型（当前 21 张表）
- `schemas/`：请求/响应结构定义
- `adapters/`：机器人适配器抽象 + Mock 实现 + 工厂
- `core/`：配置、数据库会话、异常、迁移契约

### 3.2 前端分层

目录：`r-mos-frontend/src/`

- `api/`：前端 API 封装（与后端路由对齐）
- `pages/`：业务页面（SOP、监控、报告、故障管理等）
- `teaching/`：教学域页面与状态
- `adjudication/`：裁决引擎、约束图、评分引擎、执行器、测试
- `components/Viewer3D/`：机器人 3D 交互组件

### 3.3 数据模型域划分（21 张表）

| 领域 | 表 |
|---|---|
| SOP/执行 | `sops`, `sop_steps`, `tasks`, `events`, `snapshots`, `sop_audit_logs` |
| 故障 | `fault_cases` |
| 观测与事件 | `observations`, `incidents` |
| 证据 | `evidence_bundles`, `evidence_items`, `evidence_links` |
| 外部评估 | `assessment_providers`, `external_assessments`, `assessment_audit_events` |
| 教学 | `guidance_policies`, `classes`, `courses`, `enrollments`, `assignments`, `assignment_attempts` |

---

## 4. 已经实现的功能（As-Built）

## 4.1 后端 API 已实现能力

**当前路由总量**
- HTTP：`65`
- WebSocket：`1`
- 根路径：`GET /`（`r-mos-backend/main.py`）

### 4.1.1 健康检查与适配器管理

- `GET /api/v1/health`：服务健康检查（系统 + adapter）
- `GET /api/v1/adapter/info`：机器人基础信息
- `GET /api/v1/adapter/structure`：机器人结构
- `POST /api/v1/adapter/inject-fault`：故障注入
- `DELETE /api/v1/adapter/fault/{fault_code}`：清除故障
- `GET /api/v1/adapter/faults`：活动故障列表

### 4.1.2 SOP 与任务执行

- SOP：创建、查询、列表、删除影响评估、删除
- Task：创建、启动、执行步骤、暂停、恢复、查询、报告、事件查询

核心实现点：
- 步骤顺序校验
- 可跳过步骤校验（关键步骤禁止跳过）
- 执行事件写入
- 快照采集（失败降级处理）
- 自动评分
- 自动生成证据包并关联

### 4.1.3 教学闭环（完整链路）

- 策略：`guidance-policies` 增删查
- 班级/课程/报名：`classes`, `courses`, `enrollments`
- 作业：`assignments`
- 尝试：创建、状态流转、评分
- 证据摘要：`GET /attempts/{attempt_id}/evidence`
- 诊断报告：`GET /attempts/{attempt_id}/diagnosis`

当前状态机规则（教学尝试）：
- `in_progress -> completed -> graded`
- `in_progress -> abandoned`

### 4.1.4 事件、观测、证据、评估

- Incident：列表/创建/详情
- Observation：列表/创建/详情
- EvidenceBundle：列表/创建/详情
- Assessment：
  - Provider 管理
  - External Assessment 管理
  - 审计轨迹查询
  - 撤销/争议/恢复流程

### 4.1.5 WebSocket 实时遥测

- `WS /ws/robot/status`
- 后端 `ConnectionManager` 已实现：
  - 5Hz 推送
  - Ping/Pong 心跳
  - 连接健康状态追踪
  - 失效连接清理

## 4.2 业务流程已实现能力

### 4.2.1 训练执行闭环

`SOP -> Task -> StepExecution -> Event/Snapshot -> Score -> Report`

对应关键服务：
- `TaskService`
- `EventService`
- `SnapshotService`
- `ScoringService`

### 4.2.2 教学闭环

`Assignment -> Attempt -> TaskExecution -> EvidenceEngine -> DiagnosisService`

诊断规则当前是可解释规则集：
- 错误步骤优先（`R-DIAG-001`）
- 跳步（`R-DIAG-002`）
- 超时（`R-DIAG-003`）
- 正常（`R-DIAG-000`）

### 4.2.3 故障案例安全修复已落地

`r-mos-backend/app/schemas/fault.py` 已实现：
- `sanitize_input()`
- `FaultCaseBase` / `FaultCaseUpdate` 的 `field_validator`
- 对 `name`, `description`, `category` 进行输入清洗（去除 script/html）

## 4.3 前端页面与交互已实现能力

### 4.3.1 主路由页面（`r-mos-frontend/src/App.tsx`）

已实现主要页面：
- `/`
- `/sops`
- `/tasks/:taskId`
- `/reports`, `/reports/:taskId`
- `/monitor`
- `/incidents`
- `/evidence`
- `/assessments`
- `/teaching/assignments`
- `/teaching/attempts/:id`
- `/teaching/attempts/:id/evidence`
- `/teaching/attempts/:id/diagnosis`
- `/maintenance`
- `/atom01`
- `/admin/faults`
- `/admin/seed-data`

### 4.3.2 教学域 UI

已实现：
- 学生入口：开始尝试、执行步骤、查看证据
- 教师入口：查看提交、查看证据、查看诊断
- 尝试页包含 3D 引导视角与步骤引导

### 4.3.3 监控与实时展示

`MonitorPage + useWebSocket` 已实现：
- 连接状态显示
- 指数退避重连
- 数据过期检测
- 实时传感器与关节状态展示
- 3D 机器人联动显示

### 4.3.4 裁决系统（`src/adjudication/`）

已实现核心模块：
- 约束图与零件注册
- 裁决引擎（DecisionEngine）
- SOP 执行器（SOPExecutor）
- 评分引擎（含考试模式）
- 教学/考试/维保模式切换
- 致命失败锁死（`FAILED_FATAL`）逻辑

## 4.4 测试与验收现状（已归档）

依据 `docs-archive/TEST_REPORT.md`（2026-02-04 验收）：

- PASS：`38`
- FAIL：`0`
- BLOCKED：`3`
- 通过率：`92.7%`

关键信息：
- 教学核心闭环验收通过
- 裁决系统核心用例通过
- WebSocket 连接功能通过
- 已确认缺口：未实现鉴权（`DEF-SEC-001` 标记 KNOWN）

---

## 5. 可实现功能（基于当前架构的能力边界）

以下功能尚未完整落地，但从现有架构看可平滑实现：

### 5.1 用户系统与角色权限（高优先级）

可实现内容：
- 注册、登录、刷新、登出
- 用户资料与密码管理
- 角色权限（`admin/teacher/student`）
- 路由级 + 资源级权限控制

现状说明：
- 已有 `auth` / `user` schema 草稿
- 尚无完整 auth endpoint、JWT 中间层、权限依赖
- `app/models/user.py` 当前缺失（schema 依赖未闭环）

### 5.2 真实硬件对接（中高优先级）

可实现内容：
- `GazeboAdapter` / `RealAdapter` 接入
- 与 ROS2/设备网关通信
- 真实遥测替换 Mock 数据源

现状说明：
- `BaseRobotAdapter` 接口完整
- `AdapterFactory` 已预留 `gazebo`、`real` 分支
- 当前仅 `MockRobotAdapter` 实现

### 5.3 数字孪生维保智能体（中长期）

可实现内容：
- 故障诊断问答与 SOP 智能推荐
- 基于证据包/历史尝试的复盘助手
- 维保操作建议与风险预警
- 教学评语自动生成与个性化训练路径

现状说明：
- 当前系统已具备 AI 所需核心数据面（task/event/snapshot/evidence/diagnosis）
- 但尚未集成 LLM、RAG、向量检索、Agent 工作流

### 5.4 审计与合规增强

可实现内容：
- 将 `sop_audit_logs` 全量接入任务执行主链路
- 增加按 trace 追踪、审计回放查询 API

现状说明：
- `AuditLogService` 已存在
- 但尚未在主执行链路中全面调用

---

## 6. 当前边界与已知缺口

1. **鉴权/授权未落地**  
   当前 API 基本无身份鉴别；部分管理页面仅靠前端入口区分。

2. **真实硬件链路未打通**  
   当前数据主要来自 `MockRobotAdapter`。

3. **部分页面存在 mock fallback 机制**  
   `incidents/evidence/assessments` 页面在后端不可用时会使用本地 mock 数据。

4. **AI 能力尚未接入**  
   诊断目前为规则引擎，不是大模型推理。

5. **文档历史路径有漂移**  
   旧文档部分仍引用 `docs/testing/TEST_REPORT.md`，当前已归档到 `docs-archive/TEST_REPORT.md`。

---

## 7. 运行、调试与验证（当前可用）

## 7.1 本地启动

后端：
```bash
cd r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
uvicorn main:app --host 127.0.0.1 --port 8000
```

前端：
```bash
cd r-mos-frontend
npm install
npm run dev
```

## 7.2 快速可用性检查

```bash
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/health
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/sops
```

## 7.3 测试命令

后端单测：
```bash
r-mos-backend/.venv/bin/pytest r-mos-backend/tests/unit -v
```

前端裁决测试：
```bash
cd r-mos-frontend
npm test
```

---

## 8. 关键目录与文件地图

**核心入口**
- `README.md`
- `PROJECT_MANUAL.md`（本文件）

**后端核心**
- `r-mos-backend/main.py`
- `r-mos-backend/app/api/v1/endpoints/`
- `r-mos-backend/app/services/`
- `r-mos-backend/app/models/`
- `r-mos-backend/alembic/versions/`

**前端核心**
- `r-mos-frontend/src/App.tsx`
- `r-mos-frontend/src/pages/`
- `r-mos-frontend/src/teaching/`
- `r-mos-frontend/src/adjudication/`
- `r-mos-frontend/public/models/`

**规范与运行文档**
- `docs/specs/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md`
- `docs/ops/RUNBOOK.md`
- `docs/testing/TEST_PLAN.md`
- `docs/adr/ADR.md`

**历史归档**
- `docs-archive/TEST_REPORT.md`
- `docs-archive/TEST_EXECUTION_LOG.md`
- `docs-archive/DEVELOPMENT_LOG.md`

**机器人资源层**
- `robot/README.md`
- `robot/README_cn.md`
- `robot/modules/`

---

## 9. 下一阶段开发建议（从当前状态出发）

### 阶段 A：先补“用户与权限地基”
- 建立 `user/auth` 完整模型与 API
- 引入 JWT 与角色权限中间层
- 将管理页与教学关键写操作切换到权限控制

### 阶段 B：打通“真实机器人数据链路”
- 实现 `GazeboAdapter` 或 `RealAdapter`
- 建立 mock 与 real 的切换回归机制

### 阶段 C：升级为“数字孪生维保智能体”
- 先做辅助决策（建议）再做半自动执行
- 先对接 SOP + fault-cases + evidence + diagnosis
- 保留人工确认机制（human-in-the-loop）

---

## 10. 结语

当前 R-MOS 已不是单纯页面演示项目，而是具备以下三项关键资产的可演进系统：

1. **完整业务闭环资产**：从 SOP 到证据与诊断的执行链路；
2. **可扩展工程资产**：适配器抽象、教学域模型、裁决核心；
3. **开源机器人资产**：面向 Atom01 的 3D 与上游生态对接基础。

后续只要按“鉴权地基 -> 真实数据 -> AI 能力”的顺序推进，即可从“维保平台”稳态升级到“数字孪生维保智能体平台”。

