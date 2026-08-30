# R0 纠正台账

- 版本：0.2.0
- 日期：2026-08-30

| 编号 | 旧版结论 | 纠正结果 | 影响范围 | 当前状态 |
|---|---|---|---|---|
| R0-C01 | C-0 是急停最小正确模型，包含 VDA 取消与回执步骤 | 撤销。VDA `cancelOrder` 是业务协议，非安全标准；不可取消动作可继续并按结果 FINISHED/FAILED | D-03、D-08、M-07、R1-Q1、E3 | CORRECTED |
| R0-C02 | 被取消动作显式报 FAILED | 撤销。VDA 3.0.0 允许不可取消动作成功后报 FINISHED | VDA 原子事实、状态机设计 | CORRECTED |
| R0-C03 | openTCS 仓库含 LGPL-2.1-only，复制须按该许可处理 | 撤销。固定提交的 `REUSE.toml` 无 LGPL 路径映射；许可证文本存在不等于适用 | OSS-G2、D-03 许可证表 | CORRECTED_TO_UNKNOWN |
| R0-C04 | 七个对象凭 `last_push` 即通过 G4 | 全部撤销并重做。新版使用固定的有意义提交和发布；贡献者与响应抽样仍 UNKNOWN | 六个软件候选、活跃度评分 | CORRECTED_PARTIAL |
| R0-C05 | D-03 接近饱和且不排主参考 | 撤销。没有完整搜索/淘汰记录，六个软件候选均未通过全部硬门槛 | D-03、D-04、§7.8 | REOPENED |
| R0-C06 | D-01/D-02/D-06 可裁，D-05/D-07 轻做 | 撤销为未经批准的范围缩减；八域全部恢复分母 | M-01、M-02、M-06、M-13、M-18a 及其他上游问题 | REOPENED |
| R0-C07 | OpenRemote 复制代码会迫使整个 R-MOS 以 AGPL 开源 | 降级。AGPL 对 covered work 和修改程序的义务需结合组合方式判断，不能无事实基础外推整个系统 | D-04、OSS-G2、R1 采用边界 | CORRECTED_TO_PROFESSIONAL_REVIEW |
| R0-C08 | OPC UA Robotics 的区分可外推为行业唯一 | 限定为本次所审对象集合中的事实；信息模型不等于物理安全执行 | D-03、D-08、M-07 | CORRECTED |
| R0-C09 | A6 0.1.1 Approved，可形成 R0/R1 输入 | 撤销。现行 A6 0.2.0 为 RETURN FOR REVISION，26 项且 M-14/M-19 DISPUTED | 全部 R0/R1 路线 | BLOCKED |
| R0-C10 | 定义了评分模型即可视为完成 | 撤销。资格复算已执行；未过硬门槛者不产生数值分，独立评分尚未触发 | §7.6、§5.8 | CORRECTED_RETURN_FOR_REVISION |

## 保留的旧版原子事实

在固定来源边界内，以下事实可继续使用：ros2_control 的适配器/生命周期概念；Open-RMF 的状态上报枚举；openTCS 的车辆通信适配器边界；Ditto 的对象策略和数字孪生概念；ThingsBoard CE 的开源 IoT 代码库事实；OpenRemote 的资产/realm 概念；VDA 的业务取消状态；OPC 对急停与防护性停止的分离建模。

这些事实不等于项目合格、适合引入、问题关闭或路线获批。
