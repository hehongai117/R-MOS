# Phase 2: SOP 裁决脚本数据库化 — 详细实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端硬编码的 SOP 裁决脚本（31 条）迁移到后端数据库，通过 API 加载，使新 SOP 可以通过数据录入而非代码修改来添加。

**Architecture:** 扩展后端 `SOPStep.action_params` JSON 列为裁决数据的规范存储格式，新增 `GET /api/v1/sops/{id}/adjudication` 端点返回前端可直接消费的 `SOPScriptAdjudication` 结构。前端从 API 获取 SOP 脚本，保留 `ALL_SOP_SCRIPTS` 作为离线 fallback 直到 Task 22 移除。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic 2.x / React 18 + TypeScript + Zustand

---

## 架构决策

### 1. Schema 策略：利用现有 JSON 列

后端 `SOPStep` 已有 `action_params` (JSON) 和 `validation_rules` (JSON) 列。Phase 2 定义这两个列的规范结构：

**`action_params` 存储裁决行为数据：**
```json
{
  "action": "select_tool",
  "target_parts": ["torso_link"],
  "required_tool": "phillips_screwdriver_m3",
  "preconditions": [
    { "type": "TOOL_EQUIPPED", "params": { "tool": "phillips_screwdriver_m3" }, "error_message": "请先选择工具" }
  ],
  "on_success": { "next_step_id": "step_002", "state_transition": null },
  "on_failure": { "action": "block", "message": "操作失败，请重试" },
  "is_irreversible": false,
  "fatal_on_failure": false
}
```

**`validation_rules` 存储验证和失败原因：**
```json
{
  "validations": [
    { "type": "TOOL_MATCHED", "params": { "tool": "phillips_screwdriver_m3" }, "is_required": true }
  ],
  "failure_reasons": [
    {
      "code": "ERR_WRONG_TOOL",
      "category": "WRONG_TOOL",
      "description": "工具选择错误",
      "severity": "major",
      "teaching_response": { "show_hint": true, "hint_content": "请使用十字螺丝刀", "allow_retry": true },
      "exam_response": { "deduct_points": 5, "allow_continue": true, "record_to_report": true }
    }
  ]
}
```

### 2. SOP 级新增字段

`SOP` 表新增两列（Alembic migration）：
- `version` VARCHAR(20) — SOP 版本号（如 `"2.0.0-hw"`）
- `target_module` VARCHAR(100) — 目标模块（如 `"left_elbow"`）

### 3. 难度级别统一

后端 `difficulty_level` 保持 `low/medium/high`，API 响应层做映射：
- `low` → `beginner`
- `medium` → `intermediate`  
- `high` → `advanced`

### 4. 前端 API 消费模式

```
SOPMaintenancePage
  └─ useSOPScripts(robotModelId)        ← 新 hook
       └─ GET /api/v1/sops/adjudication?robot_model_id=X
            └─ 返回 SOPScriptAdjudication[]
       └─ fallback: ALL_SOP_SCRIPTS     ← 离线兜底（Task 22 移除）
```

---

## 文件结构

**后端新建/修改：**
```
r-mos-backend/
├── alembic/versions/
│   └── 20260519_add_sop_adjudication_fields.py    ← 新建：migration
├── app/models/sop.py                               ← 修改：新增 version、target_module 列
├── app/schemas/sop.py                              ← 修改：新增 adjudication 响应 schema
├── app/api/v1/endpoints/sops.py                    ← 修改：新增 adjudication 端点
├── app/services/sop_service.py                     ← 修改：新增 adjudication 查询方法
└── scripts/seed_adjudication_sops.py               ← 新建：迁移 31 条 SOP 到 DB
```

**前端新建/修改：**
```
r-mos-frontend/src/
├── api/sopScripts.ts                               ← 新建：SOP API client
├── hooks/useSOPScripts.ts                          ← 新建：SOP 加载 hook
├── pages/SOPMaintenancePage.tsx                    ← 修改：从 API 加载 SOP
├── components/Maintenance/SOPPlayerAdjudicated.tsx ← 修改：移除直接 import
└── data/
    ├── sopScripts.ts                               ← Task 22 删除
    ├── hardwareSOPScripts.ts                       ← Task 22 删除
    └── sopKneeBearing.ts                           ← Task 22 删除
```

---

### Task 13: 扩展 SOP 数据模型 — 新增 version 和 target_module 列

**Files:**
- Modify: `r-mos-backend/app/models/sop.py`
- Create: `r-mos-backend/alembic/versions/20260519_add_sop_adjudication_fields.py`
- Modify: `r-mos-backend/app/schemas/sop.py`

- [ ] **Step 1: 修改 SOP 模型添加新列**

