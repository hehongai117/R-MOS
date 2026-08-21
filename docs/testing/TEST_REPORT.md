# R-MOS 当前测试报告

- 版本：0.1.0
- 建立日期：2026-08-21
- 状态：Active
- 上位规则：`docs/testing/ACCEPTANCE_CHARTER.md`

## 1. 使用规则

本文件只记录能绑定到具体提交和环境的实际结果。计划、期望输出、旧报告和其他提交的测试数字不得直接登记为当前 PASS。

每个批次至少记录：Test ID、提交、环境、命令或操作、关键输出、证据位置、结果、失败处理和复验结果。

## 2. 当前总览

| 范围 | 当前状态 | 说明 |
|---|---|---|
| 规则事实源修复 | PASS | DOC-RULE-001 文档门禁已通过；不代表 E1 至 E4 应用验收通过 |
| E1 软件安全与主链路 | NOT_RUN | 本批不执行应用测试 |
| E2 预生产非功能 | BLOCKED | 预生产环境和正式演练证据未在本批核实 |
| E3 真机安全 | BLOCKED | 五台真机和现场安全证据未在本批核实 |
| E4 课堂试点 | BLOCKED | 20 场课堂试点未在本批核实 |
| 生产启用 | BLOCKED | `REL-BLOCK-01` 未清零 |

## 3. 历史快照索引

以下数字只用于定位历史，不是本文件对当前提交的重新验收：

| 日期 | 来源 | 历史结果 | 状态 |
|---|---|---|---|
| 2026-08-21 | `docs/superpowers/plans/2026-08-17-sop-three-phase-guided-flow.md` | 后端 822 passed / 3 skipped；前端 511 passed / 2 skipped；前端构建 PASS | HISTORICAL |
| 2026-07-24 | `docs/2026-07-24-系统测试交接说明.md` | 当时的系统测试与交接快照 | HISTORICAL |
| 归档前 | `docs-archive/TEST_REPORT.md` | 旧测试报告 | HISTORICAL |

## 4. 当前批次记录

### DOC-RULE-001｜规则事实源修复

- 基线提交：`213775c624d79c3ec6b8adaeefb448ec9ad05107`
- 结果提交：本报告所在提交
- 环境：`codex/architecture-audit-phase0` 隔离工作区
- 范围：验收章程、最高规则及镜像、环境口径、当前报告、审查记录
- Commands Run：
  - `shasum -a 256 AGENTS.md docs/ops/CODEX_RULES.md`
  - `test -f <全部现行事实源和审查索引链接目标>`
  - `rg --pcre2 -n <旧优先级路径> AGENTS.md docs/ops/CODEX_RULES.md`
  - `rg -n <验收状态、证据等级、G1-G6、REL-BLOCK-01、HISTORICAL>`
  - `git diff --cached --check`
  - `git status --short --branch`
  - Claude Code 两轮受限只读读者复核，完整边界与结果见证据文件
- Key Output：
  - `AGENTS.md` 与规则镜像 SHA-256 完全一致。
  - 现行优先级中的具体文件和审查索引链接目标全部存在；旧 2026-03-05 悬空路径在两份最高规则中命中 0 项。
  - 验收章程包含 6 个状态、E0 至 E4、G1 至 G6 和生产阻断来源。
  - `TEST_PLAN.md` 的 14 个历史 PASS 标题全部改为 HISTORICAL，当前 PASS 标题命中 0 项。
  - Claude 第一轮发现 4 项问题，全部经独立核对后修正；第二轮确认 4 项关闭，未发现新的 P0、P1 或 P2。
  - 变更仅包含规则、验收、审查和开发记录文档；主工作区保持原分支且无改动。
- Evidence：
  - `docs/audit/2026-08-21-claude-code-readonly-evidence-v0.1.0.md`
  - `docs/audit/2026-08-21-phase0-source-register-v0.1.0.md`
  - `docs-archive/DEVELOPMENT_LOG.md`
- Result：PASS（仅 DOC-RULE-001 文档门禁）
- Failure Handling：
  - 隔离环境内 Claude 登录状态误报为未登录；在隔离限制之外复核为已登录。
  - 第一次 Claude 调用因预算不足中止；定位根因后改用 Sonnet 和受控预算，真实只读样例成功。
  - 第一次规则补丁因原文匹配差异未写入；拆成小补丁后成功，并用哈希验证镜像一致。
  - 第一次旧路径检索因默认模式不支持后向判断而失败；改用明确支持该语法的 PCRE2 后重跑。
- Notes：本批未运行后端、前端、浏览器、数据库、预生产、真机或课堂测试；E1 至 E4 和生产启用状态没有被提升。
