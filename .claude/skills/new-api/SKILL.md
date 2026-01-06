---
name: new-api
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Generate a new FastAPI endpoint file following R-MOS architecture conventions.
  This skill creates API endpoint scaffolding that conforms to the skeleton
  document specifications, including proper routing, error handling, and
  schema definitions. Use when user requests to create a new API endpoint.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Edit
---

# R-MOS New API Endpoint Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **generate scaffolding** for new FastAPI endpoint files.

It provides:
- Endpoint file generation following project conventions
- Proper import structure and error handling patterns
- Router registration guidance
- Schema file scaffolding (if needed)

### Explicit Non-Goals

This skill MUST NOT:
- Implement complete business logic (only scaffolding)
- Modify existing endpoint files
- Create database models (use `/new-model` skill instead)
- Create service layer classes (use `/new-service` skill instead)
- Bypass architecture constraints defined in skeleton document
- Generate endpoints that directly access ROS2/Gazebo
- Generate WebSocket endpoints (WebSocket uses `/ws/` prefix, not `/api/v1/`)

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Framework: `FastAPI`
- API Version: `v1` (prefix: `/api/v1`)

### Architecture Constraints (骨架文档 §2.2, §2.3)

| Constraint | Requirement |
|------------|-------------|
| API Prefix | All HTTP APIs use `/api/v1/` prefix |
| Route Definition | Endpoints use **relative paths** (no prefix in file) |
| Route Registration | Prefix added in `main.py` via `include_router` |
| WebSocket | Uses `/ws/` prefix, NOT `/api/v1/` |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- API version changes (v1 → v2)
- FastAPI is replaced with another framework
- Routing structure changes
- Error handling patterns change
- Project enters production phase with different conventions

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

- Backend directory `r-mos-backend/` exists
- API endpoints directory `r-mos-backend/app/api/v1/endpoints/` exists
- `r-mos-backend/app/api/v1/__init__.py` exists (for router registration)
- Target endpoint file does NOT already exist
- User has provided endpoint name

❌ If any precondition fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to create a new API endpoint
- User enters `/new-api <name>` command
- User mentions "创建新接口" or "create new endpoint"
- User asks to "add an API for..."

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify existing endpoint files
- Add `/api/v1/` prefix in endpoint route decorators
- Create endpoints that bypass R-MOS Core layer
- Create endpoints that directly call ROS2/Gazebo
- Implement complete business logic (only scaffolding)
- Create database models or service classes
- Skip router registration guidance
- Use non-standard error handling patterns

> 本 skill 禁止任何"顺手帮你修一下"的行为。

---

## 6. Allowed Operations & Tool Constraints

### Tool Usage Rules

- Tools may ONLY be used for purposes explicitly described below.
- All operations must be:
  - Deterministic
  - Single-pass
  - Non-looping

### Tool-Specific Constraints

- **Write**
  - Allowed: Create new endpoint file
  - Allowed: Create new schema file (if needed)
  - Forbidden: Overwrite existing files

- **Edit**
  - Allowed: Add import to `__init__.py` for router registration
  - Forbidden: Modify existing endpoint logic

- **Read / Grep / Glob**
  - Inspection only
  - Check for existing files and patterns
  - Reference existing endpoints for consistency

- **Bash**
  - Allowed: Check file existence
  - Forbidden: File write operations

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value | Source |
|-----------|-------|--------|
| Framework | FastAPI | 骨架文档 §3.2 |
| API Prefix | `/api/v1` | 骨架文档 §2.3 |
| Endpoints Directory | `app/api/v1/endpoints/` | 拆包A §2 |
| Schemas Directory | `app/schemas/` | 拆包B §2 |
| Error Response Format | See §8 Contract | 骨架文档 §4.7 |
| Business Exception | `BusinessRuleViolation` → 409 | 骨架文档 §4.7 |

### Routing Convention (骨架文档 §2.3)

```python
# ✅ 正确：端点文件使用相对路径
@router.post("/tasks/{id}/step")

# ❌ 错误：端点文件中包含前缀
@router.post("/api/v1/tasks/{id}/step")
```

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Error Response Contract (骨架文档 §4.7)

All error responses MUST conform to:

```json
{
  "status_code": 409,
  "error_type": "BusinessRuleViolation",
  "message": "错误描述",
  "details": {
    "code": "ERROR_CODE",
    "message": "详细信息",
    "details": {}
  },
  "timestamp": "ISO-8601",
  "request_id": "string"
}
```

### HTTP Status Code Contract

| Scenario | Status Code | Exception Type |
|----------|-------------|----------------|
| Success (create) | 201 | — |
| Success (read/update) | 200 | — |
| Not Found | 404 | `ResourceNotFoundError` |
| Business Rule Violation | 409 | `BusinessRuleViolation` |
| Validation Error | 422 | `RequestValidationError` |
| Server Error | 500 | `HTTPException` |

❌ Any deviation → **FAIL and require correction**

---

## 9. Execution Plan（固定流程，不可跳步）

### Placeholder Convention

In all templates below:
- `<name>` → lowercase endpoint name with underscores (e.g., `fault_report`)
- `<Name>` → PascalCase endpoint name (e.g., `FaultReport`)

These placeholders MUST be replaced with actual values during generation.

---

### Step 1 — Validate Input

* Action: Confirm endpoint name and check prerequisites
* Checks:
  - Endpoint name provided by user
  - Name follows convention (lowercase, underscores)
  - Target file does not exist
* Command:
  ```bash
  cd r-mos-backend
  ls -la app/api/v1/endpoints/
  [ -f "app/api/v1/endpoints/<name>.py" ] && echo "✗ File already exists" || echo "✓ File does not exist"
  ```
