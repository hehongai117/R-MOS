# R-MOS 项目现状报告

> 生成时间：2026-03-08  
> 适用仓库：`/Users/xuhehong/Desktop/r-mos`  
> 梳理方法：静态代码阅读 + 仓库现有计划/测试/评审文档对照  
> 事实源优先级：`AGENTS.md` > `docs/plans/2026-03-05-review-test-cleanup-execution.md` > `R-MOS_Review_Test_Cleanup_Plan.md` > `docs/review/review-checklist.md` > `docs/testing/backend-test-report.md` > `docs/testing/TEST_REPORT.md` > `docs/testing/TEST_PLAN.md`

## 执行摘要

R-MOS 当前已经不是“纯概念 demo”，而是一个可运行的全栈维保训练平台：后端有完整 FastAPI 路由、训练会话、审批/审计、LLM 封装、知识分片和 WebSocket 遥测；前端有登录、训练工作台、Agent 工作台、SOP 维保页、监控页和基于 `three.js` 的 3D 交互界面。

但它也还不是“真正完成的数字孪生 + 大模型闭环系统”。当前数字孪生主数据源仍然是 `MockRobotAdapter` 的模拟数据；`gazebo` / `real` adapter 未实现。LLM 层虽然支持 `OpenAI / Anthropic / Ollama`，但核心调用大多仍硬编码为 OpenAI；RAG 也已具备表结构与检索入口，但语义检索仍是简化版，不是 pgvector 真正相似度搜索。

最准确的项目定位是：

1. 已实现：训练/教学/诊断/审批/审计/3D 视图/模拟遥测/基础 Agent 工作台。
2. 半实现：训练项目生成、知识检索、角色化 Agent 策略、记忆闭环、风险评估。
3. 未完成：真实数字孪生接入、稳定的 LLM-Agent loop、成熟 RAG、LLM 输出反向驱动仿真/机器人执行。

---

## 1. 项目结构

### 1.1 完整目录树说明

仓库已经存在一份完整目录快照文件：`PROJECT_DIRECTORY_FULL.txt`。  
该文件比在报告中内嵌全文更适合作为“完整目录树”事实源，因为仓库还包含 `.codex/skills/`、`robot/`、缓存、日志与归档材料，直接原样展开会非常长。

本报告在此基础上给出“业务相关目录树 + 模块职责映射”。

### 1.2 业务相关目录树

```text
r-mos/
├── r-mos-backend/
│   ├── app/
│   │   ├── adapters/          # 机器人/仿真适配层，当前以 mock 为主
│   │   ├── api/v1/            # HTTP/WebSocket 路由入口
│   │   ├── core/              # 配置、数据库、异常、日志、安全
│   │   ├── models/            # ORM 模型
│   │   ├── schemas/           # Pydantic 请求/响应结构
│   │   └── services/          # 业务核心：training/teaching/llm/knowledge/policy
│   ├── alembic/               # 数据迁移
│   ├── tests/
│   │   ├── unit/
│   │   ├── e2e/
│   │   ├── eval/
│   │   └── load/
│   ├── requirements.txt
│   └── main.py
├── r-mos-frontend/
│   ├── src/
│   │   ├── adjudication/      # 裁决引擎、状态机、评分、执行器
│   │   ├── api/               # Axios SDK 与业务 API 封装
│   │   ├── components/        # 公共组件、Agent、Viewer3D、训练组件
│   │   ├── hooks/             # WebSocket 与界面 hooks
│   │   ├── pages/             # 主业务页面
│   │   ├── store/             # Zustand 状态
│   │   ├── teaching/          # 教学域页面与状态
│   │   └── types/
│   ├── public/                # 3D 模型等静态资源
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── adr/                   # ADR
│   ├── design/                # 设计文档
│   ├── ops/                   # RUNBOOK / Codex 规则
│   ├── plans/                 # 执行计划
│   ├── review/                # 审查与缺口记录
│   ├── testing/               # 测试计划/报告/验收
│   └── development/           # 项目说明与本报告
├── docs-archive/              # 历史归档文档
├── robot/                     # 外部开源机器人资源层快照
├── scripts/                   # 模型转换/导出辅助脚本
├── logs/                      # 本地日志
├── PROJECT_DIRECTORY_FULL.txt # 完整目录树原始快照
└── DEVELOPMENT_LOG.md         # 开发记录总账
```

