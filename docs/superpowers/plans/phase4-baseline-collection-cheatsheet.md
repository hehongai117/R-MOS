# Phase 4 基线采集速查清单（一页照做）

> 目的：把 Track B 四类测量工具的"起服务 → 装依赖 → 采集 → 回填"拍平成一页可照敲的清单。
> 产出目标：填满 `docs/superpowers/plans/phase4-baseline.md` 四段真实数字 → 解锁 Track C 优化子计划。
> 需在**能起全栈 + 真实 Chrome** 的机器上执行（不是 CI/沙箱）。

---

## 0. 一次性前置

```bash
# 0.1 测量依赖（未入 package.json，按需装；装一次即可）
cd r-mos-frontend && npm i -D lighthouse chrome-launcher ws

# 0.2 起后端（普通模式，供 Lighthouse/WS 用）
cd r-mos-backend && source venv/bin/activate && python main.py     # → http://localhost:8000

# 0.3 起前端（二选一）
#   生产模式（更接近真实，推荐测首屏）：
cd r-mos-frontend && npm run build && npm run preview               # → http://localhost:4173
#   开发模式（快，但含 HMR 开销，数字偏悲观）：
cd r-mos-frontend && npm run dev                                    # → http://localhost:3000
```

> 记住你用的前端地址（preview=4173 / dev=3000），下面所有 `BASE_URL` 用它。

---

## 1. 首屏 / 关键路由（Lighthouse）→ baseline 第 1 段

**受保护路由需要登录 token（否则测到的是 /login 重定向，数字无意义）。**

```bash
# 1.1 拿 access_token（替换成你的账号密码）
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"你的邮箱","password":"你的密码"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "$TOKEN"     # 确认非空

# 1.2 跑 Lighthouse（脚本会把 token 注入 localStorage 的 rmos_access_token）
cd r-mos-frontend
BASE_URL=http://localhost:4173 AUTH_TOKEN="$TOKEN" npm run perf:lighthouse
```
- 输出：终端打印 markdown 表格行（Perf Score / FCP / LCP / TBT / CLS / TTI），原始 json 落 `scripts/perf/out/`。
- **回填**：把表格行粘到 `phase4-baseline.md` §1；顺手在"观察/瓶颈候选"写下最慢路由与主因（如 LCP 大）。
- 不设 `AUTH_TOKEN` 时受保护路由会被跳过（只测 /login、/register 两个公开页）。

---

## 2. 3D 查看器渲染（DevTools 手动 trace）→ baseline 第 2 段

无脚本，照 runbook 手动采：`r-mos-frontend/scripts/perf/3d-viewer-trace-runbook.md`

```
1. Chrome 打开 SOP 维护页 (/maintenance) → 已登录
2. DevTools → Performance → Record
3. 按 runbook 操作脚本：等 3D 加载 → 点核心件进 L1 隔离 → 爆炸图 → 旋转 → 进 L2 → 停录
4. 读：首个可交互 3D 帧、稳态 FPS、帧时 P95、长任务、GPU 时间、useFrame 单帧成本、GLB 加载(数量/字节/时长)
5. 对 Monitor 页 (/monitor) 重复（含 5Hz WebSocket 驱动）
```
- **回填**：`phase4-baseline.md` §2A(SOP) / §2B(Monitor) 表格 + H1–H4 热点假设的"确认/否定"。
- 提示：H1=24 个 InteractiveLinkMesh 各自 useGLTF；H2=爆炸态子零件并发加载；H3=useFrame 逐帧材质 traverse。**只记录测量结论，先别动手优化。**

---

## 3. WebSocket 遥测 5Hz → baseline 第 3 段

后端在跑即可（第 0.2 步）：
```bash
cd r-mos-frontend
WS_URL=ws://localhost:8000/ws/robot/status WS_DURATION_SEC=20 npm run perf:ws
```
- 输出：消息间隔 mean/P50/P95、5Hz 达成率(%)、ping→pong RTT、断连次数 → markdown 表。
- **回填**：`phase4-baseline.md` §3。理想间隔≈200ms、达成率越接近 100% 越好、断连应为 0。

---

## 4. AI 管线服务端耗时 → baseline 第 4 段

需以 **PERF_TIMING=1 重启后端**（第 0.2 的普通实例不带计时）：
```bash
# 4.1 重启后端（带计时）
cd r-mos-backend && source venv/bin/activate && PERF_TIMING=1 python main.py

# 4.2 触发 AI/LLM 重端点（详见 r-mos-backend/scripts/perf/ai_pipeline_timing.md）
#     可用前端点操作，或 curl（带 -i 看响应头 X-Process-Time）：
curl -si -X POST http://localhost:8000/api/v1/training/sessions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{...}' | grep -i X-Process-Time
```
- 读：响应头 `X-Process-Time`（ms）+ 后端日志 `TIMING route=... ms=...`（含各阶段/LLM 耗时）。
- 覆盖端点：训练会话/提交反馈、workbench draft/step、agent execute、robots analysis。
- **回填**：`phase4-baseline.md` §4（总耗时 + 其中 LLM）。测完可关掉 PERF_TIMING 恢复普通实例。

---

## 5. 回填完成 → 通知我进 Track C

四段都有真实数字后，告诉我"基线已回填"。我会：
1. 按「影响 × 可行性」排序真实瓶颈；
2. 写 `docs/superpowers/plans/<date>-phase4b-optimizations.md`（每项优化含：优化前数字 → 措施 → 优化后**用同一工具**复测命令 → 期望改善）；
3. Subagent-Driven 执行，用前/后数据验证，杜绝臆测式优化。

---

### 附：命令一览（复制用）
| 目标 | 命令 |
|------|------|
| 装依赖 | `cd r-mos-frontend && npm i -D lighthouse chrome-launcher ws` |
| 起后端 | `cd r-mos-backend && source venv/bin/activate && python main.py` |
| 起前端(prod) | `cd r-mos-frontend && npm run build && npm run preview` |
| 拿 token | 见 §1.1 |
| 首屏 | `BASE_URL=http://localhost:4173 AUTH_TOKEN="$TOKEN" npm run perf:lighthouse` |
| WebSocket | `WS_URL=ws://localhost:8000/ws/robot/status WS_DURATION_SEC=20 npm run perf:ws` |
| AI 计时 | `PERF_TIMING=1 python main.py` 后触发端点，读 `X-Process-Time` |
| 3D 渲染 | 手动，照 `scripts/perf/3d-viewer-trace-runbook.md` |