* Failure condition: File already exists OR name not provided

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Reference Existing Patterns

* Action: Read existing endpoint for consistency
* Command:
  ```bash
  cat r-mos-backend/app/api/v1/endpoints/tasks.py | head -50
  ```
* Purpose: Ensure generated code follows same patterns
* Failure condition: None

---

### Step 3 — Generate Endpoint File

* Action: Create new endpoint file with scaffolding
* File: `r-mos-backend/app/api/v1/endpoints/<name>.py`
* Template: See §9.3 Template below
* Failure condition: Write operation fails

---

### Step 4 — Generate Schema File (If Needed)

* Action: Create corresponding Pydantic schema file
* File: `r-mos-backend/app/schemas/<name>.py`
* Condition: Only if user confirms schema is needed
* Template: See §9.4 Template below
* Failure condition: Write operation fails

---

### Step 5 — Provide Router Registration Guidance

* Action: Show user how to register the new router
* Output:
  ```python
  # Add to app/api/v1/__init__.py:
  from app.api.v1.endpoints.<name> import router as <name>_router

  api_router.include_router(<name>_router, tags=["<Name>s"])
  ```
* Failure condition: None (guidance only)

---

### Step 6 — Verify Generation

* Action: Confirm files were created correctly
* Command:
  ```bash
  ls -la r-mos-backend/app/api/v1/endpoints/<name>.py
  head -30 r-mos-backend/app/api/v1/endpoints/<name>.py
  ```
* Failure condition: File not found or malformed

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

### 9.3 Endpoint File Template

> ⚠️ **Dependency Note**: This template imports schema and service files that may not exist yet.
> After generating the endpoint, use `/new-service` and `/new-model` skills to create dependencies.
> The generated code will have ImportError until dependencies are created.

```python
"""
<Name> API端点

Dependencies (create if not exist):
- Schema: app/schemas/<name>.py (use /new-model or create manually)
- Service: app/services/<name>_service.py (use /new-service skill)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError
from app.schemas.<name> import (
    <Name>Create,
    <Name>Response,
    <Name>Update
)
from app.services.<name>_service import <Name>Service

router = APIRouter()


@router.get("/<name>s", response_model=List[<Name>Response], tags=["<Name>s"])
async def list_<name>s(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """查询<Name>列表"""
    try:
        service = <Name>Service(db)
        items = await service.list_<name>s(skip=skip, limit=limit)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/<name>s/{<name>_id}", response_model=<Name>Response, tags=["<Name>s"])
async def get_<name>(
    <name>_id: int,
    db: AsyncSession = Depends(get_db)
):
    """查询单个<Name>"""
    try:
        service = <Name>Service(db)
        item = await service.get_<name>(<name>_id)
        return item
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/<name>s", response_model=<Name>Response, status_code=201, tags=["<Name>s"])
async def create_<name>(
    request: <Name>Create,
    db: AsyncSession = Depends(get_db)
):
    """创建<Name>"""
    try:
        service = <Name>Service(db)
        item = await service.create_<name>(request)
        return item
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/<name>s/{<name>_id}", response_model=<Name>Response, tags=["<Name>s"])
async def update_<name>(
    <name>_id: int,
    request: <Name>Update,
    db: AsyncSession = Depends(get_db)
):
    """更新<Name>"""
    try:
        service = <Name>Service(db)
        item = await service.update_<name>(<name>_id, request)
        return item
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/<name>s/{<name>_id}", tags=["<Name>s"])
async def delete_<name>(
    <name>_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除<Name>"""
    try:
        service = <Name>Service(db)
        await service.delete_<name>(<name>_id)
        return {"message": "<Name> deleted successfully"}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 9.4 Schema File Template

```python
"""
<Name> Schema定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class <Name>Base(BaseModel):
    """<Name>基础字段"""
    # TODO: Add fields
    pass


class <Name>Create(<Name>Base):
    """创建<Name>请求"""
    pass


class <Name>Update(BaseModel):
    """更新<Name>请求"""
    # TODO: Add optional fields
    pass


class <Name>Response(<Name>Base):
    """<Name>响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Endpoint name not provided
* Target file already exists
* Endpoints directory not found
* Write operation fails

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: New API Endpoint Generation

Generated Files:
  - app/api/v1/endpoints/<name>.py: CREATED | FAILED
  - app/schemas/<name>.py: CREATED | SKIPPED | FAILED

Router Registration Required:
  File: app/api/v1/__init__.py
  Add:
    from app.api.v1.endpoints.<name> import router as <name>_router
    api_router.include_router(<name>_router, tags=["<Name>s"])

Dependencies Required:
  - Service: app/services/<name>_service.py (use /new-service skill)
  - Model: app/models/<name>.py (use /new-model skill)

Next Recommended Skill:
  - /new-service <name> - Create service layer
  - /new-model <name> - Create database model
```

---

## 11. Related Files / Interfaces（只读参考）

* `r-mos-backend/app/api/v1/endpoints/tasks.py` — Reference for patterns
* `r-mos-backend/app/api/v1/endpoints/sops.py` — Reference for patterns
* `r-mos-backend/app/api/v1/endpoints/fault_cases.py` — Reference for patterns
* `r-mos-backend/app/api/v1/__init__.py` — Router registration
* `r-mos-backend/app/schemas/task.py` — Schema reference
* `r-mos-backend/app/core/exceptions.py` — Exception definitions
* `r-mos-backend/main.py` — Application entry point

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* FastAPI is replaced with another framework
* API version changes from v1
* Routing convention changes
* Error handling patterns change
* Directory structure changes
* Exception types or status codes change

Once invalid, this skill MUST NOT be executed without human review.

---
