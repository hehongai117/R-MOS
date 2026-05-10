# Phase 5: 3D 查看器动态加载 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 3D 查看器从硬编码 atom01 静态路径迁移到基于 robot_model_id 的 API 动态加载，最终删除 1.6GB 静态文件。

**Architecture:** 核心变更是让 Atom01Model/Atom01Interactive/useAtom01AssemblyData 三个模块接受外部传入的 robotId 参数，不再在模块顶层硬编码 `getRobotModelBase('atom01')`。MonitorPage 使用 robotContextStore 的 currentRobot 作为数据源。所有对 `public/models/robots/atom01/` 的引用改为走 `/api/v1/robots/{id}/assets/` API。保留 `STATIC_ROBOT_CATALOG` 作为 fallback 直到 Task 5.5 最终清理。

**Tech Stack:** React 18 + TypeScript + react-three-fiber + drei + Zustand + FastAPI asset API

**前置依赖:**
- Phase 1 产出：`GET /api/v1/robots/{id}/assets/{path}` 端点
- Phase 4 产出：`useRobotContextStore()` with `currentRobotId` / `currentRobot`
- `config/robots.ts`：`getRobotModelBase()` / `getRobotManifestUrl()` 已支持动态 API URL

---

## 文件结构概览

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `src/components/Viewer3D/Atom01Model.tsx` | 接受 robotId prop，移除模块顶层常量 |
| Modify | `src/components/Viewer3D/Atom01Viewer.tsx` | 透传 robotId prop |
| Modify | `src/components/Viewer3D/Atom01Interactive.tsx` | 接受 robotId prop，动态 preload |
| Modify | `src/components/Viewer3D/hooks/useAtom01AssemblyData.ts` | 接受 robotId 参数 |
| Create | `src/components/Viewer3D/DynamicModelLoader.tsx` | 加载进度条 + 错误兜底 UI 组件 |
| Modify | `src/pages/MonitorPage.tsx` | 从 robotContextStore 获取 robotId，空状态兜底 |
| Modify | `src/components/Viewer3D/ModelPreloader.tsx` | 移除硬编码路径 |
| Modify | `src/pages/Atom01DemoPage.tsx` | 注入 robotId |
| Modify | `src/pages/SOPMaintenancePage.tsx` | 注入 robotId |
| Modify | `src/teaching/pages/TeachingAttemptPage.tsx` | 注入 robotId |
| Modify | `src/adjudication/data/partRegistry.ts` | 接受动态 robotId |
| Modify | `src/data/maintenanceKnowledge.ts` | 接受动态 robotId |
| Delete | `public/models/robots/atom01/` | 最终删除 1.6GB（Task 5.5） |

---

### Task 5.1: Atom01Model / Atom01Viewer 接受 robotId prop

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Viewer.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/Atom01Model.dynamic.test.tsx`（新建）

**目标:** 将 `MODEL_BASE_PATH = getRobotModelBase('atom01')` 从模块顶层常量改为组件 prop，使 GLB 加载路径动态化。

- [ ] **Step 1: 修改 Atom01Model.tsx — 添加 robotId prop**

删除模块顶层的 `MODEL_BASE_PATH` 常量，改为在组件内部根据 prop 计算。

```typescript
// 删除这两行：
// const MODEL_BASE_PATH = getRobotModelBase('atom01');
// LINK_NAMES.forEach(name => { useGLTF.preload(`${MODEL_BASE_PATH}/${name}.glb`); });

// 在 Atom01ModelProps 中添加：
export interface Atom01ModelProps {
    robotId?: string;  // 新增，默认 'atom01'
    jointAngles?: Record<string, number>;
    faultJoints?: string[];
    highlightLinks?: string[];
    scale?: number;
    position?: [number, number, number];
}

