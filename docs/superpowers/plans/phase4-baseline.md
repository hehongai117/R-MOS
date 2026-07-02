# Phase 4 性能基线（待真实环境采集回填）

> 记录日期骨架：2026-07-02
> 分支：quality-hardening-phase4
> **状态：数字列待用户在可起全栈（Vite + FastAPI + PostgreSQL + 真实浏览器）的环境采集回填。**

本文件由 Phase 4 Track B 的测量工具产出，四段分别对应：首屏/关键路由、3D 渲染、WebSocket 遥测、AI 管线。回填真实数字后，作为 Track C（针对性优化）的前/后对比基准。**在四段有真实数字前，不得开始优化（先测量后优化硬约束）。**

采集前置：
```bash
# 前端（生产模式更接近真实）
cd r-mos-frontend && npm run build && npm run preview   # 或 npm run dev
# 后端
cd r-mos-backend && source venv/bin/activate && python main.py
# 测量依赖（按需安装，未入 package.json）
cd r-mos-frontend && npm i -D lighthouse chrome-launcher ws
```

---

## 1. 首屏 / 关键路由（Lighthouse）

**采集：** `BASE_URL=http://localhost:4173 [AUTH_TOKEN=<token>] npm run perf:lighthouse`
（详见 `r-mos-frontend/scripts/perf/README.md`；受保护路由需 AUTH_TOKEN，否则测到的是 /login 重定向。）
指标读 Lighthouse desktop：Performance score、FCP、LCP、TBT、CLS、TTI。

| 路由 | Perf Score | FCP (ms) | LCP (ms) | TBT (ms) | CLS | TTI (ms) | 备注 |
|------|-----------|----------|----------|----------|-----|----------|------|
| /login | | | | | | | 公开页 |
| /register | | | | | | | 公开页 |
| /dashboard | | | | | | | 需 token |
| /my-tasks | | | | | | | 需 token |
| /scenarios | | | | | | | 需 token |
| /maintenance (SOP 工作台) | | | | | | | 需 token，3D 重 |
| /monitor | | | | | | | 需 token，3D+WS |
| /student/skills | | | | | | | 需 token |
| /workbench/teaching | | | | | | | 需 token |

**观察/瓶颈候选（回填后据实填写）：** _（例：LCP 主因、首包体积、阻塞脚本）_

---

## 2. 3D 查看器渲染（DevTools Performance trace）

**采集：** 按 `r-mos-frontend/scripts/perf/3d-viewer-trace-runbook.md` 操作脚本手动采集（Chrome DevTools Performance 或 chrome-devtools MCP performance_start_trace/stop_trace）。

### 2A. SOP 维护页（Atom01Interactive，24 个 createLink）

| 指标 | 值 | 读取位置 |
|------|-----|---------|
| 首个可交互 3D 帧 (ms) | | Performance timeline 首帧 |
| 稳态 FPS（旋转时） | | Frames 轨道 |
| 帧时 P95 (ms) | | Frames 轨道分布 |
| 长任务数 / 总时长 (ms) | | Main 轨道 long tasks |
| GPU 时间 (ms) | | GPU 轨道 |
| useFrame 单帧成本 (ms) | | Main 轨道 flame chart |
| GLB 加载：数量 / 总字节 / 时长 | | Network 瀑布 |
| 进入 L1 隔离态耗时 (ms) | | 交互→稳定 |
| 爆炸图切换耗时 (ms) | | 交互→稳定 |

### 2B. Monitor 页（ManifestDrivenRenderer + 5Hz WS）

| 指标 | 值 | 读取位置 |
|------|-----|---------|
| 首个可交互 3D 帧 (ms) | | |
| 稳态 FPS（遥测驱动） | | |
| 帧时 P95 (ms) | | |
| 长任务数 / 总时长 (ms) | | |
| GLB 加载：数量 / 总字节 / 时长 | | |

**待确认热点假设（runbook H1-H4，仅测量印证，勿预先优化）：**
- H1：24 个 `InteractiveLinkMesh` 各自 `useGLTF` → 加载/内存开销
- H2：爆炸态子零件并发 GLB 加载 → 网络/解码峰值
- H3：`useFrame` 内逐帧材质 traverse → 帧成本
- H4：_（runbook 内第 4 条，回填时据实）_

---

## 3. WebSocket 遥测（5Hz）

**采集：** 后端运行后 `WS_URL=ws://localhost:8000/ws/robot/status WS_DURATION_SEC=20 npm run perf:ws`。

| 指标 | 值 | 目标/参考 |
|------|-----|----------|
| 消息间隔均值 (ms) | | ~200ms（5Hz） |
| 间隔 P50 (ms) | | ~200ms |
| 间隔 P95 (ms) | | — |
| 5Hz 达成率 (%) | | 越接近 100% 越好 |
| ping→pong RTT (ms) | | — |
| 断连次数 | | 0 |

**观察：** _（例：间隔抖动来源、是否稳定 5Hz）_

---

## 4. AI 管线（服务端处理耗时）

**采集：** 后端以 `PERF_TIMING=1` 启动，按 `r-mos-backend/scripts/perf/ai_pipeline_timing.md` 触发各端点，读响应头 `X-Process-Time` 与结构化日志（含 LLM 调用耗时定位）。

| 端点 / 阶段 | 总耗时 (ms) | 其中 LLM (ms) | 备注 |
|------------|-----------|--------------|------|
| 生成训练项目 (project generate) | | | |
| workbench 草案生成 | | | |
| workbench 步骤提交裁决 | | | |
| AI 反馈生成 (feedback) | | | |
| agent v2 execute (多 Agent) | | | per-call timeout 90s |
| ai-assistant chat | | | per-call timeout 90s |

**观察/瓶颈候选：** _（例：哪个阶段最慢、LLM 占比、是否有非 LLM 的意外开销）_

---

## 下一步（Track C，基线就绪后）

四段回填真实数字后，进入 Task C1：按「影响 × 可行性」排序真实瓶颈，用 superpowers:writing-plans 另写 `docs/superpowers/plans/<date>-phase4b-optimizations.md`，每项优化含「优化前数字 → 措施 → 优化后复测命令（复用本轨工具）→ 期望改善」。
