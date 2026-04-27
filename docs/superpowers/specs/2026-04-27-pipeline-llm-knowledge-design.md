# R-MOS 端到端 Pipeline + LLM + 知识库设计规格

> 日期: 2026-04-27
> 状态: APPROVED
> 目标: 打通 3 个精品故障案例的完整流程（监控→诊断→维保→报告），接入 DeepSeek/MiniMax LLM，搭建混合 RAG 知识库

## 1. 项目背景与目标

### 受众
- 客户/投资人演示
- 教师团队试用验证

### 核心要求
- Pipeline 必须是真实的（非硬编码），但允许 Mock LLM fallback 保证稳定性
- 3 个精品案例覆盖入门→中等→高级难度梯度
- 任何网络条件下都能完整走通流程

### 整体架构方案
**Pipeline-First**：先打通端到端骨架（用现有规则引擎），再逐步叠加 LLM 增强。

---

## 2. Pipeline 骨架

### 数据流

```
FaultScenario.inject(fault_type)
  → MockAdapter 修改 telemetry
  → WebSocket 5Hz 推送
  → 前端 MonitorPage 告警卡片
  → 用户点击「诊断」→ 跳转 AgentWorkbench
  → DiagnoserAgent.diagnose(telemetry, knowledge_context)
  → 返回 diagnosis + maintenance_plan
  → fault_type → SOP 映射（fault_sop_mapping 表）
  → 用户确认 → 跳转 SOPPlayer
  → 步骤执行 + 证据采集 → 后端持久化
  → 任务完成 → 自动触发 ReportGenerator
  → 生成评分报告 → ReportPage 展示
```

### 新增数据表

#### fault_sop_mapping
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| fault_type | VARCHAR | 故障类型编码 (E001_OVERHEAT 等) |
| sop_id | UUID | 关联 SOP |
| difficulty | ENUM | beginner / intermediate / advanced |
| priority | INT | 同一 fault_type 多 SOP 时的优先级 |

#### task_execution
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 关联任务 |
| student_id | UUID | 学生 |
| sop_id | UUID | 执行的 SOP |
| diagnosis_trace_id | VARCHAR | 诊断追踪 ID |
| status | ENUM | in_progress / completed / abandoned |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

#### task_step_result
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| execution_id | UUID | 关联 task_execution |
| step_id | INT | 步骤序号 |
| status | ENUM | completed / skipped / failed |
| duration_seconds | INT | 耗时 |
| evidence_type | VARCHAR | photo / numeric / checkbox |
| evidence_value | JSON | 证据内容 |
| is_compliant | BOOL | 是否合规 |

### 新增 API 端点

```
POST /api/v1/tasks/from-diagnosis
  Body: { diagnosis_trace_id, fault_type, student_id }
  Response: { task_id, sop_id, sop_name }

POST /api/v1/tasks/{task_id}/steps/{step_id}/complete
  Body: { evidence_type, evidence_value, duration_seconds }
  Response: { is_compliant, feedback }

POST /api/v1/tasks/{task_id}/complete
  Body: { step_results[], evidence_refs[] }
  Response: { report_id, score: {safety, procedure, precision, efficiency, tools} }
```

---

## 3. LLM 接入

### 新增 Provider

| 文件 | 说明 |
|------|------|
| `app/services/llm/deepseek_provider.py` | DeepSeek Chat API（OpenAI 兼容格式，复用 openai SDK） |
| `app/services/llm/minimax_provider.py` | MiniMax ChatCompletion Pro（HTTP 直调） |

### Router 注册

```python
providers = {
    "deepseek": DeepSeekProvider,
    "minimax": MiniMaxProvider,
    "mock": MockProvider,  # 保留作为 fallback
}
```

### 调用策略

| 场景 | 主模型 | 备用 | 兜底 |
|------|--------|------|------|
| 诊断推理 | DeepSeek | MiniMax | Mock（规则引擎结果包装） |
| SOP 教练 | MiniMax | DeepSeek | Mock（固定提示语） |
| 知识问答 | DeepSeek | MiniMax | Mock（返回种子文本） |

超时阈值：10 秒。主模型超时自动切换备用，备用也失败则走 Mock。

### Agent 接入方式

**DiagnoserAgent — 混合模式：**
```python
async def diagnose(self, telemetry, knowledge_context=None):
    # 1. 规则引擎先跑
    rule_result = self._rule_based_diagnose(telemetry)
    # 2. LLM 增强（失败不阻塞）
    llm_result = await self._llm_enhance(telemetry, rule_result, knowledge_context)
    # 3. 合并：LLM 补充推理 + 自然语言解释 + 知识引用
    return self._merge_results(rule_result, llm_result)
```

