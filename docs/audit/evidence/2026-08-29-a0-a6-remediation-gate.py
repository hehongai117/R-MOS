#!/usr/bin/env python3
"""Validate the corrected A0-A6 audit package without touching runtime state."""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path


REPORT_PATHS = {
    "A0": "docs/audit/2026-09-02-a0-baseline-and-source-governance-audit-report-v0.2.1.md",
    "A1": "docs/audit/2026-08-30-a1-system-function-and-asset-inventory-v0.2.1.md",
    "A2": "docs/audit/2026-08-29-a2-user-roles-and-business-closure-audit-report-v0.2.0.md",
    "A3": "docs/audit/2026-08-29-a3-current-architecture-and-data-boundaries-v0.2.0.md",
    "A4": "docs/audit/2026-08-29-a4-security-control-and-realtime-audit-report-v0.2.0.md",
    "A5": "docs/audit/2026-08-29-a5-quality-operations-and-delivery-audit-report-v0.2.0.md",
    "A6": "docs/audit/2026-08-29-a6-master-audit-report-and-decision-input-v0.2.0.md",
}

REPORT_VERSIONS = {
    "A0": "0.2.1",
    "A1": "0.2.1",
    "A2": "0.2.0",
    "A3": "0.2.0",
    "A4": "0.2.0",
    "A5": "0.2.0",
    "A6": "0.2.0",
}

SUPPORT_PATHS = (
    "docs/audit/README.md",
    "docs/audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md",
    "docs/audit/evidence/2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md",
    "docs/audit/evidence/2026-08-30-realtime-channel-remediation-verification-v0.1.0.md",
    "docs/audit/evidence/2026-08-31-current-environment-and-drift-fingerprint-v0.1.0.md",
    "docs/audit/evidence/2026-09-02-a0-board-preconditions-confirmation-v0.1.0.md",
    "docs/audit/evidence/2026-09-02-a0-approved-fingerprint-probe-results-v0.1.0.md",
    "docs/audit/evidence/2026-09-02-a0-pre-r0-human-and-probe-action-pack-v0.1.0.md",
    "docs/handover/2026-08-30-a0-a6-independent-review-remediation-handover-v0.1.1.md",
    "docs/handover/2026-08-31-r1-start-readiness-v0.1.0.md",
    "docs/plans/2026-08-29-a0-a6-independent-review-remediation.md",
)

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
BACKTICK_PATH_PATTERN = re.compile(
    r"`((?:docs/|evidence/|\.\.?/)[^`\s]+\.(?:md|py|ya?ml|json))`"
)
PRODUCT_ROW_PATTERN = re.compile(
    r"^\|\s*(M-\d{2}(?:[ab])?)\s*\|\s*(P[012])\s*\|", re.MULTILINE
)
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


def find_backtick_path_errors(files: Iterable[Path], repo_root: Path) -> list[str]:
    errors: list[str] = []
    for source in files:
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        for raw_target in BACKTICK_PATH_PATTERN.findall(text):
            target_text = raw_target.split("#", 1)[0]
            target = (
                repo_root / target_text
                if target_text.startswith("docs/")
                else source.parent / target_text
            )
            if not target.exists():
                errors.append(f"{source}: missing backtick path {raw_target}")
    return errors


def validate_product_ledger(
    ledger: Path, declared_counts: dict[str, int]
) -> list[str]:
    if not ledger.exists():
        return [f"{ledger}: product ledger missing"]

    rows = PRODUCT_ROW_PATTERN.findall(ledger.read_text(encoding="utf-8"))
    ids = [master_id for master_id, _severity in rows]
    severity_counts = Counter(severity for _master_id, severity in rows)
    errors: list[str] = []

    for master_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"{ledger}: duplicate Master_ID {master_id}")

    actual_counts = {"TOTAL": len(rows), **severity_counts}
    for key in ("TOTAL", "P0", "P1", "P2"):
        declared = declared_counts[key]
        actual = actual_counts.get(key, 0)
        if declared != actual:
            errors.append(f"{ledger}: declared {key}={declared} but ledger has {actual}")
    return errors