在 `r-mos-backend/app/models/sop.py` 的 `SOP` 类中，在 `estimated_time` 之后添加：

```python
version = Column(String(20), nullable=True, comment="SOP版本号")
target_module = Column(String(100), nullable=True, comment="目标维护模块")
```

- [ ] **Step 2: 创建 Alembic migration**

```bash
cd r-mos-backend
source venv/bin/activate
alembic revision --autogenerate -m "add sop version and target_module"
```

检查生成的 migration 文件，确认只包含 `version` 和 `target_module` 两个 `add_column` 操作。

- [ ] **Step 3: 运行 migration**

```bash
alembic upgrade head
```

Expected: migration 成功，无错误。

- [ ] **Step 4: 更新 Pydantic schema**

在 `r-mos-backend/app/schemas/sop.py` 的 `SOPBase` 中添加：

```python
version: Optional[str] = Field(None, max_length=20, description="SOP版本号")
target_module: Optional[str] = Field(None, max_length=100, description="目标维护模块")
```

- [ ] **Step 5: 验证 API 兼容性**

```bash
cd r-mos-backend
python -c "from app.schemas.sop import SOPCreate, SOPResponse; print('schemas OK')"
```

- [ ] **Step 6: Commit**

```bash
git add app/models/sop.py app/schemas/sop.py alembic/versions/
git commit -m "feat(sop): add version and target_module columns to SOP model"
```

---

### Task 14: 新增 SOP 裁决 API 端点

**Files:**
- Modify: `r-mos-backend/app/schemas/sop.py`
- Modify: `r-mos-backend/app/services/sop_service.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/sops.py`

- [ ] **Step 1: 定义裁决响应 schema**

在 `r-mos-backend/app/schemas/sop.py` 末尾添加：

```python
# ===== Phase 2: SOP 裁决格式响应 =====

DIFFICULTY_MAP = {
    "low": "beginner",
    "medium": "intermediate",
    "high": "advanced",
}

class SOPAdjudicationStepResponse(BaseModel):
    """裁决格式的 SOP 步骤 — 前端 SOPStepAdjudication 的 Python 对应"""
    stepId: str
    stepIndex: int
    title: str
    description: str
    action: str
    targetParts: List[str]
    requiredTool: Optional[str] = None
    preconditions: List[Dict[str, Any]] = Field(default_factory=list)
    validations: List[Dict[str, Any]] = Field(default_factory=list)
    failureReasons: List[Dict[str, Any]] = Field(default_factory=list)
    onSuccess: Dict[str, Any] = Field(default_factory=dict)
    onFailure: Dict[str, Any] = Field(default_factory=dict)
    isIrreversible: bool = False
    fatalOnFailure: bool = False

class SOPAdjudicationResponse(BaseModel):
    """裁决格式的完整 SOP — 前端 SOPScriptAdjudication 的 Python 对应"""
    sopId: str
    title: str
    version: str
    targetModule: str
    estimatedTime: int
    difficulty: str
    steps: List[SOPAdjudicationStepResponse]

class SOPAdjudicationListResponse(BaseModel):
    """裁决格式 SOP 列表响应"""
    total: int
    items: List[SOPAdjudicationResponse]
```

- [ ] **Step 2: 在 SOPService 添加转换方法**

在 `r-mos-backend/app/services/sop_service.py` 添加：

