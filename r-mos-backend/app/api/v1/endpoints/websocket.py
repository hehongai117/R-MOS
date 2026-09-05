"""
WebSocket端点（V2.2完整版）
"""
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthenticationRequiredError
from app.services.authz_guard import ActorContext, resolve_actor_from_token
from app.services.robot.visibility import get_visible_robot_or_404
from app.services.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)

# RFC 6455 定义的关闭码；1008 = Policy Violation，用于认证失败。
WS_CLOSE_POLICY_VIOLATION = 1008


def _extract_token(websocket: WebSocket, token: str | None) -> str | None:
    """按优先级取令牌：查询参数 > Authorization 头 > Sec-WebSocket-Protocol。

    审计 M-03：浏览器原生 `WebSocket` 构造器**无法自定义请求头**，
    因此查询参数是前端唯一可用的通道；同时保留头部方式供服务端到服务端调用。
    """
    if token:
        return token
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    # 部分客户端把令牌塞在子协议里，形如 "bearer, <token>"
    protocol = websocket.headers.get("sec-websocket-protocol")
    if protocol and "," in protocol:
        head, _, tail = protocol.partition(",")
        if head.strip().lower() == "bearer":
            return tail.strip() or None
    return None


async def _authenticate(websocket: WebSocket, token: str | None) -> ActorContext | None:
    """在 `accept()` **之前**完成认证；失败则直接关闭连接。

    审计 M-03：此前两个 WS 端点零认证，匿名即可接收全量遥测。
    认证必须发生在握手完成之前——先 `accept()` 再校验等于「先接纳、后驱逐」，
    期间已可收到推送。
    """
    raw = _extract_token(websocket, token)
    # WebSocket 不经过 FastAPI 的依赖注入，拿不到被 `dependency_overrides`
    # 替换的 `get_db`。沿用测试基建既有的 `app.state.test_sessionmaker` 约定，
    # 使 WS 在测试环境连到同一个内存库；生产路径不受影响。
    session_factory = (
        getattr(websocket.app.state, "test_sessionmaker", None) or AsyncSessionLocal
    )
    try:
        async with session_factory() as db:
            return await resolve_actor_from_token(db, raw)
    except AuthenticationRequiredError as exc:
        logger.warning(f"WebSocket 认证失败，拒绝握手: {exc}")
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION, reason="unauthenticated")
        return None
    except Exception as exc:  # 认证过程异常同样不得放行
        logger.error(f"WebSocket 认证异常，拒绝握手: {exc}")
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION, reason="unauthenticated")
        return None


async def _authorize_robot_subscription(
    websocket: WebSocket,
    robot_id: int,
    actor: ActorContext,
) -> bool:
    """在握手前复用 HTTP 机器人可见性规则校验订阅权限。"""
    session_factory = getattr(websocket.app.state, "test_sessionmaker", None) or AsyncSessionLocal
    try:
        async with session_factory() as db:
            await get_visible_robot_or_404(db, robot_id, actor)
    except HTTPException as exc:
        logger.warning(
            "WebSocket 机器人订阅被拒绝 user_id=%s robot_id=%s: %s",
            actor.user_id,
            robot_id,
            exc.detail,
        )
        await websocket.close(
            code=WS_CLOSE_POLICY_VIOLATION,
            reason="robot_forbidden",
        )
        return False
    except Exception as exc:  # 授权过程异常必须安全拒绝，不能进入连接表
        logger.error(
            "WebSocket 机器人订阅校验异常 user_id=%s robot_id=%s: %s",
            actor.user_id,
            robot_id,
            exc,
        )
        await websocket.close(
            code=WS_CLOSE_POLICY_VIOLATION,
            reason="robot_forbidden",
        )
        return False
    return True


async def _handle_websocket(
    websocket: WebSocket,
    token: str | None = None,
    robot_id: int | None = None,
):
    """WebSocket处理函数：实时机器人状态推送

    连接流程：
    1. **认证**（握手前）——失败以 1008 关闭
    2. 接受连接并登记调用者身份
    3. 服务器推送遥测数据
    4. 断开时自动清理
    """
    actor = await _authenticate(websocket, token)
    if actor is None:
        return
    if robot_id is not None and not await _authorize_robot_subscription(
        websocket, robot_id, actor
    ):
        return

    # 身份随连接登记，使 send_to_user / broadcast_to_channel 的定向过滤生效
    # （审计 F-RT-03：此前连接不带身份，定向消息无接收者）。
    await manager.connect(
        websocket,
        user_id=actor.user_id,
        channels={f"user:{actor.user_id}"},
    )
    logger.info(
        f"WebSocket客户端连接 user_id={actor.user_id}"
        + (f" robot_id={robot_id}" if robot_id is not None else "")
    )
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"收到WebSocket消息: {data}")

            # 审计 F-RT-01：此前收到消息后直接丢弃，导致 handle_client_message
            # 零调用者 → last_pong 永不更新 → 健康连接约 90 秒起被跳过遥测、
            # 约 150 秒被强制关闭。
            await manager.handle_client_message(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket客户端主动断开 user_id={actor.user_id}")
    except Exception as e:
        logger.error(f"WebSocket异常: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/robot/status")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(default=None)):
    """WebSocket端点：实时机器人状态推送（向后兼容路由）

    ⚠️ 保留此路由以向后兼容。新客户端推荐使用 /ws/robot/{robot_id}/status
    """
    await _handle_websocket(websocket, token=token)


@router.websocket("/ws/robot/{robot_id}/status")
async def websocket_endpoint_with_robot(
    websocket: WebSocket,
    robot_id: int,
    token: str | None = Query(default=None),
):
    """WebSocket端点：带 robot_id 的实时机器人状态推送

    路径参数：
    - robot_id: 机器人ID

    已在握手前按 admin / SHARED / owner / 教师绑定规则校验订阅权限。

    ⚠️ **`robot_id` 仍不用于遥测数据过滤**：
    当前只有一个全局 adapter，产生的是唯一一份遥测，并不存在多台机器人各自的
    数据源可供过滤。按机器人分发遥测需要多 adapter 实例与订阅分发，超出本端点
    当前的授权边界。
    """
    await _handle_websocket(websocket, token=token, robot_id=robot_id)
