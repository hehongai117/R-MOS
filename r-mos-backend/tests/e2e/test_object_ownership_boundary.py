"""AUTH-101 的「对象归属」半边：认证通过之后仍必须比较调用者与目标对象的归属。

背景：P3-1 的默认拒绝网关只解决了「匿名」。网关生效后，任何**已登录**用户
仍可用自己的合法令牌读取他人的对象——这是 Phase 1 登记的 `AUTH-101` 中
「用认证身份做学生、教师、学校和资源归属校验」那一半，至今未闭合。

本文件锁定验收章程 G1：
- 越权**读**对外返回 **404**（不是 403——403 会泄漏"这个对象存在"）；
- 每一次拒绝都必须留一条 deny 审计，且 `resource_id` 是**真实目标编号**、
  `actor_user_id` 是**令牌主体**（不是客户端传的任何值）；
- 跨学生、跨教师、跨校都必须拒绝；
- 正向路径不得被误伤：本人读自己、同校教师读本校学生必须 200。

注意两套角色：正常注册流程只写 `users.role`（→ `ActorContext.account_role`），
**不写** `user_roles` 表，因此 `ActorContext.roles`（RBAC）对注册用户恒为空。
归属校验的特权判断必须走 `account_role`，用 `roles` 会把所有教师都判成学生。

断言即门禁语义。实现阶段不得放宽断言、不得给路由加豁免名单。
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.audit_event import AuditEvent
from app.models.school import School
from app.models.task import Task
from app.models.training import TrainingSession
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login

OTHER_SCHOOL_NAME = "另一所测试学校"


def _auth(login_json: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {login_json['access_token']}"}


def _register_at_school(client, session_factory, *, school_name: str, role: str = "teacher"):
    """在指定学校注册并登录一个用户（helpers 里的那个写死了 E2E_SCHOOL_NAME）。"""

    async def _ensure_school() -> None:
        async with session_factory() as session:
            existing = await session.execute(select(School).where(School.name == school_name))
            if existing.scalar_one_or_none() is None:
                session.add(School(name=school_name))
                await session.commit()

    asyncio.run(_ensure_school())

    email = f"cross_school_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongPass123",
        "full_name": "跨校用户",
        "role": role,
        "school_name": school_name,
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    user_id = int(resp.json()["user_id"])

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass123"})
    assert login.status_code == 200, login.text
    return user_id, login.json()


def _deny_events(session_factory) -> list[AuditEvent]:
    async def _query():
        async with session_factory() as session:
            result = await session.execute(
                select(AuditEvent).where(AuditEvent.decision == "deny")
            )
            return list(result.scalars().all())

    return asyncio.run(_query())


def _insert_task(session_factory, *, user_id: int | None) -> int:
    async def _insert() -> int:
        async with session_factory() as session:
            task = Task(title="归属校验用任务", user_id=user_id, status="pending")
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return int(task.id)

    return asyncio.run(_insert())


def _insert_session(session_factory, *, user_id: int) -> str:
    session_id = str(uuid4())

    async def _insert() -> None:
        async with session_factory() as db:
            db.add(
                TrainingSession(
                    session_id=session_id,
                    project_id=str(uuid4()),
                    user_id=user_id,
                    status="active",
                )
            )
            await db.commit()

    asyncio.run(_insert())
    return session_id


@pytest.fixture()
def two_students(e2e_env):
    """同校两名学生 + 他们的教师。返回 (client, session_factory, ids, tokens)。"""
    client, session_factory = e2e_env
    teacher_id, _, teacher_login = register_and_login(client, email_prefix="own_teacher")
    student_a, _, login_a = register_and_login(
        client, email_prefix="own_student_a", role="student", teacher_id=teacher_id
    )
    student_b, _, login_b = register_and_login(
        client, email_prefix="own_student_b", role="student", teacher_id=teacher_id
    )
    return client, session_factory, {
        "teacher_id": teacher_id,
        "student_a": student_a,
        "student_b": student_b,
        "teacher_headers": _auth(teacher_login),
        "a_headers": _auth(login_a),
        "b_headers": _auth(login_b),
    }


# ───────────────────────── 跨学生读取 ─────────────────────────


@pytest.mark.parametrize(
    "path_template",
    [
        "/api/v1/students/{target}/profile",
        "/api/v1/students/{target}/weak-steps",
        "/api/v1/training/users/{target}/sessions",
    ],
)
def test_cross_student_read_returns_404(two_students, path_template):
    """学生 B 用自己的合法令牌读学生 A 的编号 —— 必须 404（当前为 200）。"""
    client, _, ctx = two_students
    resp = client.get(
        path_template.format(target=ctx["student_a"]), headers=ctx["b_headers"]
    )
    assert resp.status_code == 404, (
        f"{path_template} 允许了跨学生读取：{resp.status_code} {resp.text[:200]}"
    )


def test_student_can_read_own_data(two_students):
    """正向路径不得被误伤：本人读自己必须 200。"""
    client, _, ctx = two_students
    resp = client.get(
        f"/api/v1/students/{ctx['student_a']}/profile", headers=ctx["a_headers"]
    )
    assert resp.status_code == 200, resp.text


def test_same_school_teacher_can_read_student(two_students):
    """正向路径不得被误伤：同校教师读本校学生必须 200。

    注意必须用 `account_role` 判特权；用 RBAC 的 `actor.roles` 会让这条变红，
    因为注册流程不写 `user_roles`。
    """
    client, _, ctx = two_students
    resp = client.get(
        f"/api/v1/students/{ctx['student_a']}/profile", headers=ctx["teacher_headers"]
    )
    assert resp.status_code == 200, resp.text


# ───────────────────────── 跨校读取 ─────────────────────────


def test_cross_school_teacher_read_returns_404(two_students):
    """另一所学校的教师读本校学生 —— 必须 404。

    这条会逼出 `actor.school_name` 的第一个消费方：ADR-AUTHN D4 在 P3-2b 只加了
    载体，全仓使用点至今为 0，因此目前没有任何一处能证明跨校访问会被拒绝。
    """
    client, session_factory, ctx = two_students
    _, other_login = _register_at_school(
        client, session_factory, school_name=OTHER_SCHOOL_NAME, role="teacher"
    )
    resp = client.get(
        f"/api/v1/students/{ctx['student_a']}/profile", headers=_auth(other_login)
    )
    assert resp.status_code == 404, (
        f"跨校教师读到了本校学生画像：{resp.status_code} {resp.text[:200]}"
    )


# ───────────────────────── 任务链 ─────────────────────────


@pytest.mark.parametrize(
    "suffix", ["", "/report", "/events"],
)
def test_cross_user_task_read_returns_404(two_students, suffix):
    """学生 B 读学生 A 的任务 / 报告 / 事件 —— 必须 404。"""
    client, session_factory, ctx = two_students
    task_id = _insert_task(session_factory, user_id=ctx["student_a"])
    resp = client.get(f"/api/v1/tasks/{task_id}{suffix}", headers=ctx["b_headers"])
    assert resp.status_code == 404, (
        f"/tasks/{{id}}{suffix} 允许了跨用户读取：{resp.status_code} {resp.text[:200]}"
    )


def test_legacy_task_without_owner_is_denied(two_students):
    """`tasks.user_id` 存量为 NULL 的行：非管理员一律 404，不留豁免后门。

    该列当前 `nullable=True` 且无外键（收紧留给 P3-4 的合并迁移）。在收紧之前，
    无主任务必须按拒绝处理——否则"无主"就成了绕过归属校验的通道。
    """
    client, session_factory, ctx = two_students
    task_id = _insert_task(session_factory, user_id=None)
    resp = client.get(f"/api/v1/tasks/{task_id}", headers=ctx["b_headers"])
    assert resp.status_code == 404, resp.text


# ───────────────────────── 训练会话 ─────────────────────────


def test_cross_user_session_detail_returns_404(two_students):
    """学生 B 读学生 A 的会话详情 —— 必须 404。"""
    client, session_factory, ctx = two_students
    session_id = _insert_session(session_factory, user_id=ctx["student_a"])
    resp = client.get(
        f"/api/v1/training/sessions/{session_id}/detail", headers=ctx["b_headers"]
    )
    assert resp.status_code == 404, resp.text


def test_cross_user_feedback_read_is_denied_before_lookup(two_students):
    """跨用户读反馈必须走**归属拒绝**（带审计的 404），而不是"没找到"的 404。

    两者对外都是 404，靠审计事件区分：归属拒绝必须留下 deny 记录。
    """
    client, session_factory, ctx = two_students
    session_id = _insert_session(session_factory, user_id=ctx["student_a"])

    resp = client.get(
        f"/api/v1/training/feedback/{session_id}", headers=ctx["b_headers"]
    )
    assert resp.status_code == 404, resp.text

    denies = _deny_events(session_factory)
    assert denies, "跨用户读反馈返回了 404，但没有留下任何 deny 审计"


def test_feedback_role_query_param_cannot_grant_teacher_view(two_students):
    """`role=teacher` 是客户端可控的查询参数，不得用它拿到教师视角。

    与 AUTH-104 的伪造身份头同类：视角必须由令牌决定。学生带 `role=teacher`
    读自己的会话，效果必须与不带该参数一致（不得升级为教师反馈）。

    ⚠️ 诚实标注：本用例**当前是绿的，但绿得没有含金量**——该会话没有
    `TrainingSubmission`，端点在读 `role` 之前就先 404 了。它只作回归网，
    **不构成"role 参数已受控"的证据**。要真正验证需补一条带 submission 的
    用例，属后续批次。
    """
    client, session_factory, ctx = two_students
    session_id = _insert_session(session_factory, user_id=ctx["student_a"])

    escalated = client.get(
        f"/api/v1/training/feedback/{session_id}?role=teacher", headers=ctx["a_headers"]
    )
    assert escalated.status_code != 200 or escalated.json().get("role") != "teacher", (
        "学生通过 role 查询参数拿到了教师视角反馈"
    )


# ───────────────────────── 拒绝审计 ─────────────────────────


def test_denied_read_writes_audit_with_real_resource_id(two_students):
    """G1：任何拒绝都必须留带**真实资源编号**的审计，主体为令牌主体。"""
    client, session_factory, ctx = two_students

    resp = client.get(
        f"/api/v1/students/{ctx['student_a']}/profile", headers=ctx["b_headers"]
    )
    assert resp.status_code == 404

    denies = _deny_events(session_factory)
    assert denies, "越权读取返回了 404，但没有写 deny 审计"

    matched = [
        e for e in denies if e.resource_id == str(ctx["student_a"])
    ]
    assert matched, (
        "deny 审计里没有真实目标编号 "
        f"{ctx['student_a']}；实际记录：{[(e.resource_type, e.resource_id) for e in denies]}"
    )
    assert all(e.actor_user_id == str(ctx["student_b"]) for e in matched), (
        "deny 审计的操作者不等于令牌主体："
        f"{[e.actor_user_id for e in matched]} != {ctx['student_b']}"
    )


# ───────────────────────── 架构门禁 ─────────────────────────


def test_covered_routes_declare_actor_dependency():
    """本批覆盖的路由函数必须能拿到调用者身份——拿不到就不可能做归属校验。

    这是静态断言，防止以后新增/改写这些端点时把 `actor` 参数丢掉。
    """
    import ast
    import pathlib

    required = {
        "training.py": {
            "get_student_skill_profile",
            "get_student_weak_steps",
            "get_user_sessions",
            "get_session_detail",
            "get_training_feedback",
        },
        "tasks.py": {"get_task", "get_task_report", "get_task_events"},
    }

    endpoints = pathlib.Path(__file__).resolve().parents[2] / "app/api/v1/endpoints"
    missing: list[str] = []
    for filename, funcs in required.items():
        tree = ast.parse((endpoints / filename).read_text())
        found = {
            node.name: [a.arg for a in node.args.args + node.args.kwonlyargs]
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for func in sorted(funcs):
            assert func in found, f"{filename}::{func} 不存在（端点被改名？）"
            if "actor" not in found[func]:
                missing.append(f"{filename}::{func}")

    assert missing == [], f"这些端点拿不到调用者身份，无法做归属校验：{missing}"
