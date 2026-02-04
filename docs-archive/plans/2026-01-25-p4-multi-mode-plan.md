# P4 多模式功能落地 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 落地教学/考试/维保三种模式差异，包括提示引导、考试评分与终止结算、模式切换、测试环境日志清理。  
**架构：** 执行器为中枢输出模式处理结果，评分引擎独立维护分数，UI 只消费结果展示。  
**技术栈：** React + TypeScript + Zustand + esbuild（测试运行）。

---

### 任务 1：测试环境存储 Mock

**文件：**
- 新增：`r-mos-frontend/scripts/test-setup.ts` 或 `r-mos-frontend/scripts/test-setup.mjs`
- 修改：`r-mos-frontend/src/adjudication/core/stateManager.ts`
- 修改：`r-mos-frontend/src/adjudication/__tests__/run-adjudication-tests.ts`

**步骤 1：先写失败测试（验证 Node 环境无 storage 警告）**  
在测试入口打印标记，断言未出现 storage 警告（以手工确认日志为准）。  

**步骤 2：运行测试验证失败**  
运行：`npm test`  
预期：出现 `persist middleware` 警告。  

**步骤 3：实现最小改动**  
在测试入口注入内存存储，并在 `stateManager` 使用 `createJSONStorage`，Node 环境下走内存存储。  

**步骤 4：运行测试验证通过**  
运行：`npm test`  
预期：无 storage 警告。  

---

### 任务 2：评分引擎 ScoringEngine

**文件：**
- 新增：`r-mos-frontend/src/adjudication/core/scoringEngine.ts`
- 修改：`r-mos-frontend/src/adjudication/index.ts`

**步骤 1：先写失败测试**  
新增 `r-mos-frontend/src/adjudication/__tests__/examMode.test.ts`：  
测试扣分后 `currentScore` 下降，`deductions` 记录正确。  

**步骤 2：运行测试验证失败**  
运行：`npm test`  
预期：找不到 ScoringEngine 或断言失败。  

**步骤 3：实现最小功能**  
实现 `reset / getState / deduct / finalize / subscribe`。  

**步骤 4：运行测试验证通过**  
运行：`npm test`  
预期：考试扣分测试通过。  

---

### 任务 3：执行器模式分流（handleFailure）

**文件：**
- 修改：`r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
- 修改：`r-mos-frontend/src/adjudication/types/adjudication.ts`

**步骤 1：先写失败测试**  
在 `examMode.test.ts` 新增：  
- 教学模式失败返回 `hint` 且允许重试  
- 考试模式失败扣分且不允许重试  
- 严重错误 `allowContinue=false` 触发 `FAILED_FATAL` 与结算标记  

**步骤 2：运行测试验证失败**  
运行：`npm test`  
预期：断言失败。  

**步骤 3：实现最小逻辑**  
在 `handleFailure` 中按三模式分支，读取 `failureReasons`，输出 `hint` 与考试扣分/终止逻辑。  

**步骤 4：运行测试验证通过**  
运行：`npm test`  
预期：三分支测试全部通过。  

---

### 任务 4：UI 落地（提示气泡 + 考试栏 + 模式切换 + 结果页）

**文件：**
- 修改：`r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`
- 修改：`r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- 可能新增：`r-mos-frontend/src/components/Maintenance/ModeSwitcher.tsx`

**步骤 1：先写失败测试（可用最小渲染断言）**  
如果缺少 UI 测试框架，则以运行日志 + 手工检查为准。  

**步骤 2：实现最小 UI 改动**  
教学模式：错误红字下方出现提示气泡 + 重试按钮。  
考试模式：顶部显示倒计时与当前得分；严重错误自动切换结果页并显示 `reasonCode`。  
模式切换：下拉切换触发执行器与评分重置。  

**步骤 3：运行测试 / 构建验证**  
运行：`npm test`  
运行：`npm run build`（可选）  

---

### 任务 5：更新开发记录

**文件：**
- 修改：`DEVELOPMENT_LOG.md`

**步骤：**  
追加 P4 完成记录、关键改动与测试说明。  

---

### 任务 6：验收输出

**输出内容：**  
1) `ScoringEngine` 核心接口代码片段  
2) `sopExecutor.handleFailure` 分流代码片段  
3) 考试模式扣分日志（`currentScore` 下降）  

