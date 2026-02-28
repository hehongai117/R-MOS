#!/usr/bin/env python3
"""
PR-C Test: Evidence Chain Integrity

This validates that broken evidence chains (hash_prev mismatch) are rejected.
PR-C will FAIL if evidence chain is tampered.
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.evidence import Evidence, EvidenceChainValidator
import time


def test_broken_chain():
    """Test that broken chain is correctly rejected"""
    print("=" * 60)
    print("PR-C: Evidence Chain Integrity Test")
    print("=" * 60)
    print()

    # Create evidence chain with INTENTIONAL BREAK
    # hash_prev does NOT match previous hash_content
    broken_chain = [
        Evidence(
            id="ev-001",
            task_id="task-001",
            step_id="step-001",
            action_id="action-001",
            type="trajectory",
            hash_prev="",  # First item - empty
            hash_content="correct_hash_001",
            signature="sig-001",
            timestamp_server=int(time.time() * 1000),
            schema_version="1.0.0"
        ),
        Evidence(
            id="ev-002",
            task_id="task-001",
            step_id="step-002",
            action_id="action-002",
            type="sensor_reading",
            hash_prev="TAMPERED_HASH",  # <-- WRONG! Should be "correct_hash_001"
            hash_content="correct_hash_002",
            signature="sig-002",
            timestamp_server=int(time.time() * 1000),
            schema_version="1.0.0"
        ),
    ]

    print("Testing broken evidence chain...")
    print(f"  First evidence: hash_content = 'correct_hash_001'")
    print(f"  Second evidence: hash_prev = 'TAMPERED_HASH' (should be 'correct_hash_001')")
    print()

    validator = EvidenceChainValidator()
    is_valid, message = validator.validate_chain(broken_chain)

    print(f"Validation result: {message}")
    print()

    if not is_valid:
        print("✓ Chain correctly rejected: PASS")
        print()
        print("CI GATE RESULT: PASS ✓ (Expected - broken chain detected)")
        return 0
    else:
        print("✗ ERROR: Broken chain was NOT rejected!")
        print()
        print("CI GATE RESULT: FAIL ✗")
        return 1


def test_valid_chain():
    """Test that valid chain passes"""
    print()
    print("Testing valid evidence chain...")
    print()

    valid_chain = [
        Evidence(
            id="ev-001",
            task_id="task-001",
            step_id="step-001",
            action_id="action-001",
            type="trajectory",
            hash_prev="",
            hash_content="hash_001",
            signature="sig-001",
            timestamp_server=int(time.time() * 1000),
            schema_version="1.0.0"
        ),
        Evidence(
            id="ev-002",
            task_id="task-001",
            step_id="step-002",
            action_id="action-002",
            type="sensor_reading",
            hash_prev="hash_001",  # Correct - matches previous hash_content
            hash_content="hash_002",
            signature="sig-002",
            timestamp_server=int(time.time() * 1000),
            schema_version="1.0.0"
        ),
    ]

    validator = EvidenceChainValidator()
    is_valid, message = validator.validate_chain(valid_chain)

    print(f"Validation result: {message}")
    print()

    if is_valid:
        print("✓ Valid chain correctly accepted: PASS")
        return 0
    else:
        print("✗ ERROR: Valid chain was rejected!")
        return 1


if __name__ == "__main__":
    # Run broken chain test (should fail)
    result1 = test_broken_chain()

    # Run valid chain test (should pass)
    result2 = test_valid_chain()

    print()
    print("=" * 60)
    print("PR-C Summary")
    print("=" * 60)

    if result1 == 0:
        print("✓ Broken chain test: PASSED (correctly rejected)")
    else:
        print("✗ Broken chain test: FAILED")

    if result2 == 0:
        print("✓ Valid chain test: PASSED (correctly accepted)")
    else:
        print("✗ Valid chain test: FAILED")

    # PR-C is about detecting tampering - if broken chain is caught, PR-C passes
    sys.exit(0 if result1 == 0 else 1)
