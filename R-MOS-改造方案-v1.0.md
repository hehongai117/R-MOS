# R-MOS 智能体改造方案 v1.0
**目标能力：将物理世界的模糊信号映射为可执行维保决策**
> 生成日期：2026-03-08 | 执行主体：Claude Code（MiniMax M2.5）+ Codex（GPT-5.4）
> 事实基础：`2026-03-08-project-current-state-report.md`

---

## 零、改造总体定位

### 现状一句话定性
R-MOS 当前是"可运行的维保训练平台"，LLM 是工具性单次调用，数字孪生是 mock 数据+3D 可视化，两者之间**没有语义桥梁，没有推理闭环，没有验证回路**。

### 改造后目标状态
```
MockAdapter(5Hz遥测) 
    → TelemetryContextBuilder(语义摘要)
    → LLM多假设推理(置信度+因果链)
    → MaintenancePlanGenerator(分级方案+RAG)
    → SimulationExecutor(孪生验证闭环)
    → 可执行决策交付学员
```

### 改造原则
1. **零破坏性**：所有改造以新增文件为主，不重写已通过测试的模块
2. **最小接口**：每个新模块只依赖已有接口，不引入新的外部依赖
3. **可测试优先**：每个模块交付时必须附带单元测试，覆盖率不低于现有基线（74.63%）
4. **执行原子性**：每个 Task 可独立执行、独立验证，失败不影响其他 Task

---

## 一、改造任务总览

| Task ID | 名称 | 执行主体 | 依赖 | 预估工时 | 验收标准 |
|---------|------|---------|------|---------|---------|
| T-01 | pgvector 真实语义检索 | Codex | 无 | 半天 | `_semantic_search` 返回余弦相似度排序结果 |
| T-02 | TelemetryContextBuilder | Claude Code | 无 | 半天 | 单测：输入 STALL 遥测→输出含 anomalies/hints 的 dict |
| T-03 | PromptTemplateEngine 接入 Builder | Codex | T-02 | 2小时 | robot_state 字段替换为 Builder 输出 |
| T-04 | 多假设推理 Prompt + FaultDiagnosisEngine | Claude Code | T-02, T-03 | 1天 | 单测：mock LLM 返回→解析出3假设+置信度 |
| T-05 | MaintenancePlanGenerator | Claude Code | T-01, T-04 | 1天 | 单测：输入诊断结果→输出5步骤JSON方案 |
| T-06 | SimulationExecutor(孪生验证闭环) | Codex | T-05 | 1天 | 单测：方案执行前后 MockAdapter 状态差异可验证 |
| T-07 | OrchestratorV2 模块注册(diagnoser) | Codex | T-04, T-05, T-06 | 半天 | E2E：`/agent/execute` 返回真实诊断结果 |
| T-08 | WebSocket 协议统一 | Codex | 无 | 2小时 | `useRobotData.ts` 与 `useWebSocket.ts` 使用同一协议 |
| T-09 | TrainingMemoryWriter 实现 | Claude Code | 无 | 半天 | 对话摘要写入 DB，不再打印 "not implemented" |
| T-10 | 前端 DiagnosisPanel 组件 | Codex | T-07 | 1天 | 学员工作台可见故障推理结果+维保方案 |

---

## 二、详细任务说明

---

### T-01：pgvector 真实语义检索

**执行主体**：Codex
**目标文件**：`r-mos-backend/app/services/knowledge/hub.py`

#### 当前问题
```python
# app/services/knowledge/hub.py
# 实际生产环境应使用 pgvector 的向量相似度搜索
# 这里简化实现为从有 embedding 的记录中随机返回
```
语义召回是假实现，随机返回，导致所有依赖 RAG 的推理都缺乏真实知识支撑。

#### 改造目标
将 `_semantic_search()` 替换为真正的余弦相似度计算。

#### 执行步骤

**Step 1**：在 `alembic/` 添加迁移，为 `ai_knowledge_chunks` 表的 embedding 列升级为 pgvector 类型。

迁移文件路径：`r-mos-backend/alembic/versions/xxxx_add_pgvector_embedding.py`

```python
# 迁移内容
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE ai_knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector(1536)")
    op.execute("""
        UPDATE ai_knowledge_chunks 
        SET embedding_vec = embedding::text::vector 
        WHERE embedding IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_vec 
        ON ai_knowledge_chunks USING ivfflat (embedding_vec vector_cosine_ops)
    """)
```

**Step 2**：修改 `KnowledgeHub._semantic_search()` 方法：

```python
async def _semantic_search(
    self,
    query: str,
    limit: int = 5,
    filters: Optional[Dict] = None
) -> List[AIKnowledgeChunk]:
    """
    真实 pgvector 余弦相似度检索
    替换原有随机返回的简化实现
    """
    # 1. 生成查询向量
    query_embedding = await self._embedding_service.embed(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # 2. 构建 pgvector 相似度查询
    async with self._db_session() as session:
        sql = text("""
            SELECT *, 1 - (embedding_vec <=> :query_vec::vector) AS similarity
            FROM ai_knowledge_chunks
            WHERE embedding_vec IS NOT NULL
            ORDER BY embedding_vec <=> :query_vec::vector
            LIMIT :limit
        """)
        result = await session.execute(sql, {
            "query_vec": embedding_str,
            "limit": limit
        })
        rows = result.fetchall()
    
    return [AIKnowledgeChunk(**row._mapping) for row in rows]
```

**Step 3**：在 `requirements.txt` 添加 `pgvector>=0.2.0`。

#### 验收测试
文件：`r-mos-backend/tests/unit/test_knowledge_semantic_search.py`

```python
async def test_semantic_search_returns_ranked_results():
    """验证：语义检索按相似度降序返回，不是随机"""
    hub = KnowledgeHub(...)
    results = await hub.search("电机堵转处理方法", mode="semantic", limit=3)
    assert len(results) > 0
    # 验证有相似度字段
    assert all(hasattr(r, 'similarity') for r in results)
    # 验证相似度降序
    similarities = [r.similarity for r in results]
    assert similarities == sorted(similarities, reverse=True)
```

---

### T-02：TelemetryContextBuilder

**执行主体**：Claude Code
**新建文件**：`r-mos-backend/app/services/llm/telemetry_context_builder.py`

#### 设计目标
这是整条链路的"信号理解层"。将 MockAdapter 输出的原始数值（joints/sensors/active_faults）转化为 LLM 可直接推理的结构化语义摘要。