def parse_declared_product_counts(a6_text: str) -> dict[str, int] | None:
    patterns = {
        "TOTAL": r"产品问题总数：(\d+)",
        "P0": r"^- P0：(\d+)$",
        "P1": r"^- P1：(\d+)$",
        "P2": r"^- P2：(\d+)$",
    }
    values: dict[str, int] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, a6_text, re.MULTILINE)
        if match is None:
            return None
        values[key] = int(match.group(1))
    return values


def find_forbidden_completion_claims_in_text(label: str, text: str) -> list[str]:
    return [
        f"{label}: forbidden completion claim {claim}"
        for claim in FORBIDDEN_COMPLETION_CLAIMS
        if claim in text
    ]


def find_forbidden_completion_claims(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        errors.extend(find_forbidden_completion_claims_in_text(str(source), text))
    return errors


def current_readme_section(readme_text: str) -> str:
    return readme_text.split("## 历史状态快照", 1)[0]


def validate_package(repo_root: Path) -> list[str]:
    errors: list[str] = []
    reports = expected_reports(repo_root)

    for stage, path in reports.items():
        if not path.exists():
            errors.append(f"{stage}: corrected report missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        expected_version = REPORT_VERSIONS[stage]
        if f"版本：{expected_version}" not in text:
            errors.append(f"{stage}: version {expected_version} marker missing")
        if stage == "A0":
            if "阶段状态：CONDITIONAL / `REOPENED / IN REVIEW`" not in text:
                errors.append("A0: truthful reopened/in-review status missing")
            if "正式批准：PENDING" not in text:
                errors.append("A0: pending final approval marker missing")
        elif "复核状态：RETURN FOR REVISION" not in text:
            errors.append(f"{stage}: truthful RETURN FOR REVISION status missing")
        if "29d2a5889e3b320a3e777e3d8c19efbbe31c0294" not in text:
            errors.append(f"{stage}: fixed fact baseline missing")
        if stage != "A0" and "M-AUD-06：BLOCKED" not in text:
            errors.append(f"{stage}: M-AUD-06 blocked marker missing")

    a6 = reports["A6"]
    if a6.exists():
        a6_text = a6.read_text(encoding="utf-8")
        declared_counts = parse_declared_product_counts(a6_text)
        expected_counts = {"TOTAL": 26, "P0": 8, "P1": 11, "P2": 7}
        if declared_counts is None:
            errors.append("A6: declared product counts are incomplete")
        else:
            for key, expected in expected_counts.items():
                if declared_counts[key] != expected:
                    errors.append(
                        f"A6: expected {key}={expected} but report declares "
                        f"{declared_counts[key]}"
                    )
            ledger = (
                repo_root
                / "docs/audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md"
            )
            errors.extend(validate_product_ledger(ledger, declared_counts))
        if "审计治理阻断项：5" not in a6_text:
            errors.append("A6: corrected governance blocker total missing")

    current_files = list(reports.values()) + [repo_root / path for path in SUPPORT_PATHS]
    errors.extend(find_local_link_errors(current_files))
    errors.extend(find_backtick_path_errors(current_files, repo_root))

    governance = repo_root / "docs/audit/evidence/2026-08-29-a0-a6-governance-closure-pack-v0.1.0.md"
    handovers = [
        repo_root
        / "docs/handover/2026-08-30-a0-a6-independent-review-remediation-handover-v0.1.1.md",
        repo_root / "docs/handover/2026-08-31-r1-start-readiness-v0.1.0.md",
    ]
    errors.extend(
        find_forbidden_completion_claims(
            [*reports.values(), governance, *handovers]
        )
    )
    readme = repo_root / SUPPORT_PATHS[0]
    if readme.exists():
        errors.extend(
            find_forbidden_completion_claims_in_text(
                f"{readme} current section",
                current_readme_section(readme.read_text(encoding="utf-8")),
            )
        )
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
