# Phase 4 性能基线（P2-2 本地采集，2026-07-23）

> 采集环境：本地 macOS，前端生产预览（`vite preview` :4173），后端普通实例（:8000），本地 PostgreSQL（rmos 库，3 台资产完整机器人）。
> 采集账号：teacher1@rmos.demo（role=teacher，可见资产完整的 ATOM-01）。
> 状态：**四段已采真实数字**。据此结论：**唯一显著瓶颈是 SOP 3D 工作台的资产加载**——已由 phase4b 优化（真实渲染 ≈90MB → ≈13.2MB，-85%，见 §2A）；其余（WebSocket 遥测、读 API、公开页、其余受保护页）均健康。
>
> ⚠️ **3D 页测量口径注意**：`protected-vitals.mjs` 的 `--disable-gpu` 只测 preload fetch、不含 canvas 渲染的基础装配体（详见 §2A 口径更正）；3D 页真实渲染传输须用软件 WebGL 探针（`--use-angle=swiftshader`）。

> ⚠️ **采集过程发现测量工具缺陷**：`scripts/perf/lighthouse.mjs` 用 `extraHeaders` 注入 Bearer token，只影响网络请求，**对客户端 localStorage 路由守卫无效** → 受保护路由全部被重定向到 /login，测到的是登录页（Perf 100/FCP 12ms 全是假象）。已新建 `scripts/perf/protected-vitals.mjs`（chrome-launcher + CDP，页面 JS 运行前注入 authStore 需要的全部 6 个 localStorage key）修复此缺陷，受保护路由数字由该脚本采集。lighthouse.mjs 仅公开页数字有效。

---

## 1. 首屏 / 关键路由

### 1A. 公开页（Lighthouse，有效）

| 路由 | Perf Score | FCP (ms) | LCP (ms) | TBT (ms) | CLS | TTI (ms) |
|------|-----------|----------|----------|----------|-----|----------|
| /login | 100 | 74 | 82 | 0 | 0 | 82 |
| /register | 100 | 45 | 60 | 0 | 0 | 60 |

公开页轻量健康，无优化需求。

### 1B. 受保护路由（protected-vitals.mjs，CDP + 完整认证注入，有效）

| 路由 | 最终URL | DOM节点 | FCP (ms) | DCL (ms) | Load (ms) | 请求数 | 传输 (KB) | 备注 |
|------|---------|---------|----------|----------|-----------|--------|-----------|------|
| /workbench/teaching | /workbench/teaching | 370 | 180 | 118 | 119 | 250 | 733 | 教师监控台，健康 |
| /maintenance | /maintenance | 487 | 108 | 72 | 73 | **185** | **80,763** | SOP 3D 工作台（此数为 preload-only 口径，真实渲染见 §2A；已 phase4b 优化） |
| /monitor | /monitor | 508 | 80 | 67 | 67 | 24 | 147 | 3D 未在首屏加载，轻 |
| /sops | /sops | 288 | 80 | 36 | 37 | 15 | 21 | 健康 |
| /dashboard | /workbench/teaching | 370 | 72 | 34 | 35 | 250 | 138 | teacher 重定向到监控台 |

**观察/瓶颈候选：**
- **`/maintenance` 单页加载传输 ~79MB（185 请求）是唯一显著瓶颈。** DOM-ready 指标（FCP/DCL/Load）都很快（72-108ms），因为 3D GLB 是 load 事件后异步拉取——页面"可交互"快，但 3D 完整渲染因 79MB 下载而慢。
- FCP/DCL/Load 时间对所有受保护路由都在健康区间（34-180ms），非瓶颈。

---

## 2. 3D 查看器渲染

### 2A. 资产传输量

> ⚠️ **测量口径更正（phase4b 确认）**：`protected-vitals.mjs` 用 headless `--disable-gpu`，WebGL 不可用 → react-three-fiber 的 Canvas 不挂载 → **只测到 `preload()` 的 fetch，测不到 canvas 渲染的基础装配体 GLB**。故本节初采的 "~79MB" 实为 **preload-only** 口径（`preloadAllParts` 预取的 155 个明细零件），非真实页面渲染总量。真实渲染总量须用**软件 WebGL** 探针（`--use-gl=angle --use-angle=swiftshader`，canvas 真挂载）测得。

**根因（phase4b 已确诊，非重复拉取）：** 155 个 GLB 全来自 `/public/models/parts/frames/`（硬编码 `partsManifest.ts`，含 `_1/_2/_3` 变体），由 `SOPMaintenancePage` 挂载时 `useEffect(preloadAllParts)` **eager 全量预加载**——这些全是"钻取某 link 才需要"的明细子零件，抵消了已有的 `DetailParts` 按需加载。首屏概览其实只需 robot-assets 的 24 个基础 link 装配体（12MB）。**无重复 URL（H1 useGLTF 重复拉取假设已证伪）。**

**优化前后（软件 WebGL 全口径实测）：**

