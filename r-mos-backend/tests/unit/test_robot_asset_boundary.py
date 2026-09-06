"""AUTH-103：机器人资产的认证与归属边界。

Phase 1 记录：`robots.py` 的工具、资产清单与任意资产路径下载均无认证、所有权或
状态校验，注释以"浏览器加载器不能附加令牌"为由把全部 GLB/JSON 归为非敏感。

本文件锁定新规格。一个决定性的数据事实：`RobotVisibility` 只有 `PRIVATE` 与
`SHARED` 两档（`app/models/robot_model.py:8-11`），**没有面向匿名的公开档**——
`SHARED` 的语义是"对同校已认证用户可见"，不是"对互联网公开"。因此资产不存在
合法的匿名读取场景，一律要求认证，并沿用统一的机器人可见性规则。

越权读取对外返回 404（验收章程 G1 + 单校五机验收矩阵对 AUTH-103 的复验口径），
不返回 403——403 会泄漏"该机器人存在"。

对应门禁 `AUTH-GATE-09`、`AUTH-GATE-10`。
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.robot_model import (
    RobotModel,
    RobotStatus,
    RobotVisibility,
    TeacherRobotBinding,
)
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login

ASSET_ROUTES = (
    "/api/v1/robots/{robot_id}/tools",
    "/api/v1/robots/{robot_id}/assets",
    "/api/v1/robots/{robot_id}/assets/manifests/assembly_manifest.json",
)


def _build_client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory
    return TestClient(app), session_factory


async def _seed_robot(
    session_factory: async_sessionmaker,
    *,
    owner_teacher_id: int,
    visibility: RobotVisibility,
    status: RobotStatus,
    bind_teacher_id: int | None = None,
) -> int:
    async with session_factory() as session:
        robot = RobotModel(
            brand="AUTH103",
            model_name=f"boundary-{visibility.value}-{status.value}",
            owner_teacher_id=owner_teacher_id,
            visibility=visibility,
            status=status,
        )
        session.add(robot)
        await session.flush()
        if bind_teacher_id is not None:
            session.add(
                TeacherRobotBinding(
                    teacher_id=bind_teacher_id, robot_model_id=robot.id
                )
            )
        await session.commit()
        return robot.id


@pytest.fixture()
def asset_env():
    client, session_factory = _build_client()
    try:
        owner_id, _, owner_login = register_and_login(client, email_prefix="asset_owner_teacher")
        other_id, _, other_login = register_and_login(client, email_prefix="asset_other_teacher")

        private_robot = asyncio.run(
            _seed_robot(
                session_factory,
                owner_teacher_id=owner_id,
                visibility=RobotVisibility.PRIVATE,
                status=RobotStatus.DRAFT,
                bind_teacher_id=owner_id,
            )
        )
        shared_robot = asyncio.run(
            _seed_robot(
                session_factory,
                owner_teacher_id=owner_id,
                visibility=RobotVisibility.SHARED,
                status=RobotStatus.READY,
                bind_teacher_id=owner_id,
            )
        )
        yield {
            "client": client,
            "owner_token": owner_login["access_token"],
            "other_token": other_login["access_token"],
            "private_robot": private_robot,
            "shared_robot": shared_robot,
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def _act_as(client: TestClient, token: str | None) -> None:
    if token is None:
        client.headers.pop("Authorization", None)
    else:
        client.headers["Authorization"] = f"Bearer {token}"


@pytest.mark.parametrize("route", ASSET_ROUTES)
def test_anonymous_cannot_touch_robot_assets(asset_env, route: str) -> None:
    """AUTH-GATE-09：匿名访问任何资产入口都必须 401。

    含 `SHARED` 机器人——SHARED 是"对同校已认证用户可见"，不是对匿名公开。
    """
    client = asset_env["client"]
    _act_as(client, None)
    for robot_id in (asset_env["private_robot"], asset_env["shared_robot"]):
        resp = client.get(route.format(robot_id=robot_id))
        assert resp.status_code == 401, f"{route} robot={robot_id}: {resp.status_code}"


@pytest.mark.parametrize("route", ASSET_ROUTES)
def test_unbound_teacher_gets_404_on_private_robot_assets(asset_env, route: str) -> None:
    """AUTH-GATE-09：其他教师访问私有机器人资产 → 404（不是 403，避免泄漏存在性）。"""
    client = asset_env["client"]
    _act_as(client, asset_env["other_token"])

    resp = client.get(route.format(robot_id=asset_env["private_robot"]))
    assert resp.status_code == 404, f"{route}: {resp.status_code} {resp.text[:160]}"


@pytest.mark.parametrize("route", ASSET_ROUTES)
def test_nonexistent_robot_assets_return_404(asset_env, route: str) -> None:
    """不存在的机器人与无权机器人对外表现一致，均为 404。"""
    client = asset_env["client"]
    _act_as(client, asset_env["owner_token"])

    resp = client.get(route.format(robot_id=999999))
    assert resp.status_code == 404


def test_bound_teacher_can_list_own_robot_assets(asset_env) -> None:
    """正向边界：绑定教师能列出自己机器人的资产，收紧不得误伤正常路径。"""
    client = asset_env["client"]
    _act_as(client, asset_env["owner_token"])

    resp = client.get(f"/api/v1/robots/{asset_env['private_robot']}/assets")
    assert resp.status_code == 200, resp.text
    assert "items" in resp.json()


def test_same_school_user_can_list_shared_robot_assets(asset_env) -> None:
    """正向边界：SHARED 机器人对同校已认证用户可见。"""
    client = asset_env["client"]
    _act_as(client, asset_env["other_token"])

    resp = client.get(f"/api/v1/robots/{asset_env['shared_robot']}/assets")
    assert resp.status_code == 200, resp.text
