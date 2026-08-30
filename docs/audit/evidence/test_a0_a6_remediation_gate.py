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
    assert reports["A1"].name.endswith("v0.2.1.md")
    assert all(
        path.name.endswith("v0.2.0.md")
        for stage, path in reports.items()
        if stage != "A1"
    )


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


def test_backtick_evidence_paths_are_checked(tmp_path: Path) -> None:
    gate = load_gate()
    source = tmp_path / "docs" / "audit" / "report.md"
    evidence = source.parent / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "existing.py").write_text("# exists\n", encoding="utf-8")
    source.write_text(
        "现有：`evidence/existing.py`\n缺失：`evidence/missing.py`\n",
        encoding="utf-8",
    )

    errors = gate.find_backtick_path_errors([source], tmp_path)

    assert errors == [f"{source}: missing backtick path evidence/missing.py"]


def test_product_ledger_is_counted_instead_of_trusting_declared_text(
    tmp_path: Path,
) -> None:
    gate = load_gate()
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        "| M-01 | P0 | first |\n"
        "| M-02 | P1 | second |\n"
        "| M-02 | P1 | duplicate |\n",
        encoding="utf-8",
    )

    errors = gate.validate_product_ledger(
        ledger,
        {"TOTAL": 3, "P0": 1, "P1": 1, "P2": 1},
    )

    assert f"{ledger}: duplicate Master_ID M-02" in errors
    assert f"{ledger}: declared P2=1 but ledger has 0" in errors


def test_historical_readme_claims_are_ignored_but_current_claims_are_rejected() -> None:
    gate = load_gate()
    readme = (
        "## 当前状态\n当前材料仍待修订。\n"
        "## 历史状态快照（已被订正）\n历史材料声称全部收口。\n"
    )

    current = gate.current_readme_section(readme)

    assert gate.find_forbidden_completion_claims_in_text("README current", current) == []
    assert gate.find_forbidden_completion_claims_in_text(
        "README current", "当前审计序列完成。"
    ) == ["README current: forbidden completion claim 审计序列完成"]


def test_remediation_package_satisfies_current_gate() -> None:
    gate = load_gate()

    assert gate.validate_package(REPO_ROOT) == []