### 1.3 模块/文件职责说明

#### 顶层

- `README.md`
  - 仓库入口索引，只保留事实源入口，不承担完整产品说明。
- `PROJECT_MANUAL.md`
  - 较完整的历史“项目说明书”，能帮助理解平台定位，但其完整度高于当前代码落地，需要和代码事实交叉验证。
- `DEVELOPMENT_LOG.md`
  - 当前最重要的变更与验证证据归档。
- `PROJECT_DIRECTORY_FULL.txt`
  - 完整目录树原始快照。

#### 后端 `r-mos-backend/`

- `main.py`
  - 真实 FastAPI 启动入口，负责 lifespan、CORS、中间件、异常处理、路由注册。
- `app/api/v1/__init__.py`
  - 全部 v1 路由与 WebSocket 路由统一注册。
- `app/adapters/`
  - 抽象机器人接口、schema、工厂和 mock 适配器。
- `app/services/llm/`
  - LLM Router、PromptTemplateEngine、审计逻辑。
- `app/services/knowledge/`
  - embedding 与 KnowledgeHub 混合检索。
- `app/services/memory/`
  - MemoryHub、短期/长期记忆、训练记忆写入。
- `app/services/training/`
  - 训练项目生成、训练会话、提交、反馈。
- `app/services/identity/`
  - 登录后 session 初始化、角色化 Agent 配置、教师监控视图辅助。
- `app/services/sop/`
  - SOP 裁决增强、质量监控。
- `app/services/orchestrator_v2.py`
  - 新版 Agent 编排器，含 FSM、幂等、策略评估。
- `tests/`
  - 单测、端到端、评估、负载 smoke。

#### 前端 `r-mos-frontend/`

- `src/App.tsx`
  - 路由总入口，定义所有主页面。
- `src/api/client.ts`
  - Axios 单例、鉴权 token 注入、401 刷新处理。
- `src/api/agent-v2.ts`
  - Agent 工作台调用后端 `/agent/execute` 及 V2 辅助接口。
- `src/pages/TrainingWorkbenchPage.tsx`
  - 学员训练工作台。
- `src/pages/agent/AgentWorkbenchPage.tsx`
  - Agent 工作台，负责 prompt 提交、trace 查看、风险卡片显示。
- `src/pages/SOPMaintenancePage.tsx`
  - 维保主页面，承载 3D 模型、爆炸图、工具确认、裁决交互。
- `src/pages/MonitorPage.tsx`
  - 监控页，展示 WebSocket 遥测和 3D 机器人状态。
- `src/components/Viewer3D/`
  - 所有 3D 相关组件，含机器人 GLB、子零件 GLB、交互/爆炸/拆解动画。
- `src/adjudication/`
  - 前端裁决核心逻辑。
- `src/store/`
  - Auth、Workbench 等 Zustand 状态。

#### 文档与资源

- `docs/ops/RUNBOOK.md`
  - 可复现运行入口。
- `docs/testing/*.md`
  - 测试基线和验收证据。
- `docs/review/*.md`
  - 当前代码缺陷、覆盖率缺口和专项审查结果。
- `robot/`
  - 第三方机器人资源层，不直接参与当前前后端运行时。

---

## 2. 技术栈

### 2.1 后端

来自 `r-mos-backend/requirements.txt` 的主要依赖如下（当前是版本下界，不是锁定版本）：

| 类别 | 依赖 | 版本 |
|---|---|---|
| Web | `fastapi` | `>=0.115.0` |
| Server | `uvicorn[standard]` | `>=0.30.0` |
| ORM | `sqlalchemy[asyncio]` | `>=2.0.30` |
| PostgreSQL | `asyncpg` | `>=0.30.0` |
| SQLite | `aiosqlite` | `>=0.22.1` |
| Migration | `alembic` | `>=1.13.0` |
| Validation | `pydantic` | `>=2.9.0` |
| Settings | `pydantic-settings` | `>=2.5.0` |
| WebSocket | `websockets` | `>=13.0` |
| LLM SDK | `openai` | `>=1.0.0` |
| LLM SDK | `anthropic` | `>=0.18.0` |
| Cache/Queue 预留 | `redis` | `>=5.0.0` |
| Test | `pytest` | `>=8.0.0` |
| Test | `pytest-asyncio` | `>=0.24.0` |
| HTTP Test | `httpx` | `>=0.27.0` |