**核心原则**：大模型拿到的不应该是数字，而应该是"意义"。

#### 完整实现

```python
# r-mos-backend/app/services/llm/telemetry_context_builder.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnomalySignal:
    joint_name: str
    anomaly_type: str          # "stall" | "overheat" | "torque_drop" | "voltage_drop"
    severity: str              # "critical" | "warning" | "info"
    current_value: float
    threshold_value: float
    description: str


@dataclass
class TelemetryContext:
    """
    TelemetryContextBuilder 的输出结构。
    直接注入 PromptTemplateEngine.ContextBlock.robot_state。
    """
    status_summary: str                        # 一句话状态描述
    anomaly_signals: List[AnomalySignal]       # 检测到的异常信号列表
    active_fault_codes: List[str]              # 活跃故障码
    reasoning_hints: List[str]                 # 引导 LLM 推理方向的提示
    system_metrics: Dict[str, Any]             # 系统级指标摘要
    raw_snapshot: Dict[str, Any]               # 保留原始快照供备查


class TelemetryContextBuilder:
    """
    将原始遥测数据（TelemetryPayload）转化为 LLM 可推理的语义摘要。

    阈值来源：MockAdapter 故障注入参数（mock.py）
    E001_OVERHEAT: temperature_increase=30.0 → 基准+30 即为过热临界
    E002_STALL:    velocity_multiplier=0.0, position_frozen=True
    E003_VOLTAGE_DROP: battery_drain=50.0, torque_multiplier=0.5
    """

    # 阈值配置（与 mock.py 故障注入参数对齐）
    THRESHOLDS = {
        "temperature": {
            "warning": 60.0,
            "critical": 75.0,
            "unit": "°C"
        },
        "torque_ratio": {          # 相对额定值的比例
            "warning": 0.6,
            "critical": 0.4,
            "unit": "ratio"
        },
        "velocity_stall": {        # 速度归零判定阈值
            "threshold": 0.01,
            "unit": "rad/s"
        },
        "battery": {
            "warning": 30.0,
            "critical": 15.0,
            "unit": "%"
        },
        "current_draw": {
            "warning": 18.0,       # 正常约 12A，过载 > 18A
            "critical": 22.0,
            "unit": "A"
        }
    }

    def build_context(self, telemetry_payload: Dict[str, Any]) -> TelemetryContext:
        """
        主入口。接受 TelemetryPayload 的字典表示。

        Args:
            telemetry_payload: {
                "joints": [{"name": str, "temperature": float, "torque": float,
                            "velocity": float, "position": float}, ...],
                "sensors": {"battery": float, "cpu_temp": float, "current_draw": float},
                "active_faults": [{"code": str, "severity": str, "description": str}, ...]
            }

        Returns:
            TelemetryContext: 结构化语义摘要
        """
        joints = telemetry_payload.get("joints", [])
        sensors = telemetry_payload.get("sensors", {})
        active_faults = telemetry_payload.get("active_faults", [])

        anomalies = self._detect_anomalies(joints, sensors)
        hints = self._generate_reasoning_hints(anomalies, active_faults, sensors)
        summary = self._build_status_summary(anomalies, active_faults)

        return TelemetryContext(
            status_summary=summary,
            anomaly_signals=anomalies,
            active_fault_codes=[f["code"] for f in active_faults],
            reasoning_hints=hints,
            system_metrics={
                "battery_pct": sensors.get("battery", 0),
                "current_draw_A": sensors.get("current_draw", 0),
                "cpu_temp_C": sensors.get("cpu_temp", 0),
                "total_joints": len(joints),
                "anomalous_joints": len(set(a.joint_name for a in anomalies))
            },
            raw_snapshot=telemetry_payload
        )

    def _detect_anomalies(
        self,
        joints: List[Dict],
        sensors: Dict
    ) -> List[AnomalySignal]:
        anomalies = []

        for joint in joints:
            name = joint.get("name", "未知关节")
            temperature = joint.get("temperature", 0)
            torque = joint.get("torque", 1.0)
            velocity = joint.get("velocity", 0)

            # 堵转检测：速度归零 + 扭矩骤降（最高优先级）
            is_stalled = (
                abs(velocity) < self.THRESHOLDS["velocity_stall"]["threshold"]
                and torque < self.THRESHOLDS["torque_ratio"]["warning"]
            )
            if is_stalled:
                anomalies.append(AnomalySignal(
                    joint_name=name,
                    anomaly_type="stall",
                    severity="critical",
                    current_value=velocity,
                    threshold_value=self.THRESHOLDS["velocity_stall"]["threshold"],
                    description=f"{name}速度归零({velocity} rad/s)且扭矩骤降至额定值{torque*100:.0f}%，符合堵转特征"
                ))

            # 过热检测
            if temperature >= self.THRESHOLDS["temperature"]["critical"]:
                anomalies.append(AnomalySignal(
                    joint_name=name,
                    anomaly_type="overheat",
                    severity="critical",
                    current_value=temperature,
                    threshold_value=self.THRESHOLDS["temperature"]["critical"],
                    description=f"{name}温度{temperature}°C，超过临界阈值{self.THRESHOLDS['temperature']['critical']}°C"
                ))
            elif temperature >= self.THRESHOLDS["temperature"]["warning"]:
                anomalies.append(AnomalySignal(
                    joint_name=name,
                    anomaly_type="overheat",
                    severity="warning",
                    current_value=temperature,
                    threshold_value=self.THRESHOLDS["temperature"]["warning"],
                    description=f"{name}温度{temperature}°C，接近警戒阈值"
                ))

            # 扭矩单独异常（非堵转情况下）
            if not is_stalled and torque < self.THRESHOLDS["torque_ratio"]["critical"]:
                anomalies.append(AnomalySignal(
                    joint_name=name,
                    anomaly_type="torque_drop",
                    severity="warning",
                    current_value=torque,
                    threshold_value=self.THRESHOLDS["torque_ratio"]["critical"],
                    description=f"{name}扭矩输出仅为额定值{torque*100:.0f}%，存在驱动异常"
                ))

        # 系统级电流过载
        current = sensors.get("current_draw", 0)
        if current >= self.THRESHOLDS["current_draw"]["critical"]:
            anomalies.append(AnomalySignal(
                joint_name="系统",
                anomaly_type="overcurrent",
                severity="critical",
                current_value=current,
                threshold_value=self.THRESHOLDS["current_draw"]["critical"],
                description=f"系统电流{current}A，超过临界值{self.THRESHOLDS['current_draw']['critical']}A，存在过载风险"
            ))

        # 电池低电量
        battery = sensors.get("battery", 100)
        if battery <= self.THRESHOLDS["battery"]["critical"]:
            anomalies.append(AnomalySignal(
                joint_name="系统",
                anomaly_type="low_battery",
                severity="critical",
                current_value=battery,
                threshold_value=self.THRESHOLDS["battery"]["critical"],
                description=f"电池电量{battery}%，低于临界值，需立即充电或更换"
            ))

        return anomalies

    def _generate_reasoning_hints(
        self,
        anomalies: List[AnomalySignal],
        active_faults: List[Dict],
        sensors: Dict
    ) -> List[str]:
        hints = []

        # 多故障并发提示
        if len(active_faults) > 1:
            hints.append(f"检测到{len(active_faults)}个并发故障码，需评估故障间因果关系，避免孤立分析")

        # 堵转特征提示
        stall_anomalies = [a for a in anomalies if a.anomaly_type == "stall"]
        if stall_anomalies:
            joints_str = "、".join(a.joint_name for a in stall_anomalies)
            hints.append(f"{joints_str}出现速度归零+扭矩骤降组合特征，优先考虑机械卡阻或驱动器失效")

        # 电流-温度联动提示
        current = sensors.get("current_draw", 0)
        has_overheat = any(a.anomaly_type == "overheat" for a in anomalies)
        if current > self.THRESHOLDS["current_draw"]["warning"] and has_overheat:
            hints.append("电流过载与关节过热同时出现，两者可能存在因果关系：机械阻力增大→电流上升→热积累")

        # 无活跃故障码但有异常信号（隐性故障）
        if len(active_faults) == 0 and len(anomalies) > 0:
            hints.append("存在异常传感器信号但无活跃故障码，可能为早期预警或传感器误报，建议进一步确认")

        return hints

    def _build_status_summary(
        self,
        anomalies: List[AnomalySignal],
        active_faults: List[Dict]
    ) -> str:
        if not anomalies and not active_faults:
            return "机器人运行状态正常，各关节参数在安全范围内"

        critical_count = sum(1 for a in anomalies if a.severity == "critical")
        warning_count = sum(1 for a in anomalies if a.severity == "warning")

        parts = []
        if critical_count > 0:
            parts.append(f"{critical_count}个严重异常")
        if warning_count > 0:
            parts.append(f"{warning_count}个警告")
        if active_faults:
            fault_codes = [f["code"] for f in active_faults]
            parts.append(f"活跃故障码：{', '.join(fault_codes)}")

        return f"检测到{'+'.join(parts)}，需立即介入处理"

    def to_prompt_dict(self, context: TelemetryContext) -> Dict[str, Any]:
        """
        将 TelemetryContext 转化为适合注入 PromptTemplateEngine 的字典格式。
        替换原有的 json.dumps(robot_state) 原始注入。
        """
        return {
            "状态摘要": context.status_summary,
            "异常信号": [
                {
                    "部位": a.joint_name,
                    "类型": a.anomaly_type,
                    "严重程度": a.severity,
                    "描述": a.description
                }
                for a in context.anomaly_signals
            ],
            "活跃故障码": context.active_fault_codes,
            "推理提示": context.reasoning_hints,
            "系统指标": context.system_metrics
        }
```

