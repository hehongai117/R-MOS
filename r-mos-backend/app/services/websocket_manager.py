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
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from app.adapters.factory import AdapterFactory
from app.adapters.schemas import TelemetryMessage, TelemetryPayload

logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    """单个连接的状态追踪"""
    websocket: WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_pong: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_healthy: bool = True
    missed_pongs: int = 0
    # 定向投递维度。WebSocket 尚无认证（审计 M-03），因此当前恒为 None/空集，
    # 定向消息不会投递给任何连接——这是**安全默认关闭**：宁可不投递，
    # 也不把教师私信与学员告警广播给全部连接。M-03 认证落地后由 connect() 填充。
    user_id: Optional[int] = None
    channels: set[str] = field(default_factory=set)


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
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
        channels: Optional[set[str]] = None,
    ):
        """接受WebSocket连接

        Args:
            websocket: 连接
            user_id: 连接所属用户。**当前调用方均未提供**（WS 无认证，审计 M-03），
                未提供时该连接不会收到任何定向消息。
            channels: 该连接订阅的频道集合。同上。
        """
        await websocket.accept()
        conn_id = self._conn_id(websocket)
        self.connections[conn_id] = ConnectionState(
            websocket=websocket, user_id=user_id, channels=set(channels or ())
        )
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
            state.last_pong = datetime.now(timezone.utc)
            state.missed_pongs = 0
            state.is_healthy = True
            logger.debug(f"收到心跳响应 [{conn_id}]")
    
    async def _heartbeat_loop(self):
        """心跳检测循环（30s 间隔）"""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                now = datetime.now(timezone.utc)
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
                    timestamp=datetime.now(timezone.utc).isoformat() + "Z",
                    payload=TelemetryPayload(
                        joints=joints,
                        sensors=sensors,
                        active_faults=active_faults
                    )
                )
                
                message_json = message.model_dump_json()
                
                # 并发发送给所有健康的连接（审计 F-RT-02：串行 await 时
                # 单个慢连接会阻塞本轮其余全部推送，在 5Hz 下尤其明显）
                healthy = [
                    (cid, st) for cid, st in list(self.connections.items()) if st.is_healthy
                ]

                async def _push_one(conn_id: str, state: ConnectionState):
                    try:
                        await state.websocket.send_text(message_json)
                        return None
                    except Exception as e:
                        logger.error(f"发送消息失败 [{conn_id}]: {e}")
                        return state.websocket

                results = await asyncio.gather(
                    *(_push_one(cid, st) for cid, st in healthy), return_exceptions=True
                )
                for ws in [r for r in results if r is not None and not isinstance(r, BaseException)]:
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

    async def _send_many(self, targets: list[tuple[str, ConnectionState]], message: dict) -> int:
        """并发投递给若干连接，返回成功数。

        并发而非串行：串行 await 时单个慢连接会阻塞本轮其余全部推送
        （审计 F-RT-02）。异常不向外抛，单连接失败不影响其他连接。
        """
        if not targets:
            return 0

        async def _one(conn_id: str, state: ConnectionState) -> bool:
            try:
                await state.websocket.send_json(message)
                return True
            except Exception as e:
                logger.warning(f"[UF-07] Send to {conn_id} failed: {e}")
                return False

        results = await asyncio.gather(
            *(_one(cid, st) for cid, st in targets), return_exceptions=True
        )
        return sum(1 for r in results if r is True)

    async def broadcast_to_channel(self, channel: str, message: dict) -> None:
        """向**订阅了该频道**的连接投递消息。

        审计 F-RT-03：此前 `channel` 参数完全不被使用，实为全量广播，
        导致班级频道事件与学员步骤告警被推送给所有连接。
        """
        targets = [
            (cid, st) for cid, st in list(self.connections.items()) if channel in st.channels
        ]
        sent = await self._send_many(targets, message)
        if not targets:
            logger.warning(
                f"[UF-07] 频道 {channel} 无订阅连接，消息未投递。"
                "（WS 尚无认证，连接不携带频道订阅——审计 M-03）"
            )
        else:
            logger.debug(f"[UF-07] 频道 {channel} 投递 {sent}/{len(targets)}")

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """向**该用户的**连接投递消息。

        审计 M-03/F-RT-03：此前遍历全部连接发送，名为定向实为广播，
        导致教师发给单个学员的私信泄露给所有在线连接。
        """
        targets = [
            (cid, st) for cid, st in list(self.connections.items()) if st.user_id == user_id
        ]
        sent = await self._send_many(targets, message)
        if not targets:
            logger.warning(
                f"[UF-07] 用户 {user_id} 无已标识连接，消息未投递。"
                "（WS 尚无认证，连接不携带用户身份——审计 M-03）"
            )
        else:
            logger.debug(f"[UF-07] 用户 {user_id} 投递 {sent}/{len(targets)}")


# 全局单例
manager = ConnectionManager()

