from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/research/rmos-open-source-reference-v0.2.0"
GATE = PACKAGE / "validate_r0_remediation.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("r0_remediation_gate", GATE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GATE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corrected_package_exists_and_preserves_historical_package() -> None:
    assert (ROOT / "docs/research/rmos-open-source-reference").is_dir()
    assert PACKAGE.is_dir()
    assert (PACKAGE / "README.md").is_file()


def test_gate_rejects_known_false_conclusions() -> None:
    gate = _load_gate()
    result = gate.validate_package(PACKAGE, ROOT)
    assert result.errors == []
    assert result.software_candidates == 6
    assert result.normative_evidence == 2
    assert result.a6_master_count == 26


def test_all_corrected_results_are_structurally_complete() -> None:
    gate = _load_gate()
    result = gate.validate_package(PACKAGE, ROOT)
    assert result.result_files == 8
    assert result.missing_required_fields == []


def test_unqualified_candidates_are_not_numerically_scored() -> None:
    gate = _load_gate()
    result = gate.validate_package(PACKAGE, ROOT)
    assert result.numeric_scores_for_ineligible == []


@pytest.mark.parametrize("master_id", ["M-01", "M-02", "M-06", "M-13", "M-18a"])
def test_cut_scope_p0_is_restored_to_denominator(master_id: str) -> None:
    gate = _load_gate()
    result = gate.validate_package(PACKAGE, ROOT)
    assert master_id in result.a6_masters
