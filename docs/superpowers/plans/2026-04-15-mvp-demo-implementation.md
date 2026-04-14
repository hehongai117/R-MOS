# MVP Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 10-15 minute investor demo showing fault detection → AI diagnosis → 3D-guided maintenance → report, using 4 focused pages with mock LLM.

**Architecture:** Add DEMO_MODE env toggle to filter sidebar to 4 pages. Extend MockRobotAdapter with gradual fault simulation. Add mock LLM provider with SSE streaming. Wire existing AgentWorkbench and SOPMaintenance pages to demo-specific data and navigation flow.

**Tech Stack:** FastAPI (SSE via StreamingResponse), React/TypeScript, Zustand, React Three Fiber, Ant Design

**Spec:** `docs/superpowers/specs/2026-04-14-mvp-demo-design.md`

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|----------------|
| `app/services/llm/mock_provider.py` | Mock LLM: intent matching + pre-written diagnosis/SOP responses |
| `app/api/v1/endpoints/demo.py` | Demo-only endpoints: SSE chat stream, fault simulation trigger, fault reset |
| `app/services/simulation/fault_scenarios.py` | Gradual fault scenario definitions (temperature ramp curves) |
| `scripts/seed_demo_data.py` | Seed SOP + historical maintenance record for demo |

### Backend — Modified Files

| File | Change |
|------|--------|
| `app/adapters/mock.py` | Add gradual fault mode (temperature ramps over 30s instead of instant) |
| `app/main.py` or `main.py` | Register demo router |

### Frontend — New Files

| File | Responsibility |
|------|----------------|
| `src/config/demoMode.ts` | DEMO_MODE flag + demo nav config + demo SOP ID constant |
| `src/data/sopKneeBearing.ts` | Left knee bearing replacement SOP script (6 steps) for adjudication engine |
| `src/api/demo.ts` | API client for demo endpoints (fault trigger, SSE chat) |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `src/components/Layout/AppLayout.tsx` | Add DEMO_MODE nav config, use it when flag is set |
| `src/pages/MonitorPage.tsx` | Fix formatMetric, add temperature alert styling, add click-to-navigate on alert joints, add hidden fault trigger (double-click logo) |
| `src/pages/agent/AgentWorkbenchPage.tsx` | Read fault context from URL params, auto-populate first message, wire submit to SSE demo endpoint, show "开始维保" button after diagnosis |
| `src/pages/SOPMaintenancePage.tsx` | Read SOP selection from URL param, auto-select knee bearing SOP, record step timestamps |
| `src/pages/ReportPage.tsx` | Add demo report view with fault summary, before/after comparison, diagnosis citations, timeline |

---

## Task 1: Demo Mode Config + Navigation Filtering

**Files:**
- Create: `r-mos-frontend/src/config/demoMode.ts`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx:64-186`

- [ ] **Step 1: Create demo mode config file**

```typescript
// src/config/demoMode.ts
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

export const DEMO_SOP_ID = 'knee-bearing-replace'
export const DEMO_FAULT_TYPE = 'knee_overheat'
export const DEMO_JOINT = 'knee_left'
```

- [ ] **Step 2: Add DEMO nav config to AppLayout**

In `src/components/Layout/AppLayout.tsx`, after the existing `ADMIN_NAV` config (around line 186), add a new `DEMO_NAV` config:

```typescript
const DEMO_NAV: LayoutConfig = {
  badgeLabel: '演示',
  badgeVariant: 'default',
  navGroups: [
    {
      label: '监控中心',
      items: [
        { label: '实时监控', to: '/monitor', icon: Activity },
      ],
    },
    {
      label: '智能诊断',
      items: [
        { label: 'AI 诊断工作台', to: '/agent/workbench', icon: Bot },
      ],
    },
    {
      label: '维保执行',
      items: [
        { label: '维保工作台', to: '/maintenance', icon: Wrench },
        { label: '维保报告', to: '/reports', icon: FileText },
      ],
    },
  ],
}
```

Ensure `Activity`, `Bot`, `Wrench`, `FileText` icons are imported from `lucide-react` (check existing imports, add missing ones).

- [ ] **Step 3: Wire DEMO_MODE into layout selection**

In the `LAYOUT_CONFIG` map (around line 188-192), change the lookup logic:

```typescript
import { DEMO_MODE } from '@/config/demoMode'

// Replace the existing LAYOUT_CONFIG usage in RoleLayoutShell (around line 270):
// Before: const config = LAYOUT_CONFIG[role]
// After:
const config = DEMO_MODE ? DEMO_NAV : LAYOUT_CONFIG[role]
```

- [ ] **Step 4: Add .env.demo file for easy toggle**

Create `r-mos-frontend/.env.demo`:
```
VITE_DEMO_MODE=true
```

- [ ] **Step 5: Verify navigation filtering**

Run: `cd r-mos-frontend && VITE_DEMO_MODE=true npm run dev`

Open browser, login as admin. Sidebar should show only 4 items: 实时监控, AI 诊断工作台, 维保工作台, 维保报告.

- [ ] **Step 6: Commit**

```bash
git add r-mos-frontend/src/config/demoMode.ts r-mos-frontend/src/components/Layout/AppLayout.tsx r-mos-frontend/.env.demo
git commit -m "feat: add DEMO_MODE navigation filtering for investor demo"
```

---

## Task 2: Fix MonitorPage Floating Point + Add Temperature Alert Styling

**Files:**
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx:69-74` (formatMetric)
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx:169-199` (MonitorJointRow)
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx:336-342` (battery display)

- [ ] **Step 1: Fix formatMetric floating point precision**

In `src/pages/MonitorPage.tsx`, replace the `formatMetric` function (lines 69-74):

```typescript
function formatMetric(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--'
  }
  const multiplier = 10 ** digits
  const rounded = Math.round(value * multiplier) / multiplier
  return rounded.toFixed(digits)
}
```

- [ ] **Step 2: Fix battery display to use formatMetric**

Find the battery MetricCard (around line 336). Change `value={batteryLevel ?? '--'}` to:

```typescript
value={batteryLevel !== null && batteryLevel !== undefined ? formatMetric(batteryLevel, 1) : '--'}
```

- [ ] **Step 3: Add temperature threshold alert styling to MonitorJointRow**

In the `MonitorJointRow` component (around lines 169-199), add temperature-based alert styling. Find the temperature `DataRow` (around line 196) and replace it:

```typescript
const TEMP_WARN = 50
const TEMP_DANGER = 55

// Inside MonitorJointRow, before the return:
const tempValue = joint.temperature ?? 0
const tempTone = tempValue >= TEMP_DANGER ? 'text-red-400' : tempValue >= TEMP_WARN ? 'text-amber-400' : ''

// Replace the temperature DataRow:
<DataRow
  label="温度"
  value={formatMetric(joint.temperature, 1)}
  unit="°C"
  className={tempTone}
/>
```

Also update the `DataRow` component (around line 155-167) to accept an optional `className` prop and apply it to the value span:

