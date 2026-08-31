# A0 治理重开与 M-AUD-06 准备记录

- 版本：0.1.0
- 日期：2026-08-31
- 状态：A0 REOPENED / IN REVIEW；AG-01 PARTIAL；AG-02～AG-05 未关闭
- 分支：`audit/phase3-auth-control-realtime`
- 重开前提交：`f5fc614e89d848a6ae25bfb2bb1da51edb905370`
- 结果提交：本文件所在提交；提交前不得把该字段视为已固定，提交后用 `git log -1 --format=%H -- <本文件路径>` 解析
- 当前 A0 报告：[A0 基线与事实源审计报告 0.2.0](../2026-08-29-a0-baseline-and-source-governance-audit-report-v0.2.0.md)
- 上位指令：[董事会完整审计与改造方向指令 0.2.0](../../plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md)
- 原治理模板：[A0–A6 审计治理闭环包 0.1.0](2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md)

原治理模板保留 2026-08-29 的待办快照，其中 A0 重开行的 `PENDING` 已由本文件的原始批准记录更新；不得再把旧行当成当前状态。

## 1. 原始重开批准记录

| 字段 | 记录 |
|---|---|
| 原始消息全文 | `` `确认重开 Audit A0 AG-01/AG-02/AG-03/AG-04/AG-05` `` |
| 规范化口令 | `确认重开 Audit A0 AG-01/AG-02/AG-03/AG-04/AG-05` |
| 发送者 | R-MOS 董事会授权用户（当前 Codex 任务中的用户消息） |
| 接收者 | Codex A0 整改执行者（当前任务） |
| 稳定任务/归档编号 | Codex task/thread `01a04e1d-cc62-7c71-84d6-34c118465cb5`；应用内消息 ID 未向执行者暴露，记为 UNKNOWN |
| 接收时间 | 2026-08-31 12:49:08 CST / 2026-08-31T04:49:08Z |
| 原始消息 SHA-256 | `dba02f75c06b6fa26c57a6841d7fe1568aec9867927b05742d642bff3e39b701`（包含首尾 Markdown 反引号） |
| 规范化口令 SHA-256 | `8ddc9700185769d87549c1757cc89eb890036181fd81634158aea2c2b12ed140` |
| 阶段 | Audit A0 |
| 原因编号 | AG-01、AG-02、AG-03、AG-04、AG-05 |
| 对应报告 | A0 0.2.0；该报告仍为 FAIL/RETURN FOR REVISION，未获重新批准 |
| 对应现场 | `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`；`audit/phase3-auth-control-realtime`；重开前 HEAD `f5fc614e...5370` |
| 原始归档位置 | 上述 Codex task/thread 的 2026-08-31 12:49:08 CST 用户消息；本文件保存逐字转录、哈希和现场关联，不替代应用内原始消息 |

本记录满足“批准重开”的口令要求，只授权对列明对象做增量取证、增量复核和增量批准。它不等于 `确认 Audit A0`，也不自动批准 A1～A6、R0 或 R1。

## 2. 重开影响面

