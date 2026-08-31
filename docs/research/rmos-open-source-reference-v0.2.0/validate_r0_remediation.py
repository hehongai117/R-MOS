#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple

import yaml


class ValidationResult(NamedTuple):
    errors: list[str]
    result_files: int
    software_candidates: int
    normative_evidence: int
    a6_master_count: int
    a6_masters: set[str]
    missing_required_fields: list[str]
    numeric_scores_for_ineligible: list[str]


REQUIRED_DOCS = {
    "README.md",
    "outline.yaml",
    "fields.yaml",
    "candidate-register.yaml",
    "source-register.yaml",
    "domain-calibration-D03.md",
    "domain-calibration-D04.md",
    "scoring-matrix.md",
    "decision-matrix.md",
    "correction-ledger.md",
    "report.md",
}

ACTIVE_CONCLUSION_FILES = {
    "README.md",
    "scoring-matrix.md",
    "decision-matrix.md",
    "report.md",
}

FALSE_ACTIVE_PHRASES = {
    "C-0 六步流程是急停最小正确模型",
    "复制代码将迫使 R-MOS 整体以 AGPL 开源",
    "被取消的动作显式报 FAILED",
    "A6 0.1.1（2026-08-29 Approved）",
}

FIXED_SOURCE_TYPES = {
    "git_commit",
    "meaningful_commit",
    "contract_source",
    "license_mapping",
    "license_text",
    "source_snapshot",
}

