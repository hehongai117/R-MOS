# 消除 ATOM-01 硬编码实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除所有运行时代码中的 ATOM-01 硬编码引用，使系统完全数据驱动（manifest/API），支持任意机器人。

**Architecture:** 利用已有的 `manifestAdapter`、`injectManifestPartRegistry`、`buildJointMetaFromManifest`、`robotContextStore` 基础设施，接通"最后一公里"并删除硬编码回退。后端通过 manifest 文件动态加载机器人 link 名称。

**Tech Stack:** React/TypeScript (前端), FastAPI/Python (后端), Zustand (状态管理), Assembly Manifest JSON (数据源)

---

## Phase 1 — 前端 Trivial 修复 (可并行)

### Task 1: 修复 SOPListPage 字段名 bug

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPListPage.tsx:71`

- [ ] **Step 1: 修复字段名**

将 `currentRobot?.name` 改为 `currentRobot?.model_name`，移除硬编码 fallback：

```typescript
// 第 71 行，修改前:
applicable_model: currentRobot?.name || 'ATOM-01',

// 修改后:
applicable_model: currentRobot?.model_name ?? '',
```

- [ ] **Step 2: 验证**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | head -20
```

预期: 无类型错误。

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/pages/SOPListPage.tsx
git commit -m "fix: use model_name instead of nonexistent name field in SOPListPage"
```

---

### Task 2: 修复 KnowledgePage 下拉框硬编码 fallback

**Files:**
- Modify: `r-mos-frontend/src/pages/KnowledgePage.tsx:428-430, 501-503`

- [ ] **Step 1: 修改搜索筛选器 fallback (约第 428-430 行)**

```typescript
// 修改前:
: <>
    <Option value="ATOM01">ATOM01</Option>
  </>

// 修改后:
: <Option value="" disabled>暂无可用机器人</Option>
```

- [ ] **Step 2: 修改创建表单 fallback (约第 501-503 行)**

同样的修改：

```typescript
// 修改前:
: <>
    <Option value="ATOM01">ATOM01</Option>
  </>

// 修改后:
: <Option value="" disabled>暂无可用机器人</Option>
```

- [ ] **Step 3: 验证**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/pages/KnowledgePage.tsx
git commit -m "fix: replace hardcoded ATOM01 fallback with empty state in KnowledgePage"
```

---

### Task 3: 修复维保工作台标题和 Shell badge

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx:253-255`
- Modify: `r-mos-frontend/src/components/Maintenance/SOPMaintenanceShell.tsx:34-43, 148-150`
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx:1314-1329`

- [ ] **Step 1: 修改 WORKSPACE_CHROME demo 标题**

在 `SOPMaintenancePage.tsx` 第 253-255 行：

```typescript
// 修改前:
demo: {
    title: 'ATOM01 维保工作台',
    breadcrumb: ['工作台', 'ATOM01 维保工作台'],
    showDraftEntry: false,
},

// 修改后:
demo: {
    title: '维保工作台',
    breadcrumb: ['工作台', '维保工作台'],
    showDraftEntry: false,
},
```

- [ ] **Step 2: 给 SOPMaintenanceLeftRailProps 添加 robotModelName**

在 `SOPMaintenanceShell.tsx` 第 34-43 行的接口中添加字段：

```typescript
interface SOPMaintenanceLeftRailProps {
  sopTitle: string
  difficultyLabel: string
  currentStepTitle?: string | null
  steps: SOPMaintenanceLeftRailStep[]
  isolationControls?: ReactNode
  sopListContent: ReactNode
  toolSelectorContent: ReactNode
  sopPlayerContent: ReactNode
  robotModelName?: string          // 新增
}
```

- [ ] **Step 3: 修改 SOPMaintenanceLeftRail 组件使用 prop**

在 `SOPMaintenanceShell.tsx`，解构新 prop 并动态渲染 badge：

```typescript
export function SOPMaintenanceLeftRail({
  sopTitle,
  difficultyLabel,
  currentStepTitle,
  steps,
  isolationControls,
  sopListContent,
  toolSelectorContent,
  sopPlayerContent,
  robotModelName,                  // 新增
}: SOPMaintenanceLeftRailProps) {
```

第 148-150 行，修改 badge：

