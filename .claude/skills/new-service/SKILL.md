---
name: new-service
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Generate a new service layer class following R-MOS architecture conventions.
  This skill creates service scaffolding with async database operations,
  proper exception handling, and integration patterns. Services encapsulate
  business logic and sit between API endpoints and data models.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Edit
---

# R-MOS New Service Layer Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **generate scaffolding** for new service layer classes.

It provides:
- Service class generation following project conventions
- Async database operation patterns
- Proper exception handling integration
- CRUD method scaffolding
- Integration with existing models and schemas

### Explicit Non-Goals

This skill MUST NOT:
- Implement complete business logic (only scaffolding)
- Modify existing service files
- Create database models (use `/new-model` skill instead)
- Create API endpoints (use `/new-api` skill instead)
- Create Pydantic schemas (use `/new-model` skill instead)
- Bypass the service layer pattern (API → Service → Model)
- Include any ROS2/Gazebo specific code in services

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- ORM: `SQLAlchemy 2.0+ (Async)`
- Database: `PostgreSQL 14+`

### Architecture Constraints (骨架文档 §3.2)

| Layer | Responsibility | This Skill |
|-------|----------------|------------|
| API Endpoints | HTTP handling, request validation | ❌ Not here |
| **Service Layer** | **Business logic, orchestration** | ✅ **This skill** |
| Models | Data persistence, ORM mapping | ❌ Not here |
| Adapters | Robot communication abstraction | ❌ Not here |

### Service Layer Responsibilities (拆包B §5)

- Task lifecycle management
- Business rule validation
- Cross-service orchestration
- Exception handling and logging
- Database transaction management

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- ORM changes from SQLAlchemy
- Async pattern changes
- Exception types change
- Service layer pattern is restructured
- Project enters production phase with different patterns

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Backend directory `r-mos-backend/` exists
- Services directory `r-mos-backend/app/services/` exists
- Target service file does NOT already exist
- User has provided service name

**Soft Requirements (WARN only, continue):**
- Related model exists (will warn if missing, suggest /new-model)
- Related schema exists (will warn if missing, suggest /new-model)

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to create a new service
- User enters `/new-service <name>` command
- User mentions "创建新服务" or "create new service"
- User asks to "add business logic for..."
- Recommended by `/new-api` skill output

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify existing service files
- Implement complete business logic (only scaffolding)
- Create database models or schemas
- Create API endpoints
- Add direct database queries in API layer
- Include ROS2/Gazebo code in services
- Skip async/await patterns
- Use synchronous database operations
- Hardcode configuration values

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
  - Allowed: Create new service file
  - Forbidden: Overwrite existing files

- **Edit**
  - Allowed: Add import to `__init__.py` if needed
  - Forbidden: Modify existing service logic

- **Read / Grep / Glob**
  - Inspection only
  - Check for existing files and patterns
  - Reference existing services for consistency

- **Bash**
  - Allowed: Check file existence
  - Forbidden: File write operations

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value | Source |
|-----------|-------|--------|
| ORM | SQLAlchemy 2.0+ (Async) | 骨架文档 §3.2 |
| Database | PostgreSQL 14+ | 骨架文档 §3.2 |
| Services Directory | `app/services/` | 拆包B §2 |
| Async Pattern | `async def` + `await` | 拆包B §5 |
| Session Type | `AsyncSession` | 拆包B §5 |
| Business Exception | `BusinessRuleViolation` | 骨架文档 §4.7 |
| Not Found Exception | `ResourceNotFoundError` | app/core/exceptions.py |

### Existing Service Patterns (拆包B)

| Service | File | Key Methods |
|---------|------|-------------|
| TaskService | `task_service.py` | `create_task`, `execute_step`, `_complete_task` |
| SOPService | `sop_service.py` | `create_sop`, `get_sop`, `delete_sop` |
| EventService | `event_service.py` | `create_event` |
| SnapshotService | `snapshot_service.py` | `create_snapshot` |
| ScoringService | `scoring_service.py` | `calculate_score` |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Service Constructor Contract

All services MUST accept `AsyncSession` as constructor parameter:

```python
def __init__(self, db: AsyncSession):
    self.db = db
```

### Method Signature Contract

All public methods MUST be async:

```python
async def create_<name>(self, request: <Name>Create) -> <Name>:
    ...

async def get_<name>(self, id: int) -> Optional[<Name>]:
    ...
```

### Exception Handling Contract

| Scenario | Exception Type | Raised By |
|----------|----------------|-----------|
| Resource not found | `ResourceNotFoundError` | Service |
| Business rule violation | `BusinessRuleViolation` | Service |
| Database error | Let propagate | SQLAlchemy |

❌ Any deviation → **FAIL and require correction**

---

## 9. Execution Plan（固定流程，不可跳步）

### Placeholder Convention

In all templates below:
- `<name>` → lowercase service name with underscores (e.g., `fault_report`)
- `<Name>` → PascalCase service name (e.g., `FaultReport`)

These placeholders MUST be replaced with actual values during generation.

---

### Step 1 — Validate Input

* Action: Confirm service name and check prerequisites
* Checks:
  - Service name provided by user
  - Name follows convention (lowercase, underscores)
  - Target file does not exist
* Command:
  ```bash
  cd r-mos-backend
  ls -la app/services/
  [ -f "app/services/<name>_service.py" ] && echo "✗ File already exists" || echo "✓ File does not exist"
  ```
* Failure condition: File already exists OR name not provided

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Reference Existing Patterns

* Action: Read existing service for consistency
* Command:
  ```bash
  cd r-mos-backend
  head -80 app/services/task_service.py
  ```
* Purpose: Ensure generated code follows same patterns
* Failure condition: None

---

### Step 3 — Check Related Dependencies

* Action: Verify if related model and schema exist
* Command:
  ```bash
  cd r-mos-backend
  echo "=== Dependency Check ==="
  [ -f "app/models/<name>.py" ] && echo "✓ Model exists" || echo "⚠ Model not found - create with /new-model"
  [ -f "app/schemas/<name>.py" ] && echo "✓ Schema exists" || echo "⚠ Schema not found - create with /new-model"
  ```
* Purpose: Inform user about missing dependencies
* Failure condition: None (informational)

---

### Step 4 — Generate Service File

* Action: Create new service file with scaffolding
* File: `r-mos-backend/app/services/<name>_service.py`
* Template: See §9.4 Template below
* Failure condition: Write operation fails

---

### Step 5 — Verify Generation

* Action: Confirm file was created correctly
* Command:
  ```bash
  cd r-mos-backend
  ls -la app/services/<name>_service.py
  head -50 app/services/<name>_service.py
  ```
* Failure condition: File not found or malformed

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

### 9.4 Service File Template

> ⚠️ **Dependency Note**: This template imports model and schema files that may not exist yet.
> Use `/new-model` skill to create model and schema if needed.
> The generated code will have ImportError until dependencies are created.

