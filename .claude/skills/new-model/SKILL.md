---
name: new-model
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Generate a new SQLAlchemy data model and corresponding Pydantic schema following
  R-MOS architecture conventions. This skill creates database model scaffolding
  with proper field definitions, relationships, and Pydantic schemas for API
  request/response validation. Use when user requests to create a new data model.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Edit
---

# R-MOS New Data Model Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **generate scaffolding** for new SQLAlchemy models and Pydantic schemas.

It provides:
- SQLAlchemy model file generation following project conventions
- Pydantic schema file generation (Create, Update, Response)
- Proper import structure and type definitions
- TimestampMixin integration
- Relationship placeholder guidance

### Explicit Non-Goals

This skill MUST NOT:
- Implement complete business logic (only scaffolding)
- Modify existing model or schema files
- Create service layer classes (use `/new-service` skill instead)
- Create API endpoints (use `/new-api` skill instead)
- Define actual relationship mappings (only provide placeholder)
- Create migration files (Alembic migrations are separate concern)
- Add database indexes beyond primary key (require explicit request)

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
- Schema Validation: `Pydantic v2`

### Architecture Constraints (骨架文档 §3.2)

| Layer | Responsibility | This Skill |
|-------|----------------|------------|
| API Endpoints | HTTP handling | ❌ Not here |
| Service Layer | Business logic | ❌ Not here |
| **Models** | **Data persistence, ORM mapping** | ✅ **This skill** |
| **Schemas** | **API request/response validation** | ✅ **This skill** |
| Adapters | Robot communication | ❌ Not here |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- SQLAlchemy is replaced with another ORM
- Pydantic version changes (v2 → v3)
- Database changes from PostgreSQL
- Model/Schema patterns change
- Project enters production phase with different conventions

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Backend directory `r-mos-backend/` exists
- Models directory `r-mos-backend/app/models/` exists
- Schemas directory `r-mos-backend/app/schemas/` exists
- `r-mos-backend/app/models/base.py` exists (contains Base and TimestampMixin)
- Target model file does NOT already exist
- Target schema file does NOT already exist
- User has provided model name

❌ If any precondition fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to create a new data model
- User enters `/new-model <name>` command
- User mentions "创建新模型" or "create new model"
- User asks to "add a model for..."
- User asks to "create a database table for..."
- Recommended by `/new-api` or `/new-service` skill output

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify existing model or schema files
- Implement complete business logic (only scaffolding)
- Create service classes or API endpoints
- Add complex relationship mappings (only placeholder)
- Create Alembic migration files
- Add non-standard field types without explicit request
- Use synchronous database patterns
- Hardcode configuration values
- Add indexes beyond primary key without explicit request

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
  - Allowed: Create new model file
  - Allowed: Create new schema file
  - Forbidden: Overwrite existing files

- **Edit**
  - Allowed: Add import to model `__init__.py` if it exists
  - Forbidden: Modify existing model/schema logic

- **Read / Grep / Glob**
  - Inspection only
  - Check for existing files and patterns
  - Reference existing models/schemas for consistency

- **Bash**
  - Allowed: Check file existence
  - Forbidden: File write operations

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value | Source |
|-----------|-------|--------|
| ORM | SQLAlchemy 2.0+ | 骨架文档 §3.2 |
| Database | PostgreSQL 14+ | 骨架文档 §3.2 |
| Schema Validation | Pydantic v2 | 骨架文档 §3.2 |
| Models Directory | `app/models/` | 拆包A §2 |
| Schemas Directory | `app/schemas/` | 拆包B §2 |
| Base Class | `Base` from `app.models.base` | app/models/base.py |
| Timestamp Mixin | `TimestampMixin` from `app.models.base` | app/models/base.py |
| Primary Key | `id: Integer, primary_key=True, index=True` | Project convention |

### Existing Model Patterns

| Model | File | Key Features |
|-------|------|--------------|
| Task | `task.py` | Enum status, relationships, nullable FK |
| SOP | `sop.py` | Cascade relationships, JSON fields |
| Event | `event.py` | Foreign key to Task, Enum type |
| Snapshot | `snapshot.py` | Foreign key to Task, JSON data |
| Fault | `fault.py` | Simple model with description |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Model Base Contract

