"""审批闸门回归测试（审计 M-06）。

修复前：策略层已算出 `requires_approval`，但 `OrchestratorV2.process_request`
在策略放行后**直接分派**，把该标志仅作为执行**之后**回填的说明字段——
即「先执行、后标记」，人工闸门根本不在执行路径上。

修复后：需审批的请求在分派前被阻断，不产生任何副作用。
"""
import asyncio

import pytest

from app.services.orchestration.fsm import ModuleDispatchResult
from app.services.orchestrator_v2 import OrchestratorV2
from app.services.policy_matrix import PolicyDecision, RiskLevel


@pytest.mark.regression
@pytest.mark.asyncio
async def test_gate_blocks_before_dispatch(monkeypatch):
    """**核心回归**：需审批时不得调用 `_dispatch_module`。"""
    orch = OrchestratorV2()
    dispatched = []

    async def _never(*args, **kwargs):
        dispatched.append(kwargs)
        raise AssertionError("需审批的请求不得进入分派")

    monkeypatch.setattr(orch, "_dispatch_module", _never)
    monkeypatch.setattr(orch, "_classify_intent", lambda *_a, **_k: _async("write-kb"))
    monkeypatch.setattr(
        "app.services.orchestrator_v2.policy_matrix.evaluate",
        lambda *_a, **_k: PolicyDecision(
            allowed=True,
            risk_level=RiskLevel.R1,
            requires_approval=True,
            approval_level="manager",
            evidence_required=["content_hash"],
        ),
    )

    result = await orch.process_request(user_id="1", message="写入知识条目")

    assert dispatched == [], "闸门未阻断，请求已被分派"
    assert result["requires_approval"] is True
    assert result["status"] == "pending_approval"
    assert result["success"] is False


@pytest.mark.regression
@pytest.mark.asyncio
async def test_gate_lets_through_when_not_required(monkeypatch):
    """不需审批时必须照常分派——闸门不得变成「全部拦截」。"""
    orch = OrchestratorV2()
    dispatched = []

    async def _dispatch(**kwargs):
        dispatched.append(kwargs)
        # 用真实返回类型，避免手写假对象逐个补属性
        return ModuleDispatchResult(
            module_id="m1", module_name="Test", success=True, output={"ok": True}
        )

    monkeypatch.setattr(orch, "_dispatch_module", _dispatch)
    monkeypatch.setattr(orch, "_classify_intent", lambda *_a, **_k: _async("read-status"))
    monkeypatch.setattr(
        "app.services.orchestrator_v2.policy_matrix.evaluate",
        lambda *_a, **_k: PolicyDecision(
            allowed=True,
            risk_level=RiskLevel.R0,
            requires_approval=False,
            approval_level=None,
            evidence_required=[],
        ),
    )

    await orch.process_request(user_id="1", message="查询状态")

    assert len(dispatched) == 1, "不需审批的请求被误拦截"


def _async(value):
    async def _inner():
        return value

    return _inner()