```tsx
// 修改前:
<span className="rounded bg-primary/10 px-2 py-1 font-mono text-xs text-primary">
  ATOM-01
</span>

// 修改后:
{robotModelName ? (
  <span className="rounded bg-primary/10 px-2 py-1 font-mono text-xs text-primary">
    {robotModelName}
  </span>
) : null}
```

- [ ] **Step 4: 在调用方传递 robotModelName**

在 `SOPMaintenancePage.tsx` 约第 1314 行的 `<SOPMaintenanceLeftRail>` 调用处添加 prop：

```tsx
<SOPMaintenanceLeftRail
    robotModelName={currentRobot?.model_name}
    sopTitle={activeSopScript?.title ?? 'SOP 步骤导航'}
    // ...其他 props 不变
/>
```

- [ ] **Step 5: 验证**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 6: Commit**

```bash
git add r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-frontend/src/components/Maintenance/SOPMaintenanceShell.tsx
git commit -m "fix: replace hardcoded ATOM-01 badge with dynamic robotModelName prop"
```

---

## Phase 2 — 前端 Manifest 接通

### Task 4: 补全 joints 类型让 MonitorPage 走 manifest

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts:143-152`
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx:36-51`

**背景：** `MonitorPage` 已有 `buildJointMetaFromManifest()` 实现 (lines 55-71)，但 `RobotDataManifest` 类型缺少 `joints` 字段，导致 `manifest.joints` 始终为 `undefined`。后端 `assembly_manifest.json` 已包含 `joints` 数组。`MonitorPage` 当前通过 `(manifest as any).display_names` 方式读取未类型化字段（line 253），说明 manifest JSON 实际返回了比类型定义更多的字段。

- [ ] **Step 1: 给 RobotDataManifest 添加 joints 字段**

在 `assemblyManifest.ts` 约第 143-152 行的 `RobotDataManifest` 接口中添加：

```typescript
export interface ManifestJointEntry {
  name: string
  type: string                    // 'revolute' | 'fixed' | 'continuous' | ...
  parent_link: string
  child_link: string
}

export interface RobotDataManifest extends AssemblyManifest {
  joints?: ManifestJointEntry[]    // 新增
  parts_registry?: ManifestPartEntry[]
  screw_instances?: ManifestScrewEntry[]
  constraints?: ManifestConstraintEntry[]
  camera_presets?: Record<string, ManifestCameraPreset>
  explode_offsets?: ManifestExplodeOffset[]
  tools?: ManifestToolEntry[]
  display_names?: Record<string, string>
  overview_config?: ManifestOverviewConfig
}
```

- [ ] **Step 2: 删除 MonitorPage 中的 ATOM01_JOINT_META 和 as any 类型绕过**

在 `MonitorPage.tsx`：

删除第 36-48 行的 `ATOM01_JOINT_META` 常量。

修改第 50-51 行的 `resolveJointMeta`：

```typescript
// 修改前:
function resolveJointMeta(jointId: string): MonitorJointMeta | null {
  return MONITOR_JOINT_MAP[jointId] ?? ATOM01_JOINT_META[jointId] ?? null
}

// 修改后:
function resolveJointMeta(jointId: string): MonitorJointMeta | null {
  return MONITOR_JOINT_MAP[jointId] ?? null
}
```

修改第 251-254 行，移除 `as any`：

```typescript
// 修改前:
const manifestJointMeta = useMemo(() => {
  if (!manifest) return null
  const displayNames = (manifest as any).display_names ?? {}
  return buildJointMetaFromManifest(manifest, displayNames)
}, [manifest])

// 修改后:
const manifestJointMeta = useMemo(() => {
  if (!manifest) return null
  const displayNames = manifest.display_names ?? {}
  return buildJointMetaFromManifest(manifest, displayNames)
}, [manifest])
```

注意：`buildJointMetaFromManifest` 的参数类型签名接受 `{ joints?: Array<...> } | null`，`RobotDataManifest` 加了 `joints` 字段后自动满足。

- [ ] **Step 3: 验证**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts r-mos-frontend/src/pages/MonitorPage.tsx
git commit -m "feat: add joints type to RobotDataManifest, remove ATOM01_JOINT_META"
```

---

### Task 5: 接通 manifest 零件/螺丝注入，删除硬编码数据

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx:284`
- Modify: `r-mos-frontend/src/adjudication/data/partRegistry.ts` — 删除 `buildPartRegistry()`、`PART_SCHEMA_REGISTRY`、`PART_SCREWS_REGISTRY`
- Modify: `r-mos-frontend/src/adjudication/data/screwInstances.ts` — 删除所有硬编码螺丝常量

