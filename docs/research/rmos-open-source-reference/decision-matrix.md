# R0 评分矩阵与契约要素合成表

- 版本：0.1.0｜日期：2026-08-29｜阶段：R0
- 依据：章程 §7.6 评分模型、§7.8 产出要求
- 事实基线：A6 0.1.1（Approved）
- 主审：Claude｜异源复核：**PENDING**（章程 §5.8 要求主审与复核方分别评分，本表尚未复核）

---

## 1. D-03/D-08 机器人适配器契约（RQ-04 / M-07）

### 1.1 本域不排主参考的理由

三个候选给出三种**正交范式**（见 `domain-calibration-D03.md`）。
按章程 §7.8，本域正式结论记为：**多个合格参考，不应二选一**，
产出物为下方的契约要素合成表，而非主参考排名。

### 1.2 R-MOS 当前契约（对照基线）

`app/adapters/base.py` 的 `BaseRobotAdapter` 共 **10 个抽象方法**：

```
connect / disconnect / is_connected
get_robot_info / get_robot_structure / get_joint_states / get_sensor_data
inject_fault / clear_fault / get_active_faults
```

**分类：连接 3、读取 4、故障注入 3。运动控制 0，停止/急停 0。**
这是 M-07「适配器契约无运动控制与急停」的精确形态。

### 1.3 契约要素合成表

| # | 要素 | 来源 | R-MOS 现状 | 建议 | 优先级 |
|---|---|---|---|---|---|
| **C-1** | **急停是状态契约的一级枚举** | Open-RMF `MODE_EMERGENCY=5` | 无状态枚举；急停仅在 Mock 内由中文关键词触发 | 定义机器人模式枚举，`EMERGENCY` 与 `IDLE/MOVING/PAUSED/ERROR` 并列 | **P0** |
| **C-2** | **停止 = 清空在途命令队列** | openTCS `clearCommandQueue()` | 无命令队列概念，下发即调用 | 与 C-1 配对实现。**只置状态位不清队列 = 假急停** | **P0** |
| **C-3** | **三态返回值** SUCCESS / FAILURE(可重试) / ERROR(严重) | ros2_control | 多为 `bool` | 用枚举返回值替换 bool，区分可重试与严重错误 | **P1** |
| **C-4** | **`on_error` 是契约方法** | ros2_control | 错误处理散在调用方 try/except | 把错误处理提升为抽象方法 | P1 |
| **C-5** | **能力分级 / 逐任务协商** | Open-RMF 分级接入；openTCS `canProcess(order)` | 10 个方法全量实现，全有或全无 | 拆成必选子集 + 可选能力；新增 `can_process(action)` | P1 |
| **C-6** | **命令队列背压与在途可见性** | openTCS `getCommandsCapacity` / `canAcceptNextCommand` / 未发已发双队列 | 完全没有 | 控制能力的前置条件，需与 C-2 一并设计 | P1 |
| **C-7** | **显式生命周期** configure/activate/deactivate/cleanup | ros2_control | 只有 connect/disconnect | 对无实时约束的 R-MOS 可能过重，**建议只取 activate/deactivate** | P2 |
| **C-8** | **故障传播默认隔离、显式声明才传播** | ros2_control Hardware Component Groups | 无分组概念 | 多关节/多部件机型才需要 | P2 |
| **C-9** | **中断建模为带生命周期的对象**（析构即恢复） | Open-RMF `Interruption` | 无 | Python 用上下文管理器等价表达 | P2 |

### 1.4 借什么 / 不借什么

**借（设计层，不复制代码）：** C-1 ~ C-9 如上。三个项目均为 C++/Java，代码不可迁移。

**明确不借：**