#### 验收测试
文件：`r-mos-backend/tests/unit/test_telemetry_context_builder.py`

```python
import pytest
from app.services.llm.telemetry_context_builder import TelemetryContextBuilder

STALL_PAYLOAD = {
    "joints": [
        {"name": "腰部关节", "temperature": 68, "torque": 0.31, "velocity": 0.0, "position": 0.1},
        {"name": "左肩关节", "temperature": 42, "torque": 0.95, "velocity": 0.8, "position": 1.2},
    ],
    "sensors": {"battery": 84, "cpu_temp": 52, "current_draw": 24.7},
    "active_faults": [{"code": "E002_STALL", "severity": "critical", "description": "腰部关节电机堵转"}]
}

NORMAL_PAYLOAD = {
    "joints": [
        {"name": "左肩关节", "temperature": 42, "torque": 0.95, "velocity": 0.8, "position": 1.2},
    ],
    "sensors": {"battery": 87, "cpu_temp": 48, "current_draw": 12.4},
    "active_faults": []
}

def test_stall_detection():
    builder = TelemetryContextBuilder()
    ctx = builder.build_context(STALL_PAYLOAD)
    stall_anomalies = [a for a in ctx.anomaly_signals if a.anomaly_type == "stall"]
    assert len(stall_anomalies) == 1
    assert stall_anomalies[0].joint_name == "腰部关节"
    assert stall_anomalies[0].severity == "critical"

def test_normal_state_no_anomalies():
    builder = TelemetryContextBuilder()
    ctx = builder.build_context(NORMAL_PAYLOAD)
    assert len(ctx.anomaly_signals) == 0
    assert "正常" in ctx.status_summary

def test_reasoning_hints_generated_for_stall():
    builder = TelemetryContextBuilder()
    ctx = builder.build_context(STALL_PAYLOAD)
    assert len(ctx.reasoning_hints) > 0
    assert any("堵转" in h or "卡阻" in h for h in ctx.reasoning_hints)

def test_to_prompt_dict_structure():
    builder = TelemetryContextBuilder()
    ctx = builder.build_context(STALL_PAYLOAD)
    d = builder.to_prompt_dict(ctx)
    assert "状态摘要" in d
    assert "异常信号" in d
    assert "推理提示" in d
```

---

### T-03：PromptTemplateEngine 接入 TelemetryContextBuilder

**执行主体**：Codex
**修改文件**：`r-mos-backend/app/services/llm/prompts.py`

#### 当前问题
```python
# 当前实现：原始 JSON 直接注入
if self.robot_state:
    messages.append({
        "role": "system",
        "content": f"机器人状态: {json.dumps(self.robot_state)}"
    })
```
大模型接收到的是原始数字字典，无法直接推理"这意味着什么"。

#### 改造内容

在 `ContextBlock` 类中新增 `use_context_builder` 字段，并在 `build_messages()` 中按条件使用 Builder 输出：

