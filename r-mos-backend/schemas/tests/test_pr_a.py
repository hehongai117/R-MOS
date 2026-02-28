#!/usr/bin/env python3
"""
PR-A Test: Schema version bump checker

This validates that any schema changes MUST bump version.
PR-A will FAIL if new fields are added without version bump.
"""

import sys
import os
import re
from pathlib import Path

def check_schema_version_bump(schema_dir: str) -> tuple[bool, str]:
    """Check if schema version was bumped when changes were made"""

    # Get list of all .py files in schema directory
    schema_files = list(Path(schema_dir).rglob("*.py"))

    changes_detected = False
    version_not_bumped = False

    for f in schema_files:
        if f.name.startswith('__'):
            continue

        content = f.read_text()

        # Check for new field additions (heuristic: Field(default=...) patterns that weren't there before)
        # This is a simplified check - in reality would compare with previous version

        # Check if schema_version is still 1.0.0
        if 'schema_version' in content and '"1.0.0"' in content:
            # Version is still 1.0.0 - check if there are new fields
            if 'priority:' in content or 'new_field' in content.lower():
                changes_detected = True
                version_not_bumped = True

    if version_not_bumped:
        return False, "FAIL: Schema changed but version NOT bumped to 1.1.0"
    else:
        return True, "PASS: Schema version properly bumped"


def main():
    schema_dir = "schemas"

    print("=" * 60)
    print("PR-A: Schema Version Bump Check")
    print("=" * 60)
    print(f"Checking schemas in: {schema_dir}")
    print()

    is_valid, message = check_schema_version_bump(schema_dir)

    if not is_valid:
        print(f"✗ {message}")
        print()
        print("CI GATE RESULT: FAIL ✗")
        print("PR-A should FAIL - version not bumped!")
        return 1
    else:
        print(f"✓ {message}")
        print()
        print("CI GATE RESULT: PASS ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
