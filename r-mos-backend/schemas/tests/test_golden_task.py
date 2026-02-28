#!/usr/bin/env python3
"""
Golden Task: Evidence Package Generation, Validation & Report

This simulates a complete evidence lifecycle:
1. Generate evidence for a task execution
2. Sign each evidence with server private key
3. Validate chain integrity
4. Verify signatures
5. Generate audit report
"""

import sys
import os
import hashlib
import hmac
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.evidence import Evidence, EvidenceChainValidator


# Simulated server keys (in production, use proper key management)
SERVER_SECRET = "rmos_secret_key_2024"


def generate_evidence_id() -> str:
    """Generate unique evidence ID"""
    return f"ev-{int(time.time() * 1000)}"


def compute_content_hash(content: dict) -> str:
    """Compute SHA256 hash of evidence content"""
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()


def sign_evidence(evidence: Evidence, secret: str) -> str:
    """Sign evidence with server secret"""
    message = f"{evidence.id}:{evidence.hash_content}:{evidence.timestamp_server}"
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature


def generate_evidence_package(task_id: str, steps: list[dict]) -> list[Evidence]:
    """Generate complete evidence package for a task"""

    evidence_chain = []
    prev_hash = ""

    print("=" * 60)
    print("Golden Task: Evidence Package Generation")
    print("=" * 60)
    print()

    for i, step in enumerate(steps):
        # Create evidence content
        content = {
            "task_id": task_id,
            "step_id": step["step_id"],
            "action_id": step["action_id"],
            "action_type": step["action_type"],
            "result": step["result"],
            "timestamp": int(time.time() * 1000)
        }

        # Compute content hash
        content_hash = compute_content_hash(content)

        # Create evidence with chain hash
        evidence = Evidence(
            id=generate_evidence_id(),
            task_id=task_id,
            step_id=step["step_id"],
            action_id=step["action_id"],
            type=step["type"],
            hash_prev=prev_hash,
            hash_content=content_hash,
            timestamp_client=content["timestamp"],
            timestamp_server=int(time.time() * 1000),
            schema_version="1.0.0"
        )

        # Sign evidence
        evidence.signature = sign_evidence(evidence, SERVER_SECRET)

        evidence_chain.append(evidence)
        prev_hash = content_hash

        print(f"  Step {i+1}: {step['action_type']}")
        print(f"    - Evidence ID: {evidence.id}")
        print(f"    - Content Hash: {content_hash[:16]}...")
        print(f"    - Chain Hash: {evidence.hash_prev[:16] if evidence.hash_prev else '(first)'}...")
        print(f"    - Signature: {evidence.signature[:16]}...")
        print()

    return evidence_chain


def validate_evidence_package(evidence_chain: list[Evidence]) -> dict:
    """Validate entire evidence package"""

    print("=" * 60)
    print("Evidence Validation")
    print("=" * 60)
    print()

    results = {
        "chain_valid": False,
        "signatures_valid": False,
        "total_evidence": len(evidence_chain),
        "errors": []
    }

    # Validate chain
    chain_valid, chain_message = EvidenceChainValidator.validate_chain(evidence_chain)
    results["chain_valid"] = chain_valid
    print(f"Chain Validation: {chain_message}")

    if not chain_valid:
        results["errors"].append(chain_message)

    # Validate signatures
    all_sigs_valid = True
    for i, ev in enumerate(evidence_chain):
        expected_sig = sign_evidence(ev, SERVER_SECRET)
        if ev.signature != expected_sig:
            all_sigs_valid = False
            results["errors"].append(f"Signature mismatch at index {i}")

    results["signatures_valid"] = all_sigs_valid
    print(f"Signature Validation: {'PASS' if all_sigs_valid else 'FAIL'}")
    print()

    return results


def generate_audit_report(task_id: str, evidence_chain: list[Evidence], validation_results: dict) -> str:
    """Generate audit report"""

    print("=" * 60)
    print("Audit Report Generation")
    print("=" * 60)
    print()

    report = []
    report.append(f"R-MOS Evidence Audit Report")
    report.append(f"=" * 40)
    report.append(f"Task ID: {task_id}")
    report.append(f"Report Time: {datetime.now().isoformat()}")
    report.append(f"Total Evidence: {len(evidence_chain)}")
    report.append("")
    report.append(f"Validation Results:")
    report.append(f"  - Chain Integrity: {'✓ PASS' if validation_results['chain_valid'] else '✗ FAIL'}")
    report.append(f"  - Signature Verification: {'✓ PASS' if validation_results['signatures_valid'] else '✗ FAIL'}")
    report.append("")

    if validation_results['errors']:
        report.append("Errors:")
        for error in validation_results['errors']:
            report.append(f"  - {error}")
        report.append("")

    report.append("Evidence Chain:")
    for i, ev in enumerate(evidence_chain):
        report.append(f"  [{i+1}] {ev.type}: {ev.action_id}")
        report.append(f"      Hash: {ev.hash_content[:16]}...")
        report.append(f"      Prev: {ev.hash_prev[:16] if ev.hash_prev else '(root)'}...")

    report.append("")
    report.append("=" * 40)
    report.append("AUDIT STATUS: " + ("PASS ✓" if validation_results['chain_valid'] and validation_results['signatures_valid'] else "FAIL ✗"))

    report_text = "\n".join(report)
    print(report_text)

    return report_text


def main():
    # Simulated task execution steps
    task_steps = [
        {
            "step_id": "step-001",
            "action_id": "action-001",
            "action_type": "select_tool",
            "type": "trajectory",
            "result": "success"
        },
        {
            "step_id": "step-002",
            "action_id": "action-002",
            "action_type": "remove_screw",
            "type": "trajectory",
            "result": "success"
        },
        {
            "step_id": "step-003",
            "action_id": "action-003",
            "action_type": "detach_part",
            "type": "sensor_reading",
            "result": "success"
        },
        {
            "step_id": "step-004",
            "action_id": "action-004",
            "action_type": "inspect",
            "type": "screenshot",
            "result": "completed"
        },
    ]

    task_id = "task-golden-001"

    # Step 1: Generate evidence package
    print("\n[1/4] Generating evidence package...")
    evidence_chain = generate_evidence_package(task_id, task_steps)

    # Step 2: Validate evidence package
    print("\n[2/4] Validating evidence package...")
    validation_results = validate_evidence_package(evidence_chain)

    # Step 3: Generate audit report
    print("\n[3/4] Generating audit report...")
    report = generate_audit_report(task_id, evidence_chain, validation_results)

    # Step 4: Final result
    print("\n[4/4] Final Result")
    print("=" * 60)

    if validation_results['chain_valid'] and validation_results['signatures_valid']:
        print("✓ GOLDEN TASK PASSED ✓")
        print()
        print("Evidence package successfully:")
        print("  - Generated with chain hashes")
        print("  - Signed with server secret")
        print("  - Chain integrity validated")
        print("  - Signatures verified")
        print("  - Audit report generated")
        print()
        print("CI GATE RESULT: PASS ✓")
        return 0
    else:
        print("✗ GOLDEN TASK FAILED ✗")
        print()
        for error in validation_results['errors']:
            print(f"  - {error}")
        print()
        print("CI GATE RESULT: FAIL ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