| 阶段 | 措施 | 真实渲染传输 | 备注 |
|------|------|-------------|------|
| before | eager 全量预加载 155 明细零件 | **≈90MB** | 12MB 基础装配体 + 78MB 明细 preload |
| final（phase4b） | 明细零件**零预加载**，首屏仅 24-link 基础装配体，明细按需 | **≈13.2MB** | -85%；24/24 base GLB 完整机体，0 明细预取 |

措施：删除 `SOPMaintenancePage` 的 `useEffect(preloadAllParts)`；明细子零件由 `DetailParts`/`SubPartsGroup` 经 Suspense 按需加载（用户钻取 link 时）。复测命令：`protected-vitals.mjs`（preload-only 口径）或软件 WebGL 探针（全口径，见下方工具表）。

### 2B. 深度交互指标（帧率/帧时/GPU）— 待手动补采

`3d-viewer-trace-runbook.md` 的稳态 FPS、帧时 P95、useFrame 单帧成本、爆炸/旋转交互开销**需 DevTools Performance 手动录制**（Three.js canvas 交互不可经 DOM 程序化驱动）。本次未采。首屏传输瓶颈已在 phase4b 解决（-85%）；交互帧率建议上云后在 staging 手动复采。

---

## 3. WebSocket 遥测 5Hz（ws-probe.mjs，有效）

| 指标 | 值 | 目标 | 评价 |
|------|-----|------|------|
| 实际吞吐 (Hz) | 4.96 | 5.0 | ✅ |
| 消息间隔均值 (ms) | 201.8 | 200 | ✅ |
| 间隔 P50 (ms) | 202.0 | 200 | ✅ |
| 间隔 P95 (ms) | 203.0 | ~200 | ✅ 抖动极小 |
| 5Hz 达成率 (%) | 100.0 | →100 | ✅ |
| 断连次数 | 0 | 0 | ✅ |

**结论：WebSocket 遥测近乎理想，无优化需求。**

---

## 4. AI 管线服务端耗时（PERF_TIMING=1，X-Process-Time）

| 端点 | X-Process-Time | 评价 |
|------|---------------|------|
| GET /api/v1/sops | 27.7 ms | ✅ 健康 |
| GET /api/v1/robots | 35.1 ms | ✅ 健康 |
| GET /api/v1/sops/adjudication | 16.0 ms | ✅ 健康 |
| POST /training/workbench/draft（AI 重端点） | 未测得 | 见说明 |

**说明：**
- 常规读/查询端点服务端耗时均 <40ms，健康，非瓶颈。
- **真实 LLM 端点延迟本地无法测**：本地无真实大模型 API key，走 mock fallback，测到的是管线开销而非真实模型延迟；且构造合法 workbench draft 请求需完整业务上下文（本次 400）。**真实 AI 管线延迟需在 staging（带真实 DeepSeek/MiniMax key）采集**——列入 P1-3 上云后的复采项。

---

## 总结与优化决策

**数据驱动结论：全栈唯一显著性能瓶颈是 SOP 3D 工作台（/maintenance）的资产加载——已由 phase4b 优化解决（真实渲染 ≈90MB → ≈13.2MB，-85%）。** 其余全部健康：
- WebSocket 遥测：近乎理想（4.96Hz / 100% / 0 断连）
- 读 API：<40ms
- 公开页 + 其余受保护页：首屏 34-180ms，传输 21-733KB

**优化已闭环（phase4b，2026-07-23）**：根因=eager 全量预加载 155 个明细零件；措施=明细零预加载、首屏仅 24-link 基础装配体、明细按需（§2A）。后续可选项（收益递减，非必须）：GLB 的 Draco/meshopt 压缩（基础装配体 12MB 仍可再压）。

**待上云后复采项**（staging，更接近真实）：真实 LLM 管线延迟（§4）、3D 交互帧率（§2B）。

---

## 采集工具（复现用）

| 目标 | 命令 |
|------|------|
| 装依赖 | `cd r-mos-frontend && npm i --no-save lighthouse chrome-launcher chrome-remote-interface ws` |
| 公开页 Lighthouse | `BASE_URL=http://localhost:4173 npm run perf:lighthouse` |
| 受保护路由（修复版） | `AUTH_JSON=/tmp/perf-auth.json BASE_URL=http://localhost:4173 ROUTES=/maintenance,/monitor,... node scripts/perf/protected-vitals.mjs`（AUTH_JSON 含 authStore 6 key，见脚本头注释） |
| WebSocket | `WS_URL=ws://localhost:8000/ws/robot/status WS_DURATION_SEC=20 npm run perf:ws` |
| AI 计时 | `PERF_TIMING=1 python main.py` 后触发端点读 `X-Process-Time` |
| 3D 页真实渲染传输 | `protected-vitals.mjs` 需软件 WebGL：chromeFlags 加 `--use-gl=angle --use-angle=swiftshader`（否则 --disable-gpu 下 canvas 不挂载，只测 preload） |
| 3D 交互 | 手动 DevTools，照 `scripts/perf/3d-viewer-trace-runbook.md` |