| 不借 | 理由 |
|---|---|
| ROS 2 消息、节点与运行时模型 | R-MOS 是 FastAPI 单机 compose，引入 ROS 2 运行时的成本与收益完全不成比例 |
| 实时性设计（ros2_control 的核心关切） | R-MOS 无实时需求 |
| 交通调度、路网、多机队冲突消解 | 单校单机场景不存在该问题 |
| JVM/Guice 体系（openTCS） | 技术栈不符 |
| **「ros2_control 有急停原语」这一说法** | 出处为 ROSCon 演讲材料，非契约文档，标 `[uncertain]`。**照此对标会重蹈 M-07** |

### 1.5 失败模式（R1 设计时必须避免）

1. **假急停**：只置 `EMERGENCY` 状态位，不清空在途命令 → 状态显示已停，排队指令继续下发。
   这与 R-MOS 现状（Mock 内关键词匹配触发）属同类缺陷，只是更隐蔽。
2. **抄枚举不抄迁移规则**：定义了 `EMERGENCY` 但没定义谁能置位、置位后哪些操作被拒绝、如何解除。
3. **生命周期过度移植**：把 ros2_control 为实时控制设计的完整状态机搬到无实时约束的系统，
   引入不必要的状态复杂度。

---

## 2. 许可证与安全风险表（D-03/D-08）

| 项目 | 许可证 | 只借设计 | 复制代码 | 引入依赖 | 部署服务 | 安全门禁 G5 |
|---|---|---|---|---|---|---|
| ros2_control | Apache-2.0 | ✅ 兼容 | ⚠️ 需保留版权/NOTICE、标注修改 | ❌ 不适用（C++） | ❌ 不推荐 | **UNKNOWN** |
| Open-RMF | Apache-2.0 | ✅ 兼容 | ⚠️ 同上 | ❌ 不适用（C++） | ❌ 不推荐 | **UNKNOWN** |
| openTCS | **多许可证（REUSE）**：Apache-2.0 / MIT / **LGPL-2.1-only** / CC-BY-4.0 / CC0-1.0 / OFL-1.1 | ✅ 兼容 | ⚠️ **必须逐文件看 SPDX 头**；仓库含 LGPL-2.1-only，抽样 API 基类为 MIT 但不得外推 | ❌ 不适用（Java） | ❌ 不推荐 | **UNKNOWN** |

**三项 G5 全部 UNKNOWN**：未取安全公告、漏洞库与 OpenSSF Scorecard。
按章程「证据不足一律 UNKNOWN」，**不得声称已通过**。
因本域拟采用方式均为「只借设计」（不引入代码、不部署服务），
G5 对本次结论的实际约束有限——但该判断本身需董事会认可，主审不自行豁免。

> **踩坑记录（供其他域复用）：** openTCS 的 GitHub API `license` 字段为 `null`，
> 因其采用 REUSE 规范而非单一 LICENSE 文件。**若按 API 元数据自动判定，会误将其淘汰。**
> 结论：OSS-G2 不得依赖 GitHub 许可证接口的自动识别结果，必须读仓库原文。

---

## 3. R1 必须决策的问题（本域）

| # | 问题 | 为什么现在答不了 |
|---|---|---|
| R1-Q1 | 急停的**权威层**在哪——软件契约、控制器固件，还是物理回路？ | 涉及真机安全责任划分，超出 E1 静态研究能力。三个开源项目都只解决软件层表达，**没有一个能替代厂家安全证据**（章程 §7.3 明示） |
| R1-Q2 | 是否引入命令队列（C-2/C-6）？ | 它会改变 R-MOS 现在「下发即调用」的同步模型，影响面超出适配器本身 |
| R1-Q3 | 能力分级（C-5）按机型层级还是按单个动作？ | Open-RMF 与 openTCS 给出两种解，取决于 R-MOS 未来机型异构程度 |

---

## 4. 完成度

| 域 | 状态 |
|---|---|
| D-03/D-08 | ✅ 3 候选深研完成、领域校准冻结、合成表产出。**待异源复核** |
| D-04 设备状态与订阅隔离 | ⏳ 未开始 |
| D-05 / D-07（轻做） | ⏳ 未开始 |