```python
from app.schemas.sop import (
    DIFFICULTY_MAP,
    SOPAdjudicationResponse,
    SOPAdjudicationStepResponse,
    SOPAdjudicationListResponse,
)

def _sop_to_adjudication(self, sop: SOP) -> SOPAdjudicationResponse:
    """将 DB SOP 转换为前端裁决格式"""
    steps = []
    sorted_steps = sorted(sop.steps, key=lambda s: s.step_index)
    
    for i, step in enumerate(sorted_steps):
        action_params = step.action_params or {}
        validation_rules = step.validation_rules or {}
        
        next_step_id = (
            f"step_{sorted_steps[i + 1].step_index:03d}"
            if i + 1 < len(sorted_steps) else None
        )
        
        steps.append(SOPAdjudicationStepResponse(
            stepId=f"step_{step.step_index:03d}",
            stepIndex=step.step_index,
            title=step.title,
            description=step.description,
            action=action_params.get("action", step.expected_action),
            targetParts=action_params.get("target_parts", [step.target_part] if step.target_part else []),
            requiredTool=action_params.get("required_tool", (step.tools_required or [None])[0]),
            preconditions=action_params.get("preconditions", []),
            validations=validation_rules.get("validations", []),
            failureReasons=validation_rules.get("failure_reasons", []),
            onSuccess=action_params.get("on_success", {
                "nextStepId": next_step_id,
                "stateTransition": None,
            }),
            onFailure=action_params.get("on_failure", {
                "action": "block",
                "message": "操作失败",
            }),
            isIrreversible=action_params.get("is_irreversible", False),
            fatalOnFailure=action_params.get("fatal_on_failure", False),
        ))
    
    return SOPAdjudicationResponse(
        sopId=f"sop-db-{sop.id}",
        title=sop.name,
        version=sop.version or "1.0.0",
        targetModule=sop.target_module or sop.applicable_model,
        estimatedTime=sop.estimated_time or len(sop.steps) * 120,
        difficulty=DIFFICULTY_MAP.get(sop.difficulty_level, "intermediate"),
        steps=steps,
    )

async def list_adjudication_sops(
    self,
    robot_model_id: int | None = None,
    applicable_model: str | None = None,
    category: str | None = None,
) -> SOPAdjudicationListResponse:
    """查询裁决格式 SOP 列表"""
    query = select(SOP).options(selectinload(SOP.steps))
    if robot_model_id:
        query = query.where(SOP.robot_model_id == robot_model_id)
    if applicable_model:
        query = query.where(SOP.applicable_model == applicable_model)
    if category:
        query = query.where(SOP.category == category)
    
    result = await self.db.execute(query)
    sops = result.scalars().all()
    
    items = [self._sop_to_adjudication(sop) for sop in sops]
    return SOPAdjudicationListResponse(total=len(items), items=items)
```

注意：`SOPService.__init__` 已有 `self.db`，方法需要放在类内。别忘了在文件顶部加 `from sqlalchemy.orm import selectinload` 和 `from sqlalchemy import select`（如果尚未导入）。

- [ ] **Step 3: 添加 API 端点**

在 `r-mos-backend/app/api/v1/endpoints/sops.py` 添加新端点：

```python
from app.schemas.sop import SOPAdjudicationListResponse

@router.get("/sops/adjudication", response_model=SOPAdjudicationListResponse, tags=["SOPs"])
async def list_adjudication_sops(
    robot_model_id: Optional[int] = Query(None, description="过滤：机器人型号ID"),
    applicable_model: Optional[str] = Query(None, description="过滤：适用机器人型号名"),
    category: Optional[str] = Query(None, description="过滤：分类"),
    db: AsyncSession = Depends(get_db),
):
    """获取裁决格式的 SOP 列表 — 前端 SOPScriptAdjudication[] 格式"""
    service = SOPService(db)
    return await service.list_adjudication_sops(
        robot_model_id=robot_model_id,
        applicable_model=applicable_model,
        category=category,
    )
```

**重要：** 此端点必须放在 `@router.get("/sops/{sop_id}")` **之前**，否则 FastAPI 会把 `adjudication` 当作 `sop_id` 参数。

- [ ] **Step 4: 测试 API**

```bash
cd r-mos-backend
python -m pytest tests/ -k sop -v 2>&1 | tail -20
# 或手动验证：
# python -c "from app.api.v1.endpoints.sops import router; print('endpoint registered')"
```

- [ ] **Step 5: Commit**

```bash
git add app/schemas/sop.py app/services/sop_service.py app/api/v1/endpoints/sops.py
git commit -m "feat(sop): add adjudication-format SOP API endpoint"
```

---

### Task 15: 创建 SOP 裁决 seed 脚本 — 迁移 sopKneeBearing

**Files:**
- Create: `r-mos-backend/scripts/seed_adjudication_sops.py`

这个 Task 先迁移一条 SOP（`SOP_KNEE_BEARING_REPLACE`）作为验证，Task 18 再迁移全部 30 条 hardware SOPs。

- [ ] **Step 1: 创建 seed 脚本**

创建 `r-mos-backend/scripts/seed_adjudication_sops.py`：