**CoachAgent — LLM 驱动 + 规则兜底：**
```python
async def get_hint(self, step_context):
    hint = await router.chat(model="deepseek-chat", messages=[...], timeout=5)
    if hint:
        return hint
    return self._template_hint(step_context)
```

### 配置项

```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
MINIMAX_API_KEY=xxx
MINIMAX_GROUP_ID=xxx
LLM_PRIMARY_PROVIDER=deepseek
LLM_FALLBACK_PROVIDER=minimax
LLM_TIMEOUT_SECONDS=10
LLM_ENABLE_MOCK_FALLBACK=true
```

### Trace 记录
所有 LLM 调用写入 audit_event 表，包含 provider、model、latency_ms、token_count、is_fallback 字段。前端 trace drawer 可查看。

---

## 4. 知识库

### 模型变更

**knowledge_document** 新增字段：
- `fault_tags: ARRAY[VARCHAR]` — 关联故障类型标签
- `sop_tags: ARRAY[VARCHAR]` — 关联 SOP 标签

**knowledge_chunk** 新增字段：
- `embedding: VECTOR(1536)` — pgvector 向量字段
- `tags: ARRAY[VARCHAR]` — 继承父文档标签

### 混合检索策略

```python
async def retrieve(self, query: str, fault_type: str = None) -> list[KnowledgeChunk]:
    results = []
    # 路径 1：标签精确匹配
    if fault_type:
        tag_results = await self._search_by_tag(fault_type, limit=5)
        results.extend(tag_results)
    # 路径 2：向量相似度搜索
    if len(results) < 5:
        vector_results = await self._search_by_embedding(
            query, limit=5 - len(results), exclude_ids=[r.id for r in results]
        )
        results.extend(vector_results)
    return results
```

### 向量方案
- **存储**：PostgreSQL + pgvector 扩展
- **Embedding**：优先 DeepSeek Embedding API；fallback 本地 sentence-transformers
- **维度**：1536
- **索引时机**：文档审批通过（APPROVED）时异步生成

### 种子数据

| 文档 | 故障标签 | 内容 |
|------|----------|------|
| 关节过热维修手册 | E001_OVERHEAT | 过热原因、降温操作、传感器校准 |
| 关节松动维修手册 | E005_LOOSE | 检测方法、扭矩标准、紧固流程 |
| 电压系统维修手册 | E003_VOLTAGE_DROP, E001_OVERHEAT | 电压排查、联动诊断树、安全断电 |
| 安全操作通用规范 | * | 通断电标准、防护装备、应急处理 |
| Atom-01 结构手册 | * | 6 关节参数、额定值、零件编号 |

共 5 份文档，约 15-25 个 chunk。通过 `scripts/seed_knowledge.py` 导入。

### 教师上传流程

```
上传 PDF/Word/TXT → 后端解析 → 切片(4000字符)
  → 存入 knowledge_document + chunk (status=PENDING)
  → 管理员审批 → APPROVED
  → 异步生成 embedding → 可被检索
```

新增端点：`POST /api/v1/knowledge/upload`

---

## 5. 三个精品故障案例

### 案例 1：E001 关节过热（入门）

**故事线**：腰部关节温度持续升高 → 过热告警 → 诊断定位 → 降温+校准 SOP → 验证恢复

| 阶段 | 行为 |
|------|------|
| 注入 | waist 温度 2°C/s 上升，75°C 触发告警 |
| 监控 | 关节卡片变红 + 告警 banner |
| 诊断 | 识别 E001 + LLM 解释 + 知识引用 |
| SOP | 4 步：停机断电→等待降温→检查风扇→重启验证 |
| 评分 | 安全 + 步骤规范 + 时间效率 |

### 案例 2：E005 关节松动（中等）

**故事线**：肘部位置偏差增大 → 精度告警 → 诊断松动 → 拆装校准 SOP → 扭矩验证

| 阶段 | 行为 |
|------|------|
| 注入 | elbow position_error 0.01→0.15 rad |
| 监控 | 精度指标异常 + 「位置偏差超限」 |
| 诊断 | 识别 E005 + LLM 分析 + 知识引用 |
| SOP | 6 步：断电→拆外壳→检查紧固件→扭矩紧固→间隙测量→校准 |
| 证据 | 步骤④扭矩照片，步骤⑤间隙数值 |
| 评分 | 工具使用 + 操作精度 + 安全 |

