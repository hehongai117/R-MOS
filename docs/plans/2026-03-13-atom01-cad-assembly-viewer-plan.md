# ATOM01 CAD Assembly Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将当前 ATOM01 的启发式 3D 爆炸图升级为装配树驱动的准 CAD 级装配查看器，支持真实装配位姿、实例级紧固件、作者定义爆炸步骤和工程化验收。

**Architecture:** 保留现有 `robots/atom01/*.glb` 作为 link 级回退资产，在其上新增 `assembly_manifest.json` 与 `explode_manifest.json` 两层数据。导出链路负责把 CAD/STEP 的装配位姿、零件层级和紧固件实例固化为前端可消费的静态清单；前端新增装配树加载器与渲染器，逐步替换当前 `partsManifest + heuristic explode` 逻辑，并保留旧实现作为回退路径。

**Tech Stack:** Python export scripts, existing CAD/STEP assets, React, Three.js, @react-three/fiber, @react-three/drei, Vitest

### Task 1: 固化装配树数据格式与导出入口

**Files:**
- Create: `r-mos-frontend/public/models/robots/atom01/assembly_manifest.json`
- Create: `r-mos-frontend/public/models/robots/atom01/explode_manifest.json`
- Modify: `scripts/convert_step_to_glb.py`
- Create: `scripts/export_atom01_assembly_manifest.py`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/assemblyManifest.test.ts`

**Step 1: Write the failing test**

新增 `assemblyManifest.test.ts`，要求装配清单至少包含：
- `version`
- `robotId`
- `rootNodeId`
- `nodes[]`
- `fastener_instances[]`
- `mesh_catalog`

并断言单个节点必须具有 `id / parent_id / transform / mesh_id / category`。

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/assemblyManifest.test.ts`

Expected: FAIL，因为 `assembly_manifest.json` 和对应解析器尚未存在。

**Step 3: Write minimal implementation**

- 定义 `assembly_manifest.json` 的最小模式：
  - `nodes[]`: 装配树节点，包含局部位姿、层级、零件类别、是否可见
  - `mesh_catalog`: `mesh_id -> glb path`
  - `fastener_instances[]`: 每颗螺钉/螺母/轴承的实例位姿
- 定义 `explode_manifest.json` 的最小模式：
  - `views[]`: 总览视图和关节局部视图
  - `sequences[]`: 每步拆解的 `node_ids / direction / distance / anchor`
- 在 `scripts/export_atom01_assembly_manifest.py` 中读取人工维护的 CSV/JSON 或 CAD 导出中间文件，先生成一版可用静态清单。
- 在 `scripts/convert_step_to_glb.py` 中补 `--preserve-transform`/中间产物约定，避免后续导出流程继续丢失装配位姿。

**Step 4: Run test to verify it passes**

Run: 同 Step 2

Expected: PASS，说明装配清单最小结构已经可被前端识别。

**Step 5: Commit**

`git commit -m "feat: add atom01 assembly and explode manifests"`

### Task 2: 新增装配树类型、加载器和数据适配层

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts`
- Create: `r-mos-frontend/src/components/Viewer3D/hooks/useAtom01AssemblyData.ts`
- Modify: `r-mos-frontend/src/components/Viewer3D/runtimeManifest.ts`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/useAtom01AssemblyData.test.ts`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/runtimeManifest.test.ts`

**Step 1: Write the failing test**

新增 `useAtom01AssemblyData.test.ts`，覆盖：
- 能从 `assembly_manifest.json` 解析出树结构
- 能按 `node_id` 找到后代节点
- 能解析单颗紧固件实例
- 缺失字段时返回明确错误而不是静默回退

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/useAtom01AssemblyData.test.ts src/components/Viewer3D/__tests__/runtimeManifest.test.ts`

Expected: FAIL，因为新的类型和 hook 尚未实现。

**Step 3: Write minimal implementation**

- 在 `assemblyManifest.ts` 中导出：
  - `AssemblyNode`
  - `AssemblyFastenerInstance`
  - `ExplodeSequence`
  - `buildAssemblyIndex()`
  - `collectAssemblyDescendants()`