```python
"""
Seed script: 将前端硬编码 SOP 裁决脚本迁移到数据库。
用法: cd r-mos-backend && python scripts/seed_adjudication_sops.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.sop import SOP, SOPStep


# ────── SOP 数据定义 ──────

SOP_KNEE_BEARING = {
    "name": "ATOM-01 左膝关节轴承更换",
    "description": "左膝关节轴承全流程更换，含拆卸、检查、安装、校准",
    "applicable_model": "ATOM-01",
    "category": "mechanical",
    "difficulty_level": "medium",
    "estimated_time": 2700,  # 45 min
    "version": "1.0.0",
    "target_module": "left_knee",
    "robot_model_id": 1,
    "steps": [
        {
            "step_index": 1,
            "title": "定位膝关节区域",
            "description": "将视角聚焦到左膝关节区域，确认维护目标",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [],
                "on_success": {"nextStepId": "step_002", "stateTransition": None},
                "on_failure": {"action": "warn", "message": "请聚焦到左膝关节区域"},
                "is_irreversible": False,
                "fatal_on_failure": False,
            },
            "validation_rules": {
                "validations": [
                    {"type": "STATE_CHECK", "params": {"target": "left_knee_link"}, "is_required": True}
                ],
                "failure_reasons": [
                    {
                        "code": "ERR_WRONG_FOCUS",
                        "category": "INCOMPLETE_ACTION",
                        "description": "未聚焦到正确区域",
                        "severity": "minor",
                        "teaching_response": {"show_hint": True, "hint_content": "请点击左膝关节区域", "allow_retry": True},
                        "exam_response": {"deduct_points": 2, "allow_continue": True, "record_to_report": True},
                    }
                ],
            },
            "is_critical": False,
            "tools_required": None,
        },
        {
            "step_index": 2,
            "title": "拆卸膝关节保护罩",
            "description": "使用十字螺丝刀拆除膝关节保护罩的4颗M3螺丝",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [
                    {"type": "PREVIOUS_STEP_COMPLETE", "params": {"step": "step_001"}, "error_message": "请先完成上一步操作"}
                ],
                "on_success": {"nextStepId": "step_003", "stateTransition": None},
                "on_failure": {"action": "block", "message": "保护罩拆卸失败"},
                "is_irreversible": False,
                "fatal_on_failure": False,
            },
            "validation_rules": {
                "validations": [],
                "failure_reasons": [
                    {
                        "code": "ERR_INCOMPLETE",
                        "category": "INCOMPLETE_ACTION",
                        "description": "保护罩未完全拆除",
                        "severity": "major",
                        "teaching_response": {"show_hint": True, "hint_content": "请确认所有螺丝已拆除", "allow_retry": True},
                        "exam_response": {"deduct_points": 5, "allow_continue": True, "record_to_report": True},
                    }
                ],
            },
            "is_critical": True,
            "tools_required": ["phillips_screwdriver_m3"],
        },
        {
            "step_index": 3,
            "title": "检查轴承磨损状态",
            "description": "目视检查轴承磨损情况，记录磨损等级",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [
                    {"type": "PREVIOUS_STEP_COMPLETE", "params": {"step": "step_002"}, "error_message": "请先拆卸保护罩"}
                ],
                "on_success": {"nextStepId": "step_004", "stateTransition": None},
                "on_failure": {"action": "warn", "message": "请仔细检查轴承状态"},
                "is_irreversible": False,
                "fatal_on_failure": False,
            },
            "validation_rules": {"validations": [], "failure_reasons": []},
            "is_critical": False,
            "tools_required": None,
        },
        {
            "step_index": 4,
            "title": "拆卸旧轴承",
            "description": "使用轴承拉拔器拆卸磨损轴承",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [
                    {"type": "PREVIOUS_STEP_COMPLETE", "params": {"step": "step_003"}, "error_message": "请先完成检查"}
                ],
                "on_success": {"nextStepId": "step_005", "stateTransition": None},
                "on_failure": {"action": "block", "message": "拆卸失败"},
                "is_irreversible": True,
                "fatal_on_failure": False,
            },
            "validation_rules": {"validations": [], "failure_reasons": []},
            "is_critical": True,
            "tools_required": None,
        },
        {
            "step_index": 5,
            "title": "安装新轴承",
            "description": "安装新轴承并确认就位",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [
                    {"type": "PREVIOUS_STEP_COMPLETE", "params": {"step": "step_004"}, "error_message": "请先拆卸旧轴承"}
                ],
                "on_success": {"nextStepId": "step_006", "stateTransition": None},
                "on_failure": {"action": "block", "message": "安装失败"},
                "is_irreversible": False,
                "fatal_on_failure": False,
            },
            "validation_rules": {"validations": [], "failure_reasons": []},
            "is_critical": True,
            "tools_required": None,
        },
        {
            "step_index": 6,
            "title": "功能验证与校准",
            "description": "重新组装后进行关节活动度测试和校准",
            "target_part": "left_knee_link",
            "expected_action": "focus_camera",
            "action_params": {
                "action": "focus_camera",
                "target_parts": ["left_knee_link"],
                "required_tool": None,
                "preconditions": [
                    {"type": "PREVIOUS_STEP_COMPLETE", "params": {"step": "step_005"}, "error_message": "请先安装新轴承"}
                ],
                "on_success": {"nextStepId": None, "stateTransition": None},
                "on_failure": {"action": "warn", "message": "校准未通过，请重试"},
                "is_irreversible": False,
                "fatal_on_failure": False,
            },
            "validation_rules": {"validations": [], "failure_reasons": []},
            "is_critical": False,
            "tools_required": None,
        },
    ],
}


async def seed():
    async with async_session_factory() as session:
        # 检查是否已存在
        existing = await session.execute(
            select(SOP).where(SOP.name == SOP_KNEE_BEARING["name"])
        )
        if existing.scalar_one_or_none():
            print(f"SOP '{SOP_KNEE_BEARING['name']}' already exists, skipping.")
            return

        steps_data = SOP_KNEE_BEARING.pop("steps")
        sop = SOP(**SOP_KNEE_BEARING)
        session.add(sop)
        await session.flush()  # get sop.id

        for step_data in steps_data:
            step = SOPStep(sop_id=sop.id, **step_data)
            session.add(step)

        await session.commit()
        print(f"Seeded SOP '{sop.name}' (id={sop.id}) with {len(steps_data)} steps.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: 运行 seed 脚本**

```bash
cd r-mos-backend
source venv/bin/activate
python scripts/seed_adjudication_sops.py
```

Expected: `Seeded SOP 'ATOM-01 左膝关节轴承更换' (id=N) with 6 steps.`

- [ ] **Step 3: 验证 API 返回**

```bash
# 启动后端后:
curl -s http://localhost:8000/api/v1/sops/adjudication | python -m json.tool | head -30
```

Expected: 返回包含 `sopId`, `title`, `steps` 的 JSON，steps 中每个步骤含 `stepId`, `action`, `targetParts` 等字段。

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_adjudication_sops.py
git commit -m "feat(sop): add seed script for adjudication SOP (knee bearing)"
```

