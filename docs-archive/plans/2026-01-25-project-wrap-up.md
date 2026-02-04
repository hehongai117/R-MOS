# 项目收尾 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 清理废弃组件、输出结项报告并完成最终提交。  
**Architecture:** 通过删除已被裁决级组件替代的旧文件，确保引用关系健康；补充结项报告总结重构成果；最后进行构建验证与提交。  
**Tech Stack:** React + TypeScript + Ant Design + Node.js + Git

---

### Task 1: 删除废弃组件

**Files:**
- Delete: `r-mos-frontend/src/components/Maintenance/SOPPlayer.tsx`
- Delete: `r-mos-frontend/src/components/Viewer3D/DisassemblyDemo.tsx`

**Step 1: 删除旧组件文件**

Run:
```bash
rm r-mos-frontend/src/components/Maintenance/SOPPlayer.tsx
rm r-mos-frontend/src/components/Viewer3D/DisassemblyDemo.tsx
```

**Step 2: 搜索引用并移除无用 Hook/工具函数**

Run:
```bash
rg -n "SOPPlayer|DisassemblyDemo" r-mos-frontend/src
```
Expected: 无旧组件引用；如有旧 Hook/工具函数无引用，确认后删除。

---

### Task 2: 构建验证

**Files:**
- Verify: `r-mos-frontend` 构建输出

**Step 1: 运行构建**

Run:
```bash
npm run build
```
Expected: 构建成功，无引用错误。

---

### Task 3: 生成结项报告

**Files:**
- Create: `docs/REFACTOR_COMPLETION_REPORT.md`

**Step 1: 写入结项报告**

内容包含：
1. 重构概述（一句话）
2. 架构变更图（文字流：UI -> SOPExecutor -> DecisionEngine -> ConstraintGraph）
3. 核心能力清单（B.2 阻断、三元判定、多模式差异等）
4. 文件指引（`src/adjudication/` 等）

---

### Task 4: 最终提交

**Files:**
- Stage: 全部改动

**Step 1: 添加全部文件**

Run:
```bash
git add .
```

**Step 2: 提交**

Run:
```bash
git commit -m "chore: 项目结项 - 清理废弃组件并生成结项报告"
```