- 在 `useAtom01AssemblyData.ts` 中封装：
  - manifest fetch
  - index build
  - load/error state
  - 旧 `manifest.json` 回退逻辑
- 在 `runtimeManifest.ts` 中新增统一接口，让运行时项目模型与 ATOM01 静态装配树共享相同消费模式，避免未来两套渲染器长期分叉。

**Step 4: Run test to verify it passes**

Run: 同 Step 2

Expected: PASS

**Step 5: Commit**

`git commit -m "feat: add atom01 assembly data adapter"`

### Task 3: 用装配树替换启发式子件挂接

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/Atom01AssemblyRenderer.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/partsManifest.ts`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/Atom01AssemblyRenderer.test.tsx`
- Test: `r-mos-frontend/src/pages/__tests__/Atom01DemoPage.test.tsx`

**Step 1: Write the failing test**

新增 `Atom01AssemblyRenderer.test.tsx`，要求：
- 给定父子节点位姿时，子节点渲染在正确局部坐标
- `fastener_instances` 会跟随父装配节点显示
- 单关节聚焦时，未选装配能保持参照可见

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/Atom01AssemblyRenderer.test.tsx src/pages/__tests__/Atom01DemoPage.test.tsx`

Expected: FAIL，因为当前渲染仍依赖 link 级 GLB 和启发式散开规则。

**Step 3: Write minimal implementation**

- 新增 `Atom01AssemblyRenderer.tsx`：
  - 按 `assembly_manifest` 递归挂接节点
  - 直接应用局部 `translation / rotation / scale`
  - 对重复紧固件使用实例化渲染
- 在 `Atom01Interactive.tsx` 中停用对装配子件的 `position.sub(center)` 归中逻辑，保留它只用于旧 `partsManifest` 回退模式。
- 在 `Atom01Model.tsx` 中保留 link 级骨架和 joint 链，把装配树节点挂到对应 link 的局部坐标系下。
- 在 `partsManifest.ts` 中降级为兼容层，仅用于旧资产或缺失装配树时回退。

**Step 4: Run test to verify it passes**

Run: 同 Step 2

Expected: PASS

**Step 5: Commit**

`git commit -m "feat: render atom01 detail parts from assembly tree"`

### Task 4: 用作者定义爆炸序列替换算法散开，并补 CAD 风格交互

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/PartInspector.tsx`
- Modify: `r-mos-frontend/src/pages/Atom01DemoPage.tsx`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/explodeSequence.test.ts`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/cadViewControls.test.tsx`

**Step 1: Write the failing test**

新增测试覆盖：
- 爆炸步骤按 `explode_manifest.sequences[]` 顺序执行
- 盖板、法兰、电机、轴承、紧固件按作者定义路径移动
- 切到工程视图时可启用正交相机、轮廓线和引导线

**Step 2: Run test to verify it fails**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/explodeSequence.test.ts src/components/Viewer3D/__tests__/cadViewControls.test.tsx`

Expected: FAIL，因为当前仍是轴向/半径驱动的算法爆炸。

**Step 3: Write minimal implementation**

- 在 `Atom01Interactive.tsx` 中新增 `explodeManifest` 消费逻辑：
  - `step_index`
  - `node_ids`
  - `direction`
  - `distance`
  - `anchor_node_id`
- 新增 CAD 风格查看器控制：
  - 正交/透视切换
  - 轮廓线
  - 爆炸引导线
  - BOM 编号高亮
  - “透明外壳 + 内部总成聚焦” 视图
- 在 `PartInspector.tsx` 和 `Atom01DemoPage.tsx` 中补装配树面板、步骤导航和紧固件筛选。

**Step 4: Run test to verify it passes**

Run: 同 Step 2

Expected: PASS

**Step 5: Commit**

`git commit -m "feat: drive atom01 explode view from authored sequences"`

### Task 5: 建立性能、校核与回归门禁

**Files:**
- Create: `scripts/check_atom01_assembly_manifest.py`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/assemblyPerformance.test.ts`
- Modify: `docs/testing/TEST_PLAN.md`
- Modify: `docs/testing/TEST_REPORT.md`
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Write the failing test**

新增回归检查，要求：
- 装配树节点不存在循环引用
- `mesh_id` 全部可解析
- 紧固件实例有合法父节点
- 目标装配视角下渲染节点数和实例数不超过预算

