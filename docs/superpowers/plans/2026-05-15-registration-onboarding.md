# 注册流程优化：学校校验 + 角色绑定 + 教师 Onboarding 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师注册时选择学校 + 完成机器人选择 onboarding，学生注册时选择学校 + 绑定教师，使新用户注册后即可使用平台全部功能。

**Architecture:** 后端新增 `schools` 白名单表、`users` 表加 `school_name` / `onboarding_completed` 字段、3 个新 API 端点；前端注册页改为分步表单、新增教师 onboarding 页、路由守卫增加 onboarding 拦截。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic (backend), React + TypeScript + Ant Design Steps (frontend)

**Design spec:** `docs/superpowers/specs/2026-05-15-registration-onboarding-design.md`

---

## 文件结构

### 后端新建

| 文件 | 职责 |
|------|------|
| `app/models/school.py` | School ORM 模型 |
| `app/api/v1/endpoints/schools.py` | 学校搜索 + 教师列表公开端点 |
| `app/api/v1/endpoints/onboarding.py` | 教师机器人选择端点 |
| `alembic/versions/20260515_add_schools_and_onboarding.py` | 迁移：schools 表 + users 新字段 |
| `scripts/seed_schools.py` | 学校名录导入脚本 |

### 后端修改

| 文件 | 改动 |
|------|------|
| `app/models/user.py` | 新增 `school_name`, `onboarding_completed` 字段 |
| `app/models/__init__.py` | 导入 School |
| `app/schemas/auth.py` | RegisterRequest 加字段，RegisterResponse 加 token 字段 |
| `app/api/v1/endpoints/auth.py` | 注册逻辑加学校校验、角色分流、自动签发 token |
| `app/api/v1/__init__.py` | 注册 schools + onboarding 路由 |

### 前端新建

| 文件 | 职责 |
|------|------|
| `src/pages/OnboardingRobotsPage.tsx` | 教师机器人选择 onboarding 页 |
| `src/api/schools.ts` | 学校搜索 + 教师列表 API |
| `src/api/onboarding.ts` | 教师 onboarding API |

### 前端修改

| 文件 | 改动 |
|------|------|
| `src/pages/RegisterPage.tsx` | 改为分步表单 |
| `src/store/authStore.ts` | AuthUser 加 `onboarding_completed`，`applySession` 处理新字段 |
| `src/components/auth/ProtectedRoute.tsx` | 增加 onboarding 拦截 |
| `src/App.tsx` | 新增 `/onboarding/robots` 路由 |

---

### Task 1: School 模型 + 数据库迁移

**Files:**
- Create: `r-mos-backend/app/models/school.py`
- Modify: `r-mos-backend/app/models/user.py:16-31`
- Modify: `r-mos-backend/app/models/__init__.py`
- Create: `r-mos-backend/alembic/versions/20260515_add_schools_and_onboarding.py`

- [ ] **Step 1: 创建 School 模型**

```python
# r-mos-backend/app/models/school.py
"""学校白名单模型。"""
from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    province = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 修改 User 模型，添加 school_name 和 onboarding_completed 字段**

在 `r-mos-backend/app/models/user.py` 的 `User` 类中，在 `hint_level` 之后添加：

```python
    school_name = Column(String(200), nullable=True)  # 学校全称，关联 schools.name
    onboarding_completed = Column(Boolean, default=True, nullable=False)  # 教师 onboarding 完成标记
```

- [ ] **Step 3: 在 models/__init__.py 中导入 School**

在 `r-mos-backend/app/models/__init__.py` 中添加：

```python
from app.models.school import School  # noqa: F401
```

- [ ] **Step 4: 创建 Alembic 迁移文件**

```python
# r-mos-backend/alembic/versions/20260515_add_schools_and_onboarding.py
"""add schools table and user onboarding fields

Revision ID: 20260515_schools
Revises: 20260507_robot_platform
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260515_schools"
down_revision = "20260507_robot_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("province", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_schools_name", "schools", ["name"])

    op.add_column("users", sa.Column("school_name", sa.String(200), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "school_name")
    op.drop_index("ix_schools_name", table_name="schools")
    op.drop_table("schools")
```

- [ ] **Step 5: 运行迁移**

```bash
cd r-mos-backend
source venv/bin/activate
alembic upgrade head
```

Expected: 迁移成功，`schools` 表已创建，`users` 表新增两个字段。

- [ ] **Step 6: 提交**

```bash
git add app/models/school.py app/models/user.py app/models/__init__.py alembic/versions/20260515_add_schools_and_onboarding.py
git commit -m "feat(models): add schools table and user onboarding fields"
```

---

### Task 2: 学校种子数据导入脚本

**Files:**
- Create: `r-mos-backend/scripts/seed_schools.py`
- Create: `r-mos-backend/data/schools.json`（用户提供教育部名录后替换）

- [ ] **Step 1: 创建种子数据文件（初始占位 + 演示数据）**

创建 `r-mos-backend/data/schools.json`：

```json
[
  {"name": "北京大学", "province": "北京市"},
  {"name": "清华大学", "province": "北京市"},
  {"name": "北京理工大学", "province": "北京市"},
  {"name": "北京航空航天大学", "province": "北京市"},
  {"name": "上海交通大学", "province": "上海市"},
  {"name": "复旦大学", "province": "上海市"},
  {"name": "浙江大学", "province": "浙江省"},
  {"name": "南京大学", "province": "江苏省"},
  {"name": "哈尔滨工业大学", "province": "黑龙江省"},
  {"name": "华中科技大学", "province": "湖北省"},
  {"name": "R-MOS 演示学校", "province": "北京市"}
]
```

说明：这是初始占位数据，用户会提供教育部官方名录后替换此文件。

- [ ] **Step 2: 创建导入脚本**

```python
# r-mos-backend/scripts/seed_schools.py
"""导入学校白名单数据到 schools 表。

