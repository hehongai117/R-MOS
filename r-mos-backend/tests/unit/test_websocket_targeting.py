"""实时通道定向投递与心跳回执的回归测试。

对应审计发现：
- F-RT-01 handle_client_message 零调用者 → 心跳误杀健康连接
- F-RT-02 串行投递 → 单个慢/坏连接阻塞全体
- F-RT-03/M-03 channel 与 user_id 参数不生效 → 定向消息实为全量广播
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.services.websocket_manager import ConnectionManager, ConnectionState


class FakeWS:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def accept(self):
        pass

    async def send_json(self, message: dict):
        if self.fail:
            raise RuntimeError("broken pipe")
        self.sent.append(message)


def _mgr_with(states: dict[str, ConnectionState]) -> ConnectionManager:
    m = ConnectionManager()
    m.connections = states
    return m


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
    await m.send_to_user(1, {"secret": "for-user-1"})
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