```python
# 修改 ContextBlock dataclass
@dataclass
class ContextBlock:
    # 现有字段保持不变...
    robot_state: Optional[Dict] = None
    use_context_builder: bool = True   # 新增：是否启用 TelemetryContextBuilder

# 修改 build_messages 中的 robot_state 注入逻辑
if self.robot_state:
    if self.use_context_builder:
        from app.services.llm.telemetry_context_builder import TelemetryContextBuilder
        builder = TelemetryContextBuilder()
        ctx = builder.build_context(self.robot_state)
        prompt_dict = builder.to_prompt_dict(ctx)
        content = f"机器人状态分析：\n{json.dumps(prompt_dict, ensure_ascii=False, indent=2)}"
    else:
        # 保留原始注入方式作为 fallback
        content = f"机器人状态: {json.dumps(self.robot_state, ensure_ascii=False)}"
    
    messages.append({
        "role": "system",
        "content": content
    })
```

**注意**：`use_context_builder=True` 为默认值，现有所有调用方无需改动，自动升级。

#### 验收
在现有 `PromptTemplateEngine` 相关测试中补充一条：注入包含堵转数据的 `robot_state` 后，生成的 messages 中应包含 "堵转" 或 "stall" 关键字。

---

### T-04：FaultDiagnosisEngine（多假设推理）

**执行主体**：Claude Code
**新建文件**：`r-mos-backend/app/services/diagnosis/fault_diagnosis_engine.py`

#### 设计目标
替换 `IntentEngine` 的单次调用方式，实现：多假设并行输出、置信度排序、因果链构建、紧急级别枚举输出。

#### 输出数据结构

```python
# r-mos-backend/app/services/diagnosis/schemas.py

from dataclasses import dataclass, field
from typing import List, Literal
from enum import Enum

class RecommendedAction(str, Enum):
    IMMEDIATE_STOP = "immediate_stop"       # 立即停机
    LIMITED_OPERATION = "limited_operation" # 限速运行，计划维保
    MONITOR_OBSERVE = "monitor_observe"     # 持续监控，暂不干预
    SCHEDULED_MAINTENANCE = "scheduled_maintenance"  # 计划内维保

@dataclass
class FaultHypothesis:
    fault_type: str
    confidence: float          # 0.0 ~ 1.0
    evidence: List[str]        # 支撑该假设的信号证据列表
    causal_chain: str          # 故障因果链描述
    ruling_out_condition: str  # 什么情况下可排除此假设

@dataclass
class DiagnosisResult:
    primary_hypothesis: FaultHypothesis
    alternative_hypotheses: List[FaultHypothesis]
    recommended_action: RecommendedAction
    urgency_level: int         # 1~5，5为最紧急
    uncertainty_note: str      # 不确定性说明
    diagnosis_basis: str       # 本次诊断所依赖的信号摘要（溯源用）
    trace_id: str              # 与 OrchestratorV2 trace 体系对接
```

#### Prompt 设计

```python
# r-mos-backend/app/services/diagnosis/fault_diagnosis_engine.py

SYSTEM_PROMPT = """你是人形机器人维保专家系统。你的任务是对机器人异常信号进行多假设故障诊断。

诊断原则：
1. 必须提供2~3个故障假设，按置信度降序排列
2. 每个假设必须有具体的传感器数据作为证据支撑
3. 主假设必须包含完整的因果链（从物理现象到故障根因）
4. recommended_action 只能是以下四个值之一：
   - "immediate_stop"（立即停机）
   - "limited_operation"（限速运行）
   - "monitor_observe"（监控观察）
   - "scheduled_maintenance"（计划维保）
5. urgency_level 为1~5整数，5为最紧急
6. 必须注明在什么条件下推翻主假设

输出必须是合法的 JSON，不包含任何额外文字。"""

USER_PROMPT_TEMPLATE = """请基于以下机器人状态信息进行故障诊断：

{telemetry_context}

历史维保记录摘要（如有）：
{maintenance_history}

相关知识库检索结果：
{knowledge_context}

请严格按照以下 JSON 结构输出：
{{
  "primary_hypothesis": {{
    "fault_type": "故障类型名称",
    "confidence": 0.85,
    "evidence": ["证据1", "证据2", "证据3"],
    "causal_chain": "信号A异常 → 导致B → 最终引发C",
    "ruling_out_condition": "如果X发生则排除此假设"
  }},
  "alternative_hypotheses": [
    {{
      "fault_type": "备选故障类型",
      "confidence": 0.10,
      "evidence": ["证据"],
      "causal_chain": "因果链",
      "ruling_out_condition": "排除条件"
    }}
  ],
  "recommended_action": "immediate_stop",
  "urgency_level": 4,
  "uncertainty_note": "需要进一步确认的条件",
  "diagnosis_basis": "本次诊断基于的核心信号描述"
}}"""
```

#### FaultDiagnosisEngine 核心实现

```python
class FaultDiagnosisEngine:
    def __init__(self, llm_router, knowledge_hub, memory_hub):
        self._llm = llm_router
        self._knowledge = knowledge_hub
        self._memory = memory_hub
        self._builder = TelemetryContextBuilder()

    async def diagnose(
        self,
        telemetry_payload: Dict,
        session_id: str,
        user_id: str
    ) -> DiagnosisResult:
        # 1. 构建语义摘要
        context = self._builder.build_context(telemetry_payload)
        context_dict = self._builder.to_prompt_dict(context)

        # 2. 检索相关知识（使用 T-01 修复后的真实 RAG）
        fault_query = context.status_summary + " " + " ".join(context.active_fault_codes)
        knowledge_chunks = await self._knowledge.search(fault_query, limit=3)
        knowledge_text = "\n".join(c.content for c in knowledge_chunks) if knowledge_chunks else "暂无相关知识"

        # 3. 检索历史维保记录
        history = await self._memory.get_recent_maintenance_history(session_id, limit=3)
        history_text = self._format_history(history) if history else "暂无历史记录"

        # 4. 构建 Prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            telemetry_context=json.dumps(context_dict, ensure_ascii=False, indent=2),
            maintenance_history=history_text,
            knowledge_context=knowledge_text
        )

        # 5. 调用 LLM（通过 LLMRouter，支持切换 provider）
        response = await self._llm.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model="gpt-4",         # 诊断任务用 gpt-4，不用 gpt-3.5
            temperature=0.1,       # 低温度保证输出稳定性
            max_tokens=2000
        )

        # 6. 解析 LLM 输出
        return self._parse_response(response, context.status_summary)

    def _parse_response(self, raw_response: str, diagnosis_basis: str) -> DiagnosisResult:
        """解析 LLM JSON 输出，带容错处理"""
        try:
            # 清理可能的 markdown 代码块包裹
            clean = raw_response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"FaultDiagnosisEngine: LLM 输出解析失败: {e}\n原始输出: {raw_response}")
            return self._fallback_result(diagnosis_basis)

        primary = data["primary_hypothesis"]
        return DiagnosisResult(
            primary_hypothesis=FaultHypothesis(**primary),
            alternative_hypotheses=[FaultHypothesis(**h) for h in data.get("alternative_hypotheses", [])],
            recommended_action=RecommendedAction(data["recommended_action"]),
            urgency_level=int(data["urgency_level"]),
            uncertainty_note=data.get("uncertainty_note", ""),
            diagnosis_basis=diagnosis_basis,
            trace_id=str(uuid.uuid4())
        )

    def _fallback_result(self, basis: str) -> DiagnosisResult:
        """LLM 解析失败时的安全降级结果"""
        return DiagnosisResult(
            primary_hypothesis=FaultHypothesis(
                fault_type="诊断失败，需人工排查",
                confidence=0.0,
                evidence=["LLM输出解析异常"],
                causal_chain="N/A",
                ruling_out_condition="N/A"
            ),
            alternative_hypotheses=[],
            recommended_action=RecommendedAction.IMMEDIATE_STOP,
            urgency_level=5,
            uncertainty_note="系统推理失败，请联系教师",
            diagnosis_basis=basis,
            trace_id=str(uuid.uuid4())
        )
```

