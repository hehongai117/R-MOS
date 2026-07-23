# Phase4b · 3D 资产加载优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 SOP 维护页首屏 3D 传输从 ~79MB 降到概览级（目标 ≤15MB），改 eager 全量预加载为"概览预加载 + 明细按需"，不损失拆装交互能力。

**Architecture:** 根因已由 P2-2 基线确诊：`SOPMaintenancePage.tsx` 挂载时 `useEffect(preloadAllParts)` 批量 `useGLTF.preload()` 全部 155 个明细零件（含 `_1/_2/_3` 变体，78.5MB），抵消了已存在的 `DetailParts.tsx` 按需加载（按 selectedLink + Suspense）。修法：收窄预加载到概览节点，让明细走既有的 on-demand 路径；用 `protected-vitals.mjs` 做前后传输量对比作为客观验收门。

**Tech Stack:** React + @react-three/fiber/drei（useGLTF.preload）、chrome-launcher+CDP 测量脚本

## Global Constraints

- **数据驱动前后对比**：每个改动用 `AUTH_JSON=/tmp/perf-auth.json BASE_URL=http://localhost:4173 ROUTES=/maintenance node scripts/perf/protected-vitals.mjs` 复测传输量，记录 before/after（基线 before = 79MB/185 请求）
- **不损失拆装能力**：概览渲染 + 用户钻取部件时 DetailParts 仍能按需加载对应零件（Suspense fallback 已存在）；L1 隔离、L2 子零件、爆炸图交互功能保持
- 前端门禁不破：`tsc --noEmit` + `eslint --max-warnings 0` + vitest 465+ 全绿；characterization 测试 mock 了 ModelPreloader，改动其行为须同步更新断言（按"规格变更"而非迁就）
- 环境：前端 `vite preview`(:4173) + 后端(:8000) + 本地 rmos 库（teacher1 可见资产完整 ATOM-01）；测量 token 在 /tmp/perf-auth.json（过期则重新登录刷新，见 phase4-baseline.md 采集工具表）
- 每 commit 尾部：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_017NYSjrARdtgRbQxW5TCv7N`；不 push（控制器统一推送）
- 命令在 `r-mos-frontend/` 下执行

## 已确诊事实（执行前置，勿重新调查）

- `/maintenance` 传输 79MB / 186 请求，其中 155 个 GLB / 78.5MB 全来自 `/public/models/parts/frames/`（硬编码 `partsManifest.ts`），**非** manifest 驱动的 robot-assets（那才 12MB/24 文件）。**无重复 URL**（不是重复拉取）。
- 主因：`SOPMaintenancePage.tsx:297-298` 的 `useEffect(() => { preloadAllParts(); }, [])` → `ModelPreloader.preloadAllParts()` → 对 `ALL_EXPLODE_PART_URLS`（partsManifest.ts:533，含 `FRAME_SUFFIXES=['','_1','_2','_3']` 全变体）逐个 `useGLTF.preload()`。
- `DetailParts.tsx` 已实现按需加载（SOPViewerScene 内，按 selectedLink + `<Suspense>`）——本优化是"关掉抵消它的 eager 预加载"，非新建懒加载。
- `partsManifest.ts` 标注 `@deprecated`（数据已迁 assembly_manifest.json detail_parts）——但本计划不做 manifest 迁移（更大工程），只收窄预加载范围。
- 概览节点：`partsManifest.ts` 有 `OVERVIEW_NODE_IDS`（来自 overview_nodes.json）——概览级只需这些。

---

### Task 1: 收窄预加载为概览级 + 前后传输量对比

**Files:**
- Modify: `src/components/Viewer3D/ModelPreloader.tsx`（新增概览级预加载函数）
- Modify: `src/pages/SOPMaintenancePage.tsx:297-298`（改调用）
- Modify: `src/pages/__tests__/SOPMaintenancePage.*.test.tsx`（3 处 mock 同步）
- Test: 复用 `scripts/perf/protected-vitals.mjs`（前后对比）

**Interfaces:**
- Produces: `preloadOverviewParts(): Promise<void>`（只预加载 OVERVIEW_NODE_IDS 对应的零件 URL，替代 preloadAllParts 的全量）

- [ ] **Step 1: 记录 before 基线（确认当前状态）**

```bash
cd r-mos-frontend
# 确保 token 新鲜（过期则重登录刷新 /tmp/perf-auth.json，见 phase4-baseline.md）
AUTH_JSON=/tmp/perf-auth.json BASE_URL=http://localhost:4173 ROUTES=/maintenance node scripts/perf/protected-vitals.mjs
```
Expected: /maintenance ≈ 79MB / 185 请求（before 基线，记入报告）

- [ ] **Step 2: 在 ModelPreloader 新增概览级预加载**

`ModelPreloader.tsx`：从 partsManifest 取概览节点对应 URL，新增函数（保留 preloadAllParts 供别处/测试用，但维护页不再调它）：

```typescript
import { OVERVIEW_NODE_IDS, overviewPartUrls } from './partsManifest'
// 若 partsManifest 未导出"概览节点→URL"映射，在 partsManifest.ts 补一个
// export function overviewPartUrls(): string[] { ... 只返回 OVERVIEW_NODE_IDS 对应零件 ... }

