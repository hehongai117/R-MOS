# R0 硬门槛与评分状态矩阵

- 版本：0.2.0
- 日期：2026-08-30
- 状态：RETURN FOR REVISION

## 1. 软件候选资格复算

章程规定：OSS-G1～G6 全部通过后，候选才进入 100 分评分。以下不是“忘记打分”，而是实际执行资格判断后的结果。

| 域 | 软件候选 | G1 | G2 | G3 | G4 | G5 | G6 | 数值评分状态 | 主/次参考 |
|---|---|---|---|---|---|---|---|---|---|
| D-03 | ros2_control | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |
| D-03 | Open-RMF | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |
| D-03 | openTCS | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |
| D-04 | Eclipse Ditto | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |
| D-04 | ThingsBoard CE | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |
| D-04 | OpenRemote | PASS | UNKNOWN | PASS | PASS | UNKNOWN | PASS | NOT_ELIGIBLE | 无 |

### G4 纠正说明

所有旧版 `last_push` 依据均已撤销。新版 G4 只使用 `source-register.yaml` 中固定的非 merge、非格式、非版本号的功能/构建提交，并辅以正式发布记录。贡献者和 issue/PR 响应尚未按章程抽样，因此活跃度评分对应子项仍为 UNKNOWN/0；G4 PASS 不等于 15 分活跃度已取满。

### 为什么没有“补一个总分”

G2 的逐文件、依赖和组合方式仍不完整；G5 的目标版本、支持期、公告、漏洞、容器和 OpenSSF 仍不完整。此时填写 0–100 总分会违反章程的先门槛后评分顺序。主审与异源复核的独立数值评分也因此尚未触发。

## 2. 规范证据

| 规范 | 类型 | 是否参加 OSS 评分 | 当前可用结论 |
|---|---|---|---|
| VDA 5050 3.0.0 | 车队控制通信规范 | 否 | 可借订单取消和状态回执语义；不得当作安全标准或急停链 |
| OPC UA Robotics 1.02 | 信息模型规范 | 否 | 在本次所审对象中可借急停/防护性停止分离的状态词汇；不得外推行业唯一或物理执行 |
| ISO 13850:2015 | 机械急停原则 | 否 | 用于界定急停设计原则；具体适用仍需风险评估和厂家资料 |
| ISO 3691-4:2023 | 无人工业车辆安全要求 | 否 | 适用于相应 AGV/AMR 类别时提供安全与验证依据；适用性须逐机器人确认 |

## 3. 各域当前结果

| 域 | 搜索状态 | 合格主参考 | 合格次参考 | 是否饱和 |
|---|---|---:|---:|---|
| D-01 | NOT_STARTED | 0 | 0 | 否 |
| D-02 | NOT_STARTED | 0 | 0 | 否 |
| D-03 | PARTIAL_REOPENED | 0 | 0 | 否 |
| D-04 | PARTIAL_REOPENED | 0 | 0 | 否 |
| D-05 | NOT_STARTED | 0 | 0 | 否 |
| D-06 | NOT_STARTED | 0 | 0 | 否 |
| D-07 | NOT_STARTED | 0 | 0 | 否 |
| D-08 | PARTIAL_REOPENED | 0 | 0 | 否 |