#### 验收测试
文件：`r-mos-backend/tests/unit/test_fault_diagnosis_engine.py`

```python
async def test_stall_diagnosis_primary_hypothesis():
    """mock LLM 返回 → 解析出正确结构"""
    mock_llm_response = json.dumps({
        "primary_hypothesis": {
            "fault_type": "电机堵转",
            "confidence": 0.88,
            "evidence": ["腰部关节速度归零", "扭矩骤降至31%"],
            "causal_chain": "机械卡阻 → 电流过载 → 热积累",
            "ruling_out_condition": "重启后速度恢复则排除"
        },
        "alternative_hypotheses": [],
        "recommended_action": "immediate_stop",
        "urgency_level": 4,
        "uncertainty_note": "需排查编码器信号",
        "diagnosis_basis": "腰部关节异常"
    })
    engine = FaultDiagnosisEngine(mock_llm(mock_llm_response), mock_knowledge(), mock_memory())
    result = await engine.diagnose(STALL_PAYLOAD, "session_001", "user_001")
    assert result.primary_hypothesis.confidence == 0.88
    assert result.recommended_action == RecommendedAction.IMMEDIATE_STOP
    assert result.urgency_level == 4

async def test_json_parse_failure_returns_fallback():
    """LLM 返回非法 JSON → 触发安全降级"""
    engine = FaultDiagnosisEngine(mock_llm("这不是JSON"), mock_knowledge(), mock_memory())
    result = await engine.diagnose(STALL_PAYLOAD, "session_001", "user_001")
    assert result.urgency_level == 5
    assert result.recommended_action == RecommendedAction.IMMEDIATE_STOP
```

---

### T-05：MaintenancePlanGenerator

**执行主体**：Claude Code
**新建文件**：`r-mos-backend/app/services/diagnosis/maintenance_plan_generator.py`

#### 设计目标
接受 `DiagnosisResult`，输出结构化的分级维保方案，含步骤序列、风险评级、降级路径。

#### 输出数据结构

```python
@dataclass
class MaintenanceStep:
    step_id: int
    action: str              # 操作名称（简短）
    detail: str              # 详细操作描述
    risk_level: str          # "低" | "中" | "高"
    estimated_duration: str  # 预估时间
    required_tools: List[str]
    safety_notes: List[str]

@dataclass
class MaintenancePlan:
    plan_id: str
    fault_type: str
    urgency_level: int
    steps: List[MaintenanceStep]
    fallback_instruction: str     # 降级处理说明
    estimated_total_time: str
    requires_supervisor: bool     # 是否需要教师确认后才能执行
```

#### Prompt 设计

```python
PLAN_SYSTEM_PROMPT = """你是机器人维保规程专家。基于故障诊断结果，生成标准化的维保操作方案。

方案要求：
1. 步骤数量：4~6步，不超过6步
2. 每步骤必须包含：操作名称、详细描述、风险等级（低/中/高）、预估时间
3. 步骤顺序必须符合安全操作规范：安全措施 → 故障隔离 → 根因处理 → 验证恢复
4. 必须包含降级处理说明（当正常步骤无法解决时如何升级处置）
5. urgency_level >= 4 时，requires_supervisor 必须为 true
6. 输出必须是合法 JSON，不包含额外文字"""

PLAN_USER_TEMPLATE = """故障诊断结果：
{diagnosis_json}

相关 SOP 知识：
{sop_knowledge}

请生成完整的维保操作方案（JSON格式）：
{{
  "plan_id": "MP-{timestamp}",
  "fault_type": "故障类型",
  "urgency_level": 4,
  "steps": [
    {{
      "step_id": 1,
      "action": "操作名称",
      "detail": "详细操作步骤描述",
      "risk_level": "低",
      "estimated_duration": "30秒",
      "required_tools": ["工具1"],
      "safety_notes": ["注意事项"]
    }}
  ],
  "fallback_instruction": "若步骤X出现异常Y，立即停止并上报",
  "estimated_total_time": "约20分钟",
  "requires_supervisor": true
}}"""
```

#### 核心实现（精简版）

```python
class MaintenancePlanGenerator:
    async def generate(self, diagnosis: DiagnosisResult) -> MaintenancePlan:
        # 1. 检索 SOP 知识（使用 T-01 修复后的真实 RAG）
        sop_query = f"{diagnosis.primary_hypothesis.fault_type} 维保规程 SOP"
        sop_chunks = await self._knowledge.search(sop_query, limit=5)
        sop_text = "\n".join(c.content for c in sop_chunks) if sop_chunks else "使用通用维保规程"

        # 2. 构建 Prompt
        user_prompt = PLAN_USER_TEMPLATE.format(
            diagnosis_json=json.dumps(asdict(diagnosis), ensure_ascii=False, indent=2),
            sop_knowledge=sop_text,
            timestamp=datetime.now().strftime("%Y%m%d-%H%M")
        )

        # 3. 调用 LLM
        response = await self._llm.chat(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model="gpt-4",
            temperature=0.1,
            max_tokens=3000
        )

        # 4. 解析并返回
        return self._parse_plan(response)
```