Usage:
    cd r-mos-backend
    source venv/bin/activate
    python scripts/seed_schools.py [--file data/schools.json]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.school import School


async def seed_schools(json_path: str) -> None:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    print(f"读取 {len(data)} 条学校记录")

    async with AsyncSessionLocal() as db:
        existing_count = (await db.execute(select(func.count(School.id)))).scalar() or 0
        print(f"数据库中已有 {existing_count} 条记录")

        inserted = 0
        for item in data:
            name = item["name"].strip()
            province = item.get("province", "").strip() or None
            exists = (
                await db.execute(select(School.id).where(School.name == name))
            ).scalar_one_or_none()
            if exists:
                continue
            db.add(School(name=name, province=province))
            inserted += 1

        await db.commit()
        print(f"新增 {inserted} 条，跳过 {len(data) - inserted} 条重复记录")


def main():
    parser = argparse.ArgumentParser(description="导入学校白名单")
    parser.add_argument(
        "--file",
        default="data/schools.json",
        help="学校 JSON 文件路径 (默认: data/schools.json)",
    )
    args = parser.parse_args()
    asyncio.run(seed_schools(args.file))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 运行种子脚本**

```bash
cd r-mos-backend
source venv/bin/activate
python scripts/seed_schools.py
```

Expected: `读取 11 条学校记录`，`新增 11 条`

- [ ] **Step 4: 验证数据**

```bash
python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, func
from app.models.school import School

async def check():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(School.id)))).scalar()
        print(f'schools 表共 {count} 条记录')
        rows = await db.execute(select(School.name, School.province).limit(5))
        for r in rows.fetchall():
            print(f'  {r[0]} ({r[1]})')

asyncio.run(check())
"
```

Expected: 显示 11 条记录及前 5 条学校名称。

- [ ] **Step 5: 提交**

```bash
git add scripts/seed_schools.py data/schools.json
git commit -m "feat(scripts): add school seed data and import script"
```

---

### Task 3: 学校搜索 + 教师列表 API

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/schools.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: 创建学校端点**

```python
# r-mos-backend/app/api/v1/endpoints/schools.py
"""学校搜索和教师列表端点（公开，无需认证）。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.school import School
from app.models.user import User

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("")
async def search_schools(
    q: str = Query("", description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """搜索学校名称（公开接口，用于注册页自动补全）。"""
    stmt = select(School.id, School.name, School.province)
    if q.strip():
        stmt = stmt.where(School.name.contains(q.strip()))
    stmt = stmt.order_by(School.name).limit(limit)

    result = await db.execute(stmt)
    items = [{"id": r.id, "name": r.name, "province": r.province} for r in result.fetchall()]
    return {"items": items}


@router.get("/{school_name}/teachers")
async def list_school_teachers(
    school_name: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定学校的教师列表（公开接口，用于学生注册时选择教师）。"""
    # 校验学校存在
    school_exists = (
        await db.execute(select(School.id).where(School.name == school_name))
    ).scalar_one_or_none()
    if school_exists is None:
        return {"items": []}

    stmt = (
        select(User.id, User.full_name, User.email)
        .where(User.role == "teacher", User.school_name == school_name)
        .order_by(User.id)
    )
    result = await db.execute(stmt)
    items = [
        {"id": r.id, "full_name": r.full_name or "", "email": r.email}
        for r in result.fetchall()
    ]
    return {"items": items}
```

- [ ] **Step 2: 注册路由**

在 `r-mos-backend/app/api/v1/__init__.py` 中添加导入和注册：

```python
from app.api.v1.endpoints import schools
```

并在 `api_router` 拼装处添加：

```python
api_router.include_router(schools.router, tags=["schools"])
```

- [ ] **Step 3: 验证端点**

重启后端后：

```bash
# 搜索学校
curl -s "http://localhost:8000/api/v1/schools?q=北京" | python3 -m json.tool

# 查看学校教师（当前应为空）
curl -s "http://localhost:8000/api/v1/schools/R-MOS%20演示学校/teachers" | python3 -m json.tool
```

Expected: 搜索返回包含「北京」的学校列表；教师列表返回空 `items`。

- [ ] **Step 4: 提交**

```bash
git add app/api/v1/endpoints/schools.py app/api/v1/__init__.py
git commit -m "feat(api): add public school search and teacher list endpoints"
```

---

### Task 4: 注册 API 改造

