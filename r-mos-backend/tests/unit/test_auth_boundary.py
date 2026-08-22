"""
T-03-a API auth boundary tests.

AUTH-GATE：默认拒绝 + 显式公开白名单。

与 2026-08-21 之前的实现相反——旧版 `_collect_protected_endpoints` 会**跳过**
没有认证依赖的路由，因此漏加认证的接口永远进不了测试矩阵（AUTH-102），
这也解释了为什么全量测试通过与 AUTH-101 可以同时成立。

现在的收集器改为：`/api/v1` 下凡不在 `PUBLIC_ROUTES` 白名单里的路由，
一律进入矩阵并断言无令牌返回 401。
"""
from __future__ import annotations

import asyncio
import re
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.core.public_routes import PUBLIC_ROUTES
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.user import User
from app.services.authz_guard import get_current_actor
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


def _has_auth_dependency(dependant) -> bool:
    if dependant.call == get_current_actor:
        return True
    return any(_has_auth_dependency(child) for child in dependant.dependencies)


_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_PATH_PARAM = re.compile(r"\{[^}]+\}")


def _sample_path(path: str) -> str:
    """把路由模板里的所有路径参数替换成一个通用样例值。

    只需让请求命中路由即可——认证网关在路径参数校验之前执行，
    因此不必为每种参数准备语义正确的样例。
    """
    return _PATH_PARAM.sub("1", path)


def _collect_must_auth_endpoints() -> list[tuple[str, str]]:
    """`/api/v1` 下所有不在公开白名单里的路由，一律必须认证。

    注意收集条件里**没有**"是否已声明认证依赖"这一项：漏加认证正是要发现的
    缺陷，按依赖存在与否过滤会让缺陷自动逃逸（AUTH-102）。
    """
    endpoints: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1"):
            continue

        for method in sorted(m for m in route.methods if m in _HTTP_METHODS):
            if (method, route.path) in PUBLIC_ROUTES:
                continue
            endpoints.append((method, route.path))

    return sorted(endpoints, key=lambda item: (item[0], item[1]))


MUST_AUTH_ENDPOINTS = _collect_must_auth_endpoints()


@pytest.fixture(scope="module")
def auth_boundary_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=TEST_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Auth Boundary",
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _grant_role_permissions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> None:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        role_result = await session.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} role")
            session.add(role)
            await session.flush()

        for permission_key in permission_keys:
            permission_result = await session.execute(
                select(Permission).where(Permission.key == permission_key)
            )
            permission = permission_result.scalar_one_or_none()
            if permission is None:
                resource_type, action = permission_key.split(":", 1)
                permission = Permission(
                    key=permission_key,
                    description=f"{permission_key} permission",
                    resource_type=resource_type,
                    action=action,
                )
                session.add(permission)
                await session.flush()

            role_permission_result = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission_result.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        user_role_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if user_role_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()


@pytest.mark.parametrize(("method", "path"), MUST_AUTH_ENDPOINTS)
def test_non_public_endpoints_reject_anonymous(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    method: str,
    path: str,
) -> None:
    """AUTH-GATE：匿名访问非白名单路由允许次数为 0。"""
    client, _ = auth_boundary_env
    kwargs = {"json": {}} if method in {"POST", "PUT", "PATCH"} else {}
    response = client.request(method, _sample_path(path), **kwargs)
    assert response.status_code == 401, (
        f"Expected 401 without token, got {response.status_code} for {method} {path}: {response.text[:200]}"
    )


def test_collector_covers_routes_without_auth_dependency() -> None:
    """AUTH-102 回归：没有声明认证依赖的路由必须进入矩阵。

    `POST /api/v1/tasks` 在改造前没有任何认证依赖，旧收集器会跳过它，
    使 AUTH-101 的 P0 缺口对测试完全不可见。
    """
    assert ("POST", "/api/v1/tasks") in MUST_AUTH_ENDPOINTS

    no_dep = [
        (method, path)
        for method, path in MUST_AUTH_ENDPOINTS
        if not any(
            _has_auth_dependency(route.dependant)
            for route in app.routes
            if isinstance(route, APIRoute) and route.path == path and method in route.methods
        )
    ]
    # 这些路由自身没声明认证依赖，只能靠网关兜底——正是本文件要守住的那条线。
    assert MUST_AUTH_ENDPOINTS, "必须认证的路由集合不应为空"
    print(f"\n[AUTH-GATE] 必须认证路由 {len(MUST_AUTH_ENDPOINTS)} 条，其中自身无认证依赖 {len(no_dep)} 条")


def test_whitelist_has_no_dead_entries() -> None:
    """白名单里不得有指向不存在路由的条目。

    路由改名或下线后留下的死条目会静默扩大攻击面。
    """
    real: set[tuple[str, str]] = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method in _HTTP_METHODS
    }
    dead = sorted(entry for entry in PUBLIC_ROUTES if entry not in real)
    assert not dead, f"公开白名单存在死条目（对应路由不存在）：{dead}"


def test_public_routes_reachable_without_token(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """白名单必须真的生效，且带路径参数的模板也能正确匹配。"""
    client, _ = auth_boundary_env

    assert client.get("/api/v1/health").status_code == 200

    # 带 {school_name} 占位符——验证白名单按路由模板匹配而非按具体路径
    resp = client.get(f"/api/v1/schools/{TEST_SCHOOL_NAME}/teachers")
    assert resp.status_code == 200, resp.text


def test_student_token_cannot_update_admin_role(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_boundary_env
    email = f"student_boundary_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)

    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="student",
            permission_keys=["agent:read"],
        )
    )

    response = client.post(
        "/api/v1/admin/users/1/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "teacher"},
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error_type"] in {"RoleRequiredError", "PermissionDeniedError"}


def test_removed_legacy_ai_endpoints_return_404(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = auth_boundary_env
    email = f"deprecated_boundary_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    command_resp = client.post(
        "/api/v1/ai/commands",
        headers=headers,
        json={
            "intent": "get_robot_structure",
            "skill_id": "robot.read.structure",
            "tool_name": "robot.get_structure",
            "tool_args": {"robot_id": "R-001"},
            "side_effects": [],
        },
    )
    assert command_resp.status_code == 404

    rag_resp = client.post(
        "/api/v1/ai/rag/query",
        headers=headers,
        json={"input_text": "电机异常如何排查", "tool_args": {"query": "电机异常"}},
    )
    assert rag_resp.status_code == 404
