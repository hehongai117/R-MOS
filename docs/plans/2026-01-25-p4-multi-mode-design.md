# P4 多模式功能落地设计文档

## 背景
P3 阶段已完成裁决引擎、约束扩展与基础测试，系统已有 `operationMode` 状态，但 UI 与行为尚未体现教学/考试/维保差异。P4 目标是把多模式差异落地，并形成“提示引导 + 评分与锁死 + 结果结算”的闭环。

## 目标
1. 教学模式：失败时显示教学提示气泡并允许重试。  
2. 考试模式：错误扣分、不可重试；严重错误直接终止并展示结果页。  
3. 维保模式：保持严格阻断逻辑。  
4. 测试日志干净：Node 测试环境不再出现存储警告。  
5. UI 支持模式切换与评分展示。

## 架构与数据流
采用“执行器为中枢”的方案：`SOPExecutor` 在 `handleFailure` 内根据 `operationMode` 产出统一的失败处理结果（含 `hint`、`allowRetry`、`lockState`、`finalizeExam` 等）。  
`ScoringEngine` 作为独立核心模块记录分数与扣分明细；考试严重错误触发 `FAILED_FATAL` 与结算事件。  
UI 仅负责展示执行器与评分引擎的状态，不自行判断规则，确保裁决层一致性与可测试性。

## 教学模式交互设计
- 位置：SOP 操作面板内，错误红字下方或旁侧。  
- 形态：灯泡图标 + 黄/蓝底色提示框，文本来自 `failureReasons[].teachingResponse.hintContent`。  
- 行为：允许重试，按钮触发执行器重试。

## 考试模式交互设计
- 顶部显示“考试倒计时（60 分钟）”与“当前得分（默认显示）”。  
- 普通错误：扣分后强制修正，不允许重试绕过。  
- 严重错误（`allowContinue=false`）：  
  1) 逻辑层立即停止计时，将系统状态置为 `FAILED_FATAL`，生成最终成绩单；  
  2) UI 自动跳转结果页，高亮致命 `reasonCode`。  
- 结果页：以 `Result/Alert` 形式展示，提供重置入口（不要求回到考试）。

## 评分引擎设计
`ScoringEngine` 提供以下能力：  
- 状态：`{ currentScore, deductions: Array<{ stepId, reason, score }> }`  
- 方法：`reset(initialScore)`、`deduct(stepId, reason, score)`、`getState()`、`finalize(reasonCode)`  
- 订阅：UI 订阅分数变化（或定时拉取快照）。

## 测试策略
1. Node 测试入口注入内存存储（mock `createJSONStorage`），消除日志噪音。  
2. 单元测试覆盖：  
   - 教学模式失败返回提示并允许重试；  
   - 考试模式失败扣分、强制修正；  
   - 严重错误触发 `FAILED_FATAL` 并生成成绩单。  
3. 输出日志用于验收：考试模式错误导致 `currentScore` 下降。

## 风险与边界
- 结果页目前为前端“页面内面板/弹窗”实现，后续可升级为独立路由。  
- 评分引擎当前为内存态，后续可接入服务端存档。  