**背景：**
- `partRegistry.ts` 已有 `injectManifestPartRegistry(manifest)` 和 `clearManifestPartRegistry()` 函数
- `getPartById()`、`getPartScrews()`、`getPartsByCategory()` 已有 `if (_manifestPartRegistry)` 优先分支
- `SOPMaintenancePage` 已调用 `useAssemblyManifest(currentRobot?.id)` 获取 manifest
- 只需在 manifest 加载后调用 `injectManifestPartRegistry`，然后删除硬编码回退数据

- [ ] **Step 1: 先审计所有硬编码常量的导入方**

```bash
cd r-mos-frontend && grep -rn "FOOT_SCREW_INSTANCES\|TORSO_SCREW_INSTANCES\|ALL_SCREW_INSTANCES\|PART_SCHEMA_REGISTRY\|PART_SCREWS_REGISTRY\|buildPartRegistry\|buildPartSchemaRegistry" src/ --include="*.ts" --include="*.tsx" | grep -v "__tests__" | grep -v ".test." | grep -v "node_modules"
```

记录所有引用位置，确保后续步骤覆盖。

- [ ] **Step 2: 在 SOPMaintenancePage 中接通 manifest 注入**

在 `SOPMaintenancePage.tsx` 中添加 import 和 useEffect：

```typescript
// 在文件顶部添加 import:
import { injectManifestPartRegistry, clearManifestPartRegistry } from '@/adjudication/data/partRegistry';

// 在 SOPMaintenancePage 函数体内，manifest 获取之后添加:
useEffect(() => {
    if (manifest?.parts_registry) {
        injectManifestPartRegistry(manifest as RobotDataManifest);
    }
    return () => { clearManifestPartRegistry(); };
}, [manifest]);
```

注意：`manifest` 来自 `useAssemblyManifest(currentRobot?.id)` (line 284)，当 `currentRobot` 切换时会自动重新获取。

- [ ] **Step 3: 删除 screwInstances.ts 中的硬编码数据**

将 `screwInstances.ts` 简化为仅保留类型导出（如果有被其他文件引用的类型），或完全清空内容只保留空导出。

检查 Step 1 的审计结果：
- 如果 `FOOT_SCREW_INSTANCES`/`TORSO_SCREW_INSTANCES` 只被 `partRegistry.ts` 引用 → 可以安全删除整个文件内容
- 如果有其他文件引用 → 先将那些文件改为使用 `getPartById()` 等函数

删除后文件内容：

```typescript
/**
 * @description 螺丝实例数据 — 已迁移至 manifest 驱动
 * @module adjudication/data/screwInstances
 */

// 螺丝实例现在通过 manifest 注入到 partRegistry
// 参见 injectManifestPartRegistry() 和 manifestAdapter.ts
```

- [ ] **Step 4: 删除 partRegistry.ts 中的硬编码数据**

删除以下内容：
1. `buildPartRegistry()` 函数（28 个零件定义，约第 55-385 行）
2. `buildPartSchemaRegistry()` 函数（约第 387-395 行）
3. `PART_SCHEMA_REGISTRY` 常量（约第 401-405 行）
4. `PART_SCREWS_REGISTRY` 常量（约第 410-453 行）
5. `FOOT_SCREW_INSTANCES` / `TORSO_SCREW_INSTANCES` 的 import（第 8 行）
6. 不再需要的 `MODEL_BASE_URL`、`PARTS_BASE`、`getPartRegistryBase` 变量/函数

保留以下内容：
1. Manifest 注入层（`_manifestPartRegistry` 等变量，`injectManifestPartRegistry`，`clearManifestPartRegistry`）
2. 辅助函数 `getPartById()`、`getPartScrews()`、`getPartsByCategory()`，但移除硬编码 fallback 分支

修改辅助函数移除 fallback：

```typescript
export function getPartById(id: string): Part | undefined {
    return _manifestPartRegistry?.[id] ?? _manifestScrewRegistry?.[id];
}

export function getPartScrews(partId: string): string[] {
    return _manifestPartScrews?.[partId] ?? [];
}

export function getPartsByCategory(category: PartCategory): Part[] {
    if (!_manifestPartRegistry) return [];
    const allParts = { ..._manifestPartRegistry, ..._manifestScrewRegistry };
    return Object.values(allParts).filter(p => p.category === category);
}
```