```typescript
function DataRow({ label, value, unit, className }: { label: string; value: string; unit: string; className?: string }) {
  return (
    <div className="flex items-baseline justify-between rounded-lg bg-bg-base/60 px-2.5 py-1.5">
      <span className="text-[11px] text-text-muted">{label}</span>
      <span className={cn('text-data text-sm tabular-nums text-text-secondary', className)}>
        {value}
        <span className="ml-0.5 text-[10px] text-text-muted">{unit}</span>
      </span>
    </div>
  )
}
```

- [ ] **Step 4: Add card-level alert border for overheating joints**

In `MonitorJointRow`, update the card border logic (around line 175) to also highlight temperature alerts:

```typescript
const isError = !!joint.error_code
const isTempAlert = (joint.temperature ?? 0) >= TEMP_DANGER

// Replace the className logic on the outer div:
<div className={cn(
  'rounded-xl border p-3',
  isError
    ? 'border-danger/30 bg-danger/5'
    : isTempAlert
      ? 'border-amber-500/30 bg-amber-500/5 animate-pulse'
      : 'border-border-subtle bg-bg-elevated/40',
)}>
```

- [ ] **Step 5: Verify fixes**

Run: `cd r-mos-frontend && npm run dev`

Check MonitorPage:
1. Battery should display as "59.9" not "59.93999999999774"
2. Joint temperature values should be properly rounded
3. If any joint temperature >= 55°C, its card should have amber pulsing border

- [ ] **Step 6: Commit**

```bash
git add r-mos-frontend/src/pages/MonitorPage.tsx
git commit -m "fix: floating point precision in monitor metrics + temperature alert styling"
```

---

## Task 3: Gradual Fault Simulation in MockRobotAdapter

**Files:**
- Create: `r-mos-backend/app/services/simulation/fault_scenarios.py`
- Modify: `r-mos-backend/app/adapters/mock.py`

- [ ] **Step 1: Create fault scenarios module**

Create `app/services/simulation/__init__.py` (empty) and `app/services/simulation/fault_scenarios.py`:

```python
"""Gradual fault scenario definitions for demo mode."""
import time
from dataclasses import dataclass, field


@dataclass
class GradualFault:
    """A fault that ramps up over a duration rather than appearing instantly."""
    fault_type: str
    joint_id: str
    start_time: float = field(default_factory=time.time)
    ramp_duration: float = 30.0  # seconds to reach full effect
    target_temp_increase: float = 30.0  # degrees C
    target_torque_noise: float = 2.0  # Nm noise amplitude

    def progress(self) -> float:
        """Return 0.0-1.0 indicating how far through the ramp we are."""
        elapsed = time.time() - self.start_time
        return min(elapsed / self.ramp_duration, 1.0)

    def current_temp_increase(self) -> float:
        return self.target_temp_increase * self.progress()

    def current_torque_noise(self) -> float:
        return self.target_torque_noise * self.progress()

    @property
    def is_complete(self) -> bool:
        return self.progress() >= 1.0


DEMO_SCENARIOS = {
    'knee_overheat': {
        'fault_type': 'knee_overheat',
        'joint_id': 'knee_left',
        'ramp_duration': 30.0,
        'target_temp_increase': 30.0,
        'target_torque_noise': 2.0,
    },
}
```

- [ ] **Step 2: Add gradual fault support to MockRobotAdapter**

In `app/adapters/mock.py`, add an import at the top:

```python
from app.services.simulation.fault_scenarios import GradualFault
```

Add a new instance variable in `__init__` (around line 23-42):

```python
self._gradual_faults: list[GradualFault] = []
```

Add two new methods after the existing `clear_fault` method (around line 331):

```python
async def start_gradual_fault(self, fault_type: str, joint_id: str,
                                ramp_duration: float = 30.0,
                                target_temp_increase: float = 30.0) -> dict:
    """Start a gradual fault that ramps up over time."""
    gf = GradualFault(
        fault_type=fault_type,
        joint_id=joint_id,
        ramp_duration=ramp_duration,
        target_temp_increase=target_temp_increase,
    )
    self._gradual_faults.append(gf)
    return {"status": "started", "fault_type": fault_type, "joint_id": joint_id}

async def reset_gradual_faults(self) -> dict:
    """Clear all gradual faults and reset to normal."""
    self._gradual_faults.clear()
    self._active_faults.clear()
    return {"status": "reset"}
```

- [ ] **Step 3: Apply gradual fault effects in telemetry generation**

In `get_joint_states()` (around lines 179-247), after the existing fault effects application, add gradual fault effects. Find the loop that iterates over joints and add after the existing fault effect block:

```python
# Apply gradual fault effects
for gf in self._gradual_faults:
    if gf.joint_id == joint_id:
        temp_increase = gf.current_temp_increase()
        torque_noise = gf.current_torque_noise()
        temperature += temp_increase
        torque += random.gauss(0, torque_noise)
        current += temp_increase * 0.05  # current rises with heat
        # Once ramp is complete, set error_code for UI detection
        if gf.is_complete and not error_code:
            error_code = "E001_OVERHEAT"
            if "E001_OVERHEAT" not in self._active_faults:
                self._active_faults.append("E001_OVERHEAT")
```

- [ ] **Step 4: Verify gradual fault works**

Run backend: `cd r-mos-backend && bash -c 'source .venv/bin/activate && python main.py'`

Test via curl:
```bash
# Start gradual fault
curl -X POST http://localhost:8000/api/v1/adapter/inject-fault \
  -H "Content-Type: application/json" \
  -d '{"fault_code": "E001_OVERHEAT", "target_part": "knee_left", "severity": "high"}'

# Check telemetry after a few seconds - temperature should be rising
curl http://localhost:8000/api/v1/adapter/faults
```

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/services/simulation/__init__.py r-mos-backend/app/services/simulation/fault_scenarios.py r-mos-backend/app/adapters/mock.py
git commit -m "feat: add gradual fault simulation for demo temperature ramp"
```

---

## Task 4: Demo API Endpoints (Fault Trigger + SSE Chat)

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/demo.py`
- Create: `r-mos-backend/app/services/llm/mock_provider.py`
- Modify: `r-mos-backend/main.py` (register demo router)

- [ ] **Step 1: Create mock LLM provider with pre-written responses**

Create `app/services/llm/mock_provider.py`:

```python
"""Mock LLM provider with pre-written responses for demo."""
import asyncio
import re
from dataclasses import dataclass


@dataclass
class MockLLMResponse:
    text: str
    diagnosis: dict | None = None
    citations: list[dict] | None = None
    sop_recommendation: dict | None = None


# --- Pre-written response templates ---

DIAGNOSIS_RESPONSE = MockLLMResponse(
    text=(
        "## 故障诊断报告\n\n"
        "**故障类型：** 左膝关节轴承磨损\n\n"
        "**严重程度：** 中高风险 (需尽快维保)\n\n"
        "**置信度：** 92%\n\n"
        "### 分析过程\n\n"
        "通过对传感器数据的多维度关联分析，我发现以下异常模式：\n\n"
        "1. **温度异常** — 左膝关节温度从正常基线 35°C 持续升高至 65°C，"
        "升温速率约 1°C/s，符合轴承摩擦过热的典型特征\n"
        "2. **扭矩波动** — 同期扭矩数据出现 ±2.1Nm 的周期性波动，"
        "表明关节内部存在不规则机械阻力\n"
        "3. **电流上升** — 驱动电流从 2.0A 上升至 2.8A，"
        "与温度升高呈正相关，说明电机在补偿额外摩擦负荷\n\n"
        "### 根因判定\n\n"
        "综合以上证据，判定根因为**左膝关节主轴承磨损**，导致滚珠与滚道之间"
        "间隙增大，运转时产生异常摩擦热。若不及时处理，可能导致轴承卡死或"
        "关节结构损伤。\n\n"
        "### 建议\n\n"
        "建议立即执行 **SOP: ATOM-01 左膝关节轴承更换**，预计耗时约 45 分钟。"
    ),
    diagnosis={
        "fault_type": "bearing_wear",
        "joint": "KNEE_LEFT",
        "severity": "high",
        "confidence": 0.92,
        "primary_hypothesis": {
            "name": "左膝关节轴承磨损",
            "confidence": 0.92,
            "affected_parts": ["left_knee_bearing", "left_knee_joint"],
            "evidence": [
                {"type": "temperature", "desc": "温度异常升高 35→65°C"},
                {"type": "torque", "desc": "扭矩周期性波动 ±2.1Nm"},
                {"type": "current", "desc": "驱动电流上升 2.0→2.8A"},
            ],
        },
        "alternative_hypotheses": [
            {
                "name": "润滑油不足",
                "confidence": 0.15,
                "affected_parts": ["left_knee_joint"],
            }
        ],
        "reasoning": "温度-扭矩-电流三维关联指向轴承机械磨损，排除润滑不足（润滑不足通常不会导致如此快速的温升）",
        "recommended_actions": [
            "立即停机，防止轴承卡死",
            "执行左膝关节轴承更换 SOP",
            "更换后进行 30 分钟空载磨合测试",
        ],
    },
    citations=[
        {"type": "sensor", "desc": "左膝温度 35→65°C（30s 内）", "source": "KNEE_LEFT.temperature"},
        {"type": "sensor", "desc": "左膝扭矩波动 ±2.1Nm", "source": "KNEE_LEFT.torque"},
        {"type": "sensor", "desc": "左膝电流 2.0→2.8A", "source": "KNEE_LEFT.current"},
        {"type": "history", "desc": "上次维保距今 180 天，超出建议周期", "source": "maintenance_log"},
    ],
    sop_recommendation={
        "sop_id": "knee-bearing-replace",
        "sop_name": "ATOM-01 左膝关节轴承更换",
        "estimated_time": "45 分钟",
        "steps_count": 6,
    },
)

SOP_GENERATION_RESPONSE = MockLLMResponse(
    text=(
        "## 维保方案已生成\n\n"
        "根据诊断结果，我已为您生成针对性维保方案：\n\n"
        "**SOP: ATOM-01 左膝关节轴承更换** (6 步)\n\n"
        "| 步骤 | 操作 | 预计时间 |\n"
        "|------|------|----------|\n"
        "| 01 | 安全确认 — 断电并确认维保隔离 | 3 分钟 |\n"
        "| 02 | 工具准备 — 确认扳手、轴承拔取器、润滑剂就位 | 5 分钟 |\n"
        "| 03 | 外壳拆卸 — 拆卸左膝关节保护外壳 (4 颗 M3 螺丝) | 8 分钟 |\n"
        "| 04 | 轴承定位 — 定位磨损轴承，记录磨损状态 | 5 分钟 |\n"
        "| 05 | 轴承更换 — 拔取旧轴承，安装新轴承，涂润滑剂 | 15 分钟 |\n"
        "| 06 | 回装验证 — 回装外壳，通电，关节活动度测试 | 9 分钟 |\n\n"
        "点击下方 **开始维保** 按钮，进入 3D 引导式维保工作台。"
    ),
    sop_recommendation={
        "sop_id": "knee-bearing-replace",
        "sop_name": "ATOM-01 左膝关节轴承更换",
        "estimated_time": "45 分钟",
        "steps_count": 6,
    },
)

EXPLANATION_RESPONSE = MockLLMResponse(
    text=(
        "## 故障机理详解\n\n"
        "### 轴承磨损的物理过程\n\n"
        "人形机器人膝关节使用深沟球轴承（型号 6205-2RS），"
        "在持续行走训练中承受周期性径向和轴向载荷。\n\n"
        "当轴承滚珠与滚道之间的润滑膜破裂后，金属直接接触产生摩擦热，"
        "导致温度快速升高。同时，磨损产生的金属微粒进入滚道间隙，"
        "形成 **磨粒磨损** 的恶性循环。\n\n"
        "### 数据关联分析\n\n"
        "- **温度↑ + 扭矩波动↑**：摩擦增大 → 热量增加 + 阻力不均\n"
        "- **电流↑**：电机 PID 控制器补偿额外阻力，增大输出电流\n"
        "- **三者正相关性 > 0.85**：排除传感器故障（传感器故障表现为随机噪声，无相关性）\n\n"
        "### 不处理的后果\n\n"
        "1. 轴承完全卡死 → 膝关节锁定 → 机器人摔倒风险\n"
        "2. 过热可能损伤周围线束和密封件\n"
        "3. 磨损碎屑扩散到相邻关节"
    ),
)

DEFAULT_RESPONSE = MockLLMResponse(
    text=(
        "我是 R-MOS 维保智能体，可以帮您完成以下任务：\n\n"
        "- 输入 **诊断** 或 **故障分析** 来分析当前设备异常\n"
        "- 输入 **维保方案** 或 **怎么修** 来生成维保 SOP\n"
        "- 输入 **为什么** 或 **解释** 来了解故障机理\n\n"
        "请告诉我您需要什么帮助。"
    ),
)


def match_intent(message: str) -> MockLLMResponse:
    """Match user message to a pre-written response based on keywords."""
    msg = message.lower().strip()

    diagnosis_kw = r"诊断|故障|什么问题|分析|检测|异常|温度.*高|过热"
    sop_kw = r"维保方案|怎么修|修复|sop|生成.*方案|开始.*维保|更换"
    explain_kw = r"为什么|解释|原因|机理|详解|怎么.*回事"

    if re.search(diagnosis_kw, msg):
        return DIAGNOSIS_RESPONSE
    if re.search(sop_kw, msg):
        return SOP_GENERATION_RESPONSE
    if re.search(explain_kw, msg):
        return EXPLANATION_RESPONSE
    return DEFAULT_RESPONSE


async def stream_text(text: str, chunk_size: int = 3, delay: float = 0.03):
    """Yield text in small chunks to simulate LLM streaming."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(delay)
```

- [ ] **Step 2: Create demo API endpoints**

Create `app/api/v1/endpoints/demo.py`:

