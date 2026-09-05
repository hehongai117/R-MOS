"""M-13：角色事实源收口与职责分离（S3-01 试点模块 A 第二批）。

两个缺陷合为一个问题编号：

1. **职责分离失效**——`auditor` 可以批准／拒绝审批。审计者同时是执行者，
   意味着「谁来监督监督者」无解；这也是 RBAC 里 auditor 被授予
   `approvals:grant`／`reject` 被 A4 判为高危的原因。
2. **角色事实源多处**——`approvals.py` 与 `ai_commands.py` 直接读 `actor.roles`，
   绕过了 `actor_has_role()` 这个唯一入口。该入口同时认 `account_role`
   （注册写入，正常用户唯一有值的来源）与 `roles`（仅种子脚本写）。
   绕过的后果在历史上已实测过：正常注册的教师/管理员被一律拒绝。

本文件断言的是**行为**：拿 auditor 令牌打真实 HTTP 端点，看读放行、写被拒。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.approval import Approval
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.user import User
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login


def _client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init())
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with sf() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.state.test_sessionmaker = sf
    return TestClient(app), sf


def _grant_auditor(sf: async_sessionmaker, *, user_id: int) -> None:
    """按种子脚本的口径把用户授为 auditor（RBAC 侧），并给足审批权限键。

    刻意把 `approvals:grant`／`reject` 也授予——本用例要证明的是
    **即使持有权限键，auditor 也不得批准**，职责分离不能只靠权限键表达。
    """

    async def _run() -> None:
        async with sf() as session:
            role = Role(name="auditor", description="审计员")
            session.add(role)
            await session.flush()
            for key in ("audit_events:read", "approvals:read", "approvals:grant", "approvals:reject"):
                perm = Permission(key=key, description=key, resource_type=key.split(":")[0], action=key.split(":")[1])
                session.add(perm)
                await session.flush()
                session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            session.add(UserRole(user_id=user_id, role_id=role.id))
            await session.commit()

    asyncio.run(_run())



def _grant_permission_only(sf: async_sessionmaker, *, user_id: int, keys: tuple[str, ...]) -> None:
    """只授权限键，角色名用中性名——本用例要测的是 `account_role` 这条来源被认，
    因此不能借 RBAC 的 `roles` 把 admin 也塞进去，否则测不出区别。"""

    async def _run() -> None:
        async with sf() as session:
            role = Role(name="perm_carrier", description="仅承载权限键")
            session.add(role)
            await session.flush()
            for key in keys:
                perm = Permission(
                    key=key, description=key,
                    resource_type=key.split(":")[0], action=key.split(":")[1],
                )
                session.add(perm)
                await session.flush()
                session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            session.add(UserRole(user_id=user_id, role_id=role.id))
            await session.commit()

    asyncio.run(_run())


def _seed_approval(sf: async_sessionmaker, *, requester_id: int) -> int:
    async def _run() -> int:
        async with sf() as session:
            approval = Approval(
                trace_id="m13-trace-001",
                command_id=1,
                tool_call_id=1,
                status="pending",
                reason="awaiting_approval",
                created_by_user_id=requester_id,
            )
            session.add(approval)
            await session.commit()
            return approval.id

    return asyncio.run(_run())


@pytest.mark.regression
def test_auditor_cannot_grant_or_reject_approval():
    """职责分离：审计员**不得**批准或拒绝审批，即便持有对应权限键。"""
    client, sf = _client()
    try:
        requester_id, _, _ = register_and_login(client, email_prefix="m13_requester")
        approval_id = _seed_approval(sf, requester_id=requester_id)

        auditor_id, _, _ = register_and_login(client, email_prefix="m13_auditor")
        _grant_auditor(sf, user_id=auditor_id)

        grant = client.post(f"/api/v1/ai/approvals/{approval_id}/grant", json={"reason": "x"})
        reject = client.post(f"/api/v1/ai/approvals/{approval_id}/reject", json={"reason": "x"})

        # 修复前此处返回 409（业务层报「关联命令不存在」）——**授权层已经放行**，
        # 只是卡在数据完整性上。非 403 即为职责分离失效的证据。
        assert grant.status_code == 403, f"审计员批准了审批: {grant.status_code} {grant.text}"
        assert reject.status_code == 403, f"审计员拒绝了审批: {reject.status_code} {reject.text}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_auditor_can_still_read_approvals():
    """审计员**仍可读**审批——职责分离限制的是决策权，不是知情权。

    没有这条，把守卫收紧成「只有 admin 能碰审批」也会让上一条全绿，
    但那样审计员就无法履行审计职责了。
    """
    client, sf = _client()
    try:
        requester_id, _, _ = register_and_login(client, email_prefix="m13_read_requester")
        approval_id = _seed_approval(sf, requester_id=requester_id)

        auditor_id, _, _ = register_and_login(client, email_prefix="m13_read_auditor")
        _grant_auditor(sf, user_id=auditor_id)

        listing = client.get("/api/v1/ai/approvals")
        detail = client.get(f"/api/v1/ai/approvals/{approval_id}")

        assert listing.status_code == 200, f"审计员无法列出审批: {listing.status_code} {listing.text}"
        assert detail.status_code == 200, f"审计员无法查看审批详情: {detail.status_code} {detail.text}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_admin_by_account_role_can_grant():
    """角色事实源收口：`account_role` 为 admin 的用户必须能批准。

    原实现只查 `actor.roles`（仅种子脚本写），正常注册的管理员 `roles` 为空集，
    会被一律拒绝——`actor_has_role()` 的文档记载过这个历史事故。
    """
    from tests.e2e.helpers import set_user_role

    client, sf = _client()
    try:
        requester_id, _, _ = register_and_login(client, email_prefix="m13_admin_requester")
        approval_id = _seed_approval(sf, requester_id=requester_id)

        admin_id, _, admin_login = register_and_login(client, email_prefix="m13_admin")
        # 只设 account_role，**不授 RBAC 角色**——本条专门验证 account_role 这条来源被认。
        asyncio.run(set_user_role(sf, user_id=admin_id, role="admin"))
        # 权限键单独授予：路由级 require_permission 是另一道门，与角色来源无关。
        # 若不授，本条会被权限键那道门拦下，测不到角色判定（见 §模块说明的新发现）。
        _grant_permission_only(sf, user_id=admin_id, keys=("approvals:grant",))
        client.headers["Authorization"] = f"Bearer {admin_login['access_token']}"

        resp = client.post(f"/api/v1/ai/approvals/{approval_id}/grant", json={"reason": "ok"})
        assert resp.status_code != 403, (
            f"account_role=admin 的管理员被拒绝批准: {resp.status_code} {resp.text}"
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
