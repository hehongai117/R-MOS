"""
WebSocket端点（V2.2完整版）
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

from app.services.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)


async def _handle_websocket(websocket: WebSocket, robot_id: int | None = None):
    """WebSocket处理函数：实时机器人状态推送（V2.2完整实现）

    连接流程：
    1. 客户端连接到 ws://host:port/ws/robot/status 或 /ws/robot/{id}/status
    2. 服务器自动开始推送遥测数据
    3. 客户端解析JSON消息
    4. 断开连接时自动清理

    robot_id: MVP阶段接收但暂不用于数据过滤，为未来多机器人支持预留
    """
    await manager.connect(websocket)
    if robot_id is not None:
        logger.info(f"WebSocket客户端连接，robot_id={robot_id}")
    try:
        while True:
            # 等待客户端消息（心跳或关闭）
            data = await websocket.receive_text()
            logger.debug(f"收到WebSocket消息: {data}")

            # MVP阶段不处理客户端消息，仅接收
            # 生产版本可处理心跳、订阅控制等

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket客户端主动断开")
    except Exception as e:
        logger.error(f"WebSocket异常: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/robot/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点：实时机器人状态推送（向后兼容路由）

    ⚠️ 保留此路由以向后兼容。新客户端推荐使用 /ws/robot/{robot_id}/status
    """
    await _handle_websocket(websocket)


@router.websocket("/ws/robot/{robot_id}/status")
async def websocket_endpoint_with_robot(websocket: WebSocket, robot_id: int):
    """WebSocket端点：带 robot_id 的实时机器人状态推送

    路径参数：
    - robot_id: 机器人ID（MVP阶段接收但暂不用于数据过滤）
    """
    await _handle_websocket(websocket, robot_id=robot_id)