运行时版本也体现在 FastAPI 标题里：

```python
app = FastAPI(
    title="R-MOS Backend",
    version="2.2.0",
)
```

来源：`r-mos-backend/main.py`

### 2.2 前端

来自 `r-mos-frontend/package.json`：

| 类别 | 依赖 | 版本 |
|---|---|---|
| 框架 | `react` | `^18.2.0` |
| 框架 | `react-dom` | `^18.2.0` |
| 构建 | `vite` | `^5.0.10` |
| 语言 | `typescript` | `^5.3.3` |
| 路由 | `react-router-dom` | `^6.21.1` |
| HTTP | `axios` | `^1.6.2` |
| UI | `antd` | `^5.12.5` |
| 状态 | `zustand` | `^4.4.7` |
| 3D | `three` | `^0.160.0` |
| 3D React | `@react-three/fiber` | `^8.15.12` |
| 3D 工具 | `@react-three/drei` | `^9.122.0` |
| 动效 | `motion` | `^12.35.0` |
| 测试 | `vitest` | `^2.1.9` |
| 测试 | `@testing-library/react` | `^16.3.2` |

### 2.3 大模型调用方式

当前代码里 LLM 层通过统一 Router 封装，支持三种 provider：

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
```

```python
class OpenAIClient(BaseLLMClient): ...
class AnthropicClient(BaseLLMClient): ...
class OllamaClient(BaseLLMClient): ...
```

来源：`r-mos-backend/app/services/llm/router.py`

结论：

1. 支持 API 方式调用 OpenAI / Anthropic。
2. 支持本地 Ollama，通过 `OLLAMA_BASE_URL` 访问本地模型服务。
3. 但“当前主链路实际使用”多数仍写死为 OpenAI，例如：
   - `IntentEngine` 用 `gpt-3.5-turbo`
   - `VerdictEnhancer` 用 `gpt-3.5-turbo`
   - `TeachingChatEngine` 用 `gpt-3.5-turbo`
   - `ProjectGenerator` 用 `gpt-4`

### 2.4 数字孪生实现方式

当前“数字孪生”分成两层：

1. **前端表现层**
   - `three` + `@react-three/fiber` + `@react-three/drei`
   - 使用本地 GLB 模型、爆炸图、零件拆解、独立零件查看器。
2. **后端数据层**
   - 通过 Adapter 抽象统一输出机器人结构、关节状态、传感器状态、故障注入结果。
   - 当前默认只实现了 `MockRobotAdapter`。

关键代码：

```python
if adapter_type == "mock":
    cls._instance = MockRobotAdapter(...)
elif adapter_type == "gazebo":
    raise NotImplementedError("Gazebo Adapter 未实现")
elif adapter_type == "real":
    raise NotImplementedError("Real Adapter 未实现")
