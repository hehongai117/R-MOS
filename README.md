# R-MOS (Robot Maintenance Operating System)

机器人维护操作系统 - 一个用于机器人维护培训和监控的全栈应用程序。

## 项目概述

R-MOS 是一个专为机器人维护培训设计的综合性平台，提供标准操作流程（SOP）管理、任务执行跟踪、实时监控和评分系统。MVP 阶段使用模拟适配器进行机器人仿真。

### 核心功能

- **SOP 管理**: 创建、编辑、删除标准操作流程
- **任务执行**: 按步骤执行维护任务，支持暂停/恢复
- **实时监控**: WebSocket 实时推送机器人遥测数据（5Hz）
- **评分系统**: 四维度评估（专业性、合规性、效率、安全性）
- **故障案例库**: 管理常见故障案例及处理方案
- **3D 可视化**: 机器人关节状态可视化展示

## 技术栈

### 后端 (r-mos-backend)

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.115+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM（异步模式） |
| PostgreSQL | - | 数据库 |
| asyncpg | 0.30+ | PostgreSQL 异步驱动 |
| Pydantic | 2.9+ | 数据验证 |
| Alembic | 1.13+ | 数据库迁移 |
| WebSockets | 13.0+ | 实时通信 |

### 前端 (r-mos-frontend)

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI 框架 |
| TypeScript | 5.3+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Ant Design | 5.12+ | UI 组件库 |
| Zustand | 4.4+ | 状态管理 |
| React Router | 6.21+ | 路由 |
| Three.js + R3F | - | 3D 可视化 |
| Axios | 1.6+ | HTTP 客户端 |

## 项目结构

```
r-mos/
├── r-mos-backend/              # 后端服务
│   ├── app/
│   │   ├── api/v1/endpoints/   # API 路由处理器
│   │   ├── services/           # 业务逻辑层
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── adapters/           # 机器人适配器抽象层
│   │   │   ├── base.py         # 抽象适配器接口
│   │   │   ├── mock.py         # Mock 实现（MVP）
│   │   │   └── factory.py      # 适配器工厂
│   │   └── core/               # 配置、数据库、异常
│   ├── alembic/                # 数据库迁移
│   ├── scripts/                # 工具脚本（种子数据等）
│   ├── tests/                  # 测试用例
│   ├── main.py                 # 应用入口
│   └── requirements.txt        # Python 依赖
│
├── r-mos-frontend/             # 前端应用
│   ├── src/
│   │   ├── api/                # API 客户端（与后端对齐）
│   │   ├── components/         # React 组件
│   │   │   ├── Layout/         # 布局组件
│   │   │   ├── common/         # 通用组件
│   │   │   ├── Task/           # 任务相关组件
│   │   │   ├── Monitor/        # 监控组件
│   │   │   └── Viewer3D/       # 3D 可视化组件
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── pages/              # 页面组件
│   │   ├── store/              # Zustand 状态管理
│   │   ├── types/              # TypeScript 类型定义
│   │   └── styles/             # 全局样式
│   ├── package.json
│   └── vite.config.ts
│
├── CLAUDE.md                   # Claude Code 开发指南
├── mvp骨架文档-v2.3.md          # 架构设计文档
├── rmos拆包A_v2.3.md           # 拆包 A: Core 骨架
├── rmos拆包B_v2.3md.md         # 拆包 B: 业务模型与流程
├── rmos拆包C-v2.2.md           # 拆包 C: SOP 管理与种子数据
└── rmos拆包D_v1.2.md           # 拆包 D: 前端实现
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### 后端设置

```bash
cd r-mos-backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接

# 创建数据库
createdb rmos_dev

# 运行数据库迁移
alembic upgrade head

# 导入种子数据
python -m scripts.seed_data

# 启动开发服务器
python main.py
# 服务启动于 http://localhost:8000
```

### 前端设置

```bash
cd r-mos-frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env

