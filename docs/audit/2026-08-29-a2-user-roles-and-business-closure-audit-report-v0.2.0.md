# A2 用户角色与业务闭环审计报告

- 版本：0.2.0
- 日期：2026-08-29
- 复核状态：RETURN FOR REVISION
- 事实基线：29d2a5889e3b320a3e777e3d8c19efbbe31c0294
- M-AUD-06：BLOCKED
- 替代关系：本文件纠正 v0.1.0 将静态链路写成真实闭环的结论。

## 1. 本阶段应完成什么

依据[董事会方向指令](../plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md)，A2 要把 A1 面向用户的功能映射到注册、入校、建班、加入、SOP、任务、训练、证据、评分、报告、维保、机器人控制、异常停止、审批和审计回放流程，并记录入口、角色、前置数据、状态、输出、失败路径、依赖和证据。

## 2. 实际提交材料

- [A2 历史流程联结证据](evidence/2026-08-27-a2-flow-linkage-v0.1.0.md)
- 原报告列出 FL-01～FL-18、BR-01～BR-14 和重复链路 D-01～D-07。

材料能够证明代码和本地数据中存在若干链路组成部分，但本阶段没有浏览器、API、服务或真机的当前运行证据。

## 3. 流程状态订正

| Flow_ID | 原状态 | 当前状态 | 订正依据 |
|---|---|---|---|
| FL-01 注册/入校 | CLOSED | STATIC_CHAIN_PRESENT + RUNTIME_UNKNOWN | 有页面/API/数据线索；未执行端到端流程。 |
| FL-02 教师建校/进入 | CLOSED | STATIC_CHAIN_PRESENT + RUNTIME_UNKNOWN | 数据存在不能证明由当前 UI 成功产生。 |
| FL-03 教师建班 | SEEDED_ONLY | SEEDED_ONLY | 保留静态结论；运行状态未知。 |
| FL-04 学生加入 | SEEDED_ONLY | SEEDED_ONLY | 保留静态结论；运行状态未知。 |
| FL-05 机器人资产管理 | CLOSED | STATIC_CHAIN_PRESENT + RUNTIME_UNKNOWN | 代码存在不等于权限、交互和持久化均已实测。 |
| FL-06 知识治理 | PARTIAL | PARTIAL | 批准后切块和检索底料断点仍成立。 |
| FL-07 SOP | PARTIAL | PARTIAL | 发布状态机缺口仍成立。 |
| FL-08 任务 | PARTIAL | PARTIAL | 终态写入与域责任未收口。 |
| FL-09 训练 | SEEDED_ONLY | SEEDED_ONLY | 前端写入口不足。 |
| FL-10 证据 | PARTIAL | PARTIAL | 多模型与授权问题未闭合。 |
| FL-11 评分 | CLOSED | STATIC_CHAIN_PRESENT + RUNTIME_UNKNOWN | 教学评分静态链存在；未执行完整流程。 |
| FL-12 报告 | PARTIAL | PARTIAL | 保留静态断点。 |
| FL-13 维保 | PARTIAL | PARTIAL | 后端能力与前端入口存在差集。 |
| FL-14 机器人控制 | MISSING | MISSING | 未找到产品级运动控制契约。 |
| FL-15 异常停止 | MISSING | MISSING | 未找到产品级急停入口与契约。 |
| FL-16 审批 | BROKEN | BROKEN | 审批不在真实执行路径上。 |
| FL-17 审计回放 | BROKEN | BROKEN | 多套回放与空数据路径未收口。 |
| FL-18 运维健康 | CLOSED/可用表述 | STATIC_ENDPOINT_PRESENT + DELIVERY_UNKNOWN | 静态端点存在；健康码语义和运行证据不足。 |

## 4. 证据边界

- FACT：静态代码、路由、前端调用和本地数据库快照能显示组成部分是否存在。
- INFERENCE：若入口、API 和数据表同时存在，可以推断存在设计意图，不能推断用户已走通。
- UNKNOWN：当前浏览器可达性、失败路径、跨角色权限、并发、持久化、断网和真实机器人行为。
- HISTORICAL：本地数据库行数属于当时快照；来源、生成路径和当前环境等价性未证实。

## 5. 门禁裁决

| 门禁 | 状态 | 说明 |
|---|---|---|
| A1 面向用户功能全部映射 | CONDITIONAL | 映射广泛，但 A1 分母未正式闭合。 |
| 关键流程断点全部登记 | CONDITIONAL | 已登记主要断点；运行失败路径未实测。 |
| 重复链路全部登记 | CONDITIONAL | 历史登记可用；A3/A6 后续又订正重复组数量与含义。 |
| “闭环”结论有运行证据 | FAIL | 5 条 CLOSED 被静态证据过度提升。 |
| M-AUD-05 | FAIL | 未保存 A2 阶段完整指纹复比。 |
| M-AUD-06 | BLOCKED | 未找到十题独立评分链。 |
| 准确批准口令 | FAIL | 未找到 `确认 Audit A2` 原始记录。 |

## 6. 最小修正要求与重开范围

1. 仅重开 FL-01、FL-02、FL-05、FL-11、FL-18 的“闭环/可用”结论及与其相关的后续表述。
2. 在获得探针批准前保持 `RUNTIME_UNKNOWN`；若申请探针，须另列目的、命令、数据、副作用与恢复方法。
3. 对所有流程补 M-AUD-05、M-AUD-06 和准确批准记录。
4. A6 功能地图不得再把上述静态链写成“可用”。

## 7. 阶段最终裁决

**FAIL。流程地图可保留，但真实闭环未被证明；需要定向重开五条被过度提升的流程和阶段批准链。**
