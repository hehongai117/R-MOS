#!/usr/bin/env python3
"""
PR-B Test: DRI Approval Check

This validates that any changes to schemas/** must have DRI approval.
PR-B will FAIL if schemas changed without @backend (@architect) approval.
"""

import sys
import os
from pathlib import Path

# DRI Matrix
DRI_APPROVAL = {
    "schemas/fsm/": "@backend",
    "schemas/evidence/": "@backend",
    "schemas/agent/": "@ai-engineer",
    "schemas/knowledge/": "@ai-engineer",
}


def check_dri_approval(schema_dir: str, pr_approvals: list[str], require_dri: bool = True) -> tuple[bool, str]:
    """Check if DRI approved the schema changes"""

    # Get list of changed schema files
    schema_files = list(Path(schema_dir).rglob("*.py"))

    files_changed = []
    for f in schema_files:
        if f.name.startswith('__'):
            continue
        # Check if file was modified (simplified - in reality would check git diff)
        content = f.read_text()
        if len(content) > 0:
            files_changed.append(str(f))

    if not files_changed:
        return True, "No schema files changed"

    # Any change to schemas/** requires DRI by default
    if require_dri:
        required_dri = {"@backend"}  # Default DRI for schemas
    else:
        # Check if any specific DRI required
        required_dri = set()
        for f in files_changed:
            for pattern, dri in DRI_APPROVAL.items():
                if pattern in f:
                    required_dri.add(dri)

    # If no DRI required, no approval needed
    if not required_dri:
        return True, "No DRI required for these files"

    # Check if approvals include required DRI
    approved_dri = set(pr_approvals)

    missing_approvals = required_dri - approved_dri

    if missing_approvals:
        return False, f"FAIL: Missing DRI approval from: {missing_approvals}"

    return True, f"PASS: All required DRI approvals present: {approved_dri}"


def main():
    print("=" * 60)
    print("PR-B: DRI Approval Check")
    print("=" * 60)
    print()

    # Simulate PR-B: no DRI approval
    print("Test: PR-B with NO DRI approval")
    print("-" * 40)

    is_valid, message = check_dri_approval("schemas", [])
    print(f"Result: {message}")

    if not is_valid:
        print()
        print("CI GATE RESULT: FAIL ✗ (Expected - no DRI approval)")
    else:
        print("ERROR: Should have failed!")
        return 1

    # Simulate PR with wrong approval (not DRI)
    print()
    print("Test: PR-B with wrong approval (@frontend instead of @backend)")
    print("-" * 40)

    is_valid, message = check_dri_approval("schemas", ["@frontend", "@product"])
    print(f"Result: {message}")

    if not is_valid:
        print()
        print("CI GATE RESULT: FAIL ✗ (Expected - wrong DRI)")
    else:
        print("ERROR: Should have failed!")
        return 1

    # Simulate correct approval
    print()
    print("Test: PR-B with correct DRI approval")
    print("-" * 40)

    is_valid, message = check_dri_approval("schemas", ["@backend"])
    print(f"Result: {message}")

    if is_valid:
        print()
        print("CI GATE RESULT: PASS ✓ (Expected - has DRI approval)")
        return 0
    else:
        print("ERROR: Should have passed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