```

来源：`r-mos-backend/app/adapters/factory.py`

所以结论不是“Gazebo/Isaac 已经接进系统”，而是：

- 运行时孪生：当前主要依赖 **自研 mock 仿真 + 前端 three.js 可视化**
- 外部资源层：`robot/` 目录内含 ROS2 / Isaac Sim / Isaac Lab / 开源机器人资料，但未接入当前应用主链路

---

## 3. 核心数据流

### 3.1 遥测/数字孪生数据流

#### 数据来源

当前后端默认数据源是 `MockRobotAdapter`：

```python
self._simulation_time += 0.1 * self._simulation_speed
base_position = math.sin(self._simulation_time * 0.5) * 1.5
base_velocity = math.cos(self._simulation_time * 0.5) * 0.1
```

并通过故障注入改变温度、扭矩、位置噪声、电池等：

```python
"E001_OVERHEAT": {"temperature_increase": 30.0, "torque_multiplier": 0.7}
"E002_STALL": {"velocity_multiplier": 0.0, "position_frozen": True}
"E003_VOLTAGE_DROP": {"battery_drain": 50.0, "torque_multiplier": 0.5}
```

来源：`r-mos-backend/app/adapters/mock.py`

#### 流转链路

1. `AdapterFactory.get_adapter()` 创建/复用 mock adapter。
2. `websocket_manager._push_telemetry()` 周期读取：
   - `get_joint_states()`
   - `get_sensor_data()`
   - `get_active_faults()`
3. 组装为 `TelemetryMessage`：

```python
message = TelemetryMessage(
    type="telemetry",
    timestamp=datetime.utcnow().isoformat() + "Z",
    payload=TelemetryPayload(
        joints=joints,
        sensors=sensors,
        active_faults=active_faults
    )
)
```

来源：`r-mos-backend/app/services/websocket_manager.py`

4. 前端 `useWebSocket()` 连接 `/ws/robot/status` 接收 JSON：

```ts
const wsUrl = `${WS_BASE_URL}/ws/robot/status`
if (data.type === 'telemetry' && data.payload) {
  setTelemetryData(data.payload)
}
```

来源：`r-mos-frontend/src/hooks/useWebSocket.ts`

5. `MonitorPage` 取 `telemetryData` 映射到传感器卡片和 `RobotViewer`。

#### 输入输出格式

- 后端 WebSocket 输出：`TelemetryMessage`
  - `type`
  - `timestamp`
  - `payload.joints[]`
  - `payload.sensors`
  - `payload.active_faults[]`

- 前端消费后输出：
  - 文本数字卡片（电池、温度、故障数）
  - 结构化关节列表
  - 3D 模型高亮/状态显示

### 3.2 Agent/LLM 数据流

#### 数据来源

Agent 请求目前主要来自前端 Agent 工作台：

```ts
const request: AgentRequestV2 = {
  user_id: user?.user_id ? String(user.user_id) : 'anonymous',
  message: content,
  intent_classification: finalIntent,
  context: {},
}
```

来源：`r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`

#### 流转链路

1. 前端调用 `/api/v1/agent/execute`
2. 后端 `orchestrator_v2.process_request(...)`
3. 资源绑定解析
4. `policy_matrix.evaluate(...)`
5. 模块分发 `_dispatch_module(...)`
6. 返回统一响应：
   - `trace_id`
   - `message`
   - `policy_decision`
   - `evidence_refs`

#### 当前真实边界

虽然链路存在，但 `OrchestratorV2` 默认模块注册仍是占位：

```python
self._module_registry.register("coach", ..., self._default_module_handler, ...)
self._module_registry.register("diagnoser", ..., self._default_module_handler, ...)
```

```python
def _default_module_handler(self, context: TaskContext) -> Any:
    return {"status": "ok", "message": "Module handler not implemented"}
