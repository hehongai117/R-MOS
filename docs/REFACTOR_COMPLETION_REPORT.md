# 裁决级重构结项报告

## 1. 重构概述
本次重构将系统从“演示级流程播放”升级为“裁决级强制判定系统”，让所有操作都受到裁决层约束并可验证。

## 2. 架构变更图（文字流）
UI -> SOPExecutor -> DecisionEngine -> ConstraintGraph  
说明：UI 仅负责展示与交互；SOPExecutor 执行步骤与状态机；DecisionEngine 负责裁决与完成判定；ConstraintGraph 提供约束事实与阻断依据。

## 3. 核心能力清单
- **B.2 强制阻断**：ACTIVE 约束必须裁决为 BLOCKED。  
- **三元完成判定**：语义 && 约束 && 几何同时满足才算完成。  
- **多模式差异**：教学提示 + 可重试；考试扣分 + 禁止重试 + 熔断结算；维保严格阻断。  
- **FAILED_FATAL 锁死**：致命错误直接锁死系统并触发结算。  

## 4. 文件指引（核心目录）
- 裁决核心逻辑：`r-mos-frontend/src/adjudication/`
- 约束数据与零件注册：`r-mos-frontend/src/adjudication/data/`
- 裁决执行器：`r-mos-frontend/src/adjudication/executor/`
- 评分引擎：`r-mos-frontend/src/adjudication/core/scoringEngine.ts`
- SOP 入口与 UI：`r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