**Files:**
- Modify: `r-mos-backend/app/schemas/auth.py:31-45,80-86`
- Modify: `r-mos-backend/app/api/v1/endpoints/auth.py:73-110`

- [ ] **Step 1: 修改 RegisterRequest schema**

在 `r-mos-backend/app/schemas/auth.py` 中，将 `RegisterRequest` 替换为：

```python
class RegisterRequest(BaseModel):
    """注册请求。"""

    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(default=None, description="用户姓名")
    role: str = Field(..., description="角色: student 或 teacher")
    school_name: str = Field(..., description="学校全称（必须在白名单中）")
    teacher_id: Optional[int] = Field(default=None, description="绑定教师ID（学生必填）")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "StrongPass123",
                "full_name": "R-MOS User",
                "role": "student",
                "school_name": "北京理工大学",
                "teacher_id": 18,
            }
        }
```

- [ ] **Step 2: 修改 RegisterResponse schema**

将 `RegisterResponse` 替换为：

```python
class RegisterResponse(BaseModel):
    """注册响应（含自动登录 token）。"""

    user_id: int = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    message: str = Field(default="注册成功", description="提示消息")
    access_token: str = Field(..., description="访问Token")
    refresh_token: str = Field(..., description="刷新Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    role: str = Field(..., description="用户角色")
    default_route: str = Field(..., description="默认跳转路由")
    onboarding_completed: bool = Field(..., description="是否完成 onboarding")
```

- [ ] **Step 3: 改造 register 端点**

将 `r-mos-backend/app/api/v1/endpoints/auth.py` 中的 `register` 函数替换为：

```python
@router.post("/auth/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.school import School

    normalized_email = payload.email.lower()

    # 1. 邮箱唯一性检查
    existing_user_result = await db.execute(
        select(User.id).where(func.lower(User.email) == normalized_email)
    )
    if existing_user_result.scalar_one_or_none() is not None:
        return _error_response(
            request, status_code=400, error_type="UserAlreadyExists",
            code="USER_001", message="邮箱已存在",
        )

    # 2. 密码强度
    if not is_strong_password(payload.password):
        return _error_response(
            request, status_code=400, error_type="WeakPassword",
            code="USER_002", message="密码强度不足",
        )

    # 3. 角色校验
    if payload.role not in ("student", "teacher"):
        return _error_response(
            request, status_code=400, error_type="InvalidRole",
            code="USER_003", message="角色必须为 student 或 teacher",
        )

    # 4. 学校白名单校验
    school_exists = (
        await db.execute(select(School.id).where(School.name == payload.school_name))
    ).scalar_one_or_none()
    if school_exists is None:
        return _error_response(
            request, status_code=400, error_type="InvalidSchool",
            code="USER_004", message="学校名称不在系统名录中，请检查输入",
        )

    # 5. 学生必须绑定教师
    teacher_id = None
    if payload.role == "student":
        if not payload.teacher_id:
            return _error_response(
                request, status_code=400, error_type="TeacherRequired",
                code="USER_005", message="学生注册必须选择一位教师",
            )
        teacher_result = await db.execute(
            select(User).where(
                User.id == payload.teacher_id,
                User.role == "teacher",
                User.school_name == payload.school_name,
            )
        )
        teacher = teacher_result.scalar_one_or_none()
        if teacher is None:
            return _error_response(
                request, status_code=400, error_type="InvalidTeacher",
                code="USER_006", message="所选教师不存在或不属于该学校",
            )
        teacher_id = payload.teacher_id

    # 6. 创建用户
    is_teacher = payload.role == "teacher"
    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        school_name=payload.school_name,
        teacher_id=teacher_id,
        onboarding_completed=not is_teacher,  # 教师需完成 onboarding
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 7. 自动签发 token（与 login 逻辑一致）
    access_token, refresh_token = _issue_token_pair()
    await _persist_tokens(db, user.id, access_token, refresh_token)

    # 8. 确定默认路由
    if is_teacher:
        default_route = "/onboarding/robots"
    else:
        default_route = "/dashboard"

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        message="注册成功",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
        role=user.role,
        default_route=default_route,
        onboarding_completed=user.onboarding_completed,
    )
```

注意：`_issue_token_pair` 和 `_persist_tokens` 是 `auth.py` 中已有的辅助函数。如果 `_persist_tokens` 不存在，需要从 `login` 函数中提取 token 持久化逻辑为独立函数。检查 `auth.py` 中 login 函数的 token 持久化代码，将其提取为 `_persist_tokens(db, user_id, access_token, refresh_token)` 函数。

- [ ] **Step 4: 修改 login 响应，增加 onboarding_completed**

在 `auth.py` 的 `login` 函数中，`TokenResponse` 返回处添加 `onboarding_completed` 字段。

在 `r-mos-backend/app/schemas/auth.py` 的 `TokenResponse` 类中添加：

```python
    onboarding_completed: bool = Field(default=True, description="是否完成 onboarding")
```

在 `auth.py` login 函数的返回值中添加：

```python
    onboarding_completed=getattr(user, 'onboarding_completed', True),
```