```

来源：`r-mos-backend/app/services/orchestrator_v2.py`

因此当前 Agent 工作台更接近“统一响应壳 + 策略/轨迹接口已接好”，不是成熟的多轮自治 Agent loop。

### 3.3 训练项目生成数据流

这是当前最接近“RAG + LLM”闭环的一条链：

1. 前端请求 `/training/projects/generate`
2. 后端 `ProjectGenerator.generate()` 先检索知识库
3. 再分析历史记录
4. 然后把知识上下文 + 历史上下文拼入 prompt
5. 用 `gpt-4` 生成 JSON 项目
6. API 以 `text/event-stream` SSE 方式分阶段返回状态

关键 prompt 片段：

```python
response = await llm_router.chat(
    messages=[{"role": "user", "content": prompt}],
    provider=LLMProvider.OPENAI,
    model="gpt-4",
    temperature=0.3,
    max_tokens=4000,
)
```

来源：`r-mos-backend/app/services/training/project_generator.py`

#### 最终输出形式

- 中间态：SSE 状态块
  - `retrieving_knowledge`
  - `analyzing_history`
  - `generating_project`
  - `completed`
- 最终态：结构化 JSON 项目配置

### 3.4 输出形态总览

| 场景 | 输入 | 输出 |
|---|---|---|
| 监控 | Mock 遥测 | 可视化 3D + 数值卡片 |
| Agent 工作台 | 文本 prompt | 文本响应 + 结构化策略决策 + trace |
| 训练项目生成 | 训练意图 + 知识检索 + 历史数据 | 结构化 JSON + SSE |
| 教学指导 | 用户文本 + 步骤上下文 | 文本指导 |
| 裁决增强 | L1 裁决 + robot_state + knowledge_context | JSON 解释 |

---

## 4. 已实现的功能模块

### 4.1 功能状态矩阵

| 模块 | 状态 | 依据 |
|---|---|---|
| 登录/注册/刷新/登出 | 基本完整 | 前后端路由齐全，`AuthContext` + `api/client.ts` + `auth` endpoint |
| RBAC/对象级访问控制 | 基本完整但有局部缺口 | 有 `require_permission`、404/403 语义和 deny audit，但 review 文档仍指出 teaching 局部归属校验不足 |
| 训练会话管理 | 基本完整 | `training.py` + `TrainingSession` 模型 + session/submission service |
| 训练项目生成 | 部分实现 | 已有 SSE、知识检索、历史分析、LLM 生成、fallback；但知识与记忆层仍简化 |
| 教学指导 | 部分实现 | `TeachingChatEngine` 存在，但主要是单次提示生成 |
| Agent 工作台 / Agent V2 | 部分实现 | 前后端接口、trace、策略决策存在；模块 handler 仍占位 |
| 审批队列 / 证据采集 | 部分实现 | 服务与 API 已有，但主要为内存态对象，不是完整持久化流程 |
| 知识库 / RAG | 部分实现 | `AIKnowledgeChunk` + `KnowledgeHub` + embedding 已有；语义检索仍简化 |
| 数字孪生监控 | 部分实现 | WebSocket + mock telemetry + 3D 视图已可运行 |
| 3D 维保交互 / 爆炸图 / 拆解演示 | 较完整 | `SOPMaintenancePage`、`Atom01Interactive`、`PartInspector`、`DisassemblyAnimation` |
| 真实机器人/Gazebo 接入 | 未实现 | Adapter 工厂中明确 `NotImplementedError` |

### 4.2 已验证能力边界

根据 `AGENTS.md` 当前项目状态快照与 `docs/testing/backend-test-report.md` / `docs/plans/2026-03-05-review-test-cleanup-execution.md`：

1. 后端基线：
   - `collected 239`
   - `236 passed, 3 skipped, 0 failed, 0 error`
2. 后端核心 14 服务覆盖率门禁：
   - `378 passed, 1 skipped, 0 failed`
   - 覆盖率 `74.63%`
3. 前端：
   - `npm test` 通过
   - `npm run build` 通过
4. E2E：
   - `pytest tests/e2e/ -v --tb=long` -> `16 passed, 0 failed`

这些结果说明：

- 平台主链路不是空壳，训练、权限、API、部分 Agent、知识接口与前端工作台已有较稳定回归。
- 但“验证通过”更多集中在 API 和服务层，不等于“高级能力全部成熟”。

---

## 5. Prompt 设计现状

### 5.1 当前系统 Prompt / Prompt 模板

#### 全局模板引擎

系统 Prompt 基础块来自 `PromptTemplateEngine`：

```python
role: str = "你是一个专业的机器人维保培训助手"
domain: str = "机器人维护与操作"
capabilities = ["提供维保操作指导", "诊断设备异常", "检索维保知识"]
```

来源：`r-mos-backend/app/services/llm/prompts.py`

它会把以下内容拼成 messages：

1. system block
2. task/step/robot_state context
3. knowledge chunks
4. output constraint
5. user message

#### 角色化附加 Prompt

`AgentPolicyFactory` 还会按角色补系统补充语句：

- 学生：
  - “你是一位维保培训导师。请引导学生思考，不要直接给出答案……”
- 教师：
  - “请直接给出完整的分析和参考答案……”
- 管理员：
  - “可以访问审计日志和系统配置。”

来源：`r-mos-backend/app/services/identity/agent_policy_factory.py`

#### 具体场景 Prompt

当前至少有以下几类独立 prompt：

1. `IntentEngine`
   - 让模型输出意图识别 JSON。
2. `VerdictEnhancer`
   - 让模型输出裁决解释 JSON。
3. `TeachingChatEngine`
   - 根据步骤和学员历史输出 100 字内指导。
4. `LLMRiskScorer`
   - 输出风险分 JSON。
5. `ProjectGenerator`
   - 输出完整训练项目 JSON。

### 5.2 大模型调用链路

当前主流调用方式是 **单次调用**，不是成熟多轮 Agent loop：

- `IntentEngine._llm_recognize()`：单次 `gpt-3.5-turbo`
- `VerdictEnhancer.explain()`：单次 `gpt-3.5-turbo`
- `TeachingChatEngine._generate_guidance()`：单次 `gpt-3.5-turbo`
- `ProjectGenerator._generate_project()`：单次 `gpt-4`
- `LLMRiskScorer._llm_score()`：单次 `gpt-3.5-turbo`

所谓 “Agent loop” 目前更多体现在：

1. 前端有 Agent 工作台
2. 后端有 `orchestrator_v2`
3. 有 trace / policy / approval / evidence 这些结构

但真正自治循环并未完成，因为 `OrchestratorV2` 默认模块 handler 还是占位。

### 5.3 是否有 RAG / 知识库

有，但仍是 **基础版**：

#### 已有部分

- 知识分片表：`AIKnowledgeChunk`
- embedding 生成：`text-embedding-3-small`
- KnowledgeHub：关键词 + 语义 + rerank + filter

关键代码：

```python
class AIKnowledgeChunk(Base):
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)
```

```python
class EmbeddingService:
    def __init__(self, model: str = "text-embedding-3-small"):
        self._client = AsyncOpenAI()
