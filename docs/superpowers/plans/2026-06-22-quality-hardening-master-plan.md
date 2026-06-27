# R-MOS 质量硬化升级 — 总控计划

> **For agentic workers:** REQUIRED SUB-SKILL: 各 Phase 使用 superpowers:subagent-driven-development 逐 Task 实施。
>
> 设计 Spec：`docs/superpowers/specs/2026-06-22-quality-hardening-upgrade-design.md`

**Goal:** 在不新增产品功能的前提下，对 R-MOS 做一次系统化质量硬化——仓库卫生、测试安全网、巨型文件重构、性能硬化。

**核心原则：** 测试先于重构（Phase 2 是 Phase 3 的硬前置）。顺序遵循「清理 → 织网 → 重构 → 优化」。

## Phase 总览

| Phase | 名称 | 详细计划 | 状态 |
|-------|------|----------|------|
| 1 | 仓库工程化与卫生 | `2026-06-22-phase1-repo-hygiene.md` | ✅ Done |
| 2 | 测试安全网（重构前置） | `2026-06-25-phase2-test-safety-net.md` | ✅ Done |
| 3 | 巨型文件重构 | 抵达时细化 | ⬜ 未开始 |
| 4 | 性能与健壮性硬化 | 抵达时细化 | ⬜ 未开始 |

> Phase 2–4 在前一阶段完成后再写详细计划：Phase 3/4 的拆分边界与优化目标依赖 Phase 2 测试暴露的真实情况，提前细化等于臆测。

## 关键路径

```
Phase 1 (卫生) ──▶ Phase 2 (测试网) ──▶ Phase 3 (重构)
                                    └──▶ Phase 4 (性能) 可与 Phase 3 错峰并行
```

## 各 Phase 验收摘要

- **P1**：根目录整洁、遗留分支清理、CLAUDE.md 链接有效、`git status` 干净。
- **P2**：6 个巨型文件具备特征测试并纳入 CI 覆盖率门禁，前后端测试全绿稳定。
- **P3**：6 个巨型文件完成职责拆分、行为等价、测试全绿、无新增 lint/type 错误。
- **P4**：关键性能路径具备「优化前/后」对比数据，健壮性改进可验证。

## 执行规范（遵循 CLAUDE.md）

- Plan 用 Opus；Task 用 Subagent 驱动、任务间 review。
- 每个 Phase 完成后更新：CLAUDE.md + 本总控计划 + 记忆（`MEMORY.md`）。
- 所有过程/结果反馈使用中文。