同时修改 `_get_default_route` 逻辑，教师未完成 onboarding 时返回 `/onboarding/robots`：

```python
def _get_default_route(user) -> str:
    if user.role == "teacher" and not getattr(user, "onboarding_completed", True):
        return "/onboarding/robots"
    routes = {
        "student": "/dashboard",
        "teacher": "/workbench/teaching",
        "admin": "/admin/console",
    }
    return routes.get(user.role, "/dashboard")
```

注意：`_get_default_route` 的签名从接受 `role: str` 改为接受 `user` 对象。需要同步更新 login 和 refresh 中的调用。

- [ ] **Step 5: 验证注册 API**

```bash
# 教师注册
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test_teacher@test.com","password":"TestPass123","full_name":"测试教师","role":"teacher","school_name":"R-MOS 演示学校"}'

# 期望: 201, 含 access_token, default_route="/onboarding/robots", onboarding_completed=false

# 无效学校
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"bad@test.com","password":"TestPass123","full_name":"坏人","role":"student","school_name":"不存在的学校"}'

# 期望: 400, "学校名称不在系统名录中"
```

- [ ] **Step 6: 提交**

```bash
git add app/schemas/auth.py app/api/v1/endpoints/auth.py
git commit -m "feat(api): enhance registration with school validation, role, and auto-login"
```

---

### Task 5: 教师 Onboarding 端点

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/onboarding.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: 创建 onboarding 端点**

```python
# r-mos-backend/app/api/v1/endpoints/onboarding.py
"""教师 Onboarding 端点。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.robot_model import RobotModel, RobotStatus, TeacherRobotBinding
from app.models.user import User
from app.services.authz_guard import ActorContext, get_current_actor

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class RobotSelectionRequest(BaseModel):
    robot_ids: list[int] = Field(..., min_length=1, max_length=5, description="机器人ID列表，1~5个")


@router.get("/robots")
async def list_available_robots(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取可选机器人列表（教师 onboarding 用）。"""
    if "teacher" not in actor.roles:
        raise HTTPException(status_code=403, detail="仅教师可访问")

    stmt = select(RobotModel).where(RobotModel.status == RobotStatus.READY)
    result = await db.execute(stmt)
    robots = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "brand": r.brand,
                "model_name": r.model_name,
                "description": r.description,
                "thumbnail_path": r.thumbnail_path,
            }
            for r in robots
        ]
    }


@router.post("/robots")
async def select_robots(
    payload: RobotSelectionRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """教师完成机器人选择（onboarding 最后一步）。"""
    if "teacher" not in actor.roles:
        raise HTTPException(status_code=403, detail="仅教师可访问")

    # 检查是否已完成 onboarding
    user_result = await db.execute(select(User).where(User.id == actor.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.onboarding_completed:
        raise HTTPException(status_code=400, detail="已完成机器人选择，无需重复操作")

    # 校验所有 robot_id 存在且状态为 ready
    for rid in payload.robot_ids:
        robot = (
            await db.execute(
                select(RobotModel).where(RobotModel.id == rid, RobotModel.status == RobotStatus.READY)
            )
        ).scalar_one_or_none()
        if not robot:
            raise HTTPException(status_code=400, detail=f"机器人 ID={rid} 不存在或不可用")

    # 批量创建绑定
    for rid in payload.robot_ids:
        existing = (
            await db.execute(
                select(TeacherRobotBinding).where(
                    TeacherRobotBinding.teacher_id == actor.user_id,
                    TeacherRobotBinding.robot_model_id == rid,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(TeacherRobotBinding(teacher_id=actor.user_id, robot_model_id=rid))

    # 更新 onboarding 状态
    user.onboarding_completed = True
    await db.commit()

    return {"message": "机器人选择完成", "bound_count": len(payload.robot_ids)}
```

- [ ] **Step 2: 注册路由**

在 `r-mos-backend/app/api/v1/__init__.py` 中添加：

```python
from app.api.v1.endpoints import onboarding

api_router.include_router(onboarding.router, tags=["onboarding"])
```

- [ ] **Step 3: 验证端点**

```bash
# 用刚注册的教师 token 获取可选机器人
curl -s -H "Authorization: Bearer <teacher_access_token>" http://localhost:8000/api/v1/onboarding/robots

# 期望: 返回 ATOM-01 等 ready 状态机器人列表

# 选择机器人
curl -s -X POST http://localhost:8000/api/v1/onboarding/robots \
  -H "Authorization: Bearer <teacher_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"robot_ids": [1]}'

# 期望: {"message": "机器人选择完成", "bound_count": 1}
```

- [ ] **Step 4: 提交**

```bash
git add app/api/v1/endpoints/onboarding.py app/api/v1/__init__.py
git commit -m "feat(api): add teacher onboarding robot selection endpoint"
```

---

### Task 6: 前端 authStore 适配

**Files:**
- Modify: `r-mos-frontend/src/store/authStore.ts`

- [ ] **Step 1: AuthUser 接口添加 onboarding_completed**

在 `src/store/authStore.ts` 的 `AuthUser` 接口中添加字段：