FIRST_PASS_DISCOVERY_DOMAINS = {"D-01", "D-02", "D-05", "D-06", "D-07"}
FIRST_PASS_DISCOVERY_EVIDENCE = (
    "evidence/2026-08-30-five-domain-candidate-discovery-v0.1.0.md"
)


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _missing_fields(data: dict, required: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{field}" for field in required if field not in data]


def validate_package(package: Path, root: Path) -> ValidationResult:
    errors: list[str] = []
    missing_required_fields: list[str] = []
    numeric_scores_for_ineligible: list[str] = []

    if not package.is_dir():
        return ValidationResult(
            errors=[f"missing package: {package}"],
            result_files=0,
            software_candidates=0,
            normative_evidence=0,
            a6_master_count=0,
            a6_masters=set(),
            missing_required_fields=[],
            numeric_scores_for_ineligible=[],
        )

    historical = root / "docs/research/rmos-open-source-reference"
    if not historical.is_dir():
        errors.append("historical R0 package is missing")

    missing_docs = sorted(name for name in REQUIRED_DOCS if not (package / name).is_file())
    if missing_docs:
        errors.append(f"missing required docs: {missing_docs}")

    outline = _load_yaml(package / "outline.yaml")
    fields = _load_yaml(package / "fields.yaml")
    candidates_doc = _load_yaml(package / "candidate-register.yaml")
    sources_doc = _load_yaml(package / "source-register.yaml")

    if outline.get("meta", {}).get("status") != "RETURN_FOR_REVISION":
        errors.append("outline status must be RETURN_FOR_REVISION")
    if outline.get("meta", {}).get("binding_r1_input") is not False:
        errors.append("R0 must not be marked as binding R1 input")

    domains = outline.get("domains", [])
    domain_ids = {domain.get("id") for domain in domains}
    expected_domains = {f"D-{number:02d}" for number in range(1, 9)}
    if domain_ids != expected_domains:
        errors.append(f"domain denominator mismatch: {sorted(domain_ids)}")

    denominator = outline.get("a6_master_denominator", {})
    a6_masters = set(denominator.get("ids", []))
    a6_master_count = denominator.get("count", 0)
    if a6_master_count != 26 or len(a6_masters) != 26:
        errors.append(f"A6 denominator must be 26, got count={a6_master_count}, unique={len(a6_masters)}")
    if set(denominator.get("disputed", [])) != {"M-14", "M-19"}:
        errors.append("M-14 and M-19 must remain disputed")

    if candidates_doc.get("meta", {}).get("saturation_reached") is not False:
        errors.append("candidate register must not claim search saturation")
    candidate_domains = candidates_doc.get("domains", {})
    for domain_id in FIRST_PASS_DISCOVERY_DOMAINS:
        domain = candidate_domains.get(domain_id, {})
        if domain.get("status") != "FIRST_PASS_DISCOVERY_COMPLETE":
            errors.append(f"{domain_id} first-pass discovery status is not registered")
        software = [item for item in domain.get("candidates", []) if item.get("kind") == "software"]
        if len(software) < 4:
            errors.append(f"{domain_id} has fewer than four first-pass software candidates")
        if any(item.get("state") in {"PASS", "ELIGIBLE"} for item in software):
            errors.append(f"{domain_id} incorrectly promotes a discovery candidate")
    if not (package / FIRST_PASS_DISCOVERY_EVIDENCE).is_file():
        errors.append("five-domain first-pass discovery evidence is missing")
    search_records = {record.get("id"): record for record in candidates_doc.get("search_records", [])}
    sr03 = search_records.get("SR-03", {})
    if sr03.get("evidence") != FIRST_PASS_DISCOVERY_EVIDENCE:
        errors.append("SR-03 does not link the five-domain discovery evidence")
    if sr03.get("result") != "FIRST_PASS_RECORDED_NOT_SATURATED":
        errors.append("SR-03 must preserve the not-saturated boundary")

    sources = {source["id"]: source for source in sources_doc.get("sources", [])}
    for source_id, source in sources.items():
        source_type = source.get("type")
        if source_type not in FIXED_SOURCE_TYPES:
            continue
        revision = str(source.get("revision", ""))
        url = str(source.get("url", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            errors.append(f"{source_id} lacks a 40-character revision")
        if revision not in url:
            errors.append(f"{source_id} URL is not pinned to its revision")

    software_required = fields.get("software_required_fields", {})
    normative_required = fields.get("normative_required_fields", [])
    result_paths = sorted((package / "results").glob("*.json"))
    software_candidates = 0
    normative_evidence = 0

    for result_path in result_paths:
        data = _load_json(result_path)
        kind = data.get("_meta", {}).get("object_kind")
        if kind == "software_candidate":
            software_candidates += 1
            for group, required in software_required.items():
                missing_required_fields.extend(
                    _missing_fields(data.get(group, {}), required, f"{result_path.name}.{group}")
                )

            hard_gates = data.get("hard_gates", {})
            if set(hard_gates) != {f"OSS-G{number}" for number in range(1, 7)}:
                errors.append(f"{result_path.name} hard-gate set is incomplete")

            g4 = hard_gates.get("OSS-G4", {})
            if g4.get("verdict") == "PASS":
                refs = g4.get("evidence_refs", [])
                if not refs:
                    errors.append(f"{result_path.name} G4 PASS has no evidence refs")
                allowed_types = {"meaningful_commit", "release", "maintainer_support_statement"}
                if not any(sources.get(ref, {}).get("type") in allowed_types for ref in refs):
                    errors.append(f"{result_path.name} G4 PASS is not backed by valid fixed evidence")

            scoring = data.get("scoring", {})
            all_pass = all(gate.get("verdict") == "PASS" for gate in hard_gates.values())
            if not all_pass and scoring.get("eligibility") != "NOT_ELIGIBLE":
                errors.append(f"{result_path.name} must be NOT_ELIGIBLE")
            if scoring.get("eligibility") == "NOT_ELIGIBLE":
                for field in ("primary_numeric_score", "reviewer_numeric_score"):
                    if scoring.get(field) is not None:
                        numeric_scores_for_ineligible.append(f"{result_path.name}.{field}")

            for ref in data.get("rmos_decision_fields", {}).get("evidence_refs", []):
                if ref not in sources:
                    errors.append(f"{result_path.name} references unknown source {ref}")

        elif kind == "normative_evidence":
            normative_evidence += 1
            missing_required_fields.extend(
                _missing_fields(data.get("normative_evidence", {}), normative_required, f"{result_path.name}.normative_evidence")
            )
            if data.get("normative_assessment", {}).get("eligibility_for_oss_scoring") != "NOT_APPLICABLE":
                errors.append(f"{result_path.name} must not enter OSS scoring")
        else:
            errors.append(f"{result_path.name} has unknown object_kind {kind}")

    if len(result_paths) != 8:
        errors.append(f"expected 8 corrected result files, got {len(result_paths)}")
    if software_candidates != 6 or normative_evidence != 2:
        errors.append(
            f"expected 6 software and 2 normative results, got {software_candidates} and {normative_evidence}"
        )

    if missing_required_fields:
        errors.append(f"missing required fields: {missing_required_fields}")
    if numeric_scores_for_ineligible:
        errors.append(f"ineligible candidates have numeric scores: {numeric_scores_for_ineligible}")

    active_text = "\n".join(
        (package / name).read_text(encoding="utf-8") for name in ACTIVE_CONCLUSION_FILES
    )
    active_text += "\n" + "\n".join(path.read_text(encoding="utf-8") for path in result_paths)
    for phrase in FALSE_ACTIVE_PHRASES:
        if phrase in active_text:
            errors.append(f"known false active conclusion remains: {phrase}")
    if any('"last_push"' in path.read_text(encoding="utf-8") for path in result_paths):
        errors.append("a corrected result still carries last_push as evidence")

    opentcs = _load_json(package / "results/opentcs.json")
    license_text = opentcs["security_license_supply_chain"]["license_spdx_and_exceptions"]
    if "no path mapping to LGPL-2.1-only" not in license_text:
        errors.append("openTCS LGPL correction is missing")
    vda = _load_json(package / "results/vda5050.json")
    if vda["normative_evidence"].get("safety_role") != "NOT_A_SAFETY_STANDARD":
        errors.append("VDA 5050 must be explicitly excluded as a safety standard")

    return ValidationResult(
        errors=errors,
        result_files=len(result_paths),
        software_candidates=software_candidates,
        normative_evidence=normative_evidence,
        a6_master_count=a6_master_count,
        a6_masters=a6_masters,
        missing_required_fields=missing_required_fields,
        numeric_scores_for_ineligible=numeric_scores_for_ineligible,
    )


def main() -> int:
    package = Path(__file__).resolve().parent
    root = package.parents[2]
    result = validate_package(package, root)
    if result.errors:
        print("R0 remediation gate: FAIL")
        for error in result.errors:
            print(f"- {error}")
        return 1
    print("R0 remediation gate: PASS")
    print(
        f"results={result.result_files}, software={result.software_candidates}, "
        f"normative={result.normative_evidence}, a6_masters={result.a6_master_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
