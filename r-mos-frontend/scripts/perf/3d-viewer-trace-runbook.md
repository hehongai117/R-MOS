# 3D 查看器渲染性能 Trace Runbook

> **用途**：在 SOP 维护页与 Monitor 页采集可复现的 3D 渲染性能基线。  
> **性质**：只读 / 只测量——不修改任何产品代码。  
> **基线记录位置**：`docs/superpowers/plans/phase4-baseline.md` 的 **"3D 渲染"** 段（Task B5 创建；按第 5 节表格模板回填）。

---

## 目录

1. [前置条件](#1-前置条件)
2. [Scenario A：SOP 维护页（Atom01Interactive 路径）](#2-scenario-a-sop-维护页)
3. [Scenario B：Monitor 页（ManifestDrivenRenderer 路径）](#3-scenario-b-monitor-页)
4. [需要采集的指标及读取位置](#4-需要采集的指标及读取位置)
5. [基线文档表格模板](#5-基线文档表格模板)
6. [待印证热点假设](#6-待印证热点假设)

---

## 1 前置条件

| 项目 | 要求 |
|------|------|
| 浏览器 | Chrome ≥ 120（DevTools Performance 面板） |
| 后端 | `python main.py` 已启动，健康检查 `GET /api/v1/health` 返回 200 |
| 前端 | `npm run dev`（Vite 开发服务器，`http://localhost:5173`） |
| 机器人数据 | ATOM-01（robotId = `"atom01"` / 数据库 id = 1）或已导入组件清单的机器人，WebSocket 遥测正常推送 |
| 浏览器缓存 | 每次 Scenario 前执行 **Hard Reload + Empty Cache**（DevTools → Network → ☑ Disable cache，或 Ctrl+Shift+R） |
| CPU 节流 | DevTools → Performance → ⚙ → CPU throttling 设为 **4× slowdown**，模拟中端设备 |

### 1.1 使用 Chrome DevTools Performance 面板

1. 打开 DevTools → **Performance** 标签。
2. 点击 ⚙ → 勾选 **"Web Vitals"** 与 **"Screenshots"**，确认 **"Enable advanced paint instrumentation"** 已开启（用于 GPU 图层信息）。
3. 按 ⏺ 开始录制；完成操作序列后按 ⏹ 停止。
4. 保存 `.json` trace：录制结果区右键 → "Save profile"，写入 `scripts/perf/out/` 目录。

### 1.2 使用 MCP chrome-devtools（自动化采集）

若通过 Claude Code 调用 MCP 工具：

```
performance_start_trace({ categories: ["blink.user_timing", "devtools.timeline", "disabled-by-default-devtools.timeline.frame", "v8.execute", "disabled-by-default-devtools.timeline.gpu"] })
# ← 执行操作序列 →
performance_stop_trace({ outputPath: "scripts/perf/out/3d-viewer-<scenario>-<date>.json" })
```

> Trace 文件可在 Chrome DevTools → Performance → "Load profile" 中二次分析。

---

## 2 Scenario A：SOP 维护页

**目标组件**：`src/pages/sopMaintenance/SOPViewerScene.tsx` → `Atom01Interactive`（`src/components/Viewer3D/Atom01Interactive.tsx`）  
**典型路径**：`http://localhost:5173/sop-maintenance`

### 2.1 操作脚本（Step-by-Step）

每步之间 **等待 3D 场景静止**（无 spinner，帧率稳定）再继续。

| 步骤 | 操作 | 等待/观察 |
|------|------|-----------|
| A-0 | **开始录制** trace | — |
| A-1 | 打开 `http://localhost:5173/sop-maintenance`；若有机器人选择器，选 **ATOM-01** | 等待 3D Canvas 出现；`Atom01Interactive` 挂载时触发 24 次 `useGLTF()` 并发 GLB 加载 |
| A-2 | 等待"加载 3D 模型..."蓝色 wireframe 方块（`LoadingFallback`）消失，模型完整显示 | **记录时间戳 T_first_frame**（首个可交互 3D 帧）|
| A-3 | 在 3D 视图中**点击**任意核心部件（例如 `torso_link` / 躯干），进入 L1 隔离态（viewState → ISOLATED） | 观察页面右上角"总览"/"隔离"状态标签切换；其余 link 半透明淡出（Gate-1 fade，opacity 0.12-0.15） |
| A-4 | 在页面顶部切换器（Ant Design `Segmented` 控件）点击 **"爆炸图"** 选项（`viewMode → 'explode'`） | 此时 `showSubParts=true & explodeAmount>0`，触发 `SubPartsGroup.useGLTF()` 并发加载该 link 下所有子零件 GLB |
| A-5 | 拖动 **爆炸程度滑块**（如存在；或观察自动爆炸动画）到最大值，各部件飞出完成 | 所有 `InteractiveLinkMesh.useFrame()` 同时运行透明度过渡 |
| A-6 | 在 3D Canvas 内**鼠标拖拽旋转**（OrbitControls，`enableRotate=true`），连续旋转 360°，持续约 3 s | 测量持续渲染帧率 |
| A-7 | **双击**已选中的部件（`onPartDoubleClick`），进入 L2 子零件模式（`isolationLevel → 2`） | 子零件级爆炸启动 |
| A-8 | 再次旋转 3D Canvas 约 2 s | — |
| A-9 | 单击页面空白处或"退出隔离"按钮，回到总览（`viewState → OVERVIEW`） | 所有 link 恢复可见 |
| A-10 | **停止录制** trace | — |

> **注意**：若当前机器人有 assembly manifest（非 ATOM-01 硬编码路径），场景将进入 `InteractiveManifestViewer` 分支，而非 `Atom01Interactive`。请确认 DevTools Network 标签中看到 `*.glb` 请求来自 `/models/atom01/` 或 `/api/v1/robots/{id}/assets/`，以确认走的是哪条分支。

---

## 3 Scenario B：Monitor 页

**目标组件**：`src/pages/MonitorPage.tsx` → `MonitorRobotViewer`（`src/components/Viewer3D/MonitorRobotViewer.tsx`）  
**典型路径**：`http://localhost:5173/monitor`

### 3.1 操作脚本（Step-by-Step）

| 步骤 | 操作 | 等待/观察 |
|------|------|-----------|
| B-0 | **开始录制** trace | — |
| B-1 | 打开 `http://localhost:5173/monitor`；确认 `useRobotContextStore` 中 `currentRobot` 已设置（否则页面显示"请先选择机器人"） | — |
| B-2 | 等待 `useAssemblyManifest(robotId)` 请求完成；若有 manifest → 进入 `ManifestDrivenRenderer` 路径；若无 → 进入 `RobotGLBViewer` 路径。DevTools Network 确认 | **记录时间戳 T_first_frame**（Spin 消失、Canvas 第一帧） |
| B-3 | 等待 WebSocket (`ws://…/ws/robot/status`) 连接建立（状态显示 **"WebSocket 已连接"**）；确认 5 Hz 遥测开始推送（`jointAngles` 更新） | 检查 `MonitorRobotViewer` 的 `jointAngles` prop 以 200 ms 间隔更新 |
| B-4 | 观察 3D 模型随 telemetry 实时更新关节角度（`ManifestDrivenRenderer` 接收 `jointAngles` 并刷新关节变换），持续 **10 s**（50 帧遥测） | 测量持续更新帧率与 5 Hz WebSocket 触发的 React re-render 成本 |
| B-5 | 在 3D Canvas 内**拖拽旋转**（`OrbitControls`，`enablePan enableZoom enableRotate`），连续旋转 360°，持续约 3 s | 测量 orbit 叠加遥测刷新的帧率 |
| B-6 | 触发告警状态（如 `/api/v1/robots/{id}/fault` 或等待 mock 故障触发 `highlightLinks` 非空），观察高亮 link 效果 | 若 `highlightLinks` 中有 link 名，`ManifestDrivenRenderer` 应变色 |
| B-7 | **停止录制** trace | — |

---

## 4 需要采集的指标及读取位置

### 4.1 FPS 与帧时间分布

| 指标 | DevTools 读取位置 |
|------|-----------------|
| 平均 FPS | Performance 面板顶部 **Frames 泳道** → hover 任意帧区块，显示该帧持续时间；统计稳定渲染段的平均值 |
| P50 / P95 / P99 帧时间 | 录制结束后 Timeline → **Frames** 泳道 → 拖选旋转操作段 → 底部 Summary 面板显示最短/最长帧时间；或导出 JSON 后用脚本分析 |
| 长任务（>50 ms） | **Main thread** 泳道 → 红色三角标记；或点击 "Long Tasks" 过滤 |

### 4.2 GPU 时间

| 指标 | DevTools 读取位置 |
|------|-----------------|
| GPU 帧时间 | Performance 面板 → **GPU** 泳道（需 Chrome Canary 或开启 `chrome://flags/#enable-devtools-experiments`）；或 Main 线程 `Commit` / `Draw Frame` 任务时长 |
| 合成层数量 | Performance → **Layers** 面板（录制时需勾选 "Enable advanced paint instrumentation"） |

### 4.3 首个可交互 3D 帧（T_first_frame）

- **定义**：从导航发起（`navigationStart`）到 `<canvas>` 内首次绘制完整机器人（Suspense fallback 消失，`LoadingFallback` wireframe 不再渲染）。
- **读取方式**：Timeline 主线程 → 搜索 `"React: commit"` 或 `"Render"`；同时对照 Network 面板最后一个 `.glb` 请求完成时间戳。
- **辅助**：在代码中可临时添加 `performance.mark('3d-first-frame')` 于 `Suspense` `onReveal` 回调（纯测量，不改产品逻辑；改动后测完即删）。

### 4.4 `useFrame` 逐帧成本

- **读取方式**：Performance 主线程 → 展开任意一帧 → 找到 `requestAnimationFrame` 回调 → 展开内部调用栈 → 找到带 `InteractiveLinkMesh` 字样的函数（或 `traverse`）。
- **关注项**：
  - `useFrame` 回调（`InteractiveLinkMesh.tsx:123`）中的 `traverse` 调用时长。
  - 24 个 `InteractiveLinkMesh` 的 `useFrame` 回调是否串行累积在同一 rAF 帧中。
  - L1 隔离爆炸态 vs 总览态下 `useFrame` 总成本对比。

### 4.5 GLB 加载瀑布（count + total bytes + time）

| 指标 | DevTools 读取位置 |
|------|-----------------|
| 请求数量 | Network 面板 → 筛选 `glb` → 计数 |
| 总字节 | Network 面板底部 **"X requests, Y kB / Z kB transferred"** |
| 首请求到末请求完成时间 | 最早 `.glb` 请求发起时间戳 → 最晚 `.glb` 完成时间戳（瀑布视图） |
| 并发请求数峰值 | 瀑布图中重叠最多的行数（HTTP/2 多路复用下通常全部并发） |

---

## 5 基线文档表格模板

将以下 Markdown 表格粘贴至 `docs/superpowers/plans/phase4-baseline.md` 的 **"3D 渲染"** 段，并回填测量值：

```markdown
### 3D 渲染基线

> 采集环境：Chrome ×× / CPU 4× throttle / 网络本地 / 日期 YYYY-MM-DD
> 采集方法：见 `scripts/perf/3d-viewer-trace-runbook.md`

#### Scenario A：SOP 维护页（Atom01Interactive 路径）

| 指标 | 单位 | 测量值 | 备注 |
|------|------|--------|------|
| T_first_frame（navigationStart → canvas 首帧） | ms | — | Suspense fallback 消失时刻 |
| GLB 请求数（初始加载） | 个 | — | 预期 24（每个 InteractiveLinkMesh 一个） |
| GLB 总传输大小 | kB | — | Network 面板 transferred |
| GLB 加载总时长（首→末完成） | ms | — | 并发瀑布宽度 |
| 稳定旋转平均 FPS（A-6 段） | fps | — | Frames 泳道 |
| P95 帧时间（旋转段） | ms | — | —  |
| 长任务 >50 ms 次数（全 Scenario） | 次 | — | 红三角计数 |
| useFrame 单帧平均成本（旋转段，所有 InteractiveLinkMesh 合计） | ms | — | rAF 展开后求均值 |
| 进入 L1 隔离 + 爆炸后子零件 GLB 额外请求数 | 个 | — | SubPartsGroup.useGLTF 触发 |
| 爆炸态旋转平均 FPS（A-8 段） | fps | — | 与稳定旋转对比 |

#### Scenario B：Monitor 页（ManifestDrivenRenderer + WebSocket 路径）

| 指标 | 单位 | 测量值 | 备注 |
|------|------|--------|------|
| T_first_frame（navigationStart → canvas 首帧） | ms | — | Spin 消失时刻 |
| manifest 请求耗时 | ms | — | useAssemblyManifest GET 请求 |
| 稳定遥测更新平均 FPS（B-4 段，10 s） | fps | — | 5 Hz jointAngles 触发 re-render |
| 5 Hz React re-render 单次成本（P50） | ms | — | rAF 中 React commit 时长 |
| orbit 叠加遥测更新平均 FPS（B-5 段） | fps | — | 与 B-4 对比 |
| P95 帧时间（orbit + telemetry 段） | ms | — | — |
| 长任务 >50 ms 次数（全 Scenario） | 次 | — | — |
```

---

## 6 待印证热点假设

> **重要**：以下仅是"根据代码结构提出的可测量假设"。**在采集到真实 trace 数据之前，不执行任何优化。** 每项假设附确认/否定标准，测量后在基线文档中标注 ✅/❌。

### H-1：24 个 InteractiveLinkMesh 各自独立调用 `useGLTF`，引发 24 路并发 GLB 加载

- **代码证据**：`Atom01Interactive.tsx` 中 `createLink()` 被调用 24 次，每次渲染一个 `InteractiveLinkMesh`（`atom01/InteractiveLinkMesh.tsx:53`）；每个组件内部直接调用 `useGLTF(\`${modelBasePath}/${name}.glb\`)`。
- **预期症状**：Network 瀑布图中出现 ~24 条并发 `.glb` 请求；若浏览器 HTTP/2 连接数耗尽则出现排队（`Stalled`）。
- **确认标准**：Network 面板 `.glb` 过滤后请求数 ≥ 24 且请求发起时间戳高度重叠。
- **否定标准**：请求数 < 24（说明有 cache 或预加载机制已生效）。

### H-2：`InteractiveLinkMesh.useFrame` 每帧 traverse 所有 Mesh 材质，24 个实例累积成本不可忽略

- **代码证据**：`InteractiveLinkMesh.tsx:123-194`，`useFrame` 回调内执行 `meshRef.current.traverse(child => { ... mat.emissive = ...; mat.opacity = ... })` ——对 cloned scene 内每个 Mesh 执行 6–8 项材质属性写操作。24 个实例的 `useFrame` 在同一 rAF 帧内串行执行。
- **预期症状**：Performance 主线程中每帧出现多个连续 `traverse` 调用，总时长随 mesh 数量线性增长；在 4× CPU 节流下可能超过 4–8 ms/帧。
- **确认标准**：trace 中可量化 `useFrame` 总成本 ≥ 2 ms/帧（CPU 节流）；移除爆炸/隔离态后 `useFrame` 成本显著下降（说明条件分支路径对材质写操作有影响）。
- **否定标准**：`useFrame` 在 trace 中不可见（被 inline 折叠），或总成本 < 0.5 ms/帧（噪声级别）。

### H-3：进入隔离爆炸态时，`SubPartsGroup.useGLTF(gltfUrls)` 触发该 link 所有子零件的并发 GLB 加载，造成瞬间带宽峰值

- **代码证据**：`SubPartsGroup.tsx:40-43`，`gltfUrls = parts.map(p => \`${PARTS_GLB_BASE}/${p.path}\`)` 后调用 `useGLTF(gltfUrls)`（多 URL 数组形式）——当 `showSubParts=true && explodeAmount>0` 触发时，一次性请求该 link 下所有 `DetailPart` 对应的 GLB。
- **预期症状**：A-4 步骤（切换爆炸图）后 Network 面板出现新一批并发 `.glb` 请求（来自 `/models/parts/`），数量等于当前 link 的 `DetailPart` 数。
- **确认标准**：A-4 时间戳前后 Network 面板出现新 `.glb` 请求波峰，且请求全部并发；主线程在加载完成前出现等待（Suspense fallback 短暂重现或帧率下降）。
- **否定标准**：无新 GLB 请求（说明 `useGLTF` 缓存已命中，预加载有效）。

### H-4：Monitor 页 5 Hz WebSocket 遥测每次触发 React re-render，`ManifestDrivenRenderer` 关节变换计算在低端设备上有累积成本

- **代码证据**：`MonitorPage.tsx:277-287` 的 `jointAngles` `useMemo` 在 `telemetryData` 变化时重算；`MonitorRobotViewer` 将新 `jointAngles` 传入 `ManifestDrivenRenderer`，后者遍历 manifest joints 更新 Three.js group rotation。每 200 ms 触发一次。
- **预期症状**：B-4 段 Performance 主线程出现规律性 ~200 ms 间隔的 React commit + Three.js 更新尖峰；若每次 commit 超过 16 ms 则帧率受限。
- **确认标准**：trace 中每 ~200 ms 可见 React `commit` task，成本在 4× CPU 节流下 > 4 ms/帧。
- **否定标准**：commit 成本 < 1 ms（说明 React memo 优化生效，`ManifestDrivenRenderer` 无不必要重渲）。

---

*文件由 Task B2（quality-hardening Phase 4）创建，仅含运维文档，不含任何产品代码变更。*
