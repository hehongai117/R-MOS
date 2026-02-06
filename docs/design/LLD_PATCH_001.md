# LLD_PATCH_001｜LLD 最小补丁清单（不重写）

> 文档状态：Draft v1.0
> 适用对象：`docs/design/LLD_TASK_BREAKDOWN_V0_3.md`
> 目的：修正当前 LLD 与规范/验收口径之间的含糊点，保证可实现、可验收、可回溯。

---

## Patch-001：清理不可解析引用占位

- 问题：LLD 中存在大量 `:contentReference[oaicite:...]` 占位符，当前仓库并无对应解析链，导致文档不可机器检查、可读性下降。
- 修正：将占位符替换为明确的本仓路径引用（如 `docs/specs/AUTHZ_RBAC_SPEC_FINAL.md#...`），保持语义不变。
- 影响范围：LLD 全文（尤其 0、1、2、3、4、5、6、7、8、9、10、11、12、14 节）。
- 对应 Test ID：`AUDIT-T008`, `E2E-T006`, `E2E-T007`（追溯链可读性与一致性保障）。

## Patch-002：统一 critical 审批组合为“策略驱动”

- 问题：LLD 将 F-003 固定为 `teacher+auditor`，而上位规范对 critical 审批存在“可配置组合”描述，造成实现口径易分叉。
- 修正：将 LLD 表述改为：
  - critical 审批组合由 `approval_policies` 决定（策略驱动）；
  - P0 必须至少支持 `teacher+auditor` 场景，以满足验收矩阵 `APPR-T005`；
  - 允许扩展 `admin+auditor` 组合。
- 影响范围：模块 F（审批）、E（执行器校验）、C（审计）、测试计划映射。
- 对应 Test ID：`APPR-T002`, `APPR-T005`, `APPR-T009`, `APPR-T010`, `SKILL-T003`。

## Patch-003：统一审批 API 前缀口径

- 问题：文档族中出现 `/api/v1/approvals/*` 与 `/api/v1/ai/approvals/*` 并存，容易导致路由实现与测试脚本不一致。
- 修正：LLD 统一以 `/api/v1/ai/approvals/*` 作为主口径；如保留旧路径，必须声明兼容别名与弃用时间。
- 影响范围：模块 F（审批 API）、G（Command 关联）、测试脚本与回归命令。
- 对应 Test ID：`APPR-T001`, `APPR-T003`, `APPR-T004`, `APPR-T007`, `APPR-T012`。

## Patch-004：补充 RAG 过滤与 HTTP 响应码双断言

- 问题：LLD 虽提到“RAG 空结果不等于 HTTP 404”，但 DoD 描述未强制双场景联测，易在实现中混淆。
- 修正：在 H-004 明确双断言模板：
  1. RAG 检索越权文档 -> 返回空/insufficient_data + `rag_filter_applied`；
  2. 直接 HTTP GET 同对象 -> 404 + `access_denied`（含真实 resource_id）。
- 影响范围：模块 H（RAG）、B（对象级权限）、C（审计）。
- 对应 Test ID：`RAG-T005`, `RAG-T008`, `SEC-T005`, `SEC-T006`, `E2E-T004`。

## Patch-005：强化写工具“审批前禁止写入”硬门控

- 问题：LLD 对写工具状态流有描述，但未把“未审批不得落库”定义为执行器硬断言，存在绕过风险。
- 修正：在 E-003 增加硬规则：
  - `side_effects` 非空且审批未 `approved` 时，执行器必须拒绝执行并记录 `tool_call_pending`；
  - 仅 `approved` 后允许写入并记录 `tool_call_success`。
- 影响范围：模块 E（执行器）、F（审批状态机）、C（审计字段）。
- 对应 Test ID：`AGENT-T006`, `AGENT-T007`, `AGENT-T008`, `AGENT-T009`, `APPR-T001`。

## Patch-006：trace_id 必填策略显式化

- 问题：LLD 强调 trace 串联，但未在任务级别明确“AI 路径关键表字段非空或应用层强校验”。
- 修正：在 G/E/F/C/J 的 DoD 增加：
  - Command、ToolCall、Approval、Audit AI 路径必须带 `trace_id`；
  - 缺失 trace_id 视为用例失败。
- 影响范围：模块 G、E、F、C、J。
- 对应 Test ID：`AUDIT-T008`, `E2E-T006`, `E2E-T007`, `E2E-T005`。

## Patch-007：补齐 Gate 与模块边界说明

- 问题：LLD 模块顺序明确，但 Gate-2 与 Gate-3 在模块 G（Command）的边界不够清晰，可能造成跨阶段开发。
- 修正：补充边界：
  - Gate-2 仅实现 G-001（状态骨架与 trace 串联）；
  - Gate-3 才实现 G-002/G-003（意图编排与业务闭环）。
- 影响范围：模块 G 与整体计划分解。
- 对应 Test ID：`SKILL-T001`, `APPR-T001`, `MVP-001`, `E2E-T001`。

---

## 生效方式

1. 本补丁文档为 LLD 的最小增量解释层，不替代原 LLD。
2. 后续若改动原 LLD，应逐条吸收本补丁并移除对应补丁项。
3. 未吸收前，以本补丁与上位规范（优先级链）共同约束实现与验收。