**Step 2: Run test to verify it fails**

Run:
- `cd /Users/xuhehong/Desktop/r-mos && source r-mos-backend/.venv/bin/activate && python scripts/check_atom01_assembly_manifest.py`
- `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/assemblyPerformance.test.ts`

Expected: FAIL，因为校核脚本和预算测试尚未实现。

**Step 3: Write minimal implementation**

- `check_atom01_assembly_manifest.py` 校验：
  - 树结构连通性
  - 位姿字段完整性
  - 爆炸序列引用有效性
  - 紧固件实例引用有效性
- 在前端增加性能预算测试，至少覆盖：
  - link 级回退模式
  - 单关节局部爆炸
  - 全屏 L2 视图
- 更新 `docs/testing/TEST_PLAN.md` 和 `docs/testing/TEST_REPORT.md`，补 ATOM01 准 CAD 模式的回归入口和验收口径。

**Step 4: Run test to verify it passes**

Run:
- `cd /Users/xuhehong/Desktop/r-mos && source r-mos-backend/.venv/bin/activate && python scripts/check_atom01_assembly_manifest.py`
- `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/assemblyPerformance.test.ts`
- `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build`

Expected:
- 校核脚本 PASS
- Vitest PASS
- 前端构建 PASS

**Step 5: Commit**

`git commit -m "test: add atom01 cad viewer validation gates"`

## Data Contract Draft

`assembly_manifest.json` 建议最小结构：

```json
{
  "version": "2026-03-13",
  "robotId": "atom01",
  "rootNodeId": "base_link",
  "mesh_catalog": {
    "torso_shell_front": "/models/parts/frames/胸腔胸部.glb"
  },
  "nodes": [
    {
      "id": "torso_shell_front",
      "parent_id": "torso_link",
      "mesh_id": "torso_shell_front",
      "category": "frame",
      "transform": {
        "translation": [0, 0, 0],
        "rotation_quat": [0, 0, 0, 1],
        "scale": [1, 1, 1]
      }
    }
  ],
  "fastener_instances": [
    {
      "id": "torso_shell_front_m3x10_01",
      "type": "M3x10",
      "parent_id": "torso_shell_front",
      "mesh_id": "fastener_m3x10_socket_head",
      "transform": {
        "translation": [0, 0, 0],
        "rotation_quat": [0, 0, 0, 1],
        "scale": [1, 1, 1]
      },
      "tool": "hex_2.5",
      "torque_nm": 0.5
    }
  ]
}
```

`explode_manifest.json` 建议最小结构：

```json
{
  "version": "2026-03-13",
  "robotId": "atom01",
  "views": [
    {
      "id": "torso_service_view",
      "focus_node_id": "torso_link",
      "camera": {
        "projection": "orthographic",
        "position": [1.2, 0.8, 0.6],
        "target": [0, 0, 0.2]
      }
    }
  ],
  "sequences": [
    {
      "id": "torso_cover_removal",
      "step_index": 1,
      "node_ids": ["torso_shell_front", "torso_shell_rear"],
      "direction": [0, 0, 1],
      "distance": 0.18,
      "anchor_node_id": "torso_link"
    }
  ]
}
```

## Verification Checklist

- 装配树节点全部可追溯到真实 mesh
- 紧固件从“规格/数量”升级为“实例/位姿”
- 旧 `manifest.json + partsManifest` 路径仍可回退
- 爆炸图步骤由 `explode_manifest` 驱动，不再依赖经验参数
- `/atom01` 页面在桌面端视图下可稳定渲染
- `npm test` 与 `npm run build` 均通过

## Execution Notes

- 第一阶段不强求一次接全机器人，只先覆盖 `torso_link / left_knee_link / right_knee_link / left_arm_pitch_link / right_arm_pitch_link` 五个高价值总成，剩余部位用旧方案回退。
- 若导出链路无法一次从 CAD 自动产出完整装配树，允许先维护人工 `assembly_manifest.json`，但字段命名必须稳定，避免后续重构前端协议。
- 若重复紧固件超过 200 个，执行阶段优先引入 `InstancedMesh`，不要等掉帧后再补。