```typescript
export interface AuthUser {
  user_id?: number
  email?: string
  full_name?: string
  role: UserRole
  guidance_mode?: GuidanceMode
  welcome_summary?: string | null
  unfinished_session?: Record<string, unknown> | null
  onboarding_completed?: boolean  // 新增
}
```

- [ ] **Step 2: applySession 处理 onboarding_completed**

在 `applySession` 函数中，将 `onboarding_completed` 从 payload 提取到 user 对象。找到设置 user 对象的位置，添加：

```typescript
onboarding_completed: payload.onboarding_completed ?? true,
```

同时在 localStorage 中持久化：

```typescript
localStorage.setItem('rmos_onboarding_completed', String(payload.onboarding_completed ?? true))
```

- [ ] **Step 3: initFromStorage 恢复 onboarding_completed**

在 `initFromStorage` 中恢复该字段：

```typescript
const onboardingCompleted = localStorage.getItem('rmos_onboarding_completed')
// 在构建 user 对象时添加:
onboarding_completed: onboardingCompleted !== 'false',
```

- [ ] **Step 4: 新增 register 方法**

在 authStore 中添加 `register` action：

```typescript
async register(data: {
  email: string
  password: string
  full_name?: string
  role: string
  school_name: string
  teacher_id?: number
}): Promise<string> {
  const response = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/auth/register`,
    data,
  )
  const payload = response.data
  get().applySession(payload, data.email)
  return payload.default_route
},
```

- [ ] **Step 5: 提交**

```bash
git add src/store/authStore.ts
git commit -m "feat(store): add onboarding_completed to auth store and register action"
```

---

### Task 7: 前端学校搜索和 onboarding API

**Files:**
- Create: `r-mos-frontend/src/api/schools.ts`
- Create: `r-mos-frontend/src/api/onboarding.ts`

- [ ] **Step 1: 创建学校 API**

```typescript
// r-mos-frontend/src/api/schools.ts
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export interface SchoolItem {
  id: number
  name: string
  province: string | null
}

export interface TeacherItem {
  id: number
  full_name: string
  email: string
}

/** 搜索学校（公开接口，无需 token） */
export async function searchSchools(q: string, limit = 10): Promise<SchoolItem[]> {
  const res = await axios.get(`${API_BASE}/api/v1/schools`, { params: { q, limit } })
  return res.data.items
}

/** 获取学校教师列表（公开接口） */
export async function listSchoolTeachers(schoolName: string): Promise<TeacherItem[]> {
  const res = await axios.get(`${API_BASE}/api/v1/schools/${encodeURIComponent(schoolName)}/teachers`)
  return res.data.items
}
```

- [ ] **Step 2: 创建 onboarding API**

```typescript
// r-mos-frontend/src/api/onboarding.ts
import { apiClient } from './client'

export interface RobotOption {
  id: number
  brand: string
  model_name: string
  description: string | null
  thumbnail_path: string | null
}

/** 获取可选机器人列表 */
export async function listAvailableRobots(): Promise<RobotOption[]> {
  const res = await apiClient.get('/onboarding/robots')
  return res.data.items
}

/** 教师选择机器人 */
export async function selectRobots(robotIds: number[]): Promise<{ message: string; bound_count: number }> {
  const res = await apiClient.post('/onboarding/robots', { robot_ids: robotIds })
  return res.data
}
```

- [ ] **Step 3: 提交**

```bash
git add src/api/schools.ts src/api/onboarding.ts
git commit -m "feat(api): add school search and onboarding API clients"
```

---

### Task 8: 前端注册页改为分步表单

**Files:**
- Modify: `r-mos-frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: 重写 RegisterPage 为分步表单**

完全重写 `src/pages/RegisterPage.tsx`。保留原有的视觉风格（暗色背景、R-MOS branding、卡片容器），将内容改为分步表单：

