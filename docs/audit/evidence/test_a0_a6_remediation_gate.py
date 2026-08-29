from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_PATH = Path(__file__).with_name("2026-08-29-a0-a6-remediation-gate.py")


def load_gate():
    spec = importlib.util.spec_from_file_location("a0_a6_remediation_gate", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_expected_reports_cover_a0_through_a6() -> None:
    gate = load_gate()

    reports = gate.expected_reports(REPO_ROOT)

    assert list(reports) == [f"A{index}" for index in range(7)]
    assert all(path.name.endswith("v0.2.0.md") for path in reports.values())


def test_local_link_checker_ignores_external_and_reports_missing(tmp_path: Path) -> None:
    gate = load_gate()
    source = tmp_path / "source.md"
    existing = tmp_path / "existing.md"
    existing.write_text("ok\n", encoding="utf-8")
    source.write_text(
        "[existing](existing.md)\n"
        "[section](#section)\n"
        "[external](https://example.com)\n"
        "[missing](missing.md)\n",
        encoding="utf-8",
    )

    errors = gate.find_local_link_errors([source])

    assert errors == [f"{source}: missing local link target missing.md"]


def test_forbidden_completion_claims_are_rejected(tmp_path: Path) -> None:
    gate = load_gate()
    source = tmp_path / "report.md"
    source.write_text("本阶段全部收口。\n", encoding="utf-8")

    errors = gate.find_forbidden_completion_claims([source])

    assert errors == [f"{source}: forbidden completion claim 全部收口"]


def test_remediation_package_satisfies_current_gate() -> None:
    gate = load_gate()

    assert gate.validate_package(REPO_ROOT) == []
