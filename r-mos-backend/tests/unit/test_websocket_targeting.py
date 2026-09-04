"""实时通道定向投递与心跳回执的回归测试。

对应审计发现：
- F-RT-01 handle_client_message 零调用者 → 心跳误杀健康连接
- F-RT-02 串行投递 → 单个慢/坏连接阻塞全体
- F-RT-03/M-03 channel 与 user_id 参数不生效 → 定向消息实为全量广播
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import WebSocketDisconnect

from app.adapters.schemas import SensorData
from app.api.v1.endpoints import websocket as websocket_endpoint_module
from app.services.authz_guard import ActorContext
from app.services.websocket_manager import ConnectionManager, ConnectionState


class FakeWS:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.sent_text: list[str] = []
        self.fail = fail
        self.closed: list[tuple[int, str]] = []

    async def accept(self):
        pass

    async def send_json(self, message: dict):
        if self.fail:
            raise RuntimeError("broken pipe")
        self.sent.append(message)

    async def send_text(self, message: str):
        if self.fail:
            raise RuntimeError("broken pipe")
        self.sent_text.append(message)

    async def close(self, code: int, reason: str):
        self.closed.append((code, reason))


class StallingWS(FakeWS):
    async def send_json(self, message: dict):
        await asyncio.Event().wait()

    async def send_text(self, message: str):
        await asyncio.Event().wait()


class YieldingCloseStallingWS(StallingWS):
    async def close(self, code: int, reason: str):
        await asyncio.sleep(0)
        await super().close(code, reason)


class FakeAdapter:
    async def get_joint_states(self):
        return []

    async def get_sensor_data(self):
        return SensorData()

    async def get_active_faults(self):
        return []


def _mgr_with(states: dict[str, ConnectionState]) -> ConnectionManager:
    m = ConnectionManager()
    m.connections = states
    return m


async def _wait_until(predicate, timeout: float = 0.1) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.001)


@pytest.mark.regression
@pytest.mark.asyncio
async def test_send_to_user_only_reaches_that_user():
    """M-03/F-RT-03：教师私信不得广播给其他连接。"""
    a, b, anon = FakeWS(), FakeWS(), FakeWS()
    m = _mgr_with({
        "a": ConnectionState(websocket=a, user_id=1),
        "b": ConnectionState(websocket=b, user_id=2),
        "anon": ConnectionState(websocket=anon),  # 未标识身份
    })
    delivered = await m.send_to_user(1, {"secret": "for-user-1"})
    assert delivered == 1
    assert a.sent == [{"secret": "for-user-1"}]
    assert b.sent == [], "泄露给了其他用户"
    assert anon.sent == [], "泄露给了未标识连接"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_broadcast_to_channel_only_reaches_subscribers():
    """F-RT-03：班级频道事件不得推给未订阅连接。"""
    sub, other = FakeWS(), FakeWS()
    m = _mgr_with({
        "sub": ConnectionState(websocket=sub, channels={"class:7"}),
        "other": ConnectionState(websocket=other, channels={"class:9"}),
    })
    await m.broadcast_to_channel("class:7", {"e": "warn"})
    assert sub.sent == [{"e": "warn"}]
    assert other.sent == [], "推给了未订阅该频道的连接"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_one_broken_connection_does_not_block_others():
    """F-RT-02：单连接失败不得影响同批其他连接投递。"""
    ok1, bad, ok2 = FakeWS(), FakeWS(fail=True), FakeWS()
    m = _mgr_with({
        "ok1": ConnectionState(websocket=ok1, channels={"c"}),
        "bad": ConnectionState(websocket=bad, channels={"c"}),
        "ok2": ConnectionState(websocket=ok2, channels={"c"}),
    })
    await m.broadcast_to_channel("c", {"n": 1})
    assert ok1.sent == [{"n": 1}]
    assert ok2.sent == [{"n": 1}], "坏连接阻断了后续连接的投递"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_stalled_connection_times_out_and_is_removed():
    """F-RT-02：永不返回的连接必须在发送上限内被清理。"""
    fast, stalled = FakeWS(), StallingWS()
    m = ConnectionManager()
    stalled_id = m._conn_id(stalled)
    m.connections = {
        m._conn_id(fast): ConnectionState(websocket=fast, channels={"c"}),
        stalled_id: ConnectionState(websocket=stalled, channels={"c"}),
    }
    m.SEND_TIMEOUT = 0.01

    delivered = await asyncio.wait_for(
        m.broadcast_to_channel("c", {"n": 1}), timeout=0.1
    )

    assert delivered == 1
    assert fast.sent == [{"n": 1}]
    assert stalled_id not in m.connections
    assert stalled.closed == [(1011, "Send timeout")]


@pytest.mark.regression
@pytest.mark.asyncio
async def test_telemetry_continues_after_stalled_connection_timeout(monkeypatch):
    """F-RT-02：慢连接被清理后，健康连接必须继续收到后续遥测批次。"""
    fast, stalled = FakeWS(), StallingWS()
    m = ConnectionManager()
    stalled_id = m._conn_id(stalled)
    m.connections = {
        m._conn_id(fast): ConnectionState(websocket=fast),
        stalled_id: ConnectionState(websocket=stalled),
    }
    m.SEND_TIMEOUT = 0.01
    m.PUSH_INTERVAL = 0.005

    async def fake_get_adapter(cls):
        return FakeAdapter()

    monkeypatch.setattr(
        "app.services.websocket_manager.AdapterFactory.get_adapter",
        classmethod(fake_get_adapter),
    )

    task = asyncio.create_task(m._push_telemetry())
    await _wait_until(lambda: len(fast.sent_text) >= 2 and stalled_id not in m.connections)
    task.cancel()
    await task

    assert len(fast.sent_text) >= 2
    telemetry = json.loads(fast.sent_text[0])
    assert telemetry["timestamp"].endswith("Z")
    assert "+00:00Z" not in telemetry["timestamp"]
    datetime.fromisoformat(telemetry["timestamp"].replace("Z", "+00:00"))
    assert stalled_id not in m.connections
    assert stalled.closed == [(1011, "Send timeout")]


@pytest.mark.regression
@pytest.mark.asyncio
async def test_heartbeat_stalled_connection_does_not_block_healthy_peer():
    """F-RT-02：一条慢连接不得阻断其他连接收到心跳。"""
    stalled, fast = StallingWS(), FakeWS()
    m = ConnectionManager()
    stalled_id = m._conn_id(stalled)
    m.connections = {
        stalled_id: ConnectionState(websocket=stalled),
        m._conn_id(fast): ConnectionState(websocket=fast),
    }
    m.SEND_TIMEOUT = 0.01
    m.HEARTBEAT_INTERVAL = 0.005

    task = asyncio.create_task(m._heartbeat_loop())
    await _wait_until(lambda: bool(fast.sent) and stalled_id not in m.connections)
    task.cancel()
    await task

    ping = next(message for message in fast.sent if message["type"] == "ping")
    assert ping["timestamp"].endswith("Z")
    assert "+00:00Z" not in ping["timestamp"]
    datetime.fromisoformat(ping["timestamp"].replace("Z", "+00:00"))
    assert stalled_id not in m.connections


@pytest.mark.regression
@pytest.mark.asyncio
async def test_last_stalled_heartbeat_connection_is_closed_before_loop_stops():
    """最后一条坏连接的关闭握手不得被心跳任务自取消截断。"""
    stalled = YieldingCloseStallingWS()
    m = ConnectionManager()
    stalled_id = m._conn_id(stalled)
    m.connections = {stalled_id: ConnectionState(websocket=stalled)}
    m.SEND_TIMEOUT = 0.005
    m.HEARTBEAT_INTERVAL = 0.005

    task = asyncio.create_task(m._heartbeat_loop())
    m._heartbeat_task = task
    await asyncio.wait_for(task, timeout=0.1)

    assert stalled_id not in m.connections
    assert stalled.closed == [(1000, "Heartbeat timeout")]


@pytest.mark.regression
@pytest.mark.asyncio
async def test_pong_resets_heartbeat_state():
    """F-RT-01：客户端 pong 必须能重置心跳计数。

    修复前 handle_client_message 零调用者，last_pong 永不更新，
    健康连接约 90 秒起被跳过遥测、约 150 秒被强制断开。
    """
    ws = FakeWS()
    stale = datetime.now(timezone.utc) - timedelta(seconds=300)
    state = ConnectionState(websocket=ws, last_pong=stale, is_healthy=False, missed_pongs=2)
    m = _mgr_with({m_id: state for m_id in [ConnectionManager()._conn_id(ws)]})

    await m.handle_client_message(ws, '{"type":"pong"}')

    assert state.missed_pongs == 0
    assert state.is_healthy is True
    assert state.last_pong > stale


@pytest.mark.regression
@pytest.mark.asyncio
async def test_endpoint_routes_pong_to_connection_state(monkeypatch):
    """F-RT-01：pong 必须经过真实端点接收循环更新连接状态。"""

    class PongThenDisconnectWS(FakeWS):
        def __init__(self):
            super().__init__()
            self.receive_count = 0

        async def receive_text(self):
            self.receive_count += 1
            if self.receive_count == 1:
                return '{"type":"pong"}'
            raise WebSocketDisconnect()

    ws = PongThenDisconnectWS()
    stale = datetime.now(timezone.utc) - timedelta(seconds=300)
    state = ConnectionState(
        websocket=ws,
        last_pong=stale,
        is_healthy=False,
        missed_pongs=2,
    )
    live_connections: dict[str, ConnectionState] = {}

    async def fake_connect(websocket, user_id=None, channels=None):
        live_connections[str(id(websocket))] = state

    def fake_disconnect(websocket):
        return None

    # 审计 M-03：端点现在先认证再握手。本用例验的是 pong 路由，
    # 故把认证打桩为固定身份；认证行为本身由
    # test_websocket_rejects_unauthenticated 覆盖。
    async def fake_auth(websocket, token):
        return ActorContext(user_id=1, email="u@x.com", roles=set(), permissions=set())

    monkeypatch.setattr(websocket_endpoint_module, "_authenticate", fake_auth)
    monkeypatch.setattr(websocket_endpoint_module.manager, "connections", live_connections)
    monkeypatch.setattr(websocket_endpoint_module.manager, "connect", fake_connect)
    monkeypatch.setattr(websocket_endpoint_module.manager, "disconnect", fake_disconnect)

    await websocket_endpoint_module._handle_websocket(ws)

    assert state.missed_pongs == 0
    assert state.is_healthy is True
    assert state.last_pong > stale


@pytest.mark.regression
@pytest.mark.asyncio
async def test_websocket_rejects_unauthenticated(monkeypatch):
    """审计 M-03：无令牌必须在 accept() **之前**被拒，不得先接纳再驱逐。"""

    class _State:
        test_sessionmaker = None

    class _App:
        state = _State()

    class RecordingWS(FakeWS):
        def __init__(self):
            super().__init__()
            self.headers = {}
            self.app = _App()
            self.accepted = False
            self.closed_with = None

        async def accept(self):
            self.accepted = True

        async def close(self, code=1000, reason=""):
            self.closed_with = (code, reason)

    ws = RecordingWS()
    connected = []

    async def fake_connect(websocket, user_id=None, channels=None):
        connected.append(websocket)

    monkeypatch.setattr(websocket_endpoint_module.manager, "connect", fake_connect)

    await websocket_endpoint_module._handle_websocket(ws, token=None)

    assert ws.accepted is False, "未认证连接不得被 accept"
    assert connected == [], "未认证连接不得进入连接表"
    assert ws.closed_with == (1008, "unauthenticated")


@pytest.mark.regression
@pytest.mark.asyncio
async def test_websocket_registers_identity_for_targeted_delivery(monkeypatch):
    """审计 M-03/F-RT-03：认证通过后身份必须随连接登记，定向投递才有接收者。"""

    class OneShotWS(FakeWS):
        def __init__(self):
            super().__init__()
            self.headers = {}
            self.n = 0

        async def receive_text(self):
            self.n += 1
            raise WebSocketDisconnect()

    ws = OneShotWS()
    captured = {}

    async def fake_auth(websocket, token):
        return ActorContext(user_id=77, email="u@x.com", roles=set(), permissions=set())

    async def fake_connect(websocket, user_id=None, channels=None):
        captured["user_id"] = user_id
        captured["channels"] = channels

    monkeypatch.setattr(websocket_endpoint_module, "_authenticate", fake_auth)
    monkeypatch.setattr(websocket_endpoint_module.manager, "connect", fake_connect)
    monkeypatch.setattr(websocket_endpoint_module.manager, "disconnect", lambda ws: None)

    await websocket_endpoint_module._handle_websocket(ws, token="t")

    assert captured["user_id"] == 77, "连接未携带认证身份，定向消息将无接收者"
    assert "user:77" in captured["channels"]
