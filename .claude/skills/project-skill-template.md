
---
name: <skill-name>
type: project-skill
project: <project-name>
phase: <MVP | Alpha | Beta | Production>
version: <x.y.z>

description: >
  <One-paragraph description of what this skill does.
  Must include purpose AND explicit boundary.>

allowed-tools:
  - <Tool-1>
  - <Tool-2>
  - <Tool-3>
---

# <Skill Title>

---

## 1. Skill Purpose（目的与边界）

### Purpose
Clearly state **what this skill exists to do**.

### Explicit Non-Goals
This skill MUST NOT:
- <Forbidden action 1>
- <Forbidden action 2>
- <Forbidden action 3>

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `<project-name>`
- Phase: `<specific phase>`
- Deployment model: `<single-node / local / mock-only / etc>`
- Target environment: `<dev / test only>`

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- <Architecture change>
- <Deployment change>
- <Schema / protocol change>
- <Hardware introduction>

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

- <Condition 1>
- <Condition 2>
- <Condition 3>

❌ If any precondition fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- <Trigger 1>
- <Trigger 2>
- <Trigger 3>

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code
- Modify schemas or data models
- Change configuration defaults
- Perform refactors or “quick fixes”
- Execute repeated retries without instruction

> 本 skill 禁止任何“顺手帮你修一下”的行为。

---

## 6. Allowed Operations & Tool Constraints

### Tool Usage Rules

- Tools may ONLY be used for purposes explicitly described below.
- All operations must be:
  - Deterministic
  - Single-pass
  - Non-looping

### Tool-Specific Constraints

- **Bash**
  - Allowed: read-only commands
  - Forbidden: file write, deletion, package install (unless explicitly allowed)

- **Read / Grep / Glob**
  - Inspection only
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

- <Endpoint definitions>
- <Protocol versions>
- <Timing / frequency constraints>
- <Schema version identifiers>

❌ These facts MUST NOT be modified or “corrected” by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

All observed data MUST conform to the following contract:

```json
{
  "<field>": "<type>",
  "<field>": "<type>"
}
````

❌ Any deviation → **FAIL and STOP**

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — <Step Name>

* Action:
* Expected result:
* Failure condition:

---

### Step 2 — <Step Name>

* Action:
* Expected result:
* Failure condition:

---

### Step N — <Step Name>

* Action:
* Expected result:
* Failure condition:

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* <Failure condition 1>
* <Failure condition 2>

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope:
Root Cause:
Evidence:
Next Recommended Skill:
```

---

## 11. Related Files / Interfaces（只读）

* <file-path-1>
* <file-path-2>
* <file-path-3>

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* <Condition 1>
* <Condition 2>
* <Condition 3>

Once invalid, this skill MUST NOT be executed without human review.

---
