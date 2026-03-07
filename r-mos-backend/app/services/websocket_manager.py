"""
WebSocket连接管理器（V2.3 增强版 - 鲁棒性提升）

新增功能：
- Ping/Pong 心跳机制（30s 间隔）
- 连接健康状态追踪
- 断线自动清理
- 消息节流保护
"""
import asyncio
import logging
from typing import Dict, Optional
from fastapi import WebSocket
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.adapters.factory import AdapterFactory
from app.adapters.schemas import TelemetryMessage, TelemetryPayload

logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    """单个连接的状态追踪"""
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_pong: datetime = field(default_factory=datetime.utcnow)
    is_healthy: bool = True
    missed_pongs: int = 0


class ConnectionManager:
    """WebSocket连接管理器 V2.3
    
    职责：
    - 管理所有WebSocket连接
    - 后台任务推送遥测数据（5Hz）
    - Ping/Pong 心跳检测（30s 间隔）
    - 处理连接断开与自动清理
    """
    
    HEARTBEAT_INTERVAL = 30  # 秒
    MAX_MISSED_PONGS = 3  # 允许连续丢失的心跳次数
    PUSH_INTERVAL = 0.2  # 5Hz = 200ms
    
    def __init__(self):
        self.connections: Dict[str, ConnectionState] = {}
        self._push_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    def _conn_id(self, websocket: WebSocket) -> str:
        """生成连接唯一标识"""
        return f"{id(websocket)}"
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        conn_id = self._conn_id(websocket)
        self.connections[conn_id] = ConnectionState(websocket=websocket)
        logger.info(f"WebSocket连接建立 [{conn_id}]，当前连接数: {len(self.connections)}")
        
        # 启动后台任务（如果是第一个连接）
        if len(self.connections) == 1:
            self._push_task = asyncio.create_task(self._push_telemetry())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        conn_id = self._conn_id(websocket)
        if conn_id in self.connections:
            del self.connections[conn_id]
        logger.info(f"WebSocket连接断开 [{conn_id}]，当前连接数: {len(self.connections)}")
        
        # 停止后台任务（如果没有连接了）
        if len(self.connections) == 0:
            if self._push_task:
                self._push_task.cancel()
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
    
    async def handle_client_message(self, websocket: WebSocket, message: str):
        """处理客户端消息（心跳响应等）"""
        conn_id = self._conn_id(websocket)
        if conn_id not in self.connections:
            return
        
        state = self.connections[conn_id]
        
        # 处理 Pong 响应
        if message == "pong" or message == '{"type":"pong"}':
            state.last_pong = datetime.utcnow()
            state.missed_pongs = 0
            state.is_healthy = True
            logger.debug(f"收到心跳响应 [{conn_id}]")
    
    async def _heartbeat_loop(self):
        """心跳检测循环（30s 间隔）"""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                now = datetime.utcnow()
                stale_connections = []
                
                for conn_id, state in list(self.connections.items()):
                    try:
                        # 发送 Ping
                        await state.websocket.send_json({"type": "ping", "timestamp": now.isoformat() + "Z"})
                        logger.debug(f"发送心跳 [{conn_id}]")
                        
                        # 检查上次 Pong 时间
                        if now - state.last_pong > timedelta(seconds=self.HEARTBEAT_INTERVAL * 2):
                            state.missed_pongs += 1
                            state.is_healthy = False
                            logger.warning(f"连接不健康 [{conn_id}]，连续丢失心跳: {state.missed_pongs}")
                            
                            if state.missed_pongs >= self.MAX_MISSED_PONGS:
                                stale_connections.append(state.websocket)
                    
                    except Exception as e:
                        logger.error(f"心跳发送失败 [{conn_id}]: {e}")
                        stale_connections.append(state.websocket)
                
                # 清理失效连接
                for ws in stale_connections:
                    self.disconnect(ws)
                    try:
                        await ws.close(code=1000, reason="Heartbeat timeout")
                    except Exception:
                        pass
                
            except asyncio.CancelledError:
                logger.info("心跳任务已取消")
                break
            except Exception as e:
                logger.error(f"心跳任务异常: {e}")
    
    async def _push_telemetry(self):
        """后台任务：5Hz推送遥测数据"""
        while True:
            try:
                adapter = await AdapterFactory.get_adapter()
                
                joints = await adapter.get_joint_states()
                sensors = await adapter.get_sensor_data()
                active_faults = await adapter.get_active_faults()
                
                message = TelemetryMessage(
                    type="telemetry",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    payload=TelemetryPayload(
                        joints=joints,
                        sensors=sensors,
                        active_faults=active_faults
                    )
                )
                
                message_json = message.model_dump_json()
                
                # 发送给所有健康的连接
                disconnected = []
                for conn_id, state in list(self.connections.items()):
                    if not state.is_healthy:
                        continue  # 跳过不健康的连接
                    try:
                        await state.websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"发送消息失败 [{conn_id}]: {e}")
                        disconnected.append(state.websocket)
                
                for ws in disconnected:
                    self.disconnect(ws)
                
                await asyncio.sleep(self.PUSH_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("推送任务已取消")
                break
            except Exception as e:
                logger.error(f"推送任务异常: {e}")
                await asyncio.sleep(1.0)
    
    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        healthy = sum(1 for s in self.connections.values() if s.is_healthy)
        return {
            "total": len(self.connections),
            "healthy": healthy,
            "unhealthy": len(self.connections) - healthy
        }

    # ============ UF-07: Teacher Monitoring Methods ============

    async def broadcast_to_channel(self, channel: str, message: dict) -> None:
        """向指定频道的所有连接广播消息

        Args:
            channel: 频道名称
            message: 消息内容
        """
        # 目前简化为向所有连接广播
        # 实际实现应该维护 channel -> connections 映射
        for conn_id, state in list(self.connections.items()):
            try:
                await state.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"[UF-07] Send to {conn_id} failed: {e}")

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """向指定用户发送消息

        Args:
            user_id: 用户ID
            message: 消息内容
        """
        # 目前简化为向所有连接广播
        # 实际实现应该维护 user_id -> connection 映射
        for conn_id, state in list(self.connections.items()):
            try:
                await state.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"[UF-07] Send to {conn_id} failed: {e}")


# 全局单例
manager = ConnectionManager()