### 案例 3：E003+E001 电压+过热联动（高级）

**故事线**：电源电压跌落 → 电流补偿 → 多关节过热 → 复合诊断 → 系统级排查

| 阶段 | 行为 |
|------|------|
| 注入 | E003 voltage 24V→19V，2s 后联动 shoulder+elbow 过热 |
| 监控 | 电压告警 → 多关节过热级联 |
| 诊断 | 识别复合故障 + LLM 分析因果链 + 知识引用 |
| SOP | 8 步：全机断电→检查电源→测量电压→修复电源→验证电压→检查温度→冷却→全系统验证 |
| 难点 | 需判断根因是电压而非过热 |
| 评分 | 全五维度 |

### SOP 数据格式

```json
{
    "sop_id": "sop-e001-overheat",
    "name": "关节过热应急处理",
    "fault_type": "E001_OVERHEAT",
    "difficulty": "beginner",
    "estimated_minutes": 15,
    "steps": [
        {
            "step_id": 1,
            "title": "停机断电",
            "instruction": "按下急停按钮，确认电源指示灯熄灭",
            "required_evidence": "photo",
            "safety_warning": "确认周围无人员后操作",
            "pass_criteria": "电源指示灯全部熄灭",
            "max_duration_seconds": 60
        }
    ]
}
```

### fault_sop_mapping 种子

| fault_type | sop_id | difficulty |
|------------|--------|-----------|
| E001_OVERHEAT | sop-e001-overheat | beginner |
| E005_LOOSE | sop-e005-loose | intermediate |
| E003_VOLTAGE_DROP | sop-e003-e001-compound | advanced |

---

## 6. 前端交互

### MonitorPage

新增告警卡片组件：
- 显示故障类型、受影响关节、当前值 vs 阈值
- 「一键诊断」按钮 → 跳转 `/agent/workbench?fault_type=xxx&joints=xxx`
- 「忽略」按钮 → 关闭告警

### AgentWorkbench

诊断完成后新增区域：
- 显示推荐 SOP 名称和预估时间
- 「创建维保任务」按钮 → 调用 `POST /tasks/from-diagnosis` → 跳转 `/maintenance?task_id=xxx`
- 「上报教师」按钮 → 已有逻辑

### SOPPlayer

改动：
- 每步完成调用 `POST /tasks/{id}/steps/{step_id}/complete`
- 上报证据（照片/数值/勾选）
- 全部完成调用 `POST /tasks/{id}/complete`
- 自动跳转 ReportPage

### ReportPage

增强：
- 五维雷达图（安全/规范/精度/效率/工具）
- 步骤明细（每步耗时 + 合规状态）
- AI 点评（LLM 生成个性化反馈）
- 知识引用（引用来源文档片段）

### 路由
无新增路由。所有改动在现有页面内完成。

---

## 7. 稳定性与 Fallback

### 三层保护

```
Layer 1: LLM 主备切换
  DeepSeek 超时/报错 → 自动切 MiniMax

Layer 2: Mock 兜底
  两个 LLM 都失败 → MockProvider 按 fault_type 返回预写结果

Layer 3: 规则引擎保底
  DiagnoserAgent 规则结果始终先算
  LLM 仅增强（解释 + 知识引用）
  全挂 = 规则结果 + 模板文案
```

### 状态展示

```
GET /api/v1/llm/health
→ {
    "deepseek": {"status": "ok", "latency_ms": 320},
    "minimax": {"status": "ok", "latency_ms": 450},
    "mock": {"status": "always_available"},
    "active_provider": "deepseek"
  }
```

前端 AgentWorkbench 顶部 LLM 状态指示灯（绿/黄/灰），教师和管理员可见。

---

## 8. 技术依赖

| 依赖 | 用途 | 备注 |
|------|------|------|
| pgvector | PostgreSQL 向量扩展 | `CREATE EXTENSION vector` |
| openai SDK | DeepSeek API 调用 | 已有，换 base_url |
| httpx | MiniMax API 调用 | 已有 |
| sentence-transformers | 本地 embedding fallback | 可选，离线时用 |

---

## 9. 不在本次范围

- 多机器人支持（仅 Atom-01）
- 学生协作/组队
- 移动端适配
- 真实机器人适配器（继续用 MockAdapter）
- 知识库版本管理
- LLM fine-tuning
