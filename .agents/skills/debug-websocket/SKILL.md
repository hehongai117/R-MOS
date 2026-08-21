---
name: debug-websocket
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Debug and validate the R-MOS WebSocket telemetry pipeline in a controlled,
  read-only, non-destructive manner. This skill is designed for diagnosis,
  verification, and fault localization only.

allowed-tools:
  - Bash
  - Read
  - Grep
---

# R-MOS WebSocket Debug Skill

---

## 1. Skill Purpose（目的与边界）

This skill exists to **verify, observe, and diagnose** the R-MOS WebSocket
telemetry channel.

**This skill is NOT allowed to:**

* Modify source code
* Modify schemas
* Change configuration values
* Apply fixes or refactors

> 本 skill 的唯一职责：
> **判断 WebSocket 是否“正确工作”，以及“为什么不正确”**

---

## 2. Scope & Lifecycle（适用范围）

This skill is valid **ONLY** under the following conditions:

* Project: **R-MOS**
* Phase: **MVP**
* Deployment: **Single-node**
* Backend: **Single instance**
* Adapter: **Mock Adapter only**
* Transport: **RFC 6455 WebSocket**

### Mandatory Review Conditions

This skill MUST be reviewed or deprecated when:

* Moving to multi-node or distributed deployment
* Introducing Docker / Kubernetes
* Connecting real robot hardware adapters
* Changing telemetry schema or message frequency policy

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

* Backend directory `r-mos-backend/` exists
* Backend health endpoint responds on port `8000`
* WebSocket endpoint path is exactly:

  ```
  /ws/robot/status
  ```
* Target is telemetry read-only validation

❌ **If any precondition fails → STOP immediately**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

* WebSocket connection cannot be established
* WebSocket connects but no messages are received
* Telemetry message structure is invalid or incomplete
* WebSocket message frequency is abnormal
* Fault injection succeeds but telemetry does not reflect it
* Frontend telemetry display is incorrect while REST API is healthy

⚠️ **Mentioning “websocket / ws / realtime” alone does NOT trigger this skill**

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

* Edit or generate any `.py`, `.ts`, `.js`, `.json` source files
* Modify TelemetryMessage schema
* Create, delete, or alter database state
* Adjust WebSocket frequency, heartbeat, or payload
* Suggest or apply direct code changes
* Perform repeated or looping debug attempts

> 本 skill **禁止“顺手修一下”**

---

## 6. Allowed Operations & Tool Constraints

### Allowed Tool Usage

* `Bash`

  * Read-only commands only
  * Allowed: `curl`, inline `python <<EOF`
  * Forbidden: file write, package install, environment mutation

* `Read`, `Grep`

  * Source inspection only

---

## 7. System Reference（不可变系统约束）

Based on **R-MOS MVP Skeleton Document V2.3**:

* WebSocket Endpoint:

  ```
  ws://[host]:[port]/ws/robot/status
  ```
* Push Frequency:

  * Target: **5Hz**
  * Acceptable Range: **4–6Hz**
* Heartbeat Interval: **30s**
* Protocol: **RFC 6455**

---

## 8. Telemetry Message Schema（强制契约）

All WebSocket messages MUST strictly conform to:

```json
{
  "type": "telemetry",
  "timestamp": "ISO-8601 UTC",
  "payload": {
    "joints": [
      {
        "joint_id": "string",
        "position": "number",
        "velocity": "number",
        "torque": "number",
        "current": "number",
        "temperature": "number",
        "error_code": "string | null"
      }
    ],
    "sensors": {
      "imu": {
        "acceleration": {"x": "number", "y": "number", "z": "number"},
        "angular_velocity": {"x": "number", "y": "number", "z": "number"}
      },
      "battery": "number",
      "temperature": "number",
      "voltage": {"main": "number", "logic": "number"}
    },
    "active_faults": ["string"]
  }
}
```

❌ Any deviation → **FAIL**

---

## 9. Execution Plan（固定且不可跳步）

### Step 1 — Backend Health Check

* Endpoint: `/api/v1/health`
* Required:

  * HTTP 200
  * `adapter_connected == true`

❌ Fail → STOP

---

### Step 2 — WebSocket Connectivity Check (once)

* Establish connection
* Timeout ≤ 5s
* Receive ≤ 5 messages

❌ No message → STOP

---

### Step 3 — Schema Validation

Verify presence and validity of:

* `type == telemetry`
* `timestamp`
* `payload.joints`
* `payload.sensors`
* `payload.active_faults`

❌ Any missing or invalid field → STOP

---

### Step 4 — Frequency Sampling

* Sample ≤ 10 messages
* Compute average interval

Pass condition:

* Frequency ∈ **[4Hz, 6Hz]**

---

### Step 5 — Fault Reflection Check (Optional)

Execute ONLY if:

* User explicitly mentions fault debugging

Verify:

* Injected fault appears in `active_faults`
* Corresponding joint reflects `error_code`

---

## 10. Exit Criteria（裁决出口）

This skill MUST terminate immediately upon:

* Schema mismatch
* WebSocket silence
* Frequency out of range
* Fault not reflected

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Root Cause:
Affected Component:
Evidence:
Recommended Next Skill:
```

---

## 11. Related Files（只读）

* `app/api/v1/endpoints/websocket.py`
* `app/services/websocket_manager.py`
* `app/adapters/schemas.py`
* `app/adapters/mock.py`
* `r-mos-frontend/src/hooks/useWebSocket.ts`

---

## 12. Skill Expiration Conditions（失效条件）

This skill becomes INVALID if:

* WebSocket endpoint path changes
* Telemetry schema version changes
* Backend entrypoint or runtime model changes
* System enters non-MVP phase

---