```python
"""Demo-only API endpoints for investor presentation."""
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.llm.mock_provider import match_intent, stream_text
from app.services.simulation.fault_scenarios import DEMO_SCENARIOS, GradualFault


router = APIRouter(prefix="/demo", tags=["demo"])


class DemoChatRequest(BaseModel):
    message: str
    fault_context: dict | None = None


class DemoFaultRequest(BaseModel):
    scenario: str = "knee_overheat"


@router.post("/chat/stream")
async def demo_chat_stream(request: Request, body: DemoChatRequest):
    """SSE endpoint that streams mock LLM responses."""
    response = match_intent(body.message)
    trace_id = str(uuid.uuid4())[:8]

    async def event_generator():
        # Send metadata first
        meta = {
            "type": "meta",
            "trace_id": trace_id,
            "diagnosis": response.diagnosis,
            "citations": response.citations,
            "sop_recommendation": response.sop_recommendation,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # Stream text chunks
        async for chunk in stream_text(response.text):
            payload = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # Send done signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/fault/start")
async def start_demo_fault(request: Request, body: DemoFaultRequest):
    """Trigger a gradual fault scenario for demo."""
    from app.adapters.factory import get_adapter
    adapter = get_adapter()

    scenario = DEMO_SCENARIOS.get(body.scenario)
    if not scenario:
        return {"error": f"Unknown scenario: {body.scenario}"}

    result = await adapter.start_gradual_fault(
        fault_type=scenario["fault_type"],
        joint_id=scenario["joint_id"],
        ramp_duration=scenario["ramp_duration"],
        target_temp_increase=scenario["target_temp_increase"],
    )
    return result


@router.post("/fault/reset")
async def reset_demo_fault(request: Request):
    """Reset all faults to normal state."""
    from app.adapters.factory import get_adapter
    adapter = get_adapter()
    result = await adapter.reset_gradual_faults()
    return result
```

- [ ] **Step 3: Register demo router in main.py**

In `r-mos-backend/main.py`, find where API routers are registered (the line with `app.include_router`). Add:

```python
from app.api.v1.endpoints.demo import router as demo_router
app.include_router(demo_router, prefix="/api/v1")
```

- [ ] **Step 4: Verify SSE streaming**

Restart backend and test:

```bash
curl -N http://localhost:8000/api/v1/demo/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我诊断这个故障"}'
```

Expected: SSE events streaming with `data: {"type": "meta", ...}` then many `data: {"type": "text", ...}` then `data: {"type": "done"}`.

- [ ] **Step 5: Verify fault trigger**

```bash
curl -X POST http://localhost:8000/api/v1/demo/fault/start \
  -H "Content-Type: application/json" \
  -d '{"scenario": "knee_overheat"}'
```

Expected: `{"status": "started", "fault_type": "knee_overheat", "joint_id": "knee_left"}`

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/app/services/llm/mock_provider.py r-mos-backend/app/api/v1/endpoints/demo.py r-mos-backend/main.py
git commit -m "feat: add demo SSE chat endpoint and fault trigger API"
```

---

## Task 5: Frontend Demo API Client

**Files:**
- Create: `r-mos-frontend/src/api/demo.ts`

- [ ] **Step 1: Create demo API client**

```typescript
// src/api/demo.ts
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface DemoChatMeta {
  type: 'meta'
  trace_id: string
  diagnosis: Record<string, unknown> | null
  citations: Array<{ type: string; desc: string; source?: string }> | null
  sop_recommendation: {
    sop_id: string
    sop_name: string
    estimated_time: string
    steps_count: number
  } | null
}

export interface DemoChatTextChunk {
  type: 'text'
  content: string
}

export interface DemoChatDone {
  type: 'done'
}

export type DemoChatEvent = DemoChatMeta | DemoChatTextChunk | DemoChatDone

export async function startDemoFault(scenario = 'knee_overheat') {
  const res = await axios.post(`${API_BASE}/api/v1/demo/fault/start`, { scenario })
  return res.data
}

export async function resetDemoFault() {
  const res = await axios.post(`${API_BASE}/api/v1/demo/fault/reset`)
  return res.data
}