- [ ] **Step 5: 修复所有因删除而断裂的 import**

根据 Step 1 审计结果，修复所有引用已删除常量的文件。将它们改为使用 `getPartById()` 等函数。

- [ ] **Step 6: 验证**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/src/adjudication/data/partRegistry.ts r-mos-frontend/src/adjudication/data/screwInstances.ts r-mos-frontend/src/pages/SOPMaintenancePage.tsx
git commit -m "feat: wire manifest injection, remove 600+ lines of hardcoded ATOM-01 part/screw data"
```

---

## Phase 3 — 后端修复

### Task 6: 移除训练 API 默认 robot_model

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py:114`

**背景：** `WorkbenchDraftRequest.robot_model` 默认为 `"ATOM01"`，导致不传此字段时静默使用 ATOM01。前端 `TrainingWorkbenchDraftPayload` 的 `robotModel` 是必填字段（`string` 类型，非 optional），所以前端总会传值。

- [ ] **Step 1: 移除默认值**

```python
# 修改前 (第 114 行):
robot_model: str = Field(default="ATOM01", min_length=1)

# 修改后:
robot_model: str = Field(min_length=1)
```

- [ ] **Step 2: 验证**

```bash
cd r-mos-backend && python -c "from app.api.v1.endpoints.training import WorkbenchDraftRequest; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/training.py
git commit -m "fix: remove hardcoded ATOM01 default from WorkbenchDraftRequest.robot_model"
```

---

### Task 7: 参数化 Mock LLM 响应

**Files:**
- Modify: `r-mos-backend/app/services/llm/mock_provider.py`
- Modify: `r-mos-backend/app/services/llm/router.py:394-395`

**背景：** `mock_provider.py` 中的 `DIAGNOSIS_RESPONSE` 和 `SOP_GENERATION_RESPONSE` 硬编码了 "ATOM-01 左膝关节轴承更换"。`match_intent(message)` 被 `router.py` 在所有 LLM 提供商失败时调用作为 fallback。

- [ ] **Step 1: 将常量改为工厂函数**

在 `mock_provider.py` 中：

将 `DIAGNOSIS_RESPONSE`（第 18-80 行）改为函数：

```python
def _make_diagnosis_response(robot_model: str = "机器人") -> MockLLMResponse:
    sop_name = f"{robot_model} 左膝关节轴承更换"
    return MockLLMResponse(
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
            f"建议立即执行 **SOP: {sop_name}**，预计耗时约 45 分钟。"
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
            "sop_name": sop_name,
            "estimated_time": "45 分钟",
            "steps_count": 6,
        },
    )
```

同样将 `SOP_GENERATION_RESPONSE`（第 82-103 行）改为函数：

```python
def _make_sop_response(robot_model: str = "机器人") -> MockLLMResponse:
    sop_name = f"{robot_model} 左膝关节轴承更换"
    return MockLLMResponse(
        text=(
            "## 维保方案已生成\n\n"
            "根据诊断结果，我已为您生成针对性维保方案：\n\n"
            f"**SOP: {sop_name}** (6 步)\n\n"
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
            "sop_name": sop_name,
            "estimated_time": "45 分钟",
            "steps_count": 6,
        },
    )
```

`EXPLANATION_RESPONSE` 和 `DEFAULT_RESPONSE` 不含 ATOM-01 引用，保持不变。

- [ ] **Step 2: 修改 match_intent 接受 robot_model 参数**

```python
# 修改前:
def match_intent(message: str) -> MockLLMResponse:

# 修改后:
def match_intent(message: str, robot_model: str = "机器人") -> MockLLMResponse:
```

函数体中将 `DIAGNOSIS_RESPONSE` 替换为 `_make_diagnosis_response(robot_model)`，`SOP_GENERATION_RESPONSE` 替换为 `_make_sop_response(robot_model)`。

- [ ] **Step 3: 修改 router.py 调用方传递 robot_model**

在 `router.py` 约第 394-395 行：

```python
# 修改前:
last_msg = messages[-1].get("content", "") if messages else ""
mock_result = match_intent(last_msg)

# 修改后:
last_msg = messages[-1].get("content", "") if messages else ""
mock_result = match_intent(last_msg)
```