```tsx
import { Bot, CheckCircle, ChevronLeft, ChevronRight, LoaderCircle, UserPlus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { debounce } from 'lodash-es'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/store/authStore'
import { searchSchools, listSchoolTeachers, type SchoolItem, type TeacherItem } from '@/api/schools'

type Role = 'student' | 'teacher'

function RegisterPage() {
  const navigate = useNavigate()
  const registerAction = useAuthStore((s) => s.register)

  // 步骤控制
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  // Step 1: 基本信息
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState<Role>('student')

  // Step 2: 学校
  const [schoolQuery, setSchoolQuery] = useState('')
  const [schoolOptions, setSchoolOptions] = useState<SchoolItem[]>([])
  const [selectedSchool, setSelectedSchool] = useState('')
  const [schoolSearching, setSchoolSearching] = useState(false)

  // Step 3: 教师选择（学生用）
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [selectedTeacherId, setSelectedTeacherId] = useState<number | null>(null)
  const [teachersLoading, setTeachersLoading] = useState(false)

  // 学校搜索（防抖）
  const debouncedSearch = useCallback(
    debounce(async (q: string) => {
      if (q.length < 2) {
        setSchoolOptions([])
        return
      }
      setSchoolSearching(true)
      try {
        const items = await searchSchools(q)
        setSchoolOptions(items)
      } catch {
        setSchoolOptions([])
      } finally {
        setSchoolSearching(false)
      }
    }, 300),
    [],
  )

  useEffect(() => {
    debouncedSearch(schoolQuery)
  }, [schoolQuery, debouncedSearch])

  // 选择学校后加载教师列表（仅学生）
  useEffect(() => {
    if (!selectedSchool || role !== 'student') return
    setTeachersLoading(true)
    listSchoolTeachers(selectedSchool)
      .then(setTeachers)
      .catch(() => setTeachers([]))
      .finally(() => setTeachersLoading(false))
  }, [selectedSchool, role])

  // Step 1 校验
  const canProceedStep1 =
    fullName.trim() && email.trim() && password.length >= 8 && password === confirmPassword

  // Step 2 校验
  const canProceedStep2 = !!selectedSchool

  // Step 3 校验（学生需选教师）
  const canSubmit = role === 'teacher' || !!selectedTeacherId

  const totalSteps = role === 'student' ? 3 : 2

  const handleNext = () => {
    if (step === 1 && !canProceedStep1) {
      if (password !== confirmPassword) toast.error('两次输入的密码不一致')
      else if (password.length < 8) toast.error('密码长度至少 8 位')
      return
    }
    if (step === 2 && role === 'teacher') {
      handleSubmit()
      return
    }
    setStep((s) => s + 1)
  }

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      const defaultRoute = await registerAction({
        email,
        password,
        full_name: fullName,
        role,
        school_name: selectedSchool,
        teacher_id: selectedTeacherId ?? undefined,
      })
      setIsSuccess(true)
      toast.success('注册成功！')
      setTimeout(() => navigate(defaultRoute), 1000)
    } catch (error: unknown) {
      const msg = (error as { response?: { data?: { message?: string } } })?.response?.data?.message ?? '注册失败'
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const stepTitle = ['基本信息', '选择学校', '选择教师'][step - 1]

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[480px] overflow-hidden rounded-2xl border border-border-subtle bg-bg-surface/80 shadow-lg backdrop-blur-sm">
        <div className="p-10">
          {/* brand header */}
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-mono text-xl font-bold text-primary">R-MOS</p>
              <p className="text-xs text-text-muted">Robot Maintenance OS</p>
            </div>
          </div>

          {isSuccess ? (
            <div className="space-y-4 py-8 text-center animate-fade-in">
              <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
              <p className="text-lg font-semibold text-text-primary">注册成功</p>
              <p className="text-sm text-text-secondary">正在跳转...</p>
            </div>
          ) : (
            <>
              {/* 步骤指示器 */}
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xl font-semibold text-text-primary">{stepTitle}</p>
                  <span className="text-xs text-text-muted">步骤 {step}/{totalSteps}</span>
                </div>
                <div className="flex gap-1">
                  {Array.from({ length: totalSteps }, (_, i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i < step ? 'bg-primary' : 'bg-border-subtle'
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Step 1: 基本信息 */}
              {step === 1 && (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted">角色</label>
                    <div className="flex gap-2">
                      {(['student', 'teacher'] as const).map((r) => (
                        <button
                          key={r}
                          type="button"
                          onClick={() => setRole(r)}
                          className={`flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                            role === r
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border-subtle text-text-secondary hover:border-text-muted'
                          }`}
                        >
                          {r === 'student' ? '学生' : '教师'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-name">姓名</label>
                    <Input id="reg-name" placeholder="您的姓名" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-email">邮箱地址</label>
                    <Input id="reg-email" type="email" placeholder="user@rmos.io" required value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-pass">密码</label>
                    <Input id="reg-pass" type="password" placeholder="至少 8 位，含大小写和数字" required value={password} onChange={(e) => setPassword(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-confirm">确认密码</label>
                    <Input id="reg-confirm" type="password" placeholder="再次输入密码" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                  </div>
                </div>
              )}

              {/* Step 2: 学校选择 */}
              {step === 2 && (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted">学校全称</label>
                    <Input
                      placeholder="输入学校名称搜索..."
                      value={schoolQuery}
                      onChange={(e) => {
                        setSchoolQuery(e.target.value)
                        setSelectedSchool('')
                      }}
                    />
                    {schoolSearching && <p className="text-xs text-text-muted">搜索中...</p>}
                  </div>
                  {schoolOptions.length > 0 && !selectedSchool && (
                    <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-border-subtle p-1">
                      {schoolOptions.map((s) => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => {
                            setSelectedSchool(s.name)
                            setSchoolQuery(s.name)
                            setSchoolOptions([])
                          }}
                          className="w-full rounded-md px-3 py-2 text-left text-sm text-text-primary hover:bg-primary/10"
                        >
                          {s.name}
                          {s.province && <span className="ml-2 text-text-muted">({s.province})</span>}
                        </button>
                      ))}
                    </div>
                  )}
                  {selectedSchool && (
                    <div className="rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
                      已选择: {selectedSchool}
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: 教师选择（仅学生） */}
              {step === 3 && role === 'student' && (
                <div className="space-y-4">
                  {teachersLoading ? (
                    <p className="text-sm text-text-muted">加载教师列表...</p>
                  ) : teachers.length === 0 ? (
                    <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-400">
                      该校暂无已注册教师，请联系教师先注册
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm text-text-secondary">请选择您的指导教师：</p>
                      {teachers.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setSelectedTeacherId(t.id)}
                          className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                            selectedTeacherId === t.id
                              ? 'border-primary bg-primary/10'
                              : 'border-border-subtle hover:border-text-muted'
                          }`}
                        >
                          <p className="font-medium text-text-primary">{t.full_name || '未设置姓名'}</p>
                          <p className="text-xs text-text-muted">{t.email}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 导航按钮 */}
              <div className="mt-6 flex gap-3">
                {step > 1 && (
                  <Button variant="outline" onClick={() => setStep((s) => s - 1)} className="flex-1">
                    <ChevronLeft className="h-4 w-4" />
                    上一步
                  </Button>
                )}
                {step < totalSteps ? (
                  <Button
                    onClick={handleNext}
                    disabled={step === 1 ? !canProceedStep1 : !canProceedStep2}
                    className="flex-1"
                  >
                    下一步
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={role === 'teacher' ? handleNext : handleSubmit}
                    disabled={!canSubmit || isLoading}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <>
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        注册中...
                      </>
                    ) : (
                      <>
                        <UserPlus className="h-4 w-4" />
                        完成注册
                      </>
                    )}
                  </Button>
                )}
              </div>

              <div className="mt-6 text-center text-sm text-text-secondary">
                已有账户？{' '}
                <Link className="text-primary underline-offset-4 hover:underline" to="/login">
                  返回登录
                </Link>
              </div>
            </>
          )}
        </div>

        <div className="border-t border-border-subtle px-10 py-3 text-center text-xs text-text-muted">
          © 2026 R-MOS · v0.2.0
        </div>
      </div>
    </div>
  )
}