---

### Task 16: 前端 SOP API client

**Files:**
- Create: `r-mos-frontend/src/api/sopScripts.ts`
- Create: `r-mos-frontend/src/hooks/useSOPScripts.ts`

- [ ] **Step 1: 创建 API client**

创建 `r-mos-frontend/src/api/sopScripts.ts`：

```typescript
import apiClient from '@/api/client'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'

interface SOPAdjudicationListResponse {
  total: number
  items: SOPScriptAdjudication[]
}

/**
 * 从后端获取裁决格式 SOP 列表。
 * 响应已是 SOPScriptAdjudication 格式，无需前端转换。
 */
export async function fetchAdjudicationSOPs(params?: {
  robot_model_id?: number
  applicable_model?: string
  category?: string
}): Promise<SOPScriptAdjudication[]> {
  const response = await apiClient.get<SOPAdjudicationListResponse>(
    '/sops/adjudication',
    { params },
  )
  return response.data.items
}
```

- [ ] **Step 2: 创建 useSOPScripts hook**

创建 `r-mos-frontend/src/hooks/useSOPScripts.ts`：

```typescript
import { useEffect, useState } from 'react'

import { fetchAdjudicationSOPs } from '@/api/sopScripts'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'
import { ALL_SOP_SCRIPTS } from '@/data/sopScripts'

/**
 * 从 API 加载裁决格式 SOP 列表，失败时降级到本地硬编码数据。
 */
export function useSOPScripts(robotModelId?: number | null) {
  const [scripts, setScripts] = useState<SOPScriptAdjudication[]>(ALL_SOP_SCRIPTS)
  const [loading, setLoading] = useState(false)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    fetchAdjudicationSOPs(
      robotModelId ? { robot_model_id: robotModelId } : undefined,
    )
      .then((items) => {
        if (!cancelled && items.length > 0) {
          setScripts(items)
          setFromApi(true)
        }
      })
      .catch(() => {
        // API 不可用，保持本地 fallback
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [robotModelId])

  return { scripts, loading, fromApi }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/api/sopScripts.ts src/hooks/useSOPScripts.ts
git commit -m "feat(sop): add frontend SOP API client and useSOPScripts hook"
```

---