注意：`router.py` 的 `chat()` 方法不接收 `robot_model` 参数。在当前架构下，mock fallback 不知道是哪个机器人。这是可以接受的——mock 响应使用通用的 "机器人" 作为默认值。如果未来需要在 mock 中也区分机器人，可以在 `chat()` 方法中添加 `context` 参数。当前不需要改 router.py。

- [ ] **Step 4: 验证**

```bash
cd r-mos-backend && python -c "from app.services.llm.mock_provider import match_intent; r = match_intent('诊断'); print('ATOM' not in r.text)"
```

预期输出: `True`

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/services/llm/mock_provider.py
git commit -m "refactor: parameterize mock LLM responses, remove hardcoded ATOM-01 SOP names"
```

---

### Task 8: 工作台生成器从 manifest 动态加载 link 名称

**Files:**
- Modify: `r-mos-backend/app/services/training/workbench_draft_generator.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py:111-116, 375-378`

**背景：**
- `_build_prompt()` 第 134 行硬编码了 ATOM01 的 link 名称列表
- `_build_fallback_payload()` 第 169 行硬编码了 `"torso_link"`
- `_default_focus_target()` 第 273-285 行硬编码了中文关键词 → ATOM01 link 名称的映射
- `_normalize_model_targets()` 第 301-304 行硬编码了 `"torso_link"`
- 解决方案：从 `assembly_manifest.json` 加载 node IDs 和 `display_names`，反转 `display_names` 作为关键词映射

- [ ] **Step 1: 给 WorkbenchDraftRequest 添加 robot_id 字段**

在 `training.py` 的 `WorkbenchDraftRequest`：

```python
class WorkbenchDraftRequest(BaseModel):
    """训练工作台空态草案生成请求。"""
    robot_model: str = Field(min_length=1)
    robot_id: int | None = None
    task_summary: str = Field(default="关节电机盖拆装", min_length=1)
    focus_prompt: str = Field(default="强调工具确认、证据留存与 AI 提示", min_length=1)
```

修改 endpoint 调用传递 `robot_id`：

```python
payload = await TrainingWorkbenchDraftGenerator(db).generate(
    user_id=actor.user_id,
    robot_model=request.robot_model,
    robot_id=request.robot_id,
    task_summary=request.task_summary,
    focus_prompt=request.focus_prompt,
)
```

- [ ] **Step 2: 修改 generate() 方法加载 manifest**

在 `workbench_draft_generator.py` 中添加 manifest 加载逻辑：

```python
import json
from pathlib import Path

class TrainingWorkbenchDraftGenerator:

    async def generate(
        self,
        *,
        user_id: int,
        robot_model: str,
        robot_id: int | None = None,
        task_summary: str,
        focus_prompt: str,
    ) -> dict:
        # 加载机器人 manifest 获取 link 名称
        link_names, display_names = self._load_robot_manifest(robot_id)

        llm_pref = await self._get_llm_preference(user_id)
        response = await llm_router.chat(
            messages=[{"role": "user", "content": self._build_prompt(robot_model, task_summary, focus_prompt, link_names=link_names)}],
            provider=self._map_provider(llm_pref["provider"]),
            model=llm_pref["model"],
            temperature=0.4,
            max_tokens=1800,
            api_key=llm_pref["api_key"],
            base_url=llm_pref["base_url"] or None,
        )
        normalized_content = self._strip_reasoning_blocks(response.content)
        try:
            payload = self._parse_response(normalized_content)
        except json.JSONDecodeError:
            payload = self._build_fallback_payload(
                robot_model=robot_model,
                task_summary=task_summary,
                focus_prompt=focus_prompt,
                llm_text=normalized_content,
                link_names=link_names,
                display_names=display_names,
            )
        return self._normalize_payload(payload, robot_model=robot_model, task_summary=task_summary, link_names=link_names, display_names=display_names)