#### 验收测试
```python
async def test_plan_generation_from_stall_diagnosis():
    result = await generator.generate(mock_stall_diagnosis)
    assert len(result.steps) >= 4
    assert result.steps[0].risk_level in ["低", "中", "高"]
    assert result.requires_supervisor == True  # urgency=4
    assert result.fallback_instruction != ""

async def test_step_ordering_safety_first():
    """验证第一步必须是安全相关操作"""
    result = await generator.generate(mock_stall_diagnosis)
    first_step = result.steps[0].action
    safety_keywords = ["急停", "停机", "断电", "锁定", "LOTO"]
    assert any(kw in first_step for kw in safety_keywords)
```

---

### T-06：SimulationExecutor（孪生验证闭环）

**执行主体**：Codex
**新建文件**：`r-mos-backend/app/services/simulation/simulation_executor.py`

#### 当前缺失
LLM 输出的维保方案没有任何路径反向写回 MockAdapter，无法验证方案有效性。这是整个架构最重要的护城河。

#### 前置改造：MockAdapter 需新增接口

在 `r-mos-backend/app/adapters/mock.py` 的 `MockRobotAdapter` 类中新增：

```python
async def apply_maintenance_action(self, action_type: str, target_joint: Optional[str] = None) -> bool:
    """
    接受维保动作指令，改变仿真状态。
    用于 SimulationExecutor 的方案验证。

    action_type 枚举：
    - "clear_fault": 清除指定故障码
    - "emergency_stop": 触发急停状态
    - "resume_operation": 恢复运行（清除急停）
    - "reset_joint": 重置关节至初始状态
    """
    if action_type == "clear_fault":
        # 清除所有活跃故障
        self._active_faults.clear()
        # 重置被故障影响的参数
        self._fault_overrides = {}
        logger.info(f"[SimulationExecutor] 故障已清除，仿真状态重置")
        return True

    elif action_type == "emergency_stop":
        self._emergency_stopped = True
        # 将所有关节速度置零
        for joint_name in self._joint_states:
            self._joint_states[joint_name]["velocity"] = 0.0
        return True

    elif action_type == "resume_operation":
        self._emergency_stopped = False
        # 恢复正常仿真推进
        return True

    elif action_type == "reset_joint" and target_joint:
        if target_joint in self._joint_states:
            self._joint_states[target_joint] = self._get_default_joint_state(target_joint)
            return True

    return False
```

#### SimulationExecutor 核心实现

```python
# r-mos-backend/app/services/simulation/simulation_executor.py

@dataclass
class VerificationResult:
    success: bool
    plan_id: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    delta_summary: Dict[str, str]   # 每项指标的变化量，如 {"velocity": "0.0 → 0.31 rad/s"}
    verdict: str                    # 一句话结论
    failed_steps: List[int]         # 执行失败的步骤 ID


class SimulationExecutor:
    """
    在 MockAdapter 中预执行维保方案，验证方案有效性。
    这是 LLM 输出反向驱动数字孪生的核心模块。
    """

    # 维保动作 → MockAdapter 指令的映射
    ACTION_MAP = {
        "急停": "emergency_stop",
        "停机": "emergency_stop",
        "断电": "emergency_stop",
        "清除故障": "clear_fault",
        "复位": "reset_joint",
        "恢复运行": "resume_operation",
        "重启": "resume_operation",
    }

    async def execute_and_verify(
        self,
        plan: MaintenancePlan,
        adapter: MockRobotAdapter
    ) -> VerificationResult:
        # 1. 记录执行前快照
        before_joints = await adapter.get_joint_states()
        before_sensors = await adapter.get_sensor_data()
        before_faults = await adapter.get_active_faults()
        before_state = self._build_state_snapshot(before_joints, before_sensors, before_faults)

        failed_steps = []

        # 2. 按步骤执行维保动作
        for step in plan.steps:
            action_type = self._map_action(step.action)
            if action_type:
                success = await adapter.apply_maintenance_action(action_type)
                if not success:
                    failed_steps.append(step.step_id)
                    logger.warning(f"[SimulationExecutor] Step {step.step_id} 执行失败: {step.action}")
            # 模拟操作耗时（仿真加速，不实际等待）
            await asyncio.sleep(0.1)

        # 3. 等待仿真状态稳定
        await asyncio.sleep(0.5)

        # 4. 记录执行后快照
        after_joints = await adapter.get_joint_states()
        after_sensors = await adapter.get_sensor_data()
        after_faults = await adapter.get_active_faults()
        after_state = self._build_state_snapshot(after_joints, after_sensors, after_faults)

        # 5. 评估方案效果
        success = self._evaluate_success(before_state, after_state, plan)
        delta = self._compute_delta(before_state, after_state)

        return VerificationResult(
            success=success,
            plan_id=plan.plan_id,
            before_state=before_state,
            after_state=after_state,
            delta_summary=delta,
            verdict=self._build_verdict(success, delta, after_faults),
            failed_steps=failed_steps
        )

    def _map_action(self, action_text: str) -> Optional[str]:
        for keyword, action_type in self.ACTION_MAP.items():
            if keyword in action_text:
                return action_type
        return None

    def _evaluate_success(self, before: Dict, after: Dict, plan: MaintenancePlan) -> bool:
        """
        评估标准：
        1. 执行后活跃故障数 <= 执行前（故障被清除或减少）
        2. 紧急级别高的方案：执行后机器人不再处于堵转状态
        """
        before_faults = len(before.get("active_faults", []))
        after_faults = len(after.get("active_faults", []))

        # 故障数减少或清零视为成功
        if after_faults < before_faults:
            return True
        # 故障未增加 + 关键指标改善也视为成功
        if after_faults <= before_faults:
            # 检查是否有关节从堵转恢复
            for joint_name, after_joint in after.get("joints", {}).items():
                before_joint = before.get("joints", {}).get(joint_name, {})
                if (before_joint.get("velocity", 0) == 0.0 and
                        after_joint.get("velocity", 0) > 0.01):
                    return True
        return False
```