### Task 17: 重构 SOPMaintenancePage — 从 API 加载 SOP

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`

- [ ] **Step 1: 替换 SOP 数据源**

在 `SOPMaintenancePage.tsx` 中：

1. 添加导入：
```typescript
import { useSOPScripts } from '@/hooks/useSOPScripts'
import { useRobotContextStore } from '@/store/robotContextStore'
```

2. 在组件内部，找到 `ALL_SOP_SCRIPTS` 的使用，替换为 hook：
```typescript
const currentRobot = useRobotContextStore((s) => s.currentRobot)
const { scripts: apiSopScripts } = useSOPScripts(currentRobot?.id)
```

3. 修改 `availableSopScripts` 的 useMemo，将 `ALL_SOP_SCRIPTS` 替换为 `apiSopScripts`：
```typescript
// 之前：
// const availableSopScripts = useMemo(() => { ... return ALL_SOP_SCRIPTS }, [...])
// 之后：runtime draft 优先，否则用 API 数据
const availableSopScripts = useMemo(() => {
  if (runtimeSopScript) return [runtimeSopScript]
  return apiSopScripts
}, [runtimeSopScript, apiSopScripts])
```

4. 移除顶部的 `import { ALL_SOP_SCRIPTS } from '@/data/sopScripts'`（如果不再直接使用）。

- [ ] **Step 2: 验证页面功能**

```bash
npm run dev
# 浏览器打开 /maintenance，确认：
# 1. SOP 列表正常加载
# 2. 选择 SOP 后步骤列表正常显示
# 3. Runtime draft 模式仍正常工作
```

- [ ] **Step 3: 确认现有测试通过**

```bash
npx vitest run src/pages/__tests__/SOPMaintenancePage.dynamic.test.tsx
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/SOPMaintenancePage.tsx
git commit -m "refactor(sop): load SOP scripts from API with local fallback"
```

---

### Task 18: 迁移 30 条 hardware SOP 到数据库

**Files:**
- Modify: `r-mos-backend/scripts/seed_adjudication_sops.py`

这是数据迁移任务。需要将 `hardwareSOPScripts.ts` 中的 30 条 SOP 转换为 Python seed 数据。

- [ ] **Step 1: 读取前端 hardwareSOPScripts.ts 的完整数据**

读取 `r-mos-frontend/src/data/hardwareSOPScripts.ts`，理解 30 条 SOP 的结构模式。每条 SOP 由 builder 函数组合生成，共三个难度层级。

- [ ] **Step 2: 在 seed 脚本中创建 Python 等价的 builder 函数**

在 `seed_adjudication_sops.py` 中添加等价的 Python builder：

```python
def focus_step(title: str, desc: str, target: str) -> dict:
    """对应前端 focusStep"""
    return {
        "title": title,
        "description": desc,
        "target_part": target,
        "expected_action": "focus_camera",
        "action_params": {
            "action": "focus_camera",
            "target_parts": [target],
            "preconditions": [],
            "on_failure": {"action": "warn", "message": "请聚焦到正确区域"},
        },
        "validation_rules": {"validations": [], "failure_reasons": []},
        "is_critical": False,
    }

def tool_step(title: str, desc: str, tool: str) -> dict:
    """对应前端 toolStep"""
    return {
        "title": title,
        "description": desc,
        "target_part": None,
        "expected_action": "select_tool",
        "action_params": {
            "action": "select_tool",
            "target_parts": [],
            "required_tool": tool,
            "preconditions": [],
            "on_failure": {"action": "block", "message": "请选择正确的工具"},
        },
        "validation_rules": {
            "validations": [{"type": "TOOL_MATCHED", "params": {"tool": tool}, "is_required": True}],
            "failure_reasons": [{
                "code": "ERR_WRONG_TOOL",
                "category": "WRONG_TOOL",
                "description": "工具选择错误",
                "severity": "major",
                "teaching_response": {"show_hint": True, "hint_content": f"请选择 {tool}", "allow_retry": True},
                "exam_response": {"deduct_points": 5, "allow_continue": True, "record_to_report": True},
            }],
        },
        "is_critical": False,
        "tools_required": [tool],
    }