// 在 Atom01Model 组件内部：
export const Atom01Model: React.FC<Atom01ModelProps> = ({
    robotId = 'atom01',
    jointAngles = {},
    // ...其余 props
}) => {
    const modelBasePath = useMemo(() => getRobotModelBase(robotId), [robotId]);

    // LinkMesh 组件也需要接受 modelBasePath
    // ...
```

核心改动：
- `Atom01ModelProps` 新增可选 `robotId?: string`（默认 `'atom01'`）
- 删除模块顶层 `MODEL_BASE_PATH` 和 `useGLTF.preload()` 调用
- `LinkMesh` 子组件接受 `modelBasePath` prop 替代闭包引用
- 在组件内用 `useMemo(() => getRobotModelBase(robotId), [robotId])` 计算路径

- [ ] **Step 2: 修改 Atom01Viewer.tsx — 透传 robotId**

```typescript
export interface Atom01ViewerProps extends Atom01ModelProps {
    // robotId 已经从 Atom01ModelProps 继承
    width?: string | number;
    height?: string | number;
    // ...其余不变
}

// 在 JSX 中透传：
<Atom01Model robotId={robotId} ... />
<Atom01Interactive robotId={robotId} ... />
```

- [ ] **Step 3: 修改 Atom01Interactive.tsx — 添加 robotId prop**

同样的模式：删除模块顶层 `MODEL_BASE_PATH`，改为组件内部计算。

```typescript
// 删除：
// const MODEL_BASE_PATH = getRobotModelBase('atom01');
// LINK_NAMES.forEach(name => { useGLTF.preload(`${MODEL_BASE_PATH}/${name}.glb`); });

export interface Atom01InteractiveProps {
    robotId?: string;  // 新增
    jointAngles?: Record<string, number>;
    // ...其余不变
}

// 在组件内部：
const modelBasePath = useMemo(() => getRobotModelBase(robotId), [robotId]);
```

注意：`InteractiveLinkMesh` 和 `SubPartsGroup` 子组件也需要接受 `modelBasePath` 参数。`InteractiveLinkMesh` 内部的 `useGLTF(\`${MODEL_BASE_PATH}/${name}.glb\`)` 需要改为 `useGLTF(\`${modelBasePath}/${name}.glb\`)`。

- [ ] **Step 4: 修改 useAtom01AssemblyData.ts — 接受 robotId 参数**

```typescript
// 删除：
// const ATOM01_MODEL_BASE = getRobotModelBase('atom01')

export function useAtom01AssemblyData(enabled = true, robotId = 'atom01'): UseAtom01AssemblyDataResult {
    const modelBase = useMemo(() => getRobotModelBase(robotId), [robotId]);

    // ...在 load() 中使用 modelBase：
    const [assemblyRaw, explodeRaw] = await Promise.all([
        fetchJson(`${modelBase}/assembly_manifest.json`),
        fetchJson(`${modelBase}/explode_manifest.json`),
    ]);
```

- [ ] **Step 5: 更新 ModelPreloader.tsx — 移除硬编码路径**

```typescript
// 删除：
// const ROBOT_BASE = '/models/robots/atom01';
// 改为接受 robotId 参数或从 context 获取
```

`ModelPreloader.tsx:64` 硬编码了 `/models/robots/atom01`，改为使用 `getRobotModelBase(robotId)` 并从 prop 或 context 获取 robotId。

- [ ] **Step 6: 运行现有测试确认无回归**

```bash
cd r-mos-frontend && npx vitest run --reporter=verbose src/components/Viewer3D/ 2>&1 | tail -30
```

预期：所有现有测试仍然通过（因为 robotId 默认值是 `'atom01'`，行为不变）。

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx \
       r-mos-frontend/src/components/Viewer3D/Atom01Viewer.tsx \
       r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx \
       r-mos-frontend/src/components/Viewer3D/hooks/useAtom01AssemblyData.ts \
       r-mos-frontend/src/components/Viewer3D/ModelPreloader.tsx
git commit -m "feat(viewer3d): accept robotId prop for dynamic model loading (Phase 5, Task 5.1)"
```

---

### Task 5.2: 加载状态与错误处理 UI 组件

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/DynamicModelLoader.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Viewer.tsx`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/DynamicModelLoader.test.tsx`（新建）

**目标:** 为动态加载 GLB 提供用户友好的加载进度条、加载失败提示、模型不存在兜底 UI。

- [ ] **Step 1: 创建 DynamicModelLoader.tsx — 加载状态 UI**

```tsx
import React, { Suspense } from 'react';
import { Html, useProgress } from '@react-three/drei';

/** 3D Canvas 内的加载进度显示 */
export const ModelLoadingFallback: React.FC = () => {
    const { progress } = useProgress();
    return (
        <Html center>
            <div style={{
                color: '#4fc3f7',
                fontFamily: 'monospace',
                fontSize: '14px',
                textAlign: 'center',
                whiteSpace: 'nowrap',
            }}>
                <div style={{ marginBottom: 8 }}>加载模型中...</div>
                <div style={{
                    width: 120,
                    height: 4,
                    background: '#1e3a5f',
                    borderRadius: 2,
                    overflow: 'hidden',
                }}>
                    <div style={{
                        width: `${progress}%`,
                        height: '100%',
                        background: '#4fc3f7',
                        transition: 'width 0.2s ease',
                    }} />
                </div>
                <div style={{ marginTop: 4, fontSize: 11, opacity: 0.7 }}>
                    {Math.round(progress)}%
                </div>
            </div>
        </Html>
    );
};

/** 加载失败兜底 — 显示在 3D Canvas 内 */
export const ModelErrorFallback: React.FC<{ message?: string }> = ({
    message = '模型加载失败',
}) => {
    return (
        <Html center>
            <div style={{
                color: '#ff6b6b',
                fontFamily: 'monospace',
                fontSize: '14px',
                textAlign: 'center',
                padding: '16px 24px',
                background: 'rgba(255, 107, 107, 0.1)',
                borderRadius: 8,
                border: '1px solid rgba(255, 107, 107, 0.3)',
            }}>
                <div style={{ marginBottom: 4 }}>{message}</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>
                    请检查机器人是否已上传 3D 模型文件
                </div>
            </div>
        </Html>
    );
};

/** 无模型数据兜底 — 占位立方体 */
export const ModelEmptyFallback: React.FC = () => {
    return (
        <mesh>
            <boxGeometry args={[0.5, 0.5, 0.5]} />
            <meshStandardMaterial color="#4fc3f7" wireframe opacity={0.3} transparent />
        </mesh>
    );
};
```

- [ ] **Step 2: 在 Atom01Viewer.tsx 中替换 LoadingFallback**

```tsx
import { ModelLoadingFallback } from './DynamicModelLoader';

// 替换原来的 LoadingFallback 组件：
// 删除旧的 const LoadingFallback = () => (...)
// 在 <Suspense> 中使用新组件：
<Suspense fallback={<ModelLoadingFallback />}>
```

- [ ] **Step 3: 编写 DynamicModelLoader 测试**

```tsx
// __tests__/DynamicModelLoader.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Mock drei Html component for DOM testing
vi.mock('@react-three/drei', () => ({
    Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    useProgress: () => ({ progress: 50 }),
}))

import { ModelErrorFallback } from '../DynamicModelLoader'

describe('ModelErrorFallback', () => {
    it('renders default error message', () => {
        render(<ModelErrorFallback />)
        expect(screen.getByText('模型加载失败')).toBeTruthy()
    })

    it('renders custom error message', () => {
        render(<ModelErrorFallback message="自定义错误" />)
        expect(screen.getByText('自定义错误')).toBeTruthy()
    })
})
```

- [ ] **Step 4: 运行测试**

```bash
cd r-mos-frontend && npx vitest run src/components/Viewer3D/__tests__/DynamicModelLoader.test.tsx --reporter=verbose
```

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/DynamicModelLoader.tsx \
       r-mos-frontend/src/components/Viewer3D/__tests__/DynamicModelLoader.test.tsx \
       r-mos-frontend/src/components/Viewer3D/Atom01Viewer.tsx
git commit -m "feat(viewer3d): add loading progress bar and error fallback UI (Phase 5, Task 5.2)"
```

---

### Task 5.3: 页面集成 — 所有消费者注入 robotId

**Files:**
- Modify: `r-mos-frontend/src/pages/Atom01DemoPage.tsx`
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- Modify: `r-mos-frontend/src/teaching/pages/TeachingAttemptPage.tsx`
- Modify: `r-mos-frontend/src/adjudication/data/partRegistry.ts`
- Modify: `r-mos-frontend/src/data/maintenanceKnowledge.ts`

**目标:** 让所有使用 3D 查看器的页面从 `robotContextStore` 获取当前机器人 ID 并传给查看器组件，而不是硬编码 `'atom01'`。

- [ ] **Step 1: 修改 Atom01DemoPage.tsx**

```tsx
import { useRobotContextStore } from '@/store/robotContextStore';

function Atom01DemoPage() {
    const currentRobot = useRobotContextStore((s) => s.currentRobot);
    // robotId: 如果有选中的机器人就用它，否则 fallback 到 'atom01'
    const robotId = currentRobot ? String(currentRobot.id) : 'atom01';

    // 传给 useAtom01AssemblyData:
    const { explodeManifest, isLoading, error } = useAtom01AssemblyData(true, robotId);

    // 传给 Atom01Viewer:
    <Atom01Viewer robotId={robotId} ... />
```

- [ ] **Step 2: 修改 SOPMaintenancePage.tsx**

```tsx
import { useRobotContextStore } from '@/store/robotContextStore';

// 在组件内部：
const currentRobot = useRobotContextStore((s) => s.currentRobot);
const robotId = currentRobot ? String(currentRobot.id) : 'atom01';

// 传给 Atom01Interactive:
<Atom01Interactive robotId={robotId} ... />
```

- [ ] **Step 3: 修改 TeachingAttemptPage.tsx**

```tsx
import { useRobotContextStore } from '@/store/robotContextStore';

const currentRobot = useRobotContextStore((s) => s.currentRobot);
const robotId = currentRobot ? String(currentRobot.id) : 'atom01';

<Atom01Interactive robotId={robotId} ... />
```

- [ ] **Step 4: 修改 partRegistry.ts — 改为函数参数**

```typescript
// 删除模块顶层：
// const ROBOT_BASE = getRobotModelBase('atom01');

// 改为在需要的函数中接受 robotId 参数，或使用工厂模式：
export function getPartRegistryBase(robotId: string = 'atom01'): string {
    return getRobotModelBase(robotId);
}
```

- [ ] **Step 5: 修改 maintenanceKnowledge.ts — 改为函数参数**

```typescript
// 删除模块顶层：
// const ROBOT_MODEL_BASE = getRobotModelBase('atom01');

// 改为在需要的函数中接受 robotId 参数
```

- [ ] **Step 6: 运行全量前端测试确认无回归**

```bash
cd r-mos-frontend && npx vitest run --reporter=verbose 2>&1 | tail -40
```

- [ ] **Step 7: Commit**

```bash
git add r-mos-frontend/src/pages/Atom01DemoPage.tsx \
       r-mos-frontend/src/pages/SOPMaintenancePage.tsx \
       r-mos-frontend/src/teaching/pages/TeachingAttemptPage.tsx \
       r-mos-frontend/src/adjudication/data/partRegistry.ts \
       r-mos-frontend/src/data/maintenanceKnowledge.ts
git commit -m "feat(pages): inject dynamic robotId from context store into all 3D viewers (Phase 5, Task 5.3)"
```

---

### Task 5.4: MonitorPage 动态适配

**Files:**
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx`
- Test: 修改现有 `r-mos-frontend/src/pages/__tests__/MonitorPage.test.tsx`

**目标:** MonitorPage 的关节映射和 3D 查看器使用 robotContextStore 的当前机器人，提供"未选择机器人"空状态兜底。

- [ ] **Step 1: 修改 MonitorPage.tsx — 引入 robotContextStore**

```tsx
import { useRobotContextStore } from '@/store/robotContextStore';

function MonitorPage() {
    const navigate = useNavigate();
    const currentRobot = useRobotContextStore((s) => s.currentRobot);
    const robotId = currentRobot ? String(currentRobot.id) : 'atom01';

    // ...把 robotId 传给 Atom01Viewer：
    <Atom01Viewer
        robotId={robotId}
        width="100%"
        height={460}
        ...
    />
```

- [ ] **Step 2: 添加"未选择机器人"空状态**

在 `MonitorPage` 组件顶部添加：

```tsx
if (!currentRobot) {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
            <WifiOff className="mb-4 h-12 w-12 opacity-30" />
            <h2 className="text-lg font-medium text-text-primary mb-2">未选择机器人</h2>
            <p className="text-sm">请先在首页选择一台机器人，再进入监控面板。</p>
        </div>
    );
}
```

- [ ] **Step 3: 将 MONITOR_JOINT_MAP / ATOM01_JOINT_META 保留为 atom01 默认值**

当前的关节映射是 atom01 特有的。对于 MVP 阶段，保留这些映射作为默认值。未来其他机器人的关节映射将来自 manifest JSON。

```tsx
// 保持现有的 MONITOR_JOINT_MAP 和 ATOM01_JOINT_META 不变
// 但在 resolveJointMeta 中添加一个 fallback:
function resolveJointMeta(jointId: string): MonitorJointMeta | null {
    // 先查 atom01 映射，后续可从 manifest 动态加载
    return MONITOR_JOINT_MAP[jointId] ?? ATOM01_JOINT_META[jointId] ?? null;
}
```

这部分暂不需要修改，因为对于 atom01 映射已经正确，对于新机器人则会 fallback 到 `null`，UI 会显示 `joint.joint_id` 原始名称（`MonitorJointRow` 已经有 `meta?.label ?? joint.joint_id` 兜底）。

- [ ] **Step 4: 运行 MonitorPage 测试**

```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/MonitorPage.test.tsx --reporter=verbose
```

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/pages/MonitorPage.tsx \
       r-mos-frontend/src/pages/__tests__/MonitorPage.test.tsx
git commit -m "feat(monitor): use dynamic robotId from context store with empty-state fallback (Phase 5, Task 5.4)"
```

---

### Task 5.5: 删除 atom01 静态文件 + 最终验证

**Files:**
- Delete: `r-mos-frontend/public/models/robots/atom01/` (1.6GB)
- Modify: `r-mos-frontend/src/config/robots.ts` — 移除 STATIC_ROBOT_CATALOG 中的 atom01 条目
- Modify: `r-mos-frontend/src/components/Viewer3D/ModelPreloader.tsx` — 移除任何残留静态引用

**前置条件:** Task 5.1-5.4 全部完成且测试通过。

> **风险提示:** 此步骤不可逆！删除前必须确认：
> 1. atom01 的 GLB 文件已上传到后端 `data/robot-assets/` 目录（通过 Phase 1 的文件上传 API）
> 2. 通过 API `GET /api/v1/robots/{id}/assets/models/base_link.glb` 能正常获取到文件
> 3. 前端所有页面的 3D 查看器都能正常通过 API 加载模型

- [ ] **Step 1: 验证 API 资产可用性**

```bash
# 确认后端资产目录存在
ls -la r-mos-backend/data/robot-assets/ 2>/dev/null || echo "WARNING: 后端资产目录不存在！需要先通过 Phase 1 API 上传 atom01 资产"
```

如果后端资产目录不存在或未包含 atom01 数据：**停止！** 需要先通过上传 API 将 atom01 的模型文件上传到后端，或手动复制 `public/models/robots/atom01/` 的内容到 `data/robot-assets/{atom01_robot_model_id}/models/`。

- [ ] **Step 2: 修改 config/robots.ts — 移除静态 fallback**

```typescript
// 删除 STATIC_ROBOT_CATALOG 中的 atom01 条目，或将整个 catalog 置空：
export const STATIC_ROBOT_CATALOG: Record<string, { label: string; basePath: string }> = {};

// getRobotModelBase 和 getRobotManifestUrl 的 fallback 分支将不再命中，
// 所有请求都走 API URL
```

- [ ] **Step 3: 删除静态文件**

```bash
rm -rf r-mos-frontend/public/models/robots/atom01/
```

确认删除后目录为空：

```bash
ls r-mos-frontend/public/models/robots/
# 预期输出：空目录或不存在
```

- [ ] **Step 4: 运行全量前端测试**

```bash
cd r-mos-frontend && npx vitest run --reporter=verbose 2>&1 | tail -40
```

注意：部分测试可能依赖静态文件（如 `assemblyManifest.test.ts` 读取 `readJsonFromPublic('models/robots/atom01/...')`），这些测试需要调整为 mock 或跳过。

- [ ] **Step 5: 修复因静态文件删除而失败的测试**

主要需要修复的测试文件：
- `src/components/Viewer3D/__tests__/assemblyManifest.test.ts` — 使用 `readJsonFromPublic` 读取静态 manifest
- `src/components/Viewer3D/hooks/__tests__/useAtom01AssemblyData.test.tsx` — 同上

修复方法：将这些测试改为内联 mock 数据，不再依赖物理文件。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(viewer3d): remove 1.6GB static atom01 assets, all models now served via API (Phase 5, Task 5.5)"
```

---

## 验证清单

完成所有 Task 后的端到端验证：

- [ ] `npm run build` 成功（无 TypeScript 错误）
- [ ] `npx vitest run` 全量测试通过
- [ ] 启动前后端，进入监控页面，3D 模型正常加载
- [ ] 切换不同机器人，3D 查看器动态更新
- [ ] 无机器人选中时，MonitorPage 显示空状态提示
- [ ] SOP 维保工作台 3D 查看器正常
- [ ] `public/models/robots/atom01/` 目录已删除
- [ ] `git status` 确认仓库大小减少 ~1.6GB

## 风险与注意事项

1. **Task 5.5 必须最后执行** — 在 5.1-5.4 全部验证通过后才能删除静态文件
2. **atom01 的 `/atom01` 路由** — 保留为 legacy 入口，但内部逻辑改为动态加载
3. **`public/models/parts/` 目录** — 子零件的详情模型（partsManifest.ts 引用），Phase 5 暂不迁移此目录（与 atom01 GLB 主模型无关）
4. **drei useGLTF 缓存** — drei 的 useGLTF 内部用 URL 作为缓存 key，切换 robotId 时 URL 变化会触发重新加载，这是期望行为
5. **后端资产存在性** — Task 5.5 前必须确认 atom01 的资产已通过 API 可访问
