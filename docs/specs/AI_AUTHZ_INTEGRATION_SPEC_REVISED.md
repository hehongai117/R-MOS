# AI_AUTHZ_INTEGRATION_SPEC｜AI 能力与权限体系集成规范

> **文档状态**: Final v1.0（一致性修订版）  
> **目标**: 规定 AI 工具调用、Skill 治理、Command 协议如何与 AUTHZ_RBAC_SPEC 完整集成，确保 AI 能力可控、可审计、可回放  
> **依据**: AUTHZ_RBAC_SPEC.md, 数字孪生维保智能体_R-MOS_.md  
> **前置依赖**: 必须先实现 AUTHZ_RBAC_SPEC 的 Phase 0-4（鉴权/RBAC/对象级/审计）

---

## 0. 核心结论

1. **AI 工具=Skill，必须权限声明**: 每个 Skill 必须声明 `preconditions`（权限/角色）、`risk_level`、`side_effects`、`allowlist_resources`
2. **写工具必须人工确认 + 审批**: medium/high/critical 风险的 Skill 必须走 Approval 流程，禁止自动执行
3. **审计全链路**: AI 对话、工具调用、审批决策、执行结果必须可追溯到 trace_id

---

## 1. 范围（In Scope / Out Scope）

### 1.1 In Scope
- Skill 元数据 schema 与权限声明
- Skill Registry + Governance（版本/签名/发布/审批/回滚）
- AI Tool Call 与 RBAC 集成（权限继承、对象级校验）
- Command 协议字段与权限/审批映射
- Approval 对象结构与审批流状态机
- 审计字段统一（trace_id、actor、resource、decision、reason、side_effect）
- 反注入硬约束（引用校验、参数白名单、上下文隔离）
- 端到端时序图与验收用例

### 1.2 Out of Scope
- LLM 模型选型与部署（后端自行选择 Anthropic/OpenAI/本地模型）
- RAG 向量库实现细节（推荐 pgvector 或 Qdrant）
- 前端 AI 对话 UI 设计（仅定义 API 契约）
- 多模态时间轴的视频/音频编解码（见 AI_TWIN_AGENT_SPEC.md）

---

## 2. 背景与现状