```python
"""
<Name>服务

Dependencies (create if not exist):
- Model: app/models/<name>.py (use /new-model skill)
- Schema: app/schemas/<name>.py (use /new-model skill)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime
import logging

from app.models.<name> import <Name>
from app.schemas.<name> import <Name>Create, <Name>Update
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError

logger = logging.getLogger(__name__)


class <Name>Service:
    """<Name>服务

    职责：
    - <Name>生命周期管理
    - 业务规则验证
    - 数据持久化操作

    架构约束：
    - 所有方法必须是 async
    - 通过构造函数接收 AsyncSession
    - 业务异常使用 BusinessRuleViolation
    - 资源不存在使用 ResourceNotFoundError
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_<name>(self, request: <Name>Create) -> <Name>:
        """创建<Name>

        Args:
            request: 创建请求

        Returns:
            创建的<Name>实例

        Raises:
            BusinessRuleViolation: 业务规则校验失败
        """
        # TODO: Add business rule validation

        item = <Name>(
            # TODO: Map request fields to model
        )

        self.db.add(item)
        await self.db.flush()

        logger.info(f"<Name>创建成功: id={item.id}")
        return item

    async def get_<name>(self, <name>_id: int) -> <Name>:
        """查询<Name>

        Args:
            <name>_id: <Name> ID

        Returns:
            <Name>实例

        Raises:
            ResourceNotFoundError: <Name>不存在
        """
        item = await self._get_<name>(<name>_id)
        if not item:
            raise ResourceNotFoundError("<Name>", <name>_id)
        return item

    async def list_<name>s(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[<Name>]:
        """查询<Name>列表

        Args:
            skip: 跳过数量
            limit: 返回数量

        Returns:
            <Name>列表
        """
        result = await self.db.execute(
            select(<Name>).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_<name>(
        self,
        <name>_id: int,
        request: <Name>Update
    ) -> <Name>:
        """更新<Name>

        Args:
            <name>_id: <Name> ID
            request: 更新请求

        Returns:
            更新后的<Name>实例

        Raises:
            ResourceNotFoundError: <Name>不存在
            BusinessRuleViolation: 业务规则校验失败
        """
        item = await self._get_<name>(<name>_id)
        if not item:
            raise ResourceNotFoundError("<Name>", <name>_id)

        # TODO: Update fields from request
        # for field, value in request.model_dump(exclude_unset=True).items():
        #     setattr(item, field, value)

        await self.db.flush()

        logger.info(f"<Name>更新成功: id={<name>_id}")
        return item

    async def delete_<name>(self, <name>_id: int) -> None:
        """删除<Name>

        Args:
            <name>_id: <Name> ID

        Raises:
            ResourceNotFoundError: <Name>不存在
            BusinessRuleViolation: 存在关联数据无法删除
        """
        item = await self._get_<name>(<name>_id)
        if not item:
            raise ResourceNotFoundError("<Name>", <name>_id)

        # TODO: Check for dependencies before deletion

        await self.db.delete(item)
        await self.db.flush()

        logger.info(f"<Name>删除成功: id={<name>_id}")

    async def _get_<name>(self, <name>_id: int) -> Optional[<Name>]:
        """内部：获取<Name>

        Args:
            <name>_id: <Name> ID

        Returns:
            <Name>实例或None
        """
        result = await self.db.execute(
            select(<Name>).where(<Name>.id == <name>_id)
        )
        return result.scalar_one_or_none()
```

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Service name not provided
* Target file already exists
* Services directory not found
* Write operation fails

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: New Service Layer Generation

Generated Files:
  - app/services/<name>_service.py: CREATED | FAILED

Dependencies Check:
  - Model (app/models/<name>.py): EXISTS | NOT FOUND
  - Schema (app/schemas/<name>.py): EXISTS | NOT FOUND

Integration Points:
  - Import in API endpoint: from app.services.<name>_service import <Name>Service
  - Instantiate with: service = <Name>Service(db)

Next Recommended Skill:
  - /new-model <name> - Create database model and schema (if not exist)
  - /new-api <name> - Create API endpoint (if not exist)
```

---

## 11. Related Files / Interfaces（只读参考）

* `r-mos-backend/app/services/task_service.py` — Primary reference (most complete)
* `r-mos-backend/app/services/sop_service.py` — CRUD patterns
* `r-mos-backend/app/services/event_service.py` — Simple service pattern
* `r-mos-backend/app/services/snapshot_service.py` — Adapter integration
* `r-mos-backend/app/services/scoring_service.py` — Calculation service
* `r-mos-backend/app/core/exceptions.py` — Exception definitions
* `r-mos-backend/app/core/database.py` — Database session

### Key Patterns from Existing Services

**TaskService (task_service.py):**
- Complex state machine logic
- Multi-service orchestration (Event, Snapshot, Scoring)
- Transaction management with `db.commit()`

**SOPService (sop_service.py):**
- Standard CRUD operations
- Cascade delete handling
- Force delete pattern

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* SQLAlchemy is replaced with another ORM
* Async pattern changes to sync
* Service layer pattern is removed or restructured
* Exception types or handling patterns change
* Directory structure changes
* Project enters production phase with different patterns

Once invalid, this skill MUST NOT be executed without human review.

---