```

#### 当前限制

`KnowledgeHub._semantic_search()` 明确写明是“简化版”，不是 pgvector 真正相似度搜索：

```python
# 实际生产环境应使用 pgvector 的向量相似度搜索
# 这里简化实现为从有 embedding 的记录中随机返回
```

所以结论是：  
**当前有知识库结构、embedding、检索 API 和 prompt 注入能力，但还不是成熟 RAG。**

---

## 6. 已知问题与局限

### 6.1 当前最明显的缺陷

1. **数字孪生后端仍是 mock，不是真实仿真/真实设备**
   - `gazebo` / `real` adapter 未实现。
2. **RAG 语义检索是简化版**
   - 语义召回没有真正做向量距离检索。
3. **Agent V2 编排层未真正落地模块执行**
   - 默认 handler 只返回 `"Module handler not implemented"`。
4. **训练记忆闭环未完成**
   - 对话摘要写入与下次推荐预计算都直接记录 `not implemented yet`。

### 6.2 硬编码 / 临时方案

1. `ProjectGenerator` 当前主模型硬编码为 `gpt-4`。
2. `IntentEngine` / `VerdictEnhancer` / `TeachingChatEngine` / `LLMRiskScorer` 均硬编码走 OpenAI。
3. `SessionInitializer` 注释里写“欢迎 prompt + LLM 生成欢迎摘要”，但代码实际是规则拼接字符串，不是真调 LLM。
4. `ApprovalQueue`、`EvidenceCollector` 等多个服务是内存态单例，不是完整持久化实现。
5. `TrainingWorkbenchPage` 的步骤文案 `STEP_COPY` 和部分聊天提示仍是前端硬编码。

### 6.3 能跑但不稳定的地方

1. **WebSocket 数据协议存在双轨**
   - `useWebSocket.ts` 按 `TelemetryMessage(type=telemetry)` 解析。
   - `components/Viewer3D/hooks/useRobotData.ts` 却按 `robot_status` 格式解析。
   - 说明前端 3D 层存在旧协议残留。
2. **文档与代码漂移**
   - 项目说明书、计划文档里一些能力描述比实际代码成熟。
3. **教学/权限局部边界仍有 review 风险**
   - `docs/review/review-checklist.md` 仍指出 teaching 某些接口需要补 teacher/class 归属校验。
4. **知识上传与 ingest 还很浅**
   - `/agent/knowledge/upload` 当前只是收文件并立即写“completed/failed” job record，不是完整知识解析管道。

---

## 7. 数字孪生与大模型的接口

### 7.1 孪生数据如何传递给大模型

当前设计上支持、但运行时并不总是实际发生。

#### 支持的格式

`PromptTemplateEngine.ContextBlock` 明确支持 `robot_state` 注入：

```python
if self.robot_state:
    messages.append({
        "role": "system",
        "content": f"机器人状态: {json.dumps(self.robot_state)}"
    })
