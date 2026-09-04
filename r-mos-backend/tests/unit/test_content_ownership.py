"""教学内容的对象级归属回归测试（审计 M-01 / 董事会裁定 §9-2）。

背景：`sops`、`fault_cases`、`robot_sop_drafts`、`external_assessments`、
`assessment_providers` 五张表此前**无任何创建者字段**，写路径因此只能做角色制
过渡——任意教师可改任意教学内容。裁定 §9-2 补齐 `created_by_user_id` 后，
这些端点改为对象级校验，本文件即该语义的行为级证据。

**这些端点此前几乎没有 HTTP 层测试**（`sops/{id}` 删除、`fault-cases/`、
`assessments/` 三组均为零覆盖），所以换守卫时「零测试失败」不是安全信号，
而是空白信号——与 tasks 那批同因（§5）。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保模型注册完整
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from app.models.sop import SOP
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login, set_user_role


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


def _seed_sop(sf: async_sessionmaker, owner_id: int | None) -> int:
    """直接建库存 SOP，可指定归属或留 NULL（系统内置内容）。"""

    async def _run() -> int:
        async with sf() as session:
            sop = SOP(
                name="归属测试 SOP",
                description="fixture",
                applicable_model="ATOM-01",
                created_by_user_id=owner_id,
            )
            session.add(sop)
            await session.commit()
            return sop.id

    return asyncio.run(_run())


@pytest.mark.regression
def test_sop_delete_rejects_non_author_teacher():
    """核心语义变化：同为教师，**非作者不得删除他人的 SOP**。

    换守卫前 `ensure_role_for_write(..., "teacher", "admin")` 会放行任意教师；
    这条用例正是新旧语义的分界——旧口径下它必然失败。
    """
    client, sf = _client()
    try:
        author_id, _, _ = register_and_login(client, email_prefix="sop_author")
        sop_id = _seed_sop(sf, author_id)

        register_and_login(client, email_prefix="sop_other_teacher")  # 另一位教师
        resp = client.delete(f"/api/v1/sops/{sop_id}")
        assert resp.status_code == 403, f"他人 SOP 被非作者教师删除: {resp.status_code} {resp.text}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_sop_delete_allowed_for_author():
    """作者本人可删——否则守卫写成无条件拒绝也能让上一条全绿。"""
    client, sf = _client()
    try:
        author_id, _, _ = register_and_login(client, email_prefix="sop_author_self")
        sop_id = _seed_sop(sf, author_id)

        resp = client.delete(f"/api/v1/sops/{sop_id}")
        assert resp.status_code != 403, f"作者删除自己的 SOP 被拒: {resp.status_code} {resp.text}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_unowned_sop_is_admin_only():
    """历史行（`created_by_user_id IS NULL`）＝系统内置内容，仅管理员可改。

    这是裁定 §9-2 对历史数据的处置：不回填、不编造归属，NULL 即「无主」。
    """
    client, sf = _client()
    try:
        sop_id = _seed_sop(sf, None)  # 无主，模拟迁移前的历史行

        register_and_login(client, email_prefix="unowned_teacher")
        denied = client.delete(f"/api/v1/sops/{sop_id}")
        assert denied.status_code == 403, f"无主 SOP 被普通教师删除: {denied.status_code}"

        admin_id, _, admin_login = register_and_login(client, email_prefix="unowned_admin")
        asyncio.run(set_user_role(sf, user_id=admin_id, role="admin"))
        client.headers["Authorization"] = f"Bearer {admin_login['access_token']}"
        allowed = client.delete(f"/api/v1/sops/{sop_id}")
        assert allowed.status_code != 403, f"管理员无法处置无主 SOP: {allowed.status_code} {allowed.text}"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.regression
def test_sop_delete_guard_actually_runs():
    """`DELETE /sops/{id}` 的守卫此前**写在 docstring 里**，从不执行。

    源码文本能搜到守卫名、AST 的函数体里却没有该调用，故关键字扫描无法发现——
    任何登录用户当时都可删除任意 SOP。这条断言的是守卫真的在执行路径上。
    """
    import ast
    import inspect

    from app.api.v1.endpoints import sops as sops_module

    src = inspect.getsource(sops_module.delete_sop)
    tree = ast.parse(src.strip())
    fn = tree.body[0]
    called = {
        getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        for node in ast.walk(fn)
        if isinstance(node, ast.Call)
    }
    assert "ensure_write_owner" in called, (
        f"delete_sop 的函数体内没有守卫调用（可能又落进 docstring 了）: {sorted(c for c in called if c)}"
    )
