#!/usr/bin/env python3
"""Validate the corrected A0-A6 audit package without touching runtime state."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path


REPORT_PATHS = {
    "A0": "docs/audit/2026-08-29-a0-baseline-and-source-governance-audit-report-v0.2.0.md",
    "A1": "docs/audit/2026-08-29-a1-system-function-and-asset-inventory-v0.2.0.md",
    "A2": "docs/audit/2026-08-29-a2-user-roles-and-business-closure-audit-report-v0.2.0.md",
    "A3": "docs/audit/2026-08-29-a3-current-architecture-and-data-boundaries-v0.2.0.md",
    "A4": "docs/audit/2026-08-29-a4-security-control-and-realtime-audit-report-v0.2.0.md",
    "A5": "docs/audit/2026-08-29-a5-quality-operations-and-delivery-audit-report-v0.2.0.md",
    "A6": "docs/audit/2026-08-29-a6-master-audit-report-and-decision-input-v0.2.0.md",
}

SUPPORT_PATHS = (
    "docs/audit/README.md",
    "docs/audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md",
    "docs/audit/evidence/2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md",
    "docs/handover/2026-08-29-a0-a6-independent-review-remediation-handover-v0.1.0.md",
    "docs/plans/2026-08-29-a0-a6-independent-review-remediation.md",
)

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FORBIDDEN_COMPLETION_CLAIMS = (
    "全部门禁达标",
    "审计序列完成",
    "全部收口",
)


def expected_reports(repo_root: Path) -> dict[str, Path]:
    return {stage: repo_root / relative for stage, relative in REPORT_PATHS.items()}


def _local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split("#", 1)[0]
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    candidate = Path(target)
    return candidate if candidate.is_absolute() else source.parent / candidate


def find_local_link_errors(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        if not source.exists():
            errors.append(f"{source}: source file missing")
            continue
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = _local_target(source, raw_target)
            if target is not None and not target.exists():
                errors.append(f"{source}: missing local link target {raw_target}")
    return errors


def find_forbidden_completion_claims(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        for claim in FORBIDDEN_COMPLETION_CLAIMS:
            if claim in text:
                errors.append(f"{source}: forbidden completion claim {claim}")
    return errors


def validate_package(repo_root: Path) -> list[str]:
    errors: list[str] = []
    reports = expected_reports(repo_root)

    for stage, path in reports.items():
        if not path.exists():
            errors.append(f"{stage}: corrected report missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if "版本：0.2.0" not in text:
            errors.append(f"{stage}: version 0.2.0 marker missing")
        if "复核状态：RETURN FOR REVISION" not in text:
            errors.append(f"{stage}: truthful RETURN FOR REVISION status missing")
        if "事实基线：29d2a5889e3b320a3e777e3d8c19efbbe31c0294" not in text:
            errors.append(f"{stage}: fixed fact baseline missing")
        if stage != "A0" and "M-AUD-06：BLOCKED" not in text:
            errors.append(f"{stage}: M-AUD-06 blocked marker missing")

    a6 = reports["A6"]
    if a6.exists():
        a6_text = a6.read_text(encoding="utf-8")
        for marker in (
            "产品问题总数：26",
            "P0：8",
            "P1：11",
            "P2：7",
            "审计治理阻断项：5",
        ):
            if marker not in a6_text:
                errors.append(f"A6: corrected total missing: {marker}")

    current_files = list(reports.values()) + [repo_root / path for path in SUPPORT_PATHS]
    errors.extend(find_local_link_errors(current_files))
    errors.extend(find_forbidden_completion_claims(reports.values()))
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    errors = validate_package(repo_root)
    if errors:
        print("A0-A6 remediation gate: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("A0-A6 remediation gate: PASS")
    print("7 corrected reports; product findings 26 (P0 8 / P1 11 / P2 7); governance blockers 5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