All models MUST inherit from `Base` and `TimestampMixin`:

```python
from .base import Base, TimestampMixin

class <Name>(Base, TimestampMixin):
    __tablename__ = "<name>s"  # plural form

    id = Column(Integer, primary_key=True, index=True)
    # ... fields
```

### Schema Contract

All schemas MUST follow Pydantic v2 patterns:

```python
class <Name>Response(<Name>Base):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (not orm_mode)
```

### Field Type Mapping

| Python Type | SQLAlchemy Type | Pydantic Type |
|-------------|-----------------|---------------|
| int | Integer | int |
| str | String(n) | str |
| bool | Boolean | bool |
| datetime | DateTime | datetime |
| Enum | SQLEnum(EnumClass) | EnumClass |
| dict/JSON | JSON | Dict[str, Any] |
| Optional | nullable=True | Optional[T] |

❌ Any deviation → **FAIL and require correction**

---

## 9. Execution Plan（固定流程，不可跳步）

### Placeholder Convention

In all templates below:
- `<name>` → lowercase model name with underscores (e.g., `fault_report`)
- `<Name>` → PascalCase model name (e.g., `FaultReport`)

These placeholders MUST be replaced with actual values during generation.

---

### Step 1 — Validate Input

* Action: Confirm model name and check prerequisites
* Checks:
  - Model name provided by user
  - Name follows convention (lowercase, underscores)
  - Target model file does not exist
  - Target schema file does not exist
* Command:
  ```bash
  cd r-mos-backend
  echo "=== Checking Prerequisites ==="
  [ -f "app/models/base.py" ] && echo "✓ base.py exists" || echo "✗ base.py not found"
  [ -f "app/models/<name>.py" ] && echo "✗ Model file already exists" || echo "✓ Model file does not exist"
  [ -f "app/schemas/<name>.py" ] && echo "✗ Schema file already exists" || echo "✓ Schema file does not exist"
  ```
* Failure condition: File already exists OR name not provided OR base.py not found

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Reference Existing Patterns

* Action: Read existing model and schema for consistency
* Command:
  ```bash
  cd r-mos-backend
  echo "=== Model Pattern Reference ==="
  head -40 app/models/task.py
  echo ""
  echo "=== Schema Pattern Reference ==="
  head -40 app/schemas/task.py
  ```
* Purpose: Ensure generated code follows same patterns
* Failure condition: None

---

### Step 3 — Generate Model File

* Action: Create new SQLAlchemy model file with scaffolding
* File: `r-mos-backend/app/models/<name>.py`
* Template: See §9.3 Template below
* Failure condition: Write operation fails

---

### Step 4 — Generate Schema File

* Action: Create corresponding Pydantic schema file
* File: `r-mos-backend/app/schemas/<name>.py`
* Template: See §9.4 Template below
* Failure condition: Write operation fails

---

### Step 5 — Verify Generation

* Action: Confirm files were created correctly
* Command:
  ```bash
  cd r-mos-backend
  echo "=== Generated Model ==="
  ls -la app/models/<name>.py
  head -30 app/models/<name>.py
  echo ""
  echo "=== Generated Schema ==="
  ls -la app/schemas/<name>.py
  head -30 app/schemas/<name>.py
  ```
* Failure condition: File not found or malformed

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

### 9.3 Model File Template