```

- [ ] **Step 3: 添加 _load_robot_manifest 方法**

```python
@staticmethod
def _load_robot_manifest(robot_id: int | None) -> tuple[list[str], dict[str, str]]:
    """从 assembly_manifest.json 加载 link 名称和 display_names。"""
    if not robot_id:
        return [], {}
    manifest_path = Path("data/robot-assets") / str(robot_id) / "manifests" / "assembly_manifest.json"
    if not manifest_path.exists():
        return [], {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        link_names = [
            n["link_name"] for n in nodes
            if n.get("link_name") and n.get("mesh_id")
        ]
        display_names = data.get("display_names", {})
        return link_names, display_names
    except (json.JSONDecodeError, KeyError):
        return [], {}
```

- [ ] **Step 4: 修改 _build_prompt 使用动态 link 名称**

```python
def _build_prompt(self, robot_model: str, task_summary: str, focus_prompt: str, *, link_names: list[str] | None = None) -> str:
    # ...前面不变...
    
    # 第 134 行区域，替换硬编码：
    link_hint = ""
    if link_names:
        link_csv = "、".join(link_names[:10])  # 最多列出 10 个
        link_hint = f"\n5. 请优先使用这些 link 名称作为 model_targets：{link_csv}。"
    
    # 在 prompt 模板中使用 link_hint 替换原来的硬编码第 5 条
```

- [ ] **Step 5: 修改 _build_fallback_payload 和 _default_focus_target**

修改 `_build_fallback_payload` 接受 `link_names` 和 `display_names`：

```python
def _build_fallback_payload(self, *, robot_model, task_summary, focus_prompt, llm_text, link_names=None, display_names=None):
    # ...
    first_link = link_names[0] if link_names else "base_link"
    # 第 169 行：用 first_link 替代 "torso_link"
    "model_targets": [first_link],
    # 第 180 行：用动态 focus target
    "model_targets": [self._default_focus_target(task_summary, display_names=display_names, link_names=link_names)],
```

修改 `_default_focus_target` 使用 manifest display_names：

```python
@staticmethod
def _default_focus_target(task_summary: str, *, display_names: dict[str, str] | None = None, link_names: list[str] | None = None) -> str:
    # 优先使用 manifest display_names（反转：中文名 → link_id）
    if display_names:
        for link_id, chinese_name in display_names.items():
            if chinese_name and chinese_name in task_summary:
                return link_id
    # fallback：使用第一个 link
    if link_names:
        return link_names[0]
    return "base_link"
```

同样修改 `_normalize_model_targets` 中第 302-304 行的 `"torso_link"` 引用：

```python
def _normalize_model_targets(self, raw_targets, *, title, instruction, task_summary, link_names=None, display_names=None):
    # ...existing validation...
    first_link = link_names[0] if link_names else "base_link"
    combined = f"{title} {instruction} {task_summary}"
    if any(keyword in combined for keyword in ("准备", "工位", "断电", "安全")):
        return [first_link]
    if any(keyword in combined for keyword in ("线缆", "接头", "连接")):
        return [first_link, self._default_focus_target(task_summary, display_names=display_names, link_names=link_names)]
    return [self._default_focus_target(task_summary, display_names=display_names, link_names=link_names)]
```

- [ ] **Step 6: 验证**

```bash
cd r-mos-backend && python -c "
from app.services.training.workbench_draft_generator import TrainingWorkbenchDraftGenerator
g = TrainingWorkbenchDraftGenerator.__new__(TrainingWorkbenchDraftGenerator)
links, names = g._load_robot_manifest(1)
print(f'Links: {len(links)}, display_names: {len(names)}')
print('ATOM' not in str(g._default_focus_target('膝盖', display_names=names, link_names=links)))
"
```

- [ ] **Step 7: Commit**

```bash
git add r-mos-backend/app/services/training/workbench_draft_generator.py r-mos-backend/app/api/v1/endpoints/training.py
git commit -m "feat: load link names from manifest, remove all ATOM01 hardcoding from draft generator"
```

---

## Phase 4 — 最终验证

### Task 9: Grep 审计 + 回归验证

- [ ] **Step 1: 运行最终 grep 审计**

```bash
grep -rn "ATOM-01\|ATOM01" r-mos-backend/app/ r-mos-frontend/src/ \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  | grep -v "__tests__" | grep -v ".test." | grep -v "node_modules"
```

**预期：零匹配。** 如果有残留，逐一检查并修复。

- [ ] **Step 2: 前端类型检查**

```bash
cd r-mos-frontend && npx tsc --noEmit
```

- [ ] **Step 3: 后端 import 检查**

```bash
cd r-mos-backend && python -c "
from app.api.v1.endpoints.training import WorkbenchDraftRequest
from app.services.llm.mock_provider import match_intent
from app.services.training.workbench_draft_generator import TrainingWorkbenchDraftGenerator
print('All imports OK')
"
```

- [ ] **Step 4: Commit (如有额外修复)**

```bash
git add -A && git commit -m "chore: final cleanup — zero ATOM-01 hardcoding in runtime code"
```