```

此外：

- `VerdictEnhancer.explain(..., robot_state=..., knowledge_context=...)`
- `TeachingChatEngine.TeachingContext.robot_state`
- `LLMRiskScorer.score(..., robot_state=...)`

也都支持把机器人状态以字典形式拼入 prompt。

#### 粒度

当前粒度不是“连续时间序列流喂给模型”，而是：

1. 某一时刻的 `robot_state` 快照
2. 某一步骤的上下文
3. 少量知识片段
4. 历史操作摘要

这更像 **step-level prompt context**，不是 streaming agent control。

### 7.2 频率

WebSocket 遥测频率是 `5Hz`，但这条频率只用于前端监控显示，不是每 200ms 都触发一次 LLM。

也就是说：

- 遥测频率：高频（5Hz）
- LLM 触发频率：低频、事件驱动（生成项目/求助/诊断/裁决解释时）

### 7.3 大模型输出如何反馈给孪生

当前基本没有“LLM 直接反向驱动数字孪生/机器人”的完整闭环。

目前输出主要反馈到：

1. 文本指导
2. JSON 项目配置
3. 裁决解释
4. 风险评分
5. Agent 工作台消息

没有看到稳定的代码路径把 LLM 输出反向写回：

- Adapter 控制命令
- 仿真引擎状态
- 3D 场景物理演化

所以当前接口关系更准确地说是：

**数字孪生/仿真数据 -> 提供上下文给 LLM**  
而不是  
**LLM -> 驱动数字孪生执行**

---

## 关键代码摘录

### A. LLM Router 支持三种 provider

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
```

来源：`r-mos-backend/app/services/llm/router.py`

### B. 数字孪生后端当前只接 mock

```python
if adapter_type == "mock":
    cls._instance = MockRobotAdapter(...)
elif adapter_type == "gazebo":
    raise NotImplementedError("Gazebo Adapter 未实现")
elif adapter_type == "real":
    raise NotImplementedError("Real Adapter 未实现")
```

来源：`r-mos-backend/app/adapters/factory.py`

### C. Mock 遥测由时间推进 + 故障注入生成

```python
base_position = math.sin(self._simulation_time * 0.5) * 1.5
base_velocity = math.cos(self._simulation_time * 0.5) * 0.1
```

来源：`r-mos-backend/app/adapters/mock.py`

### D. 当前 RAG 语义检索还是简化实现

```python
# 实际生产环境应使用 pgvector 的向量相似度搜索
# 这里简化实现为从有 embedding 的记录中随机返回
```

来源：`r-mos-backend/app/services/knowledge/hub.py`

### E. 训练记忆闭环未完成

```python
logger.info(
    f"[UF-11] Conversation summary write not implemented yet "
    f"for submission {submission.submission_id}"
)
```

来源：`r-mos-backend/app/services/memory/training_memory_writer.py`

### F. 监控页使用标准 telemetry 协议

```ts
if (data.type === 'telemetry' && data.payload) {
  setTelemetryData(data.payload)
}
```

来源：`r-mos-frontend/src/hooks/useWebSocket.ts`

---

## 最终判断

R-MOS 当前最贴切的状态是：

1. **平台级能力已成型**：账号、权限、训练、教学、审计、监控、3D 展示、训练项目、Agent 工作台都已有代码和测试证据。
2. **LLM 已接入但仍偏“工具化调用”**：多为单次 prompt，不是成熟的自治式 Agent loop。
3. **数字孪生当前偏“可视化仿真 + mock telemetry”**：前端表现较强，后端真实世界接入较弱。
4. **RAG/Memory/Approval/Policy 的骨架已经铺好**：但多处仍是简化实现、内存态实现或待完成 TODO 的“第二阶段能力”。

如果你接下来要做战略判断，这个项目不是从 0 到 1，而是正在从 **“可运行平台” 向 “可信的数字孪生维保智能体”** 过渡的中间态。