```python
"""
<Name>数据模型

Dependencies:
- Base: app/models/base.py
- TimestampMixin: app/models/base.py

⚠️ After creating this model:
1. Add import to app/models/__init__.py (if exists)
2. Run Alembic migration: alembic revision --autogenerate -m "add <name>"
3. Apply migration: alembic upgrade head
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from enum import Enum

from .base import Base, TimestampMixin


class <Name>(Base, TimestampMixin):
    """<Name>模型

    表名: <name>s

    字段说明:
    - id: 主键
    - TODO: Add field descriptions

    关系:
    - TODO: Define relationships if needed
    """
    __tablename__ = "<name>s"

    id = Column(Integer, primary_key=True, index=True)

    # TODO: Add fields based on requirements
    # Example fields:
    # name = Column(String(100), nullable=False, comment="名称")
    # description = Column(Text, nullable=True, comment="描述")
    # is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")

    # Example Enum field (define Enum class above the model class):
    # class <Name>Status(str, Enum):
    #     PENDING = "pending"
    #     ACTIVE = "active"
    #     COMPLETED = "completed"
    #
    # status = Column(SQLEnum(<Name>Status), default=<Name>Status.PENDING, nullable=False, comment="状态")

    # TODO: Add foreign keys if needed
    # Example:
    # task_id = Column(
    #     Integer,
    #     ForeignKey("tasks.id", ondelete="CASCADE"),
    #     nullable=False,
    #     index=True,
    #     comment="关联任务ID"
    # )

    # TODO: Add relationships if needed
    # Example:
    # task = relationship("Task", back_populates="<name>s")

    def __repr__(self):
        return f"<<Name>(id={self.id})>"
```

---

### 9.4 Schema File Template

```python
"""
<Name> Pydantic Schema定义

用于API请求/响应验证

Dependencies:
- Model: app/models/<name>.py
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# If model has Enum fields, import them:
# from app.models.<name> import <Name>Status


class <Name>Base(BaseModel):
    """<Name>基础字段

    包含创建和更新共用的字段
    """
    # TODO: Add common fields
    # Example:
    # name: str = Field(..., max_length=100, description="名称")
    # description: Optional[str] = Field(None, description="描述")
    pass


class <Name>Create(<Name>Base):
    """创建<Name>请求

    继承Base字段，添加创建时必需的额外字段
    """
    # TODO: Add required fields for creation
    # Example:
    # task_id: int = Field(..., gt=0, description="关联任务ID")
    pass


class <Name>Update(BaseModel):
    """更新<Name>请求

    所有字段可选，仅更新提供的字段
    """
    # TODO: Add optional fields for update
    # Example:
    # name: Optional[str] = Field(None, max_length=100, description="名称")
    # description: Optional[str] = Field(None, description="描述")
    pass


class <Name>Response(<Name>Base):
    """<Name>响应

    返回完整的<Name>信息，包括ID和时间戳
    """
    id: int
    # If model has Enum fields, add them:
    # status: <Name>Status
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (replaces orm_mode)
```

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Model name not provided
* Target model file already exists
* Target schema file already exists
* Models or schemas directory not found
* base.py not found
* Write operation fails

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: New Data Model Generation

Generated Files:
  - app/models/<name>.py: CREATED | FAILED
  - app/schemas/<name>.py: CREATED | FAILED

Post-Generation Steps Required:
  1. Add import to app/models/__init__.py (if exists):
     from .<name> import <Name>

  2. Create Alembic migration:
     alembic revision --autogenerate -m "add <name>"

  3. Apply migration:
     alembic upgrade head

Next Recommended Skill:
  - /new-service <name> - Create service layer
  - /new-api <name> - Create API endpoint
```

---

## 11. Related Files / Interfaces（只读参考）

* `r-mos-backend/app/models/base.py` — Base class and TimestampMixin
* `r-mos-backend/app/models/task.py` — Primary model reference
* `r-mos-backend/app/models/sop.py` — Complex relationships reference
* `r-mos-backend/app/models/event.py` — Simple FK reference
* `r-mos-backend/app/schemas/task.py` — Primary schema reference
* `r-mos-backend/app/schemas/sop.py` — Complex schema reference
* `r-mos-backend/app/core/database.py` — Database connection

### Key Patterns from Existing Models

**Task (task.py):**
- Enum status field with `SQLEnum`
- Nullable foreign key with `ondelete="SET NULL"`
- Multiple relationships with cascade

**SOP (sop.py):**
- JSON field for complex data
- Cascade delete relationships
- Deep nesting structure

**Event (event.py):**
- Simple foreign key reference
- Enum type field
- Minimal relationships

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* SQLAlchemy is replaced with another ORM
* Pydantic version changes from v2
* Database changes from PostgreSQL
* Model base class pattern changes
* Schema validation patterns change
* Directory structure changes
* Project enters production phase with different patterns

Once invalid, this skill MUST NOT be executed without human review.

---