#### 验收测试
```python
async def test_stall_plan_verification_passes():
    """执行 E002_STALL 维保方案 → 故障清除 → 验证通过"""
    adapter = MockRobotAdapter()
    await adapter.inject_fault("E002_STALL")
    plan = mock_stall_plan()
    
    executor = SimulationExecutor()
    result = await executor.execute_and_verify(plan, adapter)
    
    assert result.success == True
    assert len(result.failed_steps) == 0
    # 执行后故障码清零
    after_faults = await adapter.get_active_faults()
    assert len(after_faults) == 0

async def test_verification_captures_delta():
    """验证 delta_summary 包含关键指标变化"""
    result = await executor.execute_and_verify(plan, adapter)
    assert "velocity" in result.delta_summary or "faults" in result.delta_summary
```

---

### T-07：OrchestratorV2 模块注册（diagnoser 真实实现）

**执行主体**：Codex
**修改文件**：`r-mos-backend/app/services/orchestrator_v2.py`

#### 当前问题
```python
self._module_registry.register("diagnoser", ..., self._default_module_handler, ...)
# _default_module_handler 只返回 {"message": "Module handler not implemented"}
```

#### 改造内容

将 `diagnoser` 模块的 handler 替换为真实实现：

```python
# 在 OrchestratorV2.__init__ 中注入依赖
def __init__(self, ..., fault_diagnosis_engine, maintenance_plan_generator, simulation_executor):
    self._diagnoser = fault_diagnosis_engine
    self._plan_generator = maintenance_plan_generator
    self._sim_executor = simulation_executor
    # ...现有初始化代码...

    # 注册真实 handler（替换占位）
    self._module_registry.register(
        "diagnoser",
        handler=self._diagnosis_handler,
        # ...其他注册参数保持不变...
    )

async def _diagnosis_handler(self, context: TaskContext) -> Dict:
    """
    diagnoser 模块真实实现。
    接受包含 telemetry_payload 的 context，返回完整诊断+方案+验证结果。
    """
    telemetry = context.metadata.get("telemetry_payload")
    if not telemetry:
        return {"status": "error", "message": "缺少遥测数据，无法诊断"}

    # 1. 故障诊断
    diagnosis = await self._diagnoser.diagnose(
        telemetry_payload=telemetry,
        session_id=context.session_id,
        user_id=context.user_id
    )

    # 2. 生成维保方案
    plan = await self._plan_generator.generate(diagnosis)

    # 3. 孪生仿真验证（使用当前 adapter）
    adapter = AdapterFactory.get_adapter()
    verification = await self._sim_executor.execute_and_verify(plan, adapter)

    return {
        "status": "ok",
        "diagnosis": asdict(diagnosis),
        "maintenance_plan": asdict(plan),
        "verification": asdict(verification),
        "trace_id": diagnosis.trace_id
    }
```

#### 对外 API 接口变化

在 `/api/v1/agent/execute` 的请求结构中，新增可选字段 `telemetry_payload`：

```python
class AgentRequestV2(BaseModel):
    user_id: str
    message: str
    intent_classification: Optional[str]
    context: Dict = {}
    telemetry_payload: Optional[Dict] = None  # 新增：当意图为诊断时传入
```

#### 验收（E2E）
```bash
# 测试：携带堵转遥测数据调用 /agent/execute
curl -X POST /api/v1/agent/execute \
  -H "Authorization: Bearer <token>" \
  -d '{
    "user_id": "1",
    "message": "机器人出现异常，请诊断",
    "intent_classification": "fault_diagnosis",
    "telemetry_payload": {STALL_PAYLOAD}
  }'
# 期望：响应包含 diagnosis.primary_hypothesis.fault_type，不再返回 "not implemented"
```

---

### T-08：WebSocket 协议统一

**执行主体**：Codex
**修改文件**：`r-mos-frontend/src/components/Viewer3D/hooks/useRobotData.ts`

#### 当前问题
- `useWebSocket.ts` 按 `{ type: "telemetry", payload: {...} }` 解析
- `useRobotData.ts` 按 `robot_status` 格式解析（旧协议残留）
- 导致 3D 视图无法同步接收最新遥测数据

#### 改造内容

将 `useRobotData.ts` 的协议解析统一到 `TelemetryMessage` 格式：

```typescript
// 修改前（旧协议）
if (data.type === 'robot_status') {
  setRobotData(data)
}

// 修改后（统一协议）
if (data.type === 'telemetry' && data.payload) {
  // 将 TelemetryPayload 映射到 3D 视图需要的格式
  setRobotData({
    joints: data.payload.joints,
    sensors: data.payload.sensors,
    active_faults: data.payload.active_faults,
    timestamp: data.timestamp
  })
}
```

#### 验收
前端构建无报错，`MonitorPage` 3D 视图与传感器卡片数据一致。

---

### T-09：TrainingMemoryWriter 实现

**执行主体**：Claude Code
**修改文件**：`r-mos-backend/app/services/memory/training_memory_writer.py`

#### 当前问题
```python
logger.info(f"[UF-11] Conversation summary write not implemented yet for submission {submission.submission_id}")
```
记忆闭环断裂，历史维保记录无法被 T-04 的 `FaultDiagnosisEngine` 检索利用。

#### 改造内容

实现 `write_conversation_summary()` 方法：

```python
async def write_conversation_summary(
    self,
    submission_id: str,
    session_id: str,
    conversation_history: List[Dict],
    diagnosis_result: Optional[DiagnosisResult] = None
) -> bool:
    """
    将训练会话对话历史生成摘要并写入 MemoryHub。
    为后续的 FaultDiagnosisEngine 提供历史维保记录检索。
    """
    # 1. 用 LLM 生成对话摘要（简短，约100字）
    summary_prompt = f"""请将以下维保训练对话总结为100字以内的摘要，
    重点记录：故障类型、处理步骤、结果、学员表现。
    对话历史：{json.dumps(conversation_history[-10:], ensure_ascii=False)}"""
    
    summary = await self._llm.chat(
        messages=[{"role": "user", "content": summary_prompt}],
        model="gpt-3.5-turbo",
        max_tokens=200,
        temperature=0.3
    )

    # 2. 写入 MemoryHub（短期记忆，后续可升级为长期记忆）
    memory_entry = {
        "submission_id": submission_id,
        "session_id": session_id,
        "summary": summary,
        "fault_type": diagnosis_result.primary_hypothesis.fault_type if diagnosis_result else "未知",
        "outcome": "completed",
        "created_at": datetime.utcnow().isoformat()
    }
    
    await self._memory_hub.store(
        key=f"maintenance_history:{session_id}:{submission_id}",
        value=memory_entry,
        ttl_hours=720  # 30天
    )
    
    logger.info(f"[UF-11] 对话摘要已写入 memory: submission={submission_id}")
    return True
```