export default RegisterPage
```

- [ ] **Step 2: 安装 lodash-es（如果尚未安装）**

```bash
cd r-mos-frontend
npm ls lodash-es 2>/dev/null || npm install lodash-es && npm install -D @types/lodash-es
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/RegisterPage.tsx package.json package-lock.json
git commit -m "feat(frontend): rewrite register page as multi-step form with school and teacher selection"
```

---

### Task 9: 前端教师 Onboarding 页

**Files:**
- Create: `r-mos-frontend/src/pages/OnboardingRobotsPage.tsx`

- [ ] **Step 1: 创建 OnboardingRobotsPage**

```tsx
// r-mos-frontend/src/pages/OnboardingRobotsPage.tsx
import { Bot, CheckCircle, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { listAvailableRobots, selectRobots, type RobotOption } from '@/api/onboarding'
import { useAuthStore } from '@/store/authStore'

function OnboardingRobotsPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [robots, setRobots] = useState<RobotOption[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    listAvailableRobots()
      .then(setRobots)
      .catch(() => toast.error('加载机器人列表失败'))
      .finally(() => setLoading(false))
  }, [])

  const toggleRobot = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < 5) {
        next.add(id)
      } else {
        toast.warning('最多选择 5 台机器人')
      }
      return next
    })
  }

  const handleSubmit = async () => {
    if (selectedIds.size === 0) {
      toast.error('请至少选择 1 台机器人')
      return
    }
    setSubmitting(true)
    try {
      await selectRobots([...selectedIds])
      // 更新本地状态
      const store = useAuthStore.getState()
      if (store.user) {
        store.setUser({ ...store.user, onboarding_completed: true })
      }
      localStorage.setItem('rmos_onboarding_completed', 'true')
      setDone(true)
      toast.success('机器人选择完成！')
      setTimeout(() => navigate('/workbench/teaching'), 1500)
    } catch {
      toast.error('提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  // 已完成 onboarding 的教师不应看到此页
  if (user?.onboarding_completed) {
    navigate('/workbench/teaching', { replace: true })
    return null
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[640px] overflow-hidden rounded-2xl border border-border-subtle bg-bg-surface/80 shadow-lg backdrop-blur-sm">
        <div className="p-10">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-mono text-xl font-bold text-primary">R-MOS</p>
              <p className="text-xs text-text-muted">选择您要教学的机器人</p>
            </div>
          </div>

          {done ? (
            <div className="space-y-4 py-8 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
              <p className="text-lg font-semibold text-text-primary">设置完成</p>
              <p className="text-sm text-text-secondary">正在进入教学工作台...</p>
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center py-12">
              <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : robots.length === 0 ? (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-6 text-center text-sm text-yellow-400">
              暂无可用机器人，请联系管理员
            </div>
          ) : (
            <>
              <p className="mb-4 text-sm text-text-secondary">
                请选择您教学中使用的机器人型号（最多 5 台）：
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {robots.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => toggleRobot(r.id)}
                    className={`rounded-lg border p-4 text-left transition-colors ${
                      selectedIds.has(r.id)
                        ? 'border-primary bg-primary/10'
                        : 'border-border-subtle hover:border-text-muted'
                    }`}
                  >
                    <p className="font-medium text-text-primary">
                      {r.brand} {r.model_name}
                    </p>
                    {r.description && (
                      <p className="mt-1 text-xs text-text-muted line-clamp-2">{r.description}</p>
                    )}
                  </button>
                ))}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <span className="text-sm text-text-muted">
                  已选 {selectedIds.size}/5
                </span>
                <Button onClick={handleSubmit} disabled={selectedIds.size === 0 || submitting}>
                  {submitting ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      提交中...
                    </>
                  ) : (
                    '确认选择，开始使用'
                  )}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default OnboardingRobotsPage
```

- [ ] **Step 2: 在 authStore 中添加 setUser 方法**（如不存在）

在 `src/store/authStore.ts` 中添加：

```typescript
setUser(user: AuthUser) {
  set({ user })
},
```

- [ ] **Step 3: 提交**

```bash
git add src/pages/OnboardingRobotsPage.tsx src/store/authStore.ts
git commit -m "feat(frontend): add teacher onboarding robot selection page"
```

---

### Task 10: 前端路由守卫 + 路由注册

**Files:**
- Modify: `r-mos-frontend/src/components/auth/ProtectedRoute.tsx`
- Modify: `r-mos-frontend/src/App.tsx`

- [ ] **Step 1: 修改 ProtectedRoute 增加 onboarding 拦截**

在 `src/components/auth/ProtectedRoute.tsx` 中，在角色检查之前（`if (allowedRoles && ...)` 之前），添加 onboarding 拦截：

```typescript
  // 教师未完成 onboarding 时，强制跳转机器人选择页
  if (
    user.role === 'teacher' &&
    user.onboarding_completed === false &&
    location.pathname !== '/onboarding/robots'
  ) {
    return <Navigate to="/onboarding/robots" replace />
  }
```

- [ ] **Step 2: 在 App.tsx 中注册 onboarding 路由**

在 `src/App.tsx` 的路由定义中，在 ProtectedRoute 内部添加 onboarding 路由：

```tsx
<Route path="onboarding/robots" element={withSuspense(<OnboardingRobotsPage />)} />
```

在文件顶部添加 lazy import：

```tsx
const OnboardingRobotsPage = lazy(() => import('./pages/OnboardingRobotsPage'))
```

- [ ] **Step 3: 提交**

```bash
git add src/components/auth/ProtectedRoute.tsx src/App.tsx
git commit -m "feat(frontend): add onboarding route guard and robot selection route"
```

---

### Task 11: 存量 Demo 数据适配

**Files:**
- 无新文件，通过 SQL 或脚本更新存量数据

- [ ] **Step 1: 更新存量 demo 用户的 school_name**

```bash
cd r-mos-backend
source venv/bin/activate
python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def update():
    async with AsyncSessionLocal() as db:
        # 给 demo 用户设置学校
        await db.execute(text(\"\"\"
            UPDATE users SET school_name = 'R-MOS 演示学校'
            WHERE email LIKE '%@rmos.demo'
        \"\"\"))
        # 给 test 用户也设置学校（可选）
        await db.execute(text(\"\"\"
            UPDATE users SET school_name = 'R-MOS 演示学校'
            WHERE email LIKE '%@rmos.test'
        \"\"\"))
        await db.commit()
        print('Done')

asyncio.run(update())
"
```

- [ ] **Step 2: 验证存量用户数据**

```bash
python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        rows = await db.execute(text('SELECT email, role, school_name, onboarding_completed FROM users ORDER BY id'))
        for r in rows.fetchall():
            print(r)

asyncio.run(check())
"
```

Expected: 所有用户都有 `school_name`，`onboarding_completed` 为 True。

- [ ] **Step 3: 提交（如有脚本化）**

无代码文件变更，跳过提交。

---

### Task 12: 端到端验证

- [ ] **Step 1: 重启前后端**

```bash
# 重启后端
cd r-mos-backend && kill $(lsof -ti:8000) 2>/dev/null; source venv/bin/activate && python main.py &

# 前端 Vite 热更新应自动生效，若不行则：
cd r-mos-frontend && npm run dev
```

- [ ] **Step 2: 验证教师注册流程**

浏览器打开 `http://localhost:3002/register`：
1. 选择角色「教师」
2. 填写姓名/邮箱/密码
3. 输入学校名称「R-MOS 演示学校」→ 从自动补全中选择
4. 点击完成注册
5. 验证自动跳转到机器人选择页 `/onboarding/robots`
6. 勾选 ATOM-01
7. 确认 → 验证跳转到教学工作台

- [ ] **Step 3: 验证学生注册流程**

浏览器打开 `http://localhost:3002/register`：
1. 选择角色「学生」
2. 填写姓名/邮箱/密码
3. 输入学校名称「R-MOS 演示学校」
4. 在教师列表中选择刚注册的教师
5. 完成注册 → 验证跳转到 Dashboard
6. 进入 3D 展示页 → 验证能看到 ATOM-01 模型

- [ ] **Step 4: 验证错误场景**

- 输入不存在的学校名称 → 应报错「学校名称不在系统名录中」
- 学生不选教师 → 应无法提交
- 教师登录后未完成 onboarding → 应被拦截到机器人选择页
