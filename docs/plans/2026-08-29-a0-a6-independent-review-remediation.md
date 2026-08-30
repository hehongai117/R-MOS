# A0–A6 独立复核纠正实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不覆盖历史报告、不伪造批准或运行证据的前提下，把 A0–A6 修订成内部一致、可复现、可提交董事会重新确认的当前正式审计包。

**Architecture:** 历史 `Approved` 文件保持不变；每阶段新增一个 `0.2.0` 纠正版，明确保留事实、暂停结论、UNKNOWN、重开范围和批准门禁。新增一个纯只读校验器机械检查文件清单、阶段状态、问题数量、本地链接和禁止性表述；A6 使用纠正后的单一问题登记表，不再依赖已失效的 0.1.0 台账。

**Tech Stack:** Markdown、Python 3.13 标准库、Git 只读命令、pytest。

## 授权与禁止事项

- 只修改 `docs/audit/**`、本计划、`docs/audit/README.md` 和 `docs-archive/DEVELOPMENT_LOG.md`。
- 不修改应用、测试、迁移、依赖、数据库、配置和资产。
- 不启动服务，不访问数据库，不联网，不连接外部环境、生产或真机。
- 不把缺失批准、M-AUD-06、P0 送达或运行证据写成 PASS。
- 允许创建本地 commit；禁止 push。

### Task 1: 先建立失败的纠正包门禁

**Files:**
- Create: `docs/audit/evidence/2026-08-29-a0-a6-remediation-gate.py`
- Create: `docs/audit/evidence/test_a0_a6_remediation_gate.py`

1. 编写测试，要求七份 `0.2.0` 报告存在且状态不是 `Approved`。
2. 要求 A6 产品问题数为 26，分级为 8/11/7，并另列审计治理阻断项。
3. 要求全部本地 Markdown 链接存在。
4. 要求 A1–A6 明确写出 M-AUD-06 未完成，且禁止出现“全部门禁达标”“审计序列完成”等无证据结论。
5. 运行测试，确认因纠正版尚不存在而失败。

### Task 2: 修订 A0–A2

**Files:**
- Create: `docs/audit/2026-08-29-a0-baseline-and-source-governance-audit-report-v0.2.0.md`
- Create: `docs/audit/2026-08-29-a1-system-function-and-asset-inventory-v0.2.0.md`
- Create: `docs/audit/2026-08-29-a2-user-roles-and-business-closure-audit-report-v0.2.0.md`

1. A0 保留双基线和 1,769 文件分类；把错误工作区配置指纹、备用 P0 渠道和 M-AUD-06 转为 BLOCKED。
2. A1 保留已核对资产；暂停完整路径差集 0、33 条 UNUSED 可删除和全量 100% 结论。
3. A2 把 `CLOSED` 改为 `STATIC_CHAIN_PRESENT / RUNTIME_UNKNOWN`，保留断点和孤立功能映射。
4. 为三阶段写出精确重开对象、下一阶段影响和重新批准口令。

### Task 3: 修订 A3–A5

**Files:**
- Create: `docs/audit/2026-08-29-a3-current-architecture-and-data-boundaries-v0.2.0.md`
- Create: `docs/audit/2026-08-29-a4-security-control-and-realtime-audit-report-v0.2.0.md`
- Create: `docs/audit/2026-08-29-a5-quality-operations-and-delivery-audit-report-v0.2.0.md`

1. A3 区分已核对代表性代码事实与未保存脚本支持的精确数量。
2. A4 保留已由代码确认的高风险根因，暂停“100% 非公开入口矩阵”与执行期可利用性结论。
3. A5 把 CI workflow 描述统一降为配置事实；把实际运行全部标为 HISTORICAL 或 UNKNOWN。
4. 明确 E1 FAIL、E2–E4 和生产启用 BLOCKED 不变。

### Task 4: 重建 A6

**Files:**
- Create: `docs/audit/2026-08-29-a6-master-audit-report-and-decision-input-v0.2.0.md`
- Create: `docs/audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md`

1. 固定产品问题为 26 项：8 P0、11 P1、7 P2。
2. 把 M-04 放入 P1，把 M-06/M-07/M-13/M-18a 放入 P0。
3. 单独登记 A0 审计治理阻断项，不与产品严重度混算。
4. 删除“5 P0 + 13 P1”等遗留数字；所有路线结论受 E2 缺失约束。
5. 所有 A0–A5 输入逐项有去向；无法重现的数量标为 SUSPENDED/UNKNOWN。

### Task 5: 补齐可执行的治理收口包

**Files:**
- Create: `docs/audit/evidence/2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md`

1. 提供每阶段 M-AUD-06 十题候选、董事会替换位、评分记录和独立性字段。
2. 提供逐阶段准确批准口令和原始消息登记表。
3. 提供 P0 主/备用渠道送达记录模板。
4. 明确只有实际完成并保存原始证据后才可把阶段改回 Approved。

### Task 6: 索引、交接和开发记录

**Files:**
- Modify: `docs/audit/README.md`
- Create: `docs/handover/2026-08-29-a0-a6-independent-review-remediation-handover-v0.1.0.md`
- Modify: `docs-archive/DEVELOPMENT_LOG.md`

1. README 顶部切换到纠正版，并把旧 Approved 包标为历史、已被复核退回。
2. 交接文档列出当前有效文件、仍需用户完成的治理动作和禁止误读。
3. 开发记录写明命令、结果、未运行项、失败处理和下一步。

### Task 7: 验证与提交

1. 运行纠正包单元测试和门禁脚本。
2. 运行全部本地链接检查、固定词反向检查、`git diff --check`。
3. 核对 `git diff --name-only` 只有本计划列出的文件。
4. 复读七份报告，确认没有把 UNKNOWN 写成 PASS。
5. 仅暂存本任务文件并创建本地提交；不 push。

## 执行状态（2026-08-30）

- Task 1～6：完成。
- Task 7 验证：完成；门禁 PASS、单元测试 4 passed、本地链接 0 缺失、`git diff --check` PASS。
- Task 7 提交：本计划与全部整改材料在同一本地提交中固定；不 push。
- 审计状态：A0–A6 仍为 RETURN FOR REVISION；缺失的人类批准和运行证据没有被文档替代。

### Claude Code 独立复核跟进（2026-08-30）

- 裁决：CONDITIONAL 接受 `78d9c4b7`，提出 2 个 P1 和 1 个 P2 局部问题。
- 版本处理：保留 A1 0.2.0 与交接 0.1.0，新增 A1 0.2.1 与交接 0.1.1。
- 门禁处理：新增反引号证据路径检查、台账逐行复算与重复编号检查、README 当前状态区检查。
- 边界：没有把整改包的通过提升为 A0–A6、E2/E3/E4、REL-BLOCK-01 或生产通过。