# ... 类似 screw_step, detach_step, remove_step, unplug_step
```

- [ ] **Step 3: 定义全部 30 条 SOP 数据**

使用 builder 函数定义每条 SOP，结构类似前端的 `createSOP()` 调用。

```python
HARDWARE_SOPS = [
    create_sop("sop-hw-l01", "初级-外壳目视检查", "torso", "low", 8, [
        focus_step("聚焦至躯干模块", "将3D视角调整到...", "torso_link"),
        tool_step("选择检查工具", "选择目视检查工具", "visual_inspection_tool"),
        # ... remaining steps
    ]),
    # ... all 30 SOPs
]
```

- [ ] **Step 4: 扩展 seed 函数为批量模式**

```python
async def seed():
    async with async_session_factory() as session:
        all_sops = [SOP_KNEE_BEARING] + HARDWARE_SOPS
        seeded = 0
        
        for sop_data in all_sops:
            existing = await session.execute(
                select(SOP).where(SOP.name == sop_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  skip: '{sop_data['name']}' (exists)")
                continue
            
            steps_data = sop_data.pop("steps")
            sop = SOP(**sop_data)
            session.add(sop)
            await session.flush()
            
            for i, step_data in enumerate(steps_data, 1):
                step_data["step_index"] = i
                # auto-generate on_success.nextStepId
                ap = step_data.get("action_params", {})
                if "on_success" not in ap:
                    next_id = f"step_{i+1:03d}" if i < len(steps_data) else None
                    ap["on_success"] = {"nextStepId": next_id, "stateTransition": None}
                step_data["action_params"] = ap
                
                step = SOPStep(sop_id=sop.id, **step_data)
                session.add(step)
            
            sop_data["steps"] = steps_data  # restore for idempotency
            seeded += 1
        
        await session.commit()
        print(f"Seeded {seeded} SOPs (skipped {len(all_sops) - seeded}).")
```

- [ ] **Step 5: 运行 seed 脚本**

```bash
cd r-mos-backend
python scripts/seed_adjudication_sops.py
```

Expected: `Seeded 31 SOPs (skipped 0).`

- [ ] **Step 6: 验证 API 返回全量 SOP**

```bash
curl -s http://localhost:8000/api/v1/sops/adjudication | python -c "import sys,json; d=json.load(sys.stdin); print(f'total: {d[\"total\"]}')"
```

Expected: `total: 31`（或包含之前 seed 的 fault SOPs 则更多）

- [ ] **Step 7: Commit**

```bash
git add scripts/seed_adjudication_sops.py
git commit -m "feat(sop): seed all 31 adjudication SOPs to database"
```

---

### Task 19: 工具数据 API 化

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`（或 `sops.py`）
- Modify: `r-mos-backend/app/services/sop_service.py`
- Create: `r-mos-frontend/src/api/tools.ts`

工具清单已在 Phase 1 的 manifest `tools` 字段中。此 Task 确保工具也可通过 API 独立获取。

- [ ] **Step 1: 后端 — manifest tools 端点**

在 `r-mos-backend/app/api/v1/endpoints/robots.py` 中添加：

```python
@router.get("/robots/{robot_id}/tools", tags=["Robots"])
async def get_robot_tools(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取机器人的工具清单（从 assembly_manifest.json 的 tools 字段读取）"""
    # 读取 manifest 文件
    from app.services.storage.file_storage import LocalFileStorage
    import json
    
    storage = LocalFileStorage()
    manifest_path = f"{robot_id}/manifests/assembly_manifest.json"
    
    try:
        content = await storage.read_file(manifest_path)
        manifest = json.loads(content)
        tools = manifest.get("tools", [])
        return {"robot_id": robot_id, "tools": tools}
    except FileNotFoundError:
        return {"robot_id": robot_id, "tools": []}
```

- [ ] **Step 2: 前端 API client**

创建 `r-mos-frontend/src/api/tools.ts`：

```typescript
import apiClient from '@/api/client'

export interface RobotTool {
  tool_id: string
  display_name: string
  category: string
  specs?: Record<string, string>
}

export async function fetchRobotTools(robotId: number): Promise<RobotTool[]> {
  const response = await apiClient.get<{ robot_id: number; tools: RobotTool[] }>(
    `/robots/${robotId}/tools`,
  )
  return response.data.tools
}
```

- [ ] **Step 3: Commit**

```bash
# backend
cd r-mos-backend && git add app/api/v1/endpoints/robots.py
git commit -m "feat(api): add GET /robots/{id}/tools endpoint"

# frontend
cd ../r-mos-frontend && git add src/api/tools.ts
git commit -m "feat(api): add robot tools API client"
```

---

### Task 20: 评分规则配置化

**Files:**
- Modify: `r-mos-frontend/src/adjudication/core/scoringEngine.ts`
- Modify: `r-mos-frontend/src/teaching/store/teachingStore.ts`

- [ ] **Step 1: 评分引擎支持配置初始分**

在 `scoringEngine.ts` 中，确认 `reset(initialScore = 100)` 已接受参数。若消费方需要从 Task 配置传入分数，在 `SOPPlayerAdjudicated` 中调用 `scoringEngine.reset(task.initial_score ?? 100)` 即可。

此步骤主要是确认现有代码已具备灵活性，若已支持则无需修改。

- [ ] **Step 2: 教学 store 从 Task 配置读取 pass_score**

在 `teachingStore.ts` 中，修改创建 Task 的调用，使 `pass_score` 可以从 SOP 配置或作业设置中读取：

```typescript
// 之前：
// createTask({ sop_id: assignment.sopId, pass_score: 70 })
// 之后：
createTask({ sop_id: assignment.sopId, pass_score: assignment.passScore ?? 70 })
```

确认 `Assignment` 类型中已有或新增 `passScore` 可选字段。

- [ ] **Step 3: Commit**

```bash
git add src/adjudication/core/scoringEngine.ts src/teaching/store/teachingStore.ts
git commit -m "refactor(scoring): make pass_score configurable from task/assignment"
```

---

### Task 21: 维保知识库 API 化

**Files:**
- Modify: `r-mos-frontend/src/data/maintenanceKnowledge.ts`

维保知识数据（`getCorePartDetailRecord`、`getCoreScrewRecords`）与 Phase 1 的 manifest 数据有重叠。此 Task 将知识查询改为优先从 manifest 读取。

- [ ] **Step 1: 添加 manifest 注入层**

在 `maintenanceKnowledge.ts` 中添加 manifest-first 查询模式，类似 Phase 1 对 `partRegistry.ts` 的处理：

```typescript
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest'

let _manifestDisplayNames: Record<string, string> | null = null
let _manifestTools: Array<{ tool_id: string; display_name: string }> | null = null

export function injectManifestKnowledge(manifest: RobotDataManifest) {
  _manifestDisplayNames = manifest.display_names ?? null
  _manifestTools = manifest.tools ?? null
}

export function clearManifestKnowledge() {
  _manifestDisplayNames = null
  _manifestTools = null
}
```

- [ ] **Step 2: 修改查询函数优先使用 manifest 数据**

```typescript
export function getCorePartDetailRecord(partName: string, robotId?: string): PartDetailRecord | null {
  // manifest 优先
  if (_manifestDisplayNames && _manifestDisplayNames[partName]) {
    return {
      displayName: _manifestDisplayNames[partName],
      partName,
      // ... 其他字段用默认值
    }
  }
  // 原有硬编码 fallback
  // ...existing code...
}
```

- [ ] **Step 3: Commit**

```bash
git add src/data/maintenanceKnowledge.ts
git commit -m "refactor(knowledge): add manifest injection layer to maintenance knowledge"
```

---

### Task 22: 移除前端硬编码 SOP 文件

**Files:**
- Delete: `r-mos-frontend/src/data/sopScripts.ts`
- Delete: `r-mos-frontend/src/data/hardwareSOPScripts.ts`
- Delete: `r-mos-frontend/src/data/sopKneeBearing.ts`
- Modify: `r-mos-frontend/src/hooks/useSOPScripts.ts`
- Modify: 所有引用这三个文件的地方

**前提：** Task 17 已验证 API 数据加载正常，本地 fallback 可以移除。

- [ ] **Step 1: 查找所有 import 引用**

```bash
cd r-mos-frontend
grep -r "from '@/data/sopScripts'" src/ --include='*.ts' --include='*.tsx'
grep -r "from '@/data/hardwareSOPScripts'" src/ --include='*.ts' --include='*.tsx'
grep -r "from '@/data/sopKneeBearing'" src/ --include='*.ts' --include='*.tsx'
```

- [ ] **Step 2: 移除 useSOPScripts 中的 fallback**

修改 `src/hooks/useSOPScripts.ts`，移除 `ALL_SOP_SCRIPTS` import 和 fallback：

```typescript
import { useEffect, useState } from 'react'
import { fetchAdjudicationSOPs } from '@/api/sopScripts'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'

export function useSOPScripts(robotModelId?: number | null) {
  const [scripts, setScripts] = useState<SOPScriptAdjudication[]>([])
  const [loading, setLoading] = useState(true)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    fetchAdjudicationSOPs(
      robotModelId ? { robot_model_id: robotModelId } : undefined,
    )
      .then((items) => {
        if (!cancelled) {
          setScripts(items)
          setFromApi(true)
        }
      })
      .catch(() => {
        if (!cancelled) setScripts([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [robotModelId])

  return { scripts, loading, fromApi }
}
```

- [ ] **Step 3: 更新所有 remaining imports**

将每个 remaining import 替换为 API 调用或移除。

- [ ] **Step 4: 删除硬编码文件**

```bash
rm src/data/sopScripts.ts
rm src/data/hardwareSOPScripts.ts
rm src/data/sopKneeBearing.ts
```

- [ ] **Step 5: 确认编译和测试通过**

```bash
npx tsc --noEmit
npx vitest run
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(sop): remove hardcoded SOP script files, API is now the sole source"
```

---

## 验收标准

- [ ] `GET /api/v1/sops/adjudication` 返回 ≥31 条 `SOPScriptAdjudication` 格式的 SOP
- [ ] `SOPMaintenancePage` 从 API 加载 SOP，不依赖本地硬编码
- [ ] `SOPPlayerAdjudicated` 正常执行 API 加载的 SOP（步骤导航、验证、评分）
- [ ] 评分 `pass_score` 从 Task/Assignment 配置读取（默认 70）
- [ ] 维保知识查询支持从 manifest 读取
- [ ] `data/sopScripts.ts`、`hardwareSOPScripts.ts`、`sopKneeBearing.ts` 已删除
- [ ] 所有现有测试通过（adjudication 预存在失败除外）