/** 只预加载概览级零件（首屏所需），明细零件由 DetailParts 按需加载。 */
export function preloadOverviewParts(): Promise<void> {
    const urls = overviewPartUrls()
    if (urls.length === 0) return Promise.resolve()
    return new Promise<void>((resolve) => {
        function loadBatch(startIdx: number) {
            const batch = urls.slice(startIdx, startIdx + BATCH_SIZE)
            batch.forEach((url) => { try { useGLTF.preload(url) } catch { /* 忽略 */ } })
            if (startIdx + BATCH_SIZE < urls.length) {
                setTimeout(() => loadBatch(startIdx + BATCH_SIZE), BATCH_DELAY)
            } else { resolve() }
        }
        loadBatch(0)
    })
}
```

（若 partsManifest 已有直接可用的"概览零件 URL"集合就用之；没有则在 partsManifest.ts 加 `overviewPartUrls()`：遍历零件定义，只保留其 link/node 属于 `OVERVIEW_NODE_IDS` 的。实现时先读 partsManifest 结构确定映射方式，报告登记实际做法。）

- [ ] **Step 3: 维护页改调概览预加载**

`SOPMaintenancePage.tsx`：import 改为 `preloadOverviewParts`，第 297-298 的 useEffect 改为：

```typescript
    useEffect(() => {
        preloadOverviewParts();
    }, []);
```

- [ ] **Step 4: 同步 3 处 characterization 测试的 mock**

`SOPMaintenancePage.characterization.test.tsx`、`.dynamic.test.tsx`、`.test.tsx` 里 `vi.mock('@/components/Viewer3D/ModelPreloader', ...)` 补 `preloadOverviewParts: vi.fn()`（保留 preloadAllParts mock）。若有断言"preloadAllParts 被调用"改为断言 preloadOverviewParts 被调用（规格变更，按新行为）。

- [ ] **Step 5: 前端门禁 + after 测量**

```bash
npx tsc --noEmit && npm run lint && npm test 2>&1 | grep -E "Test Files|Tests "
# 重新构建预览再测（改了源码）
npm run build && (npm run preview -- --port 4173 &) && sleep 5
AUTH_JSON=/tmp/perf-auth.json BASE_URL=http://localhost:4173 ROUTES=/maintenance node scripts/perf/protected-vitals.mjs
```
Expected: tsc/lint/vitest 全绿；/maintenance 传输**显著下降**（目标 ≤15MB，即只剩概览级；记 after 数字，报告写 before→after 对比）

- [ ] **Step 6: 手工验证拆装交互不回归**

后端+预览在跑，浏览器打开 /maintenance（用 protected-vitals 同款注入或手动登录）：确认 (a) 概览 3D 正常渲染；(b) 点击/钻取某个部件时 DetailParts 按需加载该零件（可能有短暂 Suspense fallback，属预期）；(c) 爆炸图/旋转正常。报告记录验证结果（截图或描述）。

- [ ] **Step 7: Commit**

```bash
git add src/components/Viewer3D/ModelPreloader.tsx src/components/Viewer3D/partsManifest.ts src/pages/SOPMaintenancePage.tsx src/pages/__tests__/
git commit -m "perf(3d): 维护页预加载收窄为概览级，明细零件按需加载(79MB→概览)"
```

### Task 2: 文档回写 + 基线复测归档

**Files:**
- Modify: `docs/superpowers/plans/phase4-baseline.md`（§2 追加优化后对比）
- Modify: `docs/项目交接与升级路线图.md`（T2-2 标记完成）

- [ ] **Step 1: baseline.md §2 追加 after 对比**

在 §2A 后追加"优化后（phase4b）"小节：before 79MB/185 请求 → after `<实测>`；措施=概览预加载+明细按需；复测命令。

- [ ] **Step 2: 路线图 T2-2 勾选**

T2-2 小节标 ✅ 完成（日期）；技术债表"性能"行改为"已量化+首个瓶颈(3D 79MB)已优化 ✅；真实 LLM 延迟/3D 交互帧率待 staging 复采"。

- [ ] **Step 3: 门禁复跑 + Commit**

```bash
cd r-mos-frontend && npx tsc --noEmit && npm test 2>&1 | grep "Tests "
git add docs/
git commit -m "docs: phase4b 3D 加载优化前后对比回写(T2-2)"
```

---

## Self-Review 记录

1. **范围覆盖**：基线唯一瓶颈（/maintenance 79MB eager 预加载）→ Task 1 收窄预加载；前后对比为客观门（Global Constraints + Task1 Step1/5）。未做 partsManifest→manifest 迁移与 Draco 压缩（更大工程，若 after 仍超目标再在后续追加，本计划先摘最大的果）。
2. **占位符扫描**：Task1 Step2 的 `overviewPartUrls()` 给了实现方向+回退方案（读 partsManifest 结构确定映射），非 TBD；概览节点源 `OVERVIEW_NODE_IDS` 已确认存在。
3. **类型一致性**：`preloadOverviewParts(): Promise<void>` 与 preloadAllParts 同签名风格；Task1 定义、Step3/4 消费一致；测量脚本 protected-vitals.mjs 复用不改。
4. **风险**：改 eager→按需后，用户首次钻取部件有短暂加载（Suspense fallback 已存在，非新回归）；characterization 测试 mock 需同步（Task1 Step4 覆盖）。
