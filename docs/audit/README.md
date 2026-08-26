# R-MOS 架构审查索引

本目录保存 R-MOS 架构审查的规则、事实源和阶段结论。审查从固定提交出发，只把可复现证据写成事实；历史记录、设计目标和当前实现必须分开。

## 当前状态

| 项目 | 状态 |
|---|---|
| 阶段 | **Phase 3 已冻结**（第 1–3、3b、2c 批已完成；P3-4/5/6 未开始；2026-08-26 起停止代码改动） |
| 版本 | 0.4.0 |
| 日期 | 2026-08-26 |
| 审查基线提交 | `cd9422d6fa6d3fc818ade1c45cb932197b95f0dc`（Phase 1 只读审查基线） |
| 当前工作分支 | `audit/phase3-auth-control-realtime`（未 push、未合并） |
| 生产代码改动 | **有**（Phase 3 起开始修复；Phase 0–2 为零改动） |
| 29 项发现 | 5 项 IN_PROGRESS（`AUTH-101`～`AUTH-105`，**均未关闭**），24 项 NOT_STARTED |
| 当前软件裁决 | E1 FAIL；六条链路全部 FAIL |
| 高等级验收 | E2 至 E4 与生产启用继续 BLOCKED；`REL-BLOCK-01` 未清零 |

> **阶段报告的现状（2026-08-26 核对）：** Phase 0 与 Phase 1 各有独立的阶段报告；
> Phase 2 的结论分散在修复矩阵、五份 ADR 和交接文档中，**没有单独的阶段完成报告**；
> **Phase 3 尚无阶段完成报告**（进行中，逐批结论落在 `../testing/TEST_REPORT.md`
> 与 `../../docs-archive/DEVELOPMENT_LOG.md`）。Phase 3 收口时须补一份阶段报告，
> 并同步刷新本索引。

## 文件

- [Phase 0 审查章程](./2026-08-21-phase0-audit-charter-v0.1.0.md)：审查范围、证据标准、完成门槛和安全底线。
- [Phase 0 事实源登记表](./2026-08-21-phase0-source-register-v0.1.0.md)：现行、归档、缺失、冲突材料及处理建议。
- [当前验收章程](../testing/ACCEPTANCE_CHARTER.md)：现行验收裁决、证据等级和安全门禁。
- [当前测试报告](../testing/TEST_REPORT.md)：当前提交的实际结果与历史快照边界。
- [Claude Code 只读协作证据](./2026-08-21-claude-code-readonly-evidence-v0.1.0.md)：登录差异、真实调用、费用、零改动检查和独立读者复核结果。
- [Phase 1 六链路审查报告](./2026-08-21-phase1-six-chain-review-v0.1.0.md)：29 项发现、当前测试基线、六条链路裁决和建议修复顺序。
- [Phase 1 Claude Code 只读复核证据](./2026-08-21-phase1-claude-code-readonly-evidence-v0.1.0.md)：两轮独立复核、采纳过程、费用和文件保护证据。
- [Phase 1 执行计划](../plans/2026-08-21-rmos-architecture-audit-phase1.md)：固定范围、九项执行任务和收口要求。
- [Phase 2 至 Phase 6 新窗口交接](../handover/2026-08-21-phase2-phase6-handover-v0.1.0.md)：精确恢复点、29 项发现地图、推荐阶段门槛和新窗口启动提示词。
- [Phase 2 修复矩阵（29 项）](./2026-08-21-phase2-remediation-matrix-v0.1.0.md)：逐项目标文件、失败测试、通过门槛、迁移回滚与关闭标准。**Phase 2 的主要产物，兼作其阶段结论**。
- Phase 2 的五份修复 ADR：[默认拒绝与对象归属](../adr/ADR-2026-08-21-authn-default-deny-and-object-ownership.md)、[机器人绑定与适配器隔离](../adr/ADR-2026-08-21-robot-binding-and-adapter-registry.md)、[证据完整性与 SOP 版本](../adr/ADR-2026-08-21-evidence-integrity-and-sop-versioning.md)、[AI 审批与审计门禁](../adr/ADR-2026-08-21-ai-approval-and-audit-gating.md)、[运行拓扑与生产部署](../adr/ADR-2026-08-21-runtime-topology-and-production-deployment.md)。均为 **Accepted（设计定案，非实现）**。
- [Phase 3 执行计划](../plans/2026-08-21-rmos-phase3-auth-control-realtime.md)：六批范围、先写失败测试的纪律与逐批通过门槛。
- [Phase 4 执行计划](../plans/2026-08-21-rmos-phase4-evidence-ai-deployment.md)：证据、AI 与运行环境，**未开始**。
- [Phase 3 续作交接](../handover/2026-08-25-phase3-continuation-handover-v0.1.0.md)：Phase 3 中途换窗口的恢复点、已完成批次与未完成问题清单。
- **[Phase 3 中期审查报告（代码冻结点）](./2026-08-26-phase3-interim-audit-report-v0.1.0.md)**：Phase 0–3 阶段边界核对、当前测试基线、29 项状态、**7 项新发现（含 1 个已实证的 P0 成绩篡改）**、当前裁决与待决策。

## 当前结论

Phase 0 发现的规则事实源冲突已经按用户确认的方向处理：新建当前验收章程和测试报告，更新最高规则及其镜像，统一 Python 环境与开发记录位置。旧文件仍只作为历史证据，没有被原样恢复。

Phase 1 已完成身份与对象归属、任务与机器人控制、SOP 证据与报告、AI 审批与审计、遥测实时通道、部署恢复与交付六条链路审查。当前共登记 29 项：1 个 P0、24 个 P1、4 个 P2。自动测试基线通过，但不能推翻已经确认的安全和隔离反证，因此 E1 仍为 FAIL。

Claude Code 已在受限只读模式完成两轮复核。第一轮提出 1 个 P2，Codex 独立核对后采纳；第二轮没有提出修正或新发现，调用前后文件哈希一致。E2、E3、E4 和生产启用没有被提升，`REL-BLOCK-01` 继续生效。

Phase 2 把 29 项发现全部映射到六个门禁与执行批次，并产出五份 ADR（用户 2026-08-21 确认后转 Accepted）。**这是设计定案，不是实现，也不是验收。**

Phase 3 自 2026-08-22 起开始修改生产代码，已完成 5 个批次：默认拒绝网关与公开白名单（7 条）、教学域服务端身份、机器人资产边界与登录限流、3D 资产带令牌加载（含浏览器实测）、对象归属校验第一刀（8 条路由）。**`AUTH-101`～`AUTH-105` 五项全部仍为 IN_PROGRESS，一项都未关闭**：全仓 180 条路由中仍有约 115 条无对象归属校验；`robots.py` 的资产越权拒绝仍不写审计；`get_training_feedback` 仍接受客户端可控的 `role` 查询参数。逐批实测结论以 `../testing/TEST_REPORT.md` 为准，命令与失败处理以 `../../docs-archive/DEVELOPMENT_LOG.md` 为准。