export function streamDemoChat(
  message: string,
  faultContext: Record<string, unknown> | null,
  onEvent: (event: DemoChatEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()

  fetch(`${API_BASE}/api/v1/demo/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, fault_context: faultContext }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        throw new Error(`Stream failed: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (!data) continue
            try {
              const event = JSON.parse(data) as DemoChatEvent
              onEvent(event)
              if (event.type === 'done') {
                onDone()
                return
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return controller
}
```

- [ ] **Step 2: Commit**

```bash
git add r-mos-frontend/src/api/demo.ts
git commit -m "feat: add frontend demo API client with SSE streaming"
```

---

## Task 6: MonitorPage — Fault Trigger + Click-to-Navigate

**Files:**
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx`

- [ ] **Step 1: Add hidden fault trigger on logo double-click**

In `MonitorPage.tsx`, add an import for the demo API and navigation:

```typescript
import { useNavigate } from 'react-router-dom'
import { DEMO_MODE, DEMO_FAULT_TYPE, DEMO_JOINT } from '@/config/demoMode'
import { startDemoFault, resetDemoFault } from '@/api/demo'
```

Inside the MonitorPage component (around line 202), add:

```typescript
const navigate = useNavigate()
const [demoFaultActive, setDemoFaultActive] = useState(false)

const handleDemoTrigger = useCallback(async () => {
  if (!DEMO_MODE) return
  if (demoFaultActive) {
    await resetDemoFault()
    setDemoFaultActive(false)
  } else {
    await startDemoFault('knee_overheat')
    setDemoFaultActive(true)
  }
}, [demoFaultActive])
```

- [ ] **Step 2: Attach double-click to logo area**

Find the header section title (around line 290-300, the "REALTIME MONITOR" heading area). Wrap the title or the R-MOS logo/icon with an `onDoubleClick` handler:

```tsx
<h1
  className="text-2xl font-bold text-text-primary"
  onDoubleClick={handleDemoTrigger}
  title={DEMO_MODE ? (demoFaultActive ? '双击重置故障' : '双击触发故障') : undefined}
>
  实时监控
</h1>
```

- [ ] **Step 3: Add click-to-navigate on alert joint cards**

In the `MonitorJointRow` component, add a click handler to navigate to Agent workbench when the joint is in alert state. Change `MonitorJointRow` to accept an `onClick` prop:

```typescript
function MonitorJointRow({ joint, onClick }: { joint: JointState; onClick?: () => void }) {
  // ...existing code...
  const isClickable = isError || isTempAlert

  return (
    <div
      className={cn(
        'rounded-xl border p-3',
        isError
          ? 'border-danger/30 bg-danger/5'
          : isTempAlert
            ? 'border-amber-500/30 bg-amber-500/5 animate-pulse'
            : 'border-border-subtle bg-bg-elevated/40',
        isClickable && 'cursor-pointer hover:brightness-125 transition-all',
      )}
      onClick={isClickable ? onClick : undefined}
    >
```

Where `MonitorJointRow` is used (in the priorityJoints map, around line 487-491), pass the click handler:

```tsx
{priorityJoints.map((joint, index) => (
  <MonitorJointRow
    key={`${joint.joint_id}-${index}`}
    joint={joint}
    onClick={() => {
      if (DEMO_MODE) {
        navigate(`/agent/workbench?fault=${DEMO_FAULT_TYPE}&joint=${joint.joint_id}`)
      }
    }}
  />
))}
```

- [ ] **Step 4: Verify end-to-end**

1. Start backend and frontend with DEMO_MODE=true
2. Open MonitorPage
3. Double-click "实时监控" heading → fault should start ramping
4. Wait 30s → left knee joint card should pulse amber, then turn red
5. Click the alert card → should navigate to `/agent/workbench?fault=knee_overheat&joint=knee_left`

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/pages/MonitorPage.tsx
git commit -m "feat: add demo fault trigger and click-to-navigate on alert joints"
```

---

## Task 7: Agent Workbench — Mock LLM Integration

**Files:**
- Modify: `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`

This is the most complex frontend change. The existing page has a `submit()` function (lines 240-303) that calls `sendAgentRequestV2`. In DEMO_MODE, we replace this with SSE streaming from the demo endpoint.

- [ ] **Step 1: Add demo imports and URL param reading**

At the top of `AgentWorkbenchPage.tsx`, add:

```typescript
import { useSearchParams } from 'react-router-dom'
import { DEMO_MODE } from '@/config/demoMode'
import { streamDemoChat, type DemoChatMeta } from '@/api/demo'
```

Inside the component, add URL param reading:

```typescript
const [searchParams] = useSearchParams()
const faultParam = searchParams.get('fault')
const jointParam = searchParams.get('joint')
const navigate = useNavigate()
```

- [ ] **Step 2: Add demo state variables**

Add new state for demo mode after existing state declarations:

```typescript
const [demoMeta, setDemoMeta] = useState<DemoChatMeta | null>(null)
const [streamingText, setStreamingText] = useState('')
const [isStreaming, setIsStreaming] = useState(false)
const streamControllerRef = useRef<AbortController | null>(null)
```

- [ ] **Step 3: Auto-populate fault context on mount**

Add a useEffect that runs once when the page loads with fault params:

```typescript
useEffect(() => {
  if (!DEMO_MODE || !faultParam || messages.length > 0) return
  const contextMsg: ChatMessage = {
    id: `system-${Date.now()}`,
    role: 'assistant',
    content: `检测到设备告警：**${jointParam ?? '未知关节'}** 温度异常升高至 65°C，已超过安全阈值。\n\n请输入"诊断"开始故障分析，或直接描述您的需求。`,
    timestamp: Date.now(),
  }
  setMessages([contextMsg])
}, [faultParam, jointParam])
```

- [ ] **Step 4: Create demo submit handler**

Add a new `demoSubmit` function alongside the existing `submit`:

```typescript
const demoSubmit = useCallback(async (userMessage: string) => {
  if (!userMessage.trim() || isStreaming) return

  // Add user message
  const userMsg: ChatMessage = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: userMessage.trim(),
    timestamp: Date.now(),
  }
  setMessages(prev => [...prev, userMsg])
  setInput('')

  // Start streaming
  setIsStreaming(true)
  setStreamingText('')

  const assistantId = `assistant-${Date.now()}`

  streamDemoChat(
    userMessage,
    faultParam ? { fault: faultParam, joint: jointParam } : null,
    (event) => {
      if (event.type === 'meta') {
        setDemoMeta(event as DemoChatMeta)
      } else if (event.type === 'text') {
        setStreamingText(prev => prev + event.content)
      }
    },
    () => {
      // On done: finalize assistant message
      setStreamingText(finalText => {
        setMessages(prev => [...prev, {
          id: assistantId,
          role: 'assistant',
          content: finalText,
          timestamp: Date.now(),
        }])
        return ''
      })
      setIsStreaming(false)
    },
    (err) => {
      console.error('Demo chat error:', err)
      setIsStreaming(false)
    },
  )
}, [faultParam, jointParam, isStreaming])
```

- [ ] **Step 5: Wire submit button to demo handler**

Find where the submit/send button calls the existing `submit` function (around lines 518-540). Add a conditional:

```typescript
// In the send button onClick and form onSubmit:
const handleSubmit = DEMO_MODE ? () => demoSubmit(input) : () => submit(input, selectedIntent)
```

Also wire the quick action buttons similarly:

```typescript
// In quick action button onClick (around line 532-541):
onClick={() => DEMO_MODE ? demoSubmit(action.prompt) : void submit(action.prompt, action.intent)}
```

- [ ] **Step 6: Show streaming text in real-time**

In the message list rendering area (around lines 430-497), add a streaming message after the existing messages:

```tsx
{/* After the messages.map(...) block, before the scroll anchor */}
{isStreaming && streamingText && (
  <div className="flex gap-3 px-4">
    <StatusBadge role="assistant" />
    <div className="flex-1 rounded-xl bg-bg-elevated/60 p-4">
      <MessageBody content={streamingText} />
      <span className="inline-block h-4 w-1 animate-pulse bg-brand-500 ml-0.5" />
    </div>
  </div>
)}
```

- [ ] **Step 7: Show "开始维保" button after diagnosis**

After the message list, when demo meta has a sop_recommendation, show a prominent action button:

```tsx
{DEMO_MODE && demoMeta?.sop_recommendation && !isStreaming && (
  <div className="flex justify-center px-4 py-3">
    <button
      className="rounded-lg bg-brand-500 px-6 py-3 text-base font-semibold text-white shadow-lg hover:bg-brand-600 transition-colors"
      onClick={() => navigate(`/maintenance?sop=${demoMeta.sop_recommendation!.sop_id}`)}
    >
      开始维保 → {demoMeta.sop_recommendation.sop_name}
    </button>
  </div>
)}
```

- [ ] **Step 8: Wire demo diagnosis to sidebar DiagnosisPanel**

Find where `DiagnosisPanel` is rendered in the sidebar (around line 590+). When in DEMO_MODE, pass the mock diagnosis data:

```typescript
// Build diagnosis result from demo meta for the sidebar panel
const demoDiagnosis = demoMeta?.diagnosis ? {
  success: true,
  primary_hypothesis: demoMeta.diagnosis.primary_hypothesis ?? null,
  alternative_hypotheses: demoMeta.diagnosis.alternative_hypotheses ?? [],
  requires_supervisor: false,
  reasoning: (demoMeta.diagnosis as Record<string, unknown>).reasoning as string ?? '',
  recommended_actions: (demoMeta.diagnosis as Record<string, unknown>).recommended_actions as string[] ?? [],
} : null

// Pass to DiagnosisPanel:
<DiagnosisPanel
  diagnosisResult={DEMO_MODE ? demoDiagnosis : diagnosisResult}
  maintenancePlan={DEMO_MODE ? null : maintenancePlan}
  verificationResult={DEMO_MODE ? null : verificationResult}
  isLoading={isStreaming}
  onConfirmExecution={() => {
    if (DEMO_MODE && demoMeta?.sop_recommendation) {
      navigate(`/maintenance?sop=${demoMeta.sop_recommendation.sop_id}`)
    }
  }}
  onEscalateToTeacher={() => {}}
/>
```

- [ ] **Step 9: Verify demo chat flow**

1. Navigate to `/agent/workbench?fault=knee_overheat&joint=knee_left`
2. Should see auto-populated alert message
3. Type "诊断" → streaming diagnosis response appears character by character
4. Right sidebar shows diagnosis panel with hypothesis + evidence
5. "开始维保" button appears
6. Click it → navigates to `/maintenance?sop=knee-bearing-replace`

- [ ] **Step 10: Commit**

```bash
git add r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx
git commit -m "feat: integrate mock LLM SSE streaming into Agent workbench for demo"
```

---

## Task 8: Left Knee Bearing SOP Script + Seed Data

**Files:**
- Create: `r-mos-frontend/src/data/sopKneeBearing.ts`
- Create: `r-mos-backend/scripts/seed_demo_data.py`

- [ ] **Step 1: Create knee bearing SOP script for frontend adjudication**

Look at the existing SOP script format in `src/data/sopScripts.ts` (the `SOP_TORSO_MOTOR_REPLACEMENT` object around lines 72-150+) to match the structure. Create `src/data/sopKneeBearing.ts`:

```typescript
// src/data/sopKneeBearing.ts
import type { SOPScript } from '@/adjudication/types/adjudication'

export const SOP_KNEE_BEARING_REPLACE: SOPScript = {
  sopId: 'knee-bearing-replace',
  name: 'ATOM-01 左膝关节轴承更换',
  description: '左膝关节主轴承磨损，需拆卸外壳并更换轴承',
  applicableModel: 'ATOM-01',
  category: '关节维保',
  difficultyLevel: 'intermediate',
  estimatedTime: 45,
  steps: [
    {
      stepId: 'kbr-01',
      stepIndex: 0,
      title: '安全确认',
      description: '断电并确认维保隔离，确保机器人处于安全停机状态',
      action: 'FOCUS_CAMERA',
      targetParts: ['left_knee_link'],
      requiredTool: null,
      preconditions: [],
      validations: [],
      isCritical: true,
      hints: ['确认电源指示灯熄灭', '检查急停按钮已锁定'],
    },
    {
      stepId: 'kbr-02',
      stepIndex: 1,
      title: '工具准备',
      description: '确认 M3 内六角扳手、轴承拔取器、润滑脂就位',
      action: 'SELECT_TOOL',
      targetParts: [],
      requiredTool: 'hex_wrench_m3',
      preconditions: [],
      validations: [],
      isCritical: false,
      hints: ['所需工具：M3 内六角扳手、轴承拔取器、锂基润滑脂'],
    },
    {
      stepId: 'kbr-03',
      stepIndex: 2,
      title: '外壳拆卸',
      description: '拆卸左膝关节保护外壳，共 4 颗 M3 内六角螺丝',
      action: 'EXTRACT_SCREW',
      targetParts: ['left_knee_link'],
      requiredTool: 'hex_wrench_m3',
      preconditions: [],
      validations: [],
      isCritical: false,
      hints: ['按对角线顺序拆卸螺丝', '注意保管垫片'],
    },
    {
      stepId: 'kbr-04',
      stepIndex: 3,
      title: '轴承定位',
      description: '定位磨损轴承，观察并记录磨损状态（划痕、变色、异响）',
      action: 'FOCUS_CAMERA',
      targetParts: ['left_knee_link'],
      requiredTool: null,
      preconditions: [],
      validations: [],
      isCritical: false,
      hints: ['检查滚珠表面是否有凹坑', '记录磨损照片作为证据'],
    },
    {
      stepId: 'kbr-05',
      stepIndex: 4,
      title: '轴承更换',
      description: '使用拔取器取出旧轴承，安装新轴承（型号 6205-2RS），涂抹润滑脂',
      action: 'DETACH_PART',
      targetParts: ['left_knee_link'],
      requiredTool: 'bearing_puller',
      preconditions: [],
      validations: [],
      isCritical: true,
      hints: ['拔取时保持垂直用力，避免损伤轴座', '新轴承安装前涂抹薄层润滑脂'],
    },
    {
      stepId: 'kbr-06',
      stepIndex: 5,
      title: '回装验证',
      description: '回装保护外壳，通电，执行关节活动度测试（±90° 全范围旋转）',
      action: 'FOCUS_CAMERA',
      targetParts: ['left_knee_link'],
      requiredTool: 'hex_wrench_m3',
      preconditions: [],
      validations: [],
      isCritical: true,
      hints: ['螺丝按对角线顺序紧固', '通电后先低速空载运行 5 分钟'],
    },
  ],
}
```

Note: The exact `SOPScript` type may differ from the above. Check `src/adjudication/types/adjudication.ts` and `src/data/sopScripts.ts` for the actual interface shape and adjust field names accordingly.

- [ ] **Step 2: Register the new SOP in sopScripts**

In `src/data/sopScripts.ts`, find the `ALL_SOP_SCRIPTS` array or equivalent export and add:

```typescript
import { SOP_KNEE_BEARING_REPLACE } from './sopKneeBearing'

// Add to the ALL_SOP_SCRIPTS array:
export const ALL_SOP_SCRIPTS = [
  SOP_TORSO_MOTOR_REPLACEMENT,
  SOP_KNEE_BEARING_REPLACE,
  // ... any others
]
```

- [ ] **Step 3: Create backend seed script**

Create `r-mos-backend/scripts/seed_demo_data.py`:

```python
"""Seed demo data: SOP for left knee bearing replacement."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.sop import SOP, SOPStep


DEMO_SOP = {
    "name": "ATOM-01 左膝关节轴承更换",
    "description": "左膝关节主轴承磨损导致过热，需拆卸外壳并更换轴承",
    "applicable_model": "ATOM-01",
    "category": "关节维保",
    "difficulty_level": "intermediate",
    "estimated_time": 45,
}

DEMO_STEPS = [
    {"step_index": 0, "title": "安全确认", "description": "断电并确认维保隔离", "target_part": "left_knee", "expected_action": "verify", "is_critical": True, "severity_level": "BLOCK"},
    {"step_index": 1, "title": "工具准备", "description": "确认 M3 内六角扳手、轴承拔取器、润滑脂就位", "target_part": None, "expected_action": "prepare", "is_critical": False, "tools_required": ["hex_wrench_m3", "bearing_puller", "grease"]},
    {"step_index": 2, "title": "外壳拆卸", "description": "拆卸左膝关节保护外壳 (4 颗 M3 螺丝)", "target_part": "left_knee_cover", "expected_action": "remove_screws", "is_critical": False, "tools_required": ["hex_wrench_m3"]},
    {"step_index": 3, "title": "轴承定位", "description": "定位磨损轴承，记录磨损状态", "target_part": "left_knee_bearing", "expected_action": "inspect", "is_critical": False},
    {"step_index": 4, "title": "轴承更换", "description": "拔取旧轴承，安装新轴承 (6205-2RS)，涂润滑脂", "target_part": "left_knee_bearing", "expected_action": "replace", "is_critical": True, "tools_required": ["bearing_puller"]},
    {"step_index": 5, "title": "回装验证", "description": "回装外壳，通电，关节活动度测试", "target_part": "left_knee", "expected_action": "verify", "is_critical": True, "tools_required": ["hex_wrench_m3"]},
]


async def seed_demo_data():
    async with async_session_factory() as session:
        # Check if SOP already exists
        result = await session.execute(
            select(SOP).where(SOP.name == DEMO_SOP["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Demo SOP already exists: id={existing.id}")
            return existing.id

        sop = SOP(**DEMO_SOP)
        session.add(sop)
        await session.flush()

        for step_data in DEMO_STEPS:
            step = SOPStep(sop_id=sop.id, **step_data)
            session.add(step)

        await session.commit()
        print(f"✅ Demo SOP seeded: id={sop.id} name={DEMO_SOP['name']}")
        return sop.id


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
```

- [ ] **Step 4: Run seed script**

```bash
cd r-mos-backend && bash -c 'source .venv/bin/activate && python scripts/seed_demo_data.py'
```

Expected: `✅ Demo SOP seeded: id=... name=ATOM-01 左膝关节轴承更换`

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/data/sopKneeBearing.ts r-mos-frontend/src/data/sopScripts.ts r-mos-backend/scripts/seed_demo_data.py
git commit -m "feat: add knee bearing replacement SOP script and seed data"
```

---

## Task 9: SOP Maintenance Page — Demo SOP Auto-Selection

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`

- [ ] **Step 1: Read SOP param from URL and auto-select**

In `SOPMaintenancePage.tsx`, add URL param reading:

```typescript
import { useSearchParams } from 'react-router-dom'
import { DEMO_MODE } from '@/config/demoMode'
```

Inside the component:

```typescript
const [searchParams] = useSearchParams()
const sopParam = searchParams.get('sop')
```

- [ ] **Step 2: Pass initial SOP to SOPPlayerAdjudicated**

Find where `SOPPlayerAdjudicated` is rendered (in the left rail area). Add a prop:

```tsx
<SOPPlayerAdjudicated
  initialSopId={DEMO_MODE ? (sopParam ?? undefined) : undefined}
  // ...existing props
/>
```

- [ ] **Step 3: Handle initialSopId in SOPPlayerAdjudicated**

In `SOPPlayerAdjudicated.tsx`, add `initialSopId` to the component props:

```typescript
interface SOPPlayerAdjudicatedProps {
  // ...existing props
  initialSopId?: string
}
```

Add a useEffect to auto-select the SOP on mount:

```typescript
useEffect(() => {
  if (initialSopId && !selectedSOP) {
    const sop = availableSOPs.find(s => s.sopId === initialSopId)
    if (sop) {
      handleSelectSOP(initialSopId)
    }
  }
}, [initialSopId, availableSOPs])
```

- [ ] **Step 4: Add step timestamp recording for report**

In the SOPPlayerAdjudicated component, add a ref to track step timestamps:

```typescript
const stepTimestamps = useRef<Record<string, { start: number; end?: number }>>({})
```

When a step starts executing (in `handleNext` or similar, around line 392):

```typescript
stepTimestamps.current[step.stepId] = { start: Date.now() }
```

When a step completes (in the validation callback, around line 558 equivalent):

```typescript
if (stepTimestamps.current[step.stepId]) {
  stepTimestamps.current[step.stepId].end = Date.now()
}
```

- [ ] **Step 5: Navigate to report on SOP completion**

In the completion handler (around where `executionState === COMPLETE` is detected), add navigation:

```typescript
import { useNavigate } from 'react-router-dom'

const navigate = useNavigate()

// In the completion handler or effect:
useEffect(() => {
  if (context?.executionState === SOPExecutionState.COMPLETE && DEMO_MODE) {
    // Store step timestamps for report page
    sessionStorage.setItem('demo_step_timestamps', JSON.stringify(stepTimestamps.current))
    sessionStorage.setItem('demo_sop_name', selectedSOP?.name ?? '')
    // Short delay to show completion state before navigating
    const timer = setTimeout(() => navigate('/reports/demo'), 2000)
    return () => clearTimeout(timer)
  }
}, [context?.executionState])
```

- [ ] **Step 6: Verify SOP auto-selection flow**

1. Navigate to `/maintenance?sop=knee-bearing-replace`
2. SOP should auto-select and display knee bearing replacement steps
3. Step through each step with the 3D viewer updating
4. On completion, should auto-navigate to `/reports/demo`

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx
git commit -m "feat: auto-select demo SOP from URL param + step timestamps + completion navigation"
```

---

## Task 10: Report Page — Demo Report View

**Files:**
- Modify: `r-mos-frontend/src/pages/ReportPage.tsx`

- [ ] **Step 1: Add demo report mode**

In `ReportPage.tsx`, add demo detection:

```typescript
import { useParams } from 'react-router-dom'
import { DEMO_MODE } from '@/config/demoMode'

// Inside component:
const { taskId } = useParams()
const isDemoReport = DEMO_MODE && taskId === 'demo'
```

- [ ] **Step 2: Build demo report from sessionStorage**

Add a function to construct a demo report:

```typescript
function buildDemoReport() {
  const timestamps = JSON.parse(sessionStorage.getItem('demo_step_timestamps') ?? '{}')
  const sopName = sessionStorage.getItem('demo_sop_name') ?? 'ATOM-01 左膝关节轴承更换'

  const stepEntries = Object.entries(timestamps) as [string, { start: number; end?: number }][]
  const totalDuration = stepEntries.reduce((sum, [, t]) => {
    return sum + ((t.end ?? t.start) - t.start)
  }, 0)

  const STEP_NAMES = ['安全确认', '工具准备', '外壳拆卸', '轴承定位', '轴承更换', '回装验证']

  return {
    task_title: sopName,
    sop_name: sopName,
    status: 'COMPLETED' as const,
    final_score: 92,
    total_duration: Math.round(totalDuration / 1000),
    total_steps: 6,
    completed_steps: stepEntries.length,
    error_count: 0,
    started_at: stepEntries[0]?.[1]?.start
      ? new Date(stepEntries[0][1].start).toISOString()
      : new Date().toISOString(),
    completed_at: new Date().toISOString(),
    score_breakdown: {
      safety: 24,
      procedure: 23,
      precision: 22,
      efficiency: 23,
    },
    step_scores: STEP_NAMES.map((name, i) => ({
      step_index: i,
      step_title: name,
      score: i === 3 ? 14 : 16,
      max_score: 16,
      deductions: i === 3 ? [{ reason: '定位耗时略长', points: 2 }] : [],
      remarks: i === 3 ? '建议加强故障特征识别训练' : '操作规范',
    })),
    recommendations: [
      '整体操作规范，安全意识良好',
      '轴承定位环节可加强磨损特征识别训练',
      '建议下次维保时同步检查相邻关节状态',
    ],
  }
}
```

- [ ] **Step 3: Add demo-specific sections to report**

Before the existing report rendering, add demo-specific content when `isDemoReport`:

```tsx
{isDemoReport && (
  <>
    {/* Fault Summary Card */}
    <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
      <h2 className="mb-4 text-lg font-semibold text-brand-400">故障诊断摘要</h2>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-text-muted">故障类型</span>
          <p className="font-medium text-text-primary">左膝关节轴承磨损</p>
        </div>
        <div>
          <span className="text-text-muted">AI 置信度</span>
          <p className="font-medium text-green-400">92%</p>
        </div>
        <div>
          <span className="text-text-muted">风险评级</span>
          <p className="font-medium text-amber-400">中高</p>
        </div>
        <div>
          <span className="text-text-muted">处置结果</span>
          <p className="font-medium text-green-400">维保完成</p>
        </div>
      </div>
    </div>

    {/* Before/After Comparison */}
    <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
      <h2 className="mb-4 text-lg font-semibold text-brand-400">维保前后对比</h2>
      <div className="grid grid-cols-2 gap-8">
        <div className="text-center">
          <div className="text-3xl font-bold text-red-400">65°C</div>
          <div className="text-sm text-text-muted">维保前 · 左膝温度</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-green-400">35°C</div>
          <div className="text-sm text-text-muted">维保后 · 左膝温度</div>
        </div>
      </div>
    </div>

    {/* AI Diagnosis Citations */}
    <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
      <h2 className="mb-4 text-lg font-semibold text-brand-400">诊断证据链</h2>
      <div className="space-y-2">
        {[
          { icon: '🌡️', text: '左膝温度 35→65°C（30s 内）', source: 'KNEE_LEFT.temperature' },
          { icon: '⚙️', text: '左膝扭矩波动 ±2.1Nm', source: 'KNEE_LEFT.torque' },
          { icon: '⚡', text: '左膝电流 2.0→2.8A', source: 'KNEE_LEFT.current' },
          { icon: '📋', text: '上次维保距今 180 天，超出建议周期', source: 'maintenance_log' },
        ].map((c, i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg bg-bg-base/60 px-4 py-2 text-sm">
            <span>{c.icon}</span>
            <span className="text-text-primary">{c.text}</span>
            <span className="ml-auto text-xs text-text-muted">{c.source}</span>
          </div>
        ))}
      </div>
    </div>
  </>
)}
```

- [ ] **Step 4: Use demo report data when isDemoReport**

In the existing useEffect that fetches report data, add a guard:

```typescript
useEffect(() => {
  if (isDemoReport) {
    setReport(buildDemoReport())
    setLoading(false)
    return
  }
  // ...existing API fetch logic
}, [taskId, isDemoReport])
```

Ensure the `report` state and `loading` state variables are compatible with the demo report structure.

- [ ] **Step 5: Add "返回监控" button at bottom**

At the bottom of the report page, add a return button:

```tsx
{isDemoReport && (
  <div className="mt-6 flex justify-center">
    <button
      className="rounded-lg bg-brand-500 px-6 py-3 text-base font-semibold text-white hover:bg-brand-600 transition-colors"
      onClick={() => navigate('/monitor')}
    >
      返回实时监控
    </button>
  </div>
)}
```

- [ ] **Step 6: Verify report page**

1. Complete the SOP in maintenance page (or navigate directly to `/reports/demo`)
2. Should show fault summary, before/after comparison, citations, scores, recommendations
3. "返回监控" button should work

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/src/pages/ReportPage.tsx
git commit -m "feat: add demo report view with fault summary, comparison, and citations"
```

---

## Task 11: End-to-End Demo Flow Verification

**Files:** None (verification only)

- [ ] **Step 1: Start services in demo mode**

```bash
# Terminal 1 - Backend
cd r-mos-backend && bash -c 'source .venv/bin/activate && python scripts/seed_demo_data.py && python main.py'

# Terminal 2 - Frontend (demo mode)
cd r-mos-frontend && VITE_DEMO_MODE=true npm run dev
```

- [ ] **Step 2: Verify login and navigation**

1. Open browser at http://localhost:3001
2. Login as `admin@rmos.test` / `Admin@123`
3. Sidebar should show only: 实时监控, AI 诊断工作台, 维保工作台, 维保报告

- [ ] **Step 3: Verify Act 1 — Fault Detection**

1. Click "实时监控"
2. Double-click the "实时监控" heading → should trigger fault
3. Watch left knee temperature rise over 30 seconds
4. At ~55°C, knee card should pulse amber
5. At 65°C, knee card should turn red with error code
6. Click the alert card → should navigate to Agent workbench with params

- [ ] **Step 4: Verify Act 2 — AI Diagnosis**

1. Should see auto-populated alert context message
2. Type "诊断" and send → streaming diagnosis appears with typing animation
3. Right sidebar shows diagnosis panel with hypothesis, evidence, confidence
4. "开始维保" button appears at bottom
5. Click "开始维保" → navigates to maintenance page

- [ ] **Step 5: Verify Act 3 — 3D Guided Maintenance**

1. SOP should auto-select "左膝关节轴承更换"
2. 3D model should focus on left knee area
3. Step through all 6 steps, verifying 3D view changes
4. On completion, should auto-navigate to report page

- [ ] **Step 6: Verify Act 4 — Report**

1. Report should show fault summary, before/after comparison (65→35°C)
2. AI diagnosis citations should display
3. Step scores and recommendations visible
4. "返回监控" button works

- [ ] **Step 7: Fix any issues found during verification**

Document and fix any bugs, visual glitches, or flow interruptions.

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "fix: end-to-end demo flow adjustments"
```

---

## Task 12: Demo Polish + Final Cleanup

**Files:** Various touch-ups

- [ ] **Step 1: Ensure fault resets when leaving monitor page**

In MonitorPage, add cleanup:

```typescript
useEffect(() => {
  return () => {
    if (DEMO_MODE && demoFaultActive) {
      resetDemoFault()
    }
  }
}, [demoFaultActive])
```

- [ ] **Step 2: Add loading states for all transitions**

Verify each page transition has proper loading indicators:
- Monitor → Agent: page should show loading skeleton until context loads
- Agent → Maintenance: SOP should show loading until auto-selected
- Maintenance → Report: brief transition state

- [ ] **Step 3: Verify SSE cleanup on navigation**

In AgentWorkbenchPage, abort any active SSE stream on unmount:

```typescript
useEffect(() => {
  return () => {
    streamControllerRef.current?.abort()
  }
}, [])
```

- [ ] **Step 4: Test the full demo 3 times end-to-end**

Run the complete demo flow 3 times to verify reliability.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "polish: demo flow cleanup and reliability improvements"
```
