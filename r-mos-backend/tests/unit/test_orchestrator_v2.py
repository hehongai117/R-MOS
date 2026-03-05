"""
OrchestratorV2 basic flow tests.
"""
from __future__ import annotations

from app.services.orchestrator_v2 import OrchestratorV2


def test_orchestrator_v2_process_request_and_idempotency_cache():
    orchestrator = OrchestratorV2()

    response1 = orchestrator.process_request(
        user_id="u-1",
        message="读取知识",
        intent_classification="read-kb",
        idempotency_key="idem-001",
    )
    assert response1["success"] is True
    assert response1["from_cache"] is False
    assert response1["policy_decision"]["allowed"] is True

    response2 = orchestrator.process_request(
        user_id="u-1",
        message="读取知识",
        intent_classification="read-kb",
        idempotency_key="idem-001",
    )
    assert response2["success"] is True
    assert response2["from_cache"] is True
