"""AUTH-105：登录失败次数限制与临时锁定。

对应门禁 `AUTH-GATE-11`、`AUTH-GATE-12`。

分两层：
- 纯逻辑层（`LoginThrottle`）：直接推进时间验证窗口与解锁，不起 HTTP。
- 接口层（`POST /api/v1/auth/login`）：验证阈值、锁定期内正确密码同样被拒、
  成功登录清零，以及**换一个账号不受牵连**。
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
from app.models.school import School
from app.services.login_throttle import (
    LOCKOUT_SECONDS,
    MAX_FAILURES,
    WINDOW_SECONDS,
    LoginThrottle,
    login_throttle,
)
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME

PASSWORD = "StrongPass123"


# ─────────────────────────────────────────────────────────────────────────────
# 纯逻辑层
# ─────────────────────────────────────────────────────────────────────────────

def test_lock_engages_exactly_at_threshold() -> None:
    throttle = LoginThrottle()
    key = ("a@x.com", "1.2.3.4")

    for i in range(MAX_FAILURES - 1):
        assert throttle.record_failure(key, now=100.0 + i) == 0
        assert throttle.locked_seconds_remaining(key, now=100.0 + i) == 0

    assert throttle.record_failure(key, now=100.0 + MAX_FAILURES) == LOCKOUT_SECONDS
    assert throttle.locked_seconds_remaining(key, now=100.0 + MAX_FAILURES) > 0


def test_lock_expires_and_state_is_cleared() -> None:
    throttle = LoginThrottle()
    key = ("a@x.com", "1.2.3.4")
    for i in range(MAX_FAILURES):
        throttle.record_failure(key, now=100.0 + i)

    # 锁是在**第 MAX_FAILURES 次失败那一刻**起算，即 now=100+MAX_FAILURES-1
    locked_at = 100.0 + MAX_FAILURES - 1
    assert throttle.locked_seconds_remaining(key, now=locked_at + LOCKOUT_SECONDS - 1) > 0
    # 到期即解锁，且计数一并清掉——否则解锁后一次失败就会再次触发锁定
    assert throttle.locked_seconds_remaining(key, now=locked_at + LOCKOUT_SECONDS) == 0
    assert throttle.record_failure(key, now=locked_at + LOCKOUT_SECONDS + 1) == 0


def test_failures_outside_window_do_not_accumulate() -> None:
    """窗口外的历史失败不应把用户拖进锁定——否则长期偶发输错也会被锁。"""
    throttle = LoginThrottle()
    key = ("a@x.com", "1.2.3.4")

    for i in range(MAX_FAILURES - 1):
        throttle.record_failure(key, now=100.0 + i)
    # 越过整个窗口后再失败一次，不应达到阈值
    assert throttle.record_failure(key, now=100.0 + WINDOW_SECONDS + 10) == 0


def test_never_locks_permanently() -> None:
    """不做永久锁定：任何锁定都必须在有限时间后自动解除。"""
    throttle = LoginThrottle()
    key = ("a@x.com", "1.2.3.4")
    for i in range(MAX_FAILURES * 4):
        throttle.record_failure(key, now=100.0 + i)
    far_future = 100.0 + MAX_FAILURES * 4 + LOCKOUT_SECONDS + 1
    assert throttle.locked_seconds_remaining(key, now=far_future) == 0


def test_different_keys_are_independent() -> None:
    """不同账号 / 不同来源互不牵连。"""
    throttle = LoginThrottle()
    victim = ("victim@x.com", "1.2.3.4")
    other_ip = ("victim@x.com", "5.6.7.8")
    other_account = ("someone@x.com", "1.2.3.4")

    for i in range(MAX_FAILURES):
        throttle.record_failure(victim, now=100.0 + i)

    now = 100.0 + MAX_FAILURES
    assert throttle.locked_seconds_remaining(victim, now=now) > 0
    assert throttle.locked_seconds_remaining(other_ip, now=now) == 0
    assert throttle.locked_seconds_remaining(other_account, now=now) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 接口层
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def login_env():
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
    login_throttle.clear_all()  # 进程内单例，测试之间必须隔离

    with TestClient(app) as client:
        yield client

    login_throttle.clear_all()
    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None


def _register(client: TestClient, email: str) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Throttle Target",
            "role": "teacher",
            "school_name": E2E_SCHOOL_NAME,
        },
    )
    assert resp.status_code == 201, resp.text


def test_login_locks_after_threshold_and_rejects_correct_password(login_env) -> None:
    """AUTH-GATE-11/12：达到阈值后受限；**锁定期内正确密码同样被拒**。"""
    client = login_env
    email = "throttle_target@example.com"
    _register(client, email)

    for _ in range(MAX_FAILURES):
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass000"})
        assert resp.status_code == 401, resp.text

    limited = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass000"})
    assert limited.status_code == 429, limited.text
    assert limited.json()["error_type"] == "TooManyLoginAttempts"

    # 锁定期内密码正确也必须拒绝，否则限流可被"撞对即通过"绕过
    correct = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert correct.status_code == 429, correct.text


def test_other_account_not_affected_by_lockout(login_env) -> None:
    """一个账号被锁不得牵连其他账号。"""
    client = login_env
    victim = "throttle_victim@example.com"
    bystander = "throttle_bystander@example.com"
    _register(client, victim)
    _register(client, bystander)

    for _ in range(MAX_FAILURES):
        client.post("/api/v1/auth/login", json={"email": victim, "password": "WrongPass000"})

    assert client.post(
        "/api/v1/auth/login", json={"email": victim, "password": PASSWORD}
    ).status_code == 429

    ok = client.post("/api/v1/auth/login", json={"email": bystander, "password": PASSWORD})
    assert ok.status_code == 200, ok.text


def test_successful_login_resets_failure_count(login_env) -> None:
    """成功登录清零：之前的失败不得累积到下一轮。"""
    client = login_env
    email = "throttle_reset@example.com"
    _register(client, email)

    for _ in range(MAX_FAILURES - 1):
        client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass000"})

    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).status_code == 200

    # 清零后应能重新承受 MAX_FAILURES - 1 次失败而不被锁
    for _ in range(MAX_FAILURES - 1):
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass000"})
        assert resp.status_code == 401, resp.text


def test_unknown_account_does_not_leak_existence_via_throttling(login_env) -> None:
    """限流不得变成账号枚举信道：未知账号的响应码序列与已知账号一致。"""
    client = login_env
    known = "throttle_known@example.com"
    _register(client, known)
    unknown = "throttle_unknown@example.com"

    known_codes = [
        client.post("/api/v1/auth/login", json={"email": known, "password": "WrongPass000"}).status_code
        for _ in range(MAX_FAILURES + 1)
    ]
    unknown_codes = [
        client.post("/api/v1/auth/login", json={"email": unknown, "password": "WrongPass000"}).status_code
        for _ in range(MAX_FAILURES + 1)
    ]
    assert known_codes == unknown_codes, (known_codes, unknown_codes)