### 2.1 现有权限体系
[source: AUTHZ_RBAC_SPEC.md#3. 角色与权限模型]
- 角色：admin / teacher / student / auditor
- 权限格式：`{resource}:{action}`（如 `assignments:write`）
- 对象级规则：student 仅访问本人资源，teacher 仅访问所属课程范围，admin 全域
- **响应码规则**：[source: AUTHZ_RBAC_SPEC.md#4. 全局响应码规则]
  - Read 越权 → 404
  - Write 越权 → 403
  - 说明：**RAG 后过滤“返回空”属于检索层策略**，不等同于 HTTP 资源访问的响应码；HTTP GET 仍严格遵循 Read=404 / Write=403（防资源探测）
- **审批权限**：[source: AUTHZ_RBAC_SPEC.md#3.3 审批资源域]
  - approvals:read / propose / approve / reject
  - auditor 仅参与 critical 审批（OBJ-005 规则）
  - teacher 审批受课程范围约束

### 2.2 AI 能力需求
[source: 数字孪生维保智能体_R-MOS_.md#2. v0.3 目标形态]
- Layer A：RAG 知识助手（Read-Only）
- Layer B：Agent 工具调用（Read-Tools → Human-in-the-loop Write-Tools）
- Layer C：评估与回放（Eval + Replay + Regression）

[source: 数字孪生维保智能体_R-MOS_.md#5. Skill 原子化封装]
- Skill = 产品，不是脚本
- Skill 必须声明：input_schema, output_schema, preconditions, risk_level, side_effects, rollback_strategy, audit_policy, allowlist_resources, deterministic_checks

### 2.3 安全约束
[source: 数字孪生维保智能体_R-MOS_.md#0. 总原则]
- **证据优先**: 无引用不结论
- **可控执行**: 写操作默认禁用；启用必须 RBAC + 对象级权限 + 人工确认 + 审计记录
- **全链路可回放**: 输入、检索命中、引用片段、工具调用序列、输出、人工确认、执行结果、用户采纳与否

---

## 3. Skill 元数据 Schema（最小字段集）

### 3.1 Skill 定义表（skills）

```
id: UUID (PK)
skill_id: String (unique, not null)  # 格式: {domain}.{name}, 如 "tasks.create_sop_draft"
version: String (not null)  # 语义化版本, 如 "1.0.0"
name: String (not null)
description: String (not null)
input_schema: JSONB (not null)  # JSON Schema 格式
output_schema: JSONB (not null)  # 必须包含 evidence_refs 字段
preconditions: JSONB (not null)  # {required_roles, required_permissions, required_states}
risk_level: String (not null)  # low, medium, high, critical
side_effects: JSONB (not null)  # [resource_type], 如 ["sops", "tasks"]
rollback_strategy: JSONB (nullable)  # {type: "compensate"|"undo", steps: [...]}
audit_policy: JSONB (not null)  # {required_fields: [actor, args, decision, result, ...]}
allowlist_resources: JSONB (not null)  # [resource_type], 白名单
deterministic_checks: JSONB (not null)  # {param_ranges, blacklist_keywords, injection_patterns}
publisher_id: UUID (FK -> users.id, nullable)  # 发布者
publisher_signature: String (nullable)  # 签名（官方/厂商/院校）
status: String (not null)  # draft, review, published, deprecated
feature_flag: String (nullable)  # 功能开关键值（critical skills 默认禁用）
created_at: DateTime
updated_at: DateTime
published_at: DateTime (nullable)
deprecated_at: DateTime (nullable)
```

[source: 数字孪生维保智能体_R-MOS_.md#5.1 Skill 定义]

### 3.2 关键字段说明

#### input_schema / output_schema
JSON Schema 格式，例如：
```json
// input_schema
{
  "type": "object",
  "properties": {
    "course_id": {"type": "string", "format": "uuid"},
    "goal": {"type": "string", "maxLength": 500},
    "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]}
  },
  "required": ["course_id", "goal"]
}

// output_schema
{
  "type": "object",
  "properties": {
    "sop_draft_id": {"type": "string", "format": "uuid"},
    "evidence_refs": {
      "type": "array",
      "items": {"type": "string"}  // 引用 ID 列表
    }
  },
  "required": ["sop_draft_id", "evidence_refs"]
}
```

#### preconditions
```json
{
  "required_roles": ["teacher"],  // 可为空数组表示无角色限制
  "required_permissions": ["assignments:write"],
  "required_states": {  // 可选，对象级前置条件
    "course": {"status": "active"},
    "user": {"is_verified": true}
  }
}
```

#### risk_level
- **low**: 只读检索/摘要生成/复盘报告生成（可自动执行）
- **medium**: 创建任务草案/生成 SOP 草案/调整难度建议（必须 teacher confirm）
- **high**: 发布作业/评分发布/批量派单/生成最终 rubric（teacher confirm + 审计）
- **critical**: 故障注入/恢复、影响真实设备或大范围数据的操作（双人确认 + admin）

[source: 数字孪生维保智能体_R-MOS_.md#5.3 Skill 风险分级]

#### side_effects
写入的资源类型列表，如：
```json
["sops", "tasks"]  // 表示会写入 sops 和 tasks 表
```

**空数组表示无写入**：`[]`

#### rollback_strategy
对 high/critical 风险 Skill 必填：
```json
{
  "type": "compensate",  // compensate | undo
  "steps": [
    "delete sop_draft",
    "restore original assignment"
  ]
}
```

#### audit_policy
必记录字段：
```json
{
  "required_fields": [
    "actor_user_id",
    "trace_id",
    "skill_id",
    "args",
    "decision",
    "result_summary",
    "side_effects_applied"
  ]
}
```

#### allowlist_resources
白名单，Skill 只能访问这些资源类型：
```json
["sops", "tasks", "assignments"]
```

#### deterministic_checks
静态检查规则：
```json
{
  "param_ranges": {
    "difficulty": ["beginner", "intermediate", "advanced"],
    "max_steps": {"min": 1, "max": 50}
  },
  "blacklist_keywords": ["DROP TABLE", "DELETE FROM"],
  "injection_patterns": [
    "(?i)(script|onerror|javascript:)",
    "(?i)(union.*select|insert.*into)"
  ]
}
```

---

## 4. Risk Level Derivation Rules（硬约束）

**所有 Skill 必须遵守以下规则，违反将被审核拒绝。**

### 4.1 规则定义

| 规则 ID | 条件 | 要求 | 理由 |
|---------|------|------|------|
| RISK-001 | `side_effects` 非空（有写入） | `risk_level` 不能为 `low`，至少为 `medium` | 任何写入都需人工确认与审计 |
| RISK-002 | `side_effects` 包含关键资源 | `risk_level` 至少为 `high` | 关键资源影响大，需高级审批 |
| RISK-003 | `risk_level = critical` | 必须满足：<br>1. `feature_flag` 默认 false<br>2. `rollback_strategy` 非空<br>3. 审批配置要求双人确认 | Critical 动作不可逆，必须多重防护 |

**关键资源定义**（RISK-002）：
- `assignments`（发布作业）
- `grades`（评分相关）
- `publishing`（发布动作）
- `bulk_dispatch`（批量操作）
- `faults`（故障注入/清除）
- `delete`（删除操作，如涉及 `side_effects` 中的删除动作）

### 4.2 示例验证

**✅ 合规示例**:
```json
{
  "skill_id": "sops.create_draft",
  "side_effects": ["sops"],  // 有写入
  "risk_level": "medium"  // ≥ medium，符合 RISK-001
}
```

**❌ 违规示例**:
```json
{
  "skill_id": "bad_skill",
  "side_effects": ["tasks"],  // 有写入
  "risk_level": "low"  // 违反 RISK-001
}
```

**✅ 合规示例（关键资源）**:
```json
{
  "skill_id": "teaching.publish_grades",
  "side_effects": ["grades", "assignments"],  // 关键资源
  "risk_level": "high"  // ≥ high，符合 RISK-002
}
```

**❌ 违规示例（关键资源）**:
```json
{
  "skill_id": "bad_publish",
  "side_effects": ["assignments"],  // 关键资源
  "risk_level": "medium"  // 违反 RISK-002，应为 high
}
```

**✅ 合规示例（critical）**:
```json
{
  "skill_id": "adapter.inject_fault",
  "side_effects": ["faults"],
  "risk_level": "critical",
  "feature_flag": "enable_fault_injection",  // 默认 false
  "rollback_strategy": {
    "type": "undo",
    "steps": ["clear_fault"]
  }  // 非空，符合 RISK-003
}
```

### 4.3 审核检查清单

在 Skill 审核（draft → review → published）时，审核员必须验证：

- [ ] `side_effects` 非空 → `risk_level` 不是 `low`（RISK-001）
- [ ] `side_effects` 包含关键资源 → `risk_level` 至少为 `high`（RISK-002）
- [ ] `risk_level = critical` → `feature_flag` 存在且默认 false，`rollback_strategy` 非空（RISK-003）

---

## 5. Skill 生命周期与治理

### 5.1 状态机

```
draft → review → published → deprecated
         ↑          ↓
         └── rejected (from review)
```

**状态转移规则**:
- draft → review: 任何 Skill 发布者可提交
- review → published: 需 admin 审核通过（或配置的 skill_reviewer 角色），**必须通过 4.3 审核检查清单**
- review → rejected: admin 拒绝，附原因
- published → deprecated: admin 标记废弃（已调用的保留，新调用禁止）
- draft → draft: 编辑中

### 5.2 审核流程（review）

**审核对象**: skill_reviews 表
```
id: UUID (PK)
skill_id: UUID (FK -> skills.id)
reviewer_id: UUID (FK -> users.id)
status: String  # pending, approved, rejected
decision: String  # approve, reject, request_changes
reason: String (nullable)
created_at: DateTime
reviewed_at: DateTime (nullable)
```

**审核检查清单**（必须人工确认）:
- [ ] input_schema / output_schema 完整且合理
- [ ] preconditions 正确声明权限与角色
- [ ] **risk_level 评估合理，遵守 4.1 硬约束规则**
- [ ] side_effects 清单完整
- [ ] rollback_strategy（high/critical 必填）已提供
- [ ] allowlist_resources 最小化
- [ ] deterministic_checks 覆盖注入风险
- [ ] 测试用例通过（见 skill_test_cases 表，后续）

### 5.3 版本管理

- 语义化版本：MAJOR.MINOR.PATCH
- 每次 schema/preconditions/risk_level 变更必须递增版本
- 版本发布后不可修改（immutable），只能新建版本
- 调用时指定版本（默认 latest published）

### 5.4 签名与来源

- **publisher_signature**: 格式 `{org_type}:{org_name}`，如：
  - `official:anthropic`（官方）
  - `vendor:acme_robotics`（厂商）
  - `institution:tsinghua`（院校）
- 用于信任评估与审计

---

## 6. AI Tool Call 与 RBAC 集成

### 6.1 工具调用流程

```
User Input (Command) 
  → LLM generates tool calls 
  → 权限校验（API-level + Skill preconditions） 
  → 对象级权限校验（如需访问 attempt/task/course） 
  → 审批门控（medium/high/critical） 
  → [人工确认] 
  → 执行 Skill 
  → 审计记录 
  → 返回结果（含 evidence_refs）
```

### 6.2 权限继承规则

**原则**: AI 工具调用继承当前用户的权限上下文

**实施**:
1. 从请求中提取 `current_user`（通过 JWT）
2. 验证 Skill preconditions:
   ```python
   # 伪代码
   skill = get_skill(skill_id, version)
   
   # 角色校验
   if skill.preconditions.required_roles:
       if not any(role in current_user.roles for role in skill.preconditions.required_roles):
           raise ForbiddenError("Missing required role")
   
   # 权限校验
   if skill.preconditions.required_permissions:
       if not all(perm in current_user.permissions for perm in skill.preconditions.required_permissions):
           raise ForbiddenError("Missing required permission")
   ```
3. 对象级校验（如 Skill 需访问 attempt）:
   ```python
   # 例如 get_attempt_evidence(attempt_id)
   attempt = await attempt_service.get_attempt(attempt_id, current_user)  # 内部走对象级规则
   # 若无权访问，内部抛 NotFoundError（READ 越权 → 404，遵循 AUTHZ_RBAC_SPEC#4.1）
   ```

### 6.3 参数校验与反注入

**静态检查**（在 LLM 输出解析后、执行前）:
```python
# 伪代码
def validate_skill_args(skill: Skill, args: dict, current_user: User):
    # 1. Schema 校验
    validate_json_schema(args, skill.input_schema)
    
    # 2. deterministic_checks
    checks = skill.deterministic_checks
    
    # 参数范围
    for param, constraints in checks.get("param_ranges", {}).items():
        if param in args:
            if isinstance(constraints, dict):  # min/max
                if "min" in constraints and args[param] < constraints["min"]:
                    raise ValidationError(f"{param} below min")
                if "max" in constraints and args[param] > constraints["max"]:
                    raise ValidationError(f"{param} above max")
            elif isinstance(constraints, list):  # enum
                if args[param] not in constraints:
                    raise ValidationError(f"{param} not in allowed values")
    
    # 黑名单关键词
    for keyword in checks.get("blacklist_keywords", []):
        if any(keyword.lower() in str(v).lower() for v in args.values()):
            raise SecurityError(f"Blacklist keyword detected: {keyword}")
    
    # 注入模式
    import re
    for pattern in checks.get("injection_patterns", []):
        if any(re.search(pattern, str(v)) for v in args.values()):
            raise SecurityError(f"Injection pattern detected")
    
    # 3. 引用 ID 校验（LLM 输出的引用必须存在且可访问）
    if "evidence_refs" in args:
        for ref_id in args["evidence_refs"]:
            # 校验 ref_id 存在于 evidence_items / events / snapshots
            if not await verify_reference_exists(ref_id, current_user):
                raise ValidationError(f"Invalid reference: {ref_id}")
```

[source: 数字孪生维保智能体_R-MOS_.md#13.1 Prompt/Tool 注入防护]

---

## 7. Command 协议（消息即指令）

### 7.1 Command 对象结构

```
id: UUID (PK)
trace_id: UUID (unique, not null)  # 全链路追踪 ID
actor_user_id: UUID (FK -> users.id, not null)
actor_role: String (not null)  # 当前用户主角色
intent: String (not null)  # dispatch, explain, verify, replay, summarize, adjust_difficulty, highlight, critique, approve
scope: JSONB (nullable)  # {course_id, assignment_id, attempt_id, task_id, sop_id}
input_text: String (not null)  # 用户原始输入
constraints: JSONB (nullable)  # {safety_redlines, forbidden_actions, time_limit, difficulty_range}
required_approvals: JSONB (nullable)  # {approvers: [{role, user_id}], min_count}
status: String (not null)  # queued, running, waiting_approval, done, failed, canceled
created_at: DateTime
started_at: DateTime (nullable)
completed_at: DateTime (nullable)
```

### 7.2 intent 类型与权限映射

| Intent | 描述 | 典型 Skill | 最低权限 | 审批要求 |
|--------|------|-----------|---------|---------|
| dispatch | 自然语言派单 | create_sop_draft, create_task_chain_draft | assignments:write | medium → teacher confirm |
| explain | 解释步骤/概念 | get_sop_step, get_robot_structure | sops:read | low → 无 |
| verify | 验证执行结果 | get_task_events, get_snapshot | tasks:read | low → 无 |
| replay | 回放执行过程 | get_multimodal_timeline, locate_in_timeline | tasks:read | low → 无 |
| summarize | 生成复盘报告 | generate_evidence_bundle | evidence_bundles:read | low → 无（无写入） |
| adjust_difficulty | 难度调整建议 | apply_difficulty_profile | assignments:write | medium → teacher confirm |
| highlight | AR/VR 高亮 | highlight_parts_in_3d | tasks:read | low → 无 |
| critique | 教学点评 | submit_teacher_feedback | assignments:write | medium → teacher confirm（有写入） |
| approve | 审批操作 | approve_high_risk_action | (specific permission) | N/A（用户行为，非 Skill） |

[source: 数字孪生维保智能体_R-MOS_.md#7. 交互入口]

### 7.3 Command 输出回执（command_results）

```
id: UUID (PK)
command_id: UUID (FK -> commands.id)
status: String  # 同 commands.status
artifacts: JSONB  # {sop_draft_id, task_chain_draft_id, report_id, evidence_refs: [...]}
next_actions: JSONB  # {type: "confirm"|"supplement", message, required_data}
citations: JSONB  # [{ref_type, ref_id, snippet, timestamp}]
tool_calls: JSONB  # [{skill_id, args, result_summary, latency, success}]
error: JSONB (nullable)  # {code, message, details}
created_at: DateTime
```

---

## 8. Approval 对象与审批流

### 8.1 Approval 表结构

```
id: UUID (PK)
trace_id: UUID (not null)  # 关联 Command 或 ToolCall
action_type: String (not null)  # skill_call, bulk_action, high_risk_operation
resource_type: String (nullable)  # assignments, tasks, faults, etc.
resource_id: UUID (nullable)
risk_level: String (not null)  # medium, high, critical
proposer_user_id: UUID (FK -> users.id, not null)
required_approvers: JSONB (not null)  # [{role, user_id (optional)}]
approvals_received: JSONB  # [{approver_id, timestamp, signature, decision: approve|reject}]
status: String (not null)  # pending, approved, rejected, expired, canceled
reason: String (nullable)  # 拒绝原因
expires_at: DateTime (not null)  # 审批超时时间
created_at: DateTime
approved_at: DateTime (nullable)
rejected_at: DateTime (nullable)
```

### 8.2 审批规则映射

| Risk Level | 审批要求 | 超时时间 | 示例场景 |
|-----------|---------|---------|---------|
| low | 无需审批 | N/A | 只读检索、摘要生成（无写入） |
| medium | teacher confirm + 审计 | 24h | 创建 SOP 草案、调整难度建议、教学点评 |
| high | teacher confirm + 审计 | 48h | 发布作业、评分发布、批量派单 |
| critical | 双人确认（teacher + admin）或（admin + auditor）+ feature flag | 72h | 故障注入、批量删除、恢复操作 |

[source: 数字孪生维保智能体_R-MOS_.md#12. 审批流]

### 8.2.1 审批权限要求（Approval Permission Requirements）

**权限继承规则**：[source: AUTHZ_RBAC_SPEC#3.3 审批资源域]

| Risk Level | 执行审批需要的权限 | 角色约束 |
|-----------|------------------|---------|
| low | 无需审批 | N/A |
| medium | approvals:approve | teacher（课程范围内） |
| high | approvals:approve + 审计 | teacher（课程范围内） |
| critical | approvals:approve（双人） | teacher + auditor 或 admin + auditor |

**auditor 特殊约束**：
- auditor 具有 approvals:approve / reject 权限
- **但仅限 risk_level=critical 的 approvals**（AUTHZ_RBAC_SPEC#OBJ-005）
- 尝试审批 medium/high → 403, AUTHZ_005, audit_event(deny, reason="auditor_only_critical")

**实施伪代码**：
\```python
async def approve_approval(approval_id: UUID, current_user: User):
    approval = await approval_service.get_by_id(approval_id)
    
    # 1. 基础权限检查
    if not current_user.has_permission("approvals:approve"):
        raise ForbiddenError("Missing approvals:approve")
    
    # 2. auditor 仅可审批 critical（AUTHZ_RBAC_SPEC#OBJ-005）
    if current_user.has_role("auditor"):
        if approval.risk_level != "critical":
            await audit_log(
                actor=current_user,
                action="approval_denied",
                resource_type="approval",
                resource_id=approval_id,
                decision="deny",
                reason="auditor_only_critical"
            )
            raise ForbiddenError("Auditor can only approve critical approvals")
    
    # 3. teacher 课程范围检查（如适用）
    if current_user.has_role("teacher"):
        if not await _is_in_teacher_scope(current_user, approval):
            raise ForbiddenError("Out of course scope")
    
    # ... 执行审批逻辑
\```
### 8.3 审批状态机

```
pending → approved → (执行)
         ↓
      rejected (终止)
         ↓
      expired (超时终止)
         ↓
      canceled (提议者取消)
```

### 8.4 双人确认策略（critical）

**配置示例** (approval_policies 表，design add):
```
id: UUID (PK)
risk_level: String (not null)  # critical
required_approver_combinations: JSONB (not null)  
# [
#   {"roles": ["teacher", "admin"], "min_count": 2},
#   {"roles": ["admin", "auditor"], "min_count": 2}
# ]
# 表示：(teacher + admin) 或 (admin + auditor) 任一组合满足即可
```

---

## 9. 审计字段统一

### 9.1 扩展 audit_events 表（在 AUTHZ_RBAC_SPEC 基础上）

增加字段：
```
trace_id: UUID (nullable)  # 关联 Command / ToolCall
skill_id: String (nullable)  # 如果是 AI 工具调用
skill_version: String (nullable)
tool_call_args: JSONB (nullable)  # 工具调用参数（脱敏后）
side_effects_applied: JSONB (nullable)  # 实际写入的资源 [{resource_type, resource_id, action}]
approval_id: UUID (FK -> approvals.id, nullable)  # 关联审批记录
```

### 9.2 必审计场景（AI 相关）

| 场景 | action | 必记录字段 |
|------|--------|-----------|
| AI 工具调用（低危） | tool_call | trace_id, skill_id, actor_user_id, args(summary), result(summary) |
| AI 工具调用（中/高危，等待审批） | tool_call_pending | trace_id, skill_id, approval_id, required_approvers |
| 审批通过 | approval_granted | trace_id, approval_id, approver_id, decision |
| 审批拒绝 | approval_rejected | trace_id, approval_id, approver_id, reason |
| 工具执行成功 | tool_call_success | trace_id, skill_id, side_effects_applied |
| 工具执行失败 | tool_call_failure | trace_id, skill_id, error_code, error_message |
| 引用校验失败 | reference_validation_failed | trace_id, skill_id, invalid_refs |

---

## 10. 对象级权限在 AI 检索与工具调用中的落点

### 10.1 检索场景（RAG）

**场景**: 学生问"我的上次失败是什么原因？"

**实施**:
1. 向量检索候选文档（events, snapshots, evidence_items）
2. **后过滤**（Post-filtering）: 对每个候选文档执行对象级权限校验
   ```python
   # 伪代码
   candidates = vector_search(query_embedding, top_k=20)
   accessible_docs = []
   for doc in candidates:
       try:
           if doc.type == "event":
               task = await task_service.get_task(doc.task_id, current_user)  # 走对象级规则
               accessible_docs.append(doc)  # 无异常表示有权访问
           elif doc.type == "evidence_item":
               attempt = await attempt_service.get_attempt(doc.attempt_id, current_user)
               accessible_docs.append(doc)
       except (NotFoundError, ForbiddenError):
           # 越权，跳过该文档（遵循 AUTHZ_RBAC_SPEC#4.1）
           pass
   
   return accessible_docs[:top_k_final]
   ```

**性能优化建议** (design add):
- 向量库存储时预标记 `owner_user_id`, `course_id` 等元数据
- 检索时先用元数据过滤（如 `owner_user_id = current_user.id`），再做向量检索
- 对 teacher/admin 可扩大元数据过滤范围（如 `course_id IN user_courses`）

### 10.2 工具调用场景

**场景**: Teacher 调用 `get_attempt_diagnosis(attempt_id)`

**实施**:
```python
# Skill 实现内部
async def execute_get_attempt_diagnosis(args: dict, current_user: User):
    attempt_id = args["attempt_id"]
    
    # 1. 对象级权限校验（复用 Service 层逻辑）
    attempt = await attempt_service.get_attempt(attempt_id, current_user)
    # 若无权访问，内部抛 NotFoundError（READ 越权 → 404，遵循 AUTHZ_RBAC_SPEC#4.1），审计已记录
    
    # 2. 获取诊断
    diagnosis = await diagnosis_service.get_diagnosis(attempt.id)
    
    # 3. 返回（含引用）
    return {
        "diagnosis": diagnosis,
        "evidence_refs": [diagnosis.id, attempt.id]  # 必须含引用
    }
```
### 10.3 RAG 检索过滤与 HTTP 响应码边界

**核心原则**：RAG 检索层的"过滤/返回空"是**检索行为**，不等同于 HTTP 资源访问响应码。

**边界说明**：

| 场景 | 行为 | 响应 | 审计 |
|------|------|------|------|
| **RAG 向量检索** | 后过滤无权访问文档 | 返回空列表或有权文档 | audit_events(action=rag_filter_applied, deny_count=N, trace_id) |
| **HTTP GET 资源** | 直接访问特定资源 | 404（Read 越权，AUTHZ_RBAC_SPEC#4.1） | audit_events(action=access_denied, resource_id=X, decision=deny) |
| **HTTP POST/PATCH/DELETE** | 修改资源 | 403（Write 越权，AUTHZ_RBAC_SPEC#4.1） | audit_events(action=modify_denied, resource_id=X, decision=deny) |

**详细说明**：

1. **RAG 检索层**：
   - 检索候选文档后，执行对象级权限后过滤
   - 无权访问的文档不返回（用户不知道这些文档存在）
   - 审计记录：`action="rag_filter_applied"`, `deny_count=N`（被过滤的文档数量），`trace_id`
   - **不泄露具体对象 ID**（防止探测）

2. **HTTP 资源访问**：
   - 用户明确请求特定资源（如 GET /teaching/attempts/{id}）
   - 遵循 AUTHZ_RBAC_SPEC#4.1：Read 越权 → 404, Write 越权 → 403
   - 审计记录：完整 resource_id（即使返回 404）

**实施示例**：

\```python
# RAG 检索场景
async def rag_search(query: str, current_user: User, trace_id: UUID):
    candidates = await vector_search(query, top_k=20)
    accessible_docs = []
    denied_count = 0
    
    for doc in candidates:
        try:
            # 对象级权限校验（可能抛异常）
            if doc.type == "attempt":
                await attempt_service.get_attempt(doc.attempt_id, current_user)
            accessible_docs.append(doc)
        except (NotFoundError, ForbiddenError):
            denied_count += 1  # 记录被过滤数量，不记录具体 ID
    
    # 审计：仅记录过滤统计
    if denied_count > 0:
        await audit_log(
            actor=current_user,
            action="rag_filter_applied",
            decision="deny",
            reason=f"filtered_{denied_count}_docs",
            request_meta={"trace_id": trace_id, "deny_count": denied_count}
        )
    
    return accessible_docs

# HTTP GET 场景（对比）
async def get_attempt(attempt_id: UUID, current_user: User):
    attempt = await repo.get_by_id(attempt_id)
    if not attempt:
        raise NotFoundError()  # 真正不存在
    
    if not _can_access(current_user, attempt):
        # 审计：记录具体 resource_id
        await audit_log(
            actor=current_user,
            action="access_denied",
            resource_type="attempt",
            resource_id=attempt_id,  # 具体 ID
            decision="deny",
            reason="not_owner"
        )
        raise NotFoundError()  # Read 越权 → 404（AUTHZ_RBAC_SPEC#4.1）
    
    return attempt
\```

**验收要求**（见 ACCEPTANCE_TEST_MATRIX）：
- RAG-T002: 学生检索他人 evidence → 返回空 + audit(rag_filter_applied, deny_count>0, trace_id)
- RAG-T005: RAG 检索后直接 HTTP GET 无权文档 → 404（不是返回空）
---

## 11. 端到端时序图（文字版）

### 场景: Teacher 自然语言派单（medium 风险）

```
1. User (Teacher) → POST /api/v1/ai/commands
   {
     "intent": "dispatch",
     "input_text": "为机器人维修课创建一个中级难度的电机故障诊断作业",
     "scope": {"course_id": "uuid-123"}
   }

2. API Gateway → Auth Middleware
   - 验证 JWT
   - 提取 current_user (role: teacher, permissions: [assignments:write])

3. Command Handler → LLM Agent
   - 构造 prompt（含用户输入 + 系统约束）
   - LLM 返回工具调用序列：
     [
       {
         "skill_id": "tasks.create_sop_draft",
         "version": "1.0.0",
         "args": {
           "course_id": "uuid-123",
           "goal": "电机故障诊断",
           "difficulty": "intermediate"
         }
       }
     ]

4. Tool Executor → Skill Registry
   - 查询 skill: tasks.create_sop_draft v1.0.0
   - 检查 preconditions:
     - required_roles: [teacher] ✓
     - required_permissions: [assignments:write] ✓
   - 检查 risk_level: medium（side_effects: ["sops"], 遵循 RISK-001）
   - deterministic_checks: 参数范围校验 ✓

5. Tool Executor → Approval Service
   - risk_level = medium → 需要 teacher confirm
   - 创建 Approval:
     {
       "trace_id": "cmd-uuid",
       "action_type": "skill_call",
       "risk_level": "medium",
       "proposer_user_id": current_user.id,
       "required_approvers": [{"role": "teacher", "user_id": current_user.id}],
       "status": "pending",
       "expires_at": now + 24h
     }
   - 写审计: tool_call_pending

6. Tool Executor → User
   - 返回:
     {
       "status": "waiting_approval",
       "approval_id": "approval-uuid",
       "message": "需要确认：将创建 SOP 草案（中级难度，电机故障诊断）",
       "next_actions": [
         {"type": "confirm", "approval_id": "approval-uuid"},
         {"type": "cancel"}
       ]
     }

7. User → POST /api/v1/ai/approvals/{approval_id}/confirm

8. Approval Service → 更新 Approval
   - approvals_received: [{"approver_id": current_user.id, "decision": "approve", "timestamp": now}]
   - status: approved
   - 写审计: approval_granted

9. Tool Executor → Skill Implementation
   - 执行 tasks.create_sop_draft
   - 生成 SOP 草案 (sop_draft_id)
   - 写入 side_effects: [{"resource_type": "sops", "resource_id": sop_draft_id, "action": "create"}]
   - 写审计: tool_call_success

10. Tool Executor → User
    - 返回:
      {
        "status": "done",
        "artifacts": {
          "sop_draft_id": "uuid-456",
          "evidence_refs": ["sop:uuid-456", "course:uuid-123"]
        },
        "citations": [
          {"ref_type": "sop", "ref_id": "uuid-456", "snippet": "电机故障诊断 SOP..."}
        ]
      }
```

### 场景: Student 访问他人 evidence（对象级拒绝）

```
1. User (Student A) → AI Command: "显示 attempt-999 的证据"
   (attempt-999 属于 Student B)

2. LLM → 调用工具: get_attempt_evidence(attempt_id="attempt-999")

3. Tool Executor → Skill Registry
   - preconditions: required_permissions: [evidence_bundles:read] ✓
   - risk_level: low → 无需审批

4. Skill Implementation → Service Layer
   - attempt_service.get_attempt("attempt-999", current_user=Student A)
   - 对象级规则: attempt.user_id != Student A.id
   - 抛 NotFoundError（READ 越权 → 404，遵循 AUTHZ_RBAC_SPEC#4.1）
   - 写审计: access_denied

5. Tool Executor → 捕获异常
   - 写审计: tool_call_failure (reason: access_denied)

6. Tool Executor → User
   - 返回:
     {
       "status": "failed",
       "error": {
         "code": "AUTHZ_004",
         "message": "Resource not found or access denied"
       }
     }
```

---

## 12. 验收用例（必测清单）

### 12.1 Skill 权限继承

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| SKILL-T001 | Teacher 调用 medium 风险 Skill | 已登录 teacher | AI 调用 create_sop_draft | 返回 waiting_approval + approval_id |
| SKILL-T002 | Student 调用 teacher-only Skill | 已登录 student | AI 调用 create_sop_draft | 返回 failed (AUTHZ_001: Missing required role) + audit_event(deny) |
| SKILL-T003 | Admin 调用 critical 风险 Skill | 已登录 admin | AI 调用 inject_fault | 返回 waiting_approval + 需双人确认 |
| SKILL-T004 | Skill 违反 RISK-001 | 创建 skill (side_effects 非空, risk_level=low) | 提交审核 | 审核拒绝（违反 RISK-001） |
| SKILL-T005 | Skill 违反 RISK-002 | 创建 skill (side_effects 含 assignments, risk_level=medium) | 提交审核 | 审核拒绝（违反 RISK-002） |

### 12.2 对象级权限在 AI 检索

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| RAG-T001 | Student 检索本人 evidence | Student A, 有 attempt-A | RAG 检索"我的失败证据" | 返回 attempt-A 相关文档 |
| RAG-T002 | Student 检索他人 evidence | Student A, 存在 attempt-B | RAG 检索"attempt-B 的证据" | 返回空或"无可访问文档"（后过滤拒绝） |
| RAG-T003 | Teacher 检索本课程 evidence | Teacher, course-1 | RAG 检索"course-1 的学生错误" | 返回 course-1 相关文档 |
| RAG-T004 | Teacher 检索他人课程 evidence | Teacher, course-1 | RAG 检索"course-2 的学生错误" | 返回空或"无可访问文档" |

### 12.3 审批流

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| APPR-T001 | Medium 风险需确认 | Teacher 调用 medium Skill | 等待审批 | status=waiting_approval |
| APPR-T002 | Teacher 确认审批 | 待审批记录 | POST /approvals/{id}/confirm | status=approved, 执行 Skill |
| APPR-T003 | Teacher 拒绝审批 | 待审批记录 | POST /approvals/{id}/reject | status=rejected, 不执行 |
| APPR-T004 | 审批超时 | 待审批记录 24h | 系统定时检查 | status=expired, 不执行 |
| APPR-T005 | Critical 双人确认 | Admin 调用 critical Skill | 等待审批 | required_approvers: 2, 必须 teacher+admin 或 admin+auditor |
| APPR-T006 | Critical 单人确认失败 | 待审批(critical) | 仅 teacher confirm | status=pending, 需等待第二人 |
| APPR-T007 | Critical 双人确认成功 | 待审批(critical) | teacher + admin confirm | status=approved, 执行 Skill |

### 12.4 反注入

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| INJ-T001 | 黑名单关键词检测 | 无 | AI 调用 Skill (args 含 "DROP TABLE") | 返回 failed (SecurityError) + audit_event |
| INJ-T002 | 注入模式检测 | 无 | AI 调用 Skill (args 含 "<script>") | 返回 failed (SecurityError) + audit_event |
| INJ-T003 | 引用 ID 校验 | 无 | AI 调用 Skill (evidence_refs: ["fake-id"]) | 返回 failed (ValidationError: Invalid reference) |
| INJ-T004 | 参数范围校验 | 无 | AI 调用 Skill (difficulty="超级困难") | 返回 failed (ValidationError: not in allowed values) |

### 12.5 审计可追溯

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| AUD-T001 | 工具调用成功审计 | Teacher 调用 low Skill 成功 | 执行后查询 audit_events | 存在 tool_call_success 记录，含 trace_id, skill_id, side_effects |
| AUD-T002 | 工具调用失败审计 | Student 调用 teacher-only Skill | 执行后查询 audit_events | 存在 tool_call_failure 记录，reason=access_denied |
| AUD-T003 | 审批决策审计 | Teacher 确认审批 | 执行后查询 audit_events | 存在 approval_granted 记录，含 approval_id, approver_id |
| AUD-T004 | 按 trace_id 回放 | 已完成 Command | GET /audit/events?trace_id={cmd_trace_id} | 返回完整工具调用序列（pending → granted → success） |

---

## 13. 实施优先级与里程碑

### Phase 1: Skill Registry & Schema（Week 1-2）
- [ ] 创建 skills, skill_reviews 表
- [ ] 实现 Skill CRUD API（admin）
- [ ] 实现审核流程（review → published），**集成 4.3 审核检查清单**
- [ ] 种子数据（Read Tools: get_robot_structure, get_task_status, etc.）

### Phase 2: 权限集成（Week 3-4）
- [ ] Skill preconditions 校验（角色/权限）
- [ ] 对象级权限在 Skill 实现中落地（复用 Service 层，遵循 AUTHZ_RBAC_SPEC#4.1）
- [ ] deterministic_checks 静态校验
- [ ] 单元测试（SKILL-T001 ~ SKILL-T005, INJ-T001 ~ INJ-T004）

### Phase 3: Approval 流程（Week 5-6）
- [ ] 创建 approvals, approval_policies 表
- [ ] 实现 Approval 状态机与 API
- [ ] 风险分级自动路由审批
- [ ] 单元测试（APPR-T001 ~ APPR-T007）

### Phase 4: Command 协议与 LLM 集成（Week 7-8）
- [ ] 创建 commands, command_results 表
- [ ] 实现 POST /api/v1/ai/commands
- [ ] LLM Agent 工具调用编排（含审批等待）
- [ ] 集成测试（端到端时序）

### Phase 5: RAG 与对象级过滤（Week 9-10）
- [ ] 向量库（pgvector/Qdrant）部署
- [ ] 知识库构建（SOP/故障库/历史 evidence）
- [ ] RAG 检索后过滤（对象级权限，遵循 AUTHZ_RBAC_SPEC#4.1）
- [ ] 单元测试（RAG-T001 ~ RAG-T004）

### Phase 6: 审计扩展与回放（Week 11-12）
- [ ] 扩展 audit_events 表（trace_id, skill_id, approval_id）
- [ ] 实现按 trace_id 回放 API
- [ ] 审计可视化（时间线）
- [ ] 单元测试（AUD-T001 ~ AUD-T004）

---

## 14. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 幻觉生成不存在的引用 | 用户误信 | 引用 ID 强制校验（后端）+ 前端展示"未验证引用"警告 |
| 审批绕过（前端篡改） | 越权执行 | 审批状态后端强校验 + 审计 |
| Skill 发布恶意代码 | 系统安全风险 | 审核流程（**含 4.3 检查清单**）+ 沙箱执行（未来） + 签名信任 |
| 对象级过滤性能瓶颈 | RAG 检索慢 | 向量库元数据预过滤 + 缓存 + 批量权限校验 |
| 审批超时未处理 | 阻塞工作流 | 定时任务清理 expired approvals + 邮件/推送提醒 |
| 违反 risk_level 硬约束 | 安全风险 | 审核流程强制验证 RISK-001/002/003 |

---

**文档结束**
