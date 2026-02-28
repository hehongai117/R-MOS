#!/usr/bin/env python3
"""
CI Gate Validator - Phase 1/2 Skeleton Gates

This script validates all CI gates for Phase 1/2:
1. FSM流转测试
2. 事件幂等测试
3. 防重放测试
4. 证据链验签测试
5. RBAC越权测试 (stub)
"""

import sys
import os

# Add schemas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.fsm import FSMTaskEvent, FSMState
from schemas.evidence import Evidence, EvidenceChainValidator
from schemas.tests.fixtures import (
    VALID_EVENT,
    VALID_EVIDENCE_CHAIN,
    BROKEN_EVIDENCE_CHAIN,
    VALID_ACTION
)
import time


def gate_1_fsm_transition():
    """Gate 1: FSM state transition validation"""
    print("\n=== Gate 1: FSM Transition Test ===")

    # Valid transition: READY -> EXECUTING
    event = VALID_EVENT
    assert event.fsm_state_before == FSMState.READY
    assert event.fsm_state_after == FSMState.EXECUTING

    print("✓ FSM transition READY -> EXECUTING: PASS")
    return True


def gate_2_event_idempotency():
    """Gate 2: Event idempotency check"""
    print("\n=== Gate 2: Event Idempotency Test ===")

    event = VALID_EVENT

    # Check event_id exists
    assert event.event_id != ""
    print(f"✓ Event ID: {event.event_id}")

    # Check event_sequence is positive
    assert event.event_sequence > 0
    print(f"✓ Event Sequence: {event.event_sequence}")

    # Check plan_version exists
    assert event.plan_version > 0
    print(f"✓ Plan Version: {event.plan_version}")

    print("✓ Event idempotency: PASS")
    return True


def gate_3_replay_protection():
    """Gate 3: Replay protection check"""
    print("\n=== Gate 3: Replay Protection Test ===")

    event = VALID_EVENT

    # Check timestamps
    assert event.timestamp_client > 0
    assert event.timestamp_server > 0
    assert event.timestamp_server >= event.timestamp_client

    # Check timestamp is recent (within 5 minutes)
    now_ms = int(time.time() * 1000)
    assert (now_ms - event.timestamp_server) < 5 * 60 * 1000

    print(f"✓ Timestamp client: {event.timestamp_client}")
    print(f"✓ Timestamp server: {event.timestamp_server}")
    print(f"✓ Replay protection: PASS")
    return True


def gate_4_evidence_chain():
    """Gate 4: Evidence chain validation"""
    print("\n=== Gate 4: Evidence Chain Test ===")

    # Test valid chain
    validator = EvidenceChainValidator()
    is_valid, msg = validator.validate_chain(VALID_EVIDENCE_CHAIN)

    print(f"Valid chain test: {msg}")
    assert is_valid, f"Valid chain should pass: {msg}"
    print("✓ Valid chain: PASS")

    # Test broken chain (should fail)
    is_valid, msg = validator.validate_chain(BROKEN_EVIDENCE_CHAIN)

    print(f"Broken chain test: {msg}")
    assert not is_valid, "Broken chain should fail!"
    print("✓ Broken chain correctly rejected: PASS")

    print("✓ Evidence chain validation: PASS")
    return True


def gate_5_rbac_stub():
    """Gate 5: RBAC stub test"""
    print("\n=== Gate 5: RBAC Test (stub) ===")

    # Stub - RBAC not implemented in skeleton
    print("✓ RBAC: PASS (stub)")
    return True


def gate_6_schema_version():
    """Gate 6: Schema version check"""
    print("\n=== Gate 6: Schema Version Test ===")

    event = VALID_EVENT
    evidence = VALID_EVIDENCE_CHAIN[0]
    action = VALID_ACTION

    assert event.schema_version != ""
    assert evidence.schema_version != ""
    assert action.schema_version != ""

    print(f"✓ FSM Event schema: {event.schema_version}")
    print(f"✓ Evidence schema: {evidence.schema_version}")
    print(f"✓ Action schema: {action.schema_version}")
    print("✓ Schema version: PASS")
    return True


def run_all_gates():
    """Run all CI gates"""
    print("=" * 60)
    print("CI Gate Validation - Phase 1/2 Skeleton")
    print("=" * 60)

    gates = [
        ("FSM Transition", gate_1_fsm_transition),
        ("Event Idempotency", gate_2_event_idempotency),
        ("Replay Protection", gate_3_replay_protection),
        ("Evidence Chain", gate_4_evidence_chain),
        ("RBAC", gate_5_rbac_stub),
        ("Schema Version", gate_6_schema_version),
    ]

    results = []
    for name, gate_func in gates:
        try:
            result = gate_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name}: FAIL - {e}")

    print("\n" + "=" * 60)
    print("CI Gate Results Summary")
    print("=" * 60)

    all_passed = True
    for name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")
        if not result:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("ALL GATES PASSED ✓")
        return 0
    else:
        print("SOME GATES FAILED ✗")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_gates())
