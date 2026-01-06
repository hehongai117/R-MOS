"""
WebSocket端点（V2.2完整版）
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

from app.services.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/robot/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点：实时机器人状态推送（V2.2完整实现）
    
    ⚠️ 强制约束：
    - 路径必须为 /ws/robot/status
    - 推送频率：5Hz（200ms间隔）
    - 消息格式：TelemetryMessage（见schemas.py）
    
    连接流程：
    1. 客户端连接到 ws://host:port/ws/robot/status
    2. 服务器自动开始推送遥测数据
    3. 客户端解析JSON消息
    4. 断开连接时自动清理
    """
    await manager.connect(websocket)
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
