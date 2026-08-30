# A0–A6 独立复核整改交接

- 版本：0.1.1
- 编制：2026-08-29 至 2026-08-30
- 工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 分支：`audit/phase3-auth-control-realtime`
- 事实基线：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 首轮整改提交：`78d9c4b723cc443f9c50c7cf1248d98f09bb6d3f`
- 状态：Claude Code 独立复核提出的三项局部问题已整改；外部治理与运行证据仍待人类动作
- 替代关系：本文件替代 v0.1.0，登记 A1 0.2.1 和门禁增强；v0.1.0 保留。

## 1. 已完成

1. 保留所有历史报告和已复核版本，不覆盖历史文件。
2. A0、A2～A6 保持 0.2.0；A1 新增 0.2.1 修正证据脚本路径；七阶段统一保持 `RETURN FOR REVISION`。
3. 把静态代码事实、推断、历史结果和 UNKNOWN 分开。
4. 把五条被误写成 CLOSED 的流程降为 `STATIC_CHAIN_PRESENT + RUNTIME_UNKNOWN`。
5. 重算 A6：产品问题 26 个，P0 8、P1 11、P2 7。
6. 把 5 个审计治理阻断项从产品问题严重度中独立列出。
7. 治理闭环包提供准确批准口令、七阶段 M-AUD-06 候选题、P0 主备通道记录表和指纹复比表。
8. 自动门禁现在机械统计台账行数、严重度和重复编号，同时检查 Markdown 链接、反引号证据路径及当前正式状态区的无证据完成表述。

## 2. 当前正式材料入口

- [A0 0.2.0](../audit/2026-08-29-a0-baseline-and-source-governance-audit-report-v0.2.0.md)
- [A1 0.2.1](../audit/2026-08-30-a1-system-function-and-asset-inventory-v0.2.1.md)
- [A2 0.2.0](../audit/2026-08-29-a2-user-roles-and-business-closure-audit-report-v0.2.0.md)
- [A3 0.2.0](../audit/2026-08-29-a3-current-architecture-and-data-boundaries-v0.2.0.md)
- [A4 0.2.0](../audit/2026-08-29-a4-security-control-and-realtime-audit-report-v0.2.0.md)
- [A5 0.2.0](../audit/2026-08-29-a5-quality-operations-and-delivery-audit-report-v0.2.0.md)
- [A6 0.2.0](../audit/2026-08-29-a6-master-audit-report-and-decision-input-v0.2.0.md)
- [订正归并台账](../audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md)
- [治理闭环包](../audit/evidence/2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md)
- [整改实施计划](../plans/2026-08-29-a0-a6-independent-review-remediation.md)

## 3. Claude Code 独立复核后的修订

| 复核问题 | 修订结果 |
|---|---|
| A1 0.2.0 引用不存在的脚本名 | 新增 A1 0.2.1，改为真实脚本并使用可检查链接 |
| A6 门禁只检查声明字符串 | 改为逐行统计 Master_ID、严重度、总数和重复编号，并与 A6 声明互证 |
| 禁止完成表述未覆盖配套材料 | 报告、治理包、交接全量检查；README 只检查历史分界线之前的当前状态区，避免误伤追溯原文 |

## 4. 没有完成、也不能由文档代办的事项

- 董事会尚未按准确口令完成 A0～A6 的定向重开与重新批准。
- 七阶段 M-AUD-06 尚未由董事会密封出题、独立答题和独立评分。
- P0 主、备用通知通道及八个 P0 的实际送达证据尚未补齐。
- A0～A6 的完整环境指纹复比和当前 HEAD 漂移评估尚未完成。
- 未进行受控 E2、恢复、回滚、断网、真机或课堂验收。
- 未改变 E1 FAIL、E2/E3/E4 BLOCKED、REL-BLOCK-01 或生产启用状态。

## 5. 下一步顺序

1. 董事会先批准治理闭环包中的定向重开口令。
2. A0 补 B-REF/干预链、指纹、P0 主备通道、截止日期和 M-AUD-06。
3. A0 准确批准后，按 A1～A5 订正版的最小范围依次增量补证。
4. 解决 M-14 分组与 M-19 严重度争议。
5. 重新生成 A6，确认 26 项台账和所有运行 UNKNOWN/BLOCKED。
6. 最后才逐阶段使用准确批准口令；A6 重新批准前不形成绑定性 R0/R1 路线决定。

## 6. 只读验证

在 worktree 根目录执行：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python docs/audit/evidence/2026-08-29-a0-a6-remediation-gate.py
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest docs/audit/evidence/test_a0_a6_remediation_gate.py -q
git diff --check
```

这些命令只检查整改材料，不启动服务、不写数据库、不连接外部环境。

## 7. 最终交接结论

Claude Code 指出的三项局部问题已纳入版本化修订。**整改包的防错能力得到加强，但 A0–A6 审计仍未正式完成；下一位主审应执行治理闭环，而不是继续 R0 或把本交接当成批准。**
