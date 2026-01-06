"""
WebSocket连接管理器（V2.2新增）
"""
import asyncio
import logging
from typing import List, Optional
from fastapi import WebSocket
from datetime import datetime

from app.adapters.factory import AdapterFactory
from app.adapters.schemas import TelemetryMessage, TelemetryPayload

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器
    
    职责：
    - 管理所有WebSocket连接
    - 后台任务推送遥测数据（5Hz）
    - 处理连接断开
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._push_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
        
        # 如果是第一个连接，启动推送任务
        if len(self.active_connections) == 1:
            self._push_task = asyncio.create_task(self._push_telemetry())
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")
        
        # 如果没有连接了，停止推送任务
        if len(self.active_connections) == 0 and self._push_task:
            self._push_task.cancel()
    
    async def _push_telemetry(self):
        """后台任务：5Hz推送遥测数据（V2.2核心实现）"""
        while True:
            try:
                # 从Adapter获取数据
                adapter = await AdapterFactory.get_adapter()
                
                joints = await adapter.get_joint_states()
                sensors = await adapter.get_sensor_data()
                active_faults = await adapter.get_active_faults()
                
                # 构造TelemetryMessage
                message = TelemetryMessage(
                    type="telemetry",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    payload=TelemetryPayload(
                        joints=joints,
                        sensors=sensors,
                        active_faults=active_faults
                    )
                )
                
                # 序列化为JSON
                message_json = message.model_dump_json()
                
                # 发送给所有连接
                disconnected = []
                for connection in self.active_connections:
                    try:
                        await connection.send_text(message_json)
                    except Exception as e:
                        logger.error(f"发送消息失败: {e}")
                        disconnected.append(connection)
                
                # 移除断开的连接
                for conn in disconnected:
                    self.disconnect(conn)
                
                # 5Hz = 200ms间隔
                await asyncio.sleep(0.2)
                
            except asyncio.CancelledError:
                logger.info("推送任务已取消")
                break
            except Exception as e:
                logger.error(f"推送任务异常: {e}")
                await asyncio.sleep(1.0)  # 出错后等待1秒重试


# 全局单例
manager = ConnectionManager()