| 对象/结论 | 重开后的状态 | 说明 |
|---|---|---|
| A0 阶段 | REOPENED / IN REVIEW | 允许处理 AG-01～AG-05；完成后仍须董事会使用 `确认 Audit A0` 单独批准 |
| AG-01 的 A0 重开动作 | COMPLETE | 本文件保存准确口令、角色、时间、报告、重开前提交与稳定任务归档编号；结果提交只在本文件进入 Git 后固定 |
| AG-01 的 A0 再批准动作 | PENDING | 不能由本次重开口令替代 |
| AG-02 / M-AUD-06 | BLOCKED / NEXT HUMAN ACTION | 候选题尚未获董事会密封批准，董事会尚未独立新增或替换至少 3 题 |
| AG-03 / 八个 P0 主备送达 | BLOCKED | 未取得真实主通道、备用通道、接收者及送达回执 |
| AG-04 / A0 环境指纹 | PARTIAL / BLOCKED | [当前环境与漂移指纹](2026-08-31-current-environment-and-drift-fingerprint-v0.1.0.md)已有 Git、Python、Node、配置与存储元数据；数据库、运行路由和前端入口仍需单独批准探针 |
| AG-05 / 漂移复比 | PARTIAL / BLOCKED | [当前环境与漂移指纹](2026-08-31-current-environment-and-drift-fingerprint-v0.1.0.md)已登记当前漂移；精确分母复算、历史同期对照和影响归因未闭合 |
| B-REF 与完整 INTERVENTION-SET | UNKNOWN / BLOCKED | [A0 0.2.0 第 5～6 节](../2026-08-29-a0-baseline-and-source-governance-audit-report-v0.2.0.md)要求补齐逐提交批准映射，尚未闭合 |
| A0～A6 总截止日期 | UNKNOWN / BLOCKED | 未找到可独立核验的正式董事会截止日期确认；未确认不得进入 A1 |
| A1 清单范围与排除项 | NOT APPROVED / BLOCKED | 尚无 A0 重开后的准确批准记录；不能用旧材料或本次重开口令替代 |
| 固定 B-ASIS 的 1,769 个 Git 文件分类 | HISTORICAL / 保留 | 只证明固定 Git 分母的分类，不因定向重开失效，也不外推为全系统完成 |
| A1～A6 | PREWRITTEN / NOT FORMALLY APPROVED | A0 未重新批准前不能按正式阶段完成处理 |
| R1 | BLOCKED | 董事会指令要求 A6 与 R0 均通过后才可开始 |

## 3. 本次重开允许处理的对象

- AG-01：A0 重开原文、受影响范围、后续再批准链。
- AG-02：A0 的 M-AUD-06 最终题目、原始回答、冻结评分标准、逐题评分和角色独立性。
- AG-03：M-01、M-02、M-03、M-05、M-06、M-07、M-13、M-18a 的主通道与备用通道真实送达证据。
- AG-04：A0 环境指纹缺失项，包括数据库、运行路由和前端可达入口；任何探针仍需先单独获批。
- AG-05：从固定 B-ASIS 到当前工作区的漂移复比、归因、受影响分母和依赖结论。

未列入本次口令的固定 Git 文件分类无需重做。若后续证据扩大影响面，必须先补充受影响对象和依赖结论，不能静默扩大重开范围。

## 4. A0 M-AUD-06 候选题（尚未获董事会批准）

下列题目继承自治理闭环包，只是主审候选题，不是最终题：

| 编号 | 候选问题 |
|---|---|
| A0-Q01 | B-REF、B-ASIS 和 INTERVENTION-SET 分别回答什么问题？ |
| A0-Q02 | 为什么 1,769 个 Git 文件分类完成不能代表全系统审完？ |
| A0-Q03 | A0 运行环境指纹必须包含哪些事实源？ |
| A0-Q04 | 哪些无法取得的快照必须标 UNKNOWN，为什么？ |
| A0-Q05 | P0 主通道和备用通道分别需要保存什么送达证据？ |
| A0-Q06 | Phase 3 为什么只能作为干预层，不能成为审计边界？ |
| A0-Q07 | M-AUD-05 如何阻止后续阶段无解释地换基线？ |
| A0-Q08 | A0 未批准时 A1～A6 的正式地位是什么？ |
| A0-Q09 | `.env` 指纹来源错误影响哪些结论？ |
| A0-Q10 | A0 目前哪些门禁仍为 FAIL、BLOCKED、PARTIAL 或 UNKNOWN？ |

## 5. AG-02 下一道人工作业

董事会需要返回最终 10 题，并满足以下条件：

1. 明确写出 `确认 A0 M-AUD-06 最终题目`；
2. 给出最终 A0-Q01～A0-Q10 全文；
3. 至少 3 题由董事会独立新增或替换，并标记 `BOARD-NEW` 或 `BOARD-REPLACED`；
4. 在最终题目冻结前，不向答题者提供参考答案或评分表；
5. 题目冻结后，由非主审的新会话作答，再由另一名非主审评分者按冻结标准逐题评分。

仅回复“确认这些题目”或原样接受十道主审候选题，不满足董事会独立新增或替换至少 3 题的要求。

## 6. 当前裁决

**A0 已按准确口令重开，状态为 IN REVIEW。AG-01 整体仍为 PARTIAL，只有其中的“A0 重开动作”完成；AG-02～AG-05、B-REF/INTERVENTION-SET、总截止日期、A1 范围、A0 再批准、A1～A6、R0 和 R1 的状态均未被提升。**