# 启动开发服务器
npm run dev
# 服务启动于 http://localhost:3000
```

### 端口策略（Phase2 验收）

- 后端默认端口 `8000`；若 `8000` 出现 `EPERM`，切换到 `18000`
- 前端默认端口 `3000`；若出现 `EPERM`，切换到 `3100`
- 所有本机 HTTP 验证必须使用：`curl --noproxy 127.0.0.1,localhost ...`
- 验收时必须将后端/前端“实际使用端口”写入 `docs/testing/TEST_REPORT.md`

## API 路由规范

### HTTP REST API

所有 HTTP API 使用 `/api/v1` 前缀：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/sops` | GET | 获取 SOP 列表 |
| `/api/v1/sops/{id}` | GET | 获取 SOP 详情 |
| `/api/v1/sops` | POST | 创建 SOP |
| `/api/v1/sops/{id}` | DELETE | 删除 SOP |
| `/api/v1/tasks` | POST | 创建任务 |
| `/api/v1/tasks/{id}` | GET | 获取任务详情 |
| `/api/v1/tasks/{id}/start` | POST | 开始任务 |
| `/api/v1/tasks/{id}/step` | POST | 执行步骤 |
| `/api/v1/tasks/{id}/pause` | POST | 暂停任务 |
| `/api/v1/tasks/{id}/resume` | POST | 恢复任务 |
| `/api/v1/tasks/{id}/report` | GET | 获取任务报告 |
| `/api/v1/adapter/status` | GET | 获取适配器状态 |
| `/api/v1/fault-cases` | GET/POST | 故障案例 CRUD |
| `/docs` | GET | OpenAPI 文档 |

### WebSocket

WebSocket 端点不使用前缀：

| 端点 | 描述 |
|------|------|
| `/ws/robot/status` | 实时遥测数据（5Hz） |

## 评分系统

任务评分基于四个维度（各占 25%）：

| 维度 | 描述 |
|------|------|
| 专业性 (Professionalism) | 操作规范性 |
| 合规性 (Compliance) | 步骤遵循度 |
| 效率 (Efficiency) | 完成时效 |
| 安全性 (Safety) | 安全操作 |

**扣分规则**：
- 跳过步骤: -5 分
- 执行错误: -10 分
- 超时: -15 分

**目标覆盖率**: >80%

## 适配器模式

后端使用适配器模式进行机器人通信抽象，便于未来扩展：

```
┌─────────────────────────────────┐
│     BaseRobotAdapter (抽象)      │
├─────────────────────────────────┤
│ + connect()                     │
│ + disconnect()                  │
│ + get_telemetry()               │
│ + execute_command()             │
└─────────────────────────────────┘
          ▲
          │ 实现
    ┌─────┴─────┐
    │           │
┌───┴───┐  ┌────┴────┐
│ Mock  │  │ Future  │
│Adapter│  │Adapters │
└───────┘  └─────────┘
    ↓           ↓
  MVP      Gazebo/Real
```

## 开发命令

### 后端

```bash
# 运行测试
pytest tests/unit -v

# 运行测试（带覆盖率）
pytest --cov=app --cov-report=term-missing tests/unit

# 代码格式化
black app/

# 类型检查
mypy app/
```

### 前端

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint

# 预览生产构建
npm run preview
```

## 环境配置

### 后端 (.env)

```env
# 数据库连接
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rmos_dev

# 适配器类型
ROBOT_ADAPTER_TYPE=mock

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### 前端 (.env)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 开发状态

### 后端进度 (V2.3.1)

- [x] Core 骨架（拆包 A）
- [x] 业务模型与流程（拆包 B）
- [x] SOP 管理与种子数据（拆包 C）
- [x] 所有审计问题已修复

### 前端进度 (Phase 1-6)

- [x] 项目验证与补全
- [x] 类型定义完善（与后端 Schema 对齐）
- [x] API 层完善（5 个模块，23 个函数）
- [x] 布局与基础组件
- [x] 核心页面（首页、SOP、任务、监控、报告）
- [x] 管理功能（故障案例 CRUD、种子数据说明）

### 待优化项

- [ ] TaskExecutionPage 404 处理优化（P0）
- [ ] HomePage 错误处理增强（P1）
- [ ] 列表空状态自定义（P1）

## 文档索引

| 文档 | 描述 |
|------|------|
| `CLAUDE.md` | Claude Code 开发指南 |
| `mvp骨架文档-v2.3.md` | 整体架构设计 |
| `rmos拆包A_v2.3.md` | Core 骨架详细设计 |
| `rmos拆包B_v2.3md.md` | 业务模型与流程设计 |
| `rmos拆包C-v2.2.md` | SOP 管理与种子数据设计 |
| `rmos拆包D_v1.2.md` | 前端实现设计 |
| `r-mos-backend/AUDIT_REPORT.md` | 后端审计报告 |
| `r-mos-frontend/DEVELOPMENT_LOG.md` | 前端开发记录 |
| `r-mos-frontend/PHASE1_3_AUDIT_REPORT.md` | 前端审计报告 |

## 许可证

私有项目 - 保留所有权利

---

**版本**: 2.3.1
**最后更新**: 2026-01-06