---

### T-10：前端 DiagnosisPanel 组件

**执行主体**：Codex
**新建文件**：`r-mos-frontend/src/components/DiagnosisPanel/DiagnosisPanel.tsx`
**接入位置**：`SOPMaintenancePage.tsx` 和 `AgentWorkbenchPage.tsx`

#### 设计目标
将 T-07 的完整诊断结果（诊断+方案+验证）在学员工作台可视化展示。样式与现有 Industrial Precision Dark 风格一致。

#### 组件接口

```typescript
interface DiagnosisPanelProps {
  diagnosisResult: DiagnosisResult | null
  maintenancePlan: MaintenancePlan | null
  verificationResult: VerificationResult | null
  isLoading: boolean
  onConfirmExecution: () => void   // 学员确认执行方案
  onEscalateToTeacher: () => void  // 上报教师审核
}
```

#### 渲染结构

```
DiagnosisPanel
├── DiagnosisHypothesisCard     # 多假设列表 + 置信度条
├── CausalChainDisplay          # 因果链文本展示
├── MaintenancePlanStepList     # 步骤列表（可逐步展开）
├── VerificationResultBadge     # 孪生验证通过/失败状态
└── ActionButtons               # 确认执行 / 上报教师
```

#### 关键实现要点（给 Codex 的提示）

1. 置信度条使用 CSS transition 动画，加载时从0增长到实际值
2. `requires_supervisor: true` 时，"确认执行"按钮 disabled，只显示"上报教师"
3. 多假设按置信度排序，主假设用绿色边框突出，备选假设用灰色
4. 孪生验证通过显示绿色"✓ 仿真验证通过"，失败显示红色"⚠ 验证未通过"及原因
5. 组件接受 `isLoading` 状态，展示骨架屏（Skeleton）而非空白

---

## 三、执行顺序与依赖关系

```
阶段 A（并行，无依赖）：
  T-01 pgvector           ← Codex 执行
  T-02 TelemetryBuilder   ← Claude Code 执行
  T-08 WebSocket统一      ← Codex 执行
  T-09 MemoryWriter       ← Claude Code 执行

阶段 B（依赖 A 完成后）：
  T-03 PromptEngine接入   ← Codex 执行（依赖 T-02）
  T-04 DiagnosisEngine    ← Claude Code 执行（依赖 T-01, T-02）

阶段 C（依赖 B 完成后）：
  T-05 PlanGenerator      ← Claude Code 执行（依赖 T-01, T-04）
  T-06 SimulationExecutor ← Codex 执行（依赖 T-05，需改造 MockAdapter）

阶段 D（依赖 C 完成后）：
  T-07 OrchestratorV2     ← Codex 执行（依赖 T-04, T-05, T-06）

阶段 E（依赖 D 完成后）：
  T-10 DiagnosisPanel     ← Codex 执行（依赖 T-07 API 稳定）
```

---

## 四、测试验收标准

### 每个 Task 完成的门禁条件

1. **单元测试**：新增测试全部通过，不允许跳过（no skip）
2. **覆盖率**：改造后后端整体覆盖率不低于改造前（74.63%）
3. **回归测试**：`pytest tests/ -v` 全部通过（239个原有测试不得新增 failure）
4. **前端构建**：`npm run build` 无报错

### 完整链路集成验收（所有 Task 完成后）

执行以下 E2E 测试场景：

```
场景：学员训练中触发 E002_STALL

Step 1: 触发故障注入 → MockAdapter 注入 E002_STALL
Step 2: WebSocket 推送 → 前端监控页显示关节堵转状态（T-08 验证）
Step 3: 调用 /agent/execute（携带遥测数据）
Step 4: 后端处理链路：
        TelemetryContextBuilder → FaultDiagnosisEngine → 
        MaintenancePlanGenerator → SimulationExecutor → OrchestratorV2
Step 5: 前端 DiagnosisPanel 展示：
        - 主假设"电机堵转"，置信度 > 0.7
        - 维保方案 >= 4 步骤
        - 孪生验证结果：success=true
Step 6: 学员点击"上报教师审核"（因 requires_supervisor=true）

验收标准：全链路 < 8秒响应（不含 LLM 调用时间）
```

---

## 五、给执行主体的关键注意事项

### 给 Claude Code（MiniMax M2.5）

1. T-02、T-04、T-05、T-09 是新建文件任务，优先创建独立模块，不修改已有通过测试的代码
2. 所有新服务类必须支持依赖注入（构造函数传入 `llm_router`, `knowledge_hub` 等），不在类内部直接实例化
3. 所有 LLM 调用必须通过现有的 `LLMRouter`，不直接使用 `openai.ChatCompletion`
4. 异常处理：每个 LLM 调用都需要 try/except，失败时返回 fallback 结果，不允许裸抛异常到 API 层
5. 日志格式统一：`logger.info(f"[模块名] 操作描述: key={value}")`

### 给 Codex（GPT-5.4）

1. T-01 的 pgvector 迁移必须是幂等的（`IF NOT EXISTS`），不破坏现有数据
2. T-03 修改 `PromptTemplateEngine` 时，`use_context_builder=False` 的回退路径必须保留
3. T-06 改造 `MockRobotAdapter` 时，原有的故障注入逻辑（`inject_fault()`）不得破坏，新增 `apply_maintenance_action()` 方法
4. T-07 注册 diagnoser handler 时，通过 `_module_registry` 的标准接口注册，不硬编码在 `process_request()` 主流程中
5. T-08 修改 `useRobotData.ts` 时，保留原有的错误处理和重连逻辑，只修改消息解析部分
6. T-10 组件开发时，样式严格遵循现有 Ant Design 5.x 主题，不引入新的 UI 库

---

## 六、改造完成后的系统状态

改造完成后，R-MOS 的核心能力将从：

> "可运行的维保训练平台 + LLM 工具化单次调用"

升级为：

> "具备模糊信号→语义理解→多假设推理→方案生成→孪生验证完整闭环的数字孪生维保智能体"

这是从"可运行"到"可信"的关键跨越，也是整个系统最重要的差异化护城河。

---

*文档版本：v1.0 | 生成工具：Claude Sonnet 4.6 | 基于 R-MOS 项目现状报告 2026-03-08*
