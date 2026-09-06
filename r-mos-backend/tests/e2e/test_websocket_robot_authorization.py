"""M-03：带 robot_id 的 WebSocket 订阅授权边界。"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.models.user import User
from tests.e2e.helpers import register_and_login


async def _seed_robot(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_teacher_id: int,
    visibility: RobotVisibility,
) -> int:
    async with session_factory() as session:
        robot = RobotModel(
            brand="M03",
            model_name=f"ws-{visibility.value}",
            owner_teacher_id=owner_teacher_id,
            visibility=visibility,
            status=RobotStatus.READY,
        )
        session.add(robot)
        await session.commit()
        await session.refresh(robot)
        return robot.id


async def _set_user_school(
    session_factory: async_sessionmaker[AsyncSession], user_id: int, school_name: str
) -> None:
    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        user.school_name = school_name
        await session.commit()


def _robot_ws_path(robot_id: int, token: str) -> str:
    return f"/ws/robot/{robot_id}/status?token={token}"


@pytest.mark.regression
def test_unbound_user_cannot_subscribe_to_private_robot(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """缺失 robot_id 可见性校验时，此连接会被错误接纳。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(client, email_prefix="ws_robot_owner")
    _, _, other_login = register_and_login(client, email_prefix="ws_robot_other")
    robot_id = asyncio.run(
        _seed_robot(
            session_factory,
            owner_teacher_id=owner_id,
            visibility=RobotVisibility.PRIVATE,
        )
    )

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            _robot_ws_path(robot_id, other_login["access_token"])
        ):
            pass

    assert exc_info.value.code == 1008
    assert exc_info.value.reason == "robot_forbidden"


@pytest.mark.regression
def test_owner_can_subscribe_to_private_robot(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """授权不能退化成对带 robot_id 路由一律拒绝。"""
    client, session_factory = e2e_env
    owner_id, _, owner_login = register_and_login(client, email_prefix="ws_robot_owner")
    robot_id = asyncio.run(
        _seed_robot(
            session_factory,
            owner_teacher_id=owner_id,
            visibility=RobotVisibility.PRIVATE,
        )
    )

    with client.websocket_connect(
        _robot_ws_path(robot_id, owner_login["access_token"])
    ) as websocket:
        message = websocket.receive_json()

    assert message["type"] == "telemetry"


@pytest.mark.regression
def test_same_school_user_can_subscribe_to_shared_robot(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """SHARED 规则必须与 HTTP 机器人可见性保持一致。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(client, email_prefix="ws_shared_owner")
    _, _, other_login = register_and_login(client, email_prefix="ws_shared_other")
    robot_id = asyncio.run(
        _seed_robot(
            session_factory,
            owner_teacher_id=owner_id,
            visibility=RobotVisibility.SHARED,
        )
    )

    with client.websocket_connect(
        _robot_ws_path(robot_id, other_login["access_token"])
    ) as websocket:
        message = websocket.receive_json()

    assert message["type"] == "telemetry"


@pytest.mark.regression
def test_cross_school_user_cannot_subscribe_to_shared_robot(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """SHARED 的学校边界必须由 HTTP 与 WebSocket 的唯一实现共同执行。"""
    client, session_factory = e2e_env
    owner_id, _, _ = register_and_login(client, email_prefix="ws_shared_owner")
    foreign_id, _, foreign_login = register_and_login(
        client, email_prefix="ws_shared_foreign"
    )
    asyncio.run(_set_user_school(session_factory, foreign_id, "WebSocket 外校"))
    robot_id = asyncio.run(
        _seed_robot(
            session_factory,
            owner_teacher_id=owner_id,
            visibility=RobotVisibility.SHARED,
        )
    )

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            _robot_ws_path(robot_id, foreign_login["access_token"])
        ):
            pass

    assert exc_info.value.code == 1008
    assert exc_info.value.reason == "robot_forbidden"
