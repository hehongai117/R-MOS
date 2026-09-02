#!/usr/bin/env python3
"""Recalculate Git and static-code drift between B-ASIS and a target commit.

This script reads Git objects and Python source only. It does not import the
application, connect to a database, start services, access the network, or
write output files.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys
from collections import Counter


BASELINE = "29d2a5889e3b320a3e777e3d8c19efbbe31c0294"
BREF_CANDIDATE = "361eaac85002eec4e9388ae4d7f30c2e3591eee6"
TARGET = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
ROOT = pathlib.Path(__file__).resolve().parents[3]


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "core.quotePath=false", *args], cwd=ROOT, text=True
    )


def load_classifier():
    path = pathlib.Path(__file__).with_name(
        "2026-08-26-a0-whole-project-source-denominator.py"
    )
    spec = importlib.util.spec_from_file_location("a0_denominator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify


def tree_paths(commit: str) -> list[str]:
    return [p for p in git("ls-tree", "-r", "--name-only", commit).splitlines() if p]


def normalized_class(path: str, classify) -> str:
    category = classify(path)
    if category == "unclassified" and path.startswith("docs/research/") and path.endswith(".py"):
        return "research_validation_scripts"
    return category


def source_at(commit: str, path: str) -> str:
    return git("show", f"{commit}:{path}")


def static_python_facts(commit: str) -> dict[str, int]:
    paths = [
        p
        for p in tree_paths(commit)
        if p == "r-mos-backend/main.py"
        or (p.startswith("r-mos-backend/app/") and p.endswith(".py"))
    ]
    http = ws = 0
    methods: Counter[str] = Counter()
    tables: set[str] = set()
    route_modules: set[str] = set()
    for path in paths:
        tree = ast.parse(source_at(commit, path), filename=path)
        module_has_route = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    call = dec if isinstance(dec, ast.Call) else None
                    attr = call.func if call else dec
                    if not isinstance(attr, ast.Attribute):
                        continue
                    if attr.attr in HTTP_VERBS:
                        http += 1
                        methods[attr.attr.upper()] += 1
                        module_has_route = True
                    elif attr.attr == "websocket":
                        ws += 1
                        module_has_route = True
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "__tablename__"
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        tables.add(node.value.value)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Table"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                tables.add(node.args[0].value)
        if module_has_route:
            route_modules.add(path)
    return {
        "http_route_decorators": http,
        "http_methods": dict(sorted(methods.items())),
        "websocket_route_decorators": ws,
        "static_tables": len(tables),
        "route_modules": len(route_modules),
    }


def changed_group(path: str) -> str:
    if path.startswith("r-mos-backend/app/") or path == "r-mos-backend/main.py":
        return "backend_application"
    if path.startswith("r-mos-backend/tests/"):
        return "backend_tests"
    if path.startswith("r-mos-frontend/src/"):
        return "frontend_application"
    if path.startswith("r-mos-backend/alembic/"):
        return "migrations"
    if path in {
        "r-mos-backend/requirements.txt",
        "r-mos-frontend/package.json",
        "r-mos-frontend/package-lock.json",
    }:
        return "dependency_manifests"
    if path.startswith(".github/") or path in {"docker-compose.yml", ".env.example"}:
        return "ci_or_config"
    if path.startswith("docs/audit/"):
        return "audit_material"
    if path.startswith("docs/research/"):
        return "research_material"
    if path.startswith("docs/") or path.startswith("docs-archive/"):
        return "other_documentation"
    return "other"


def intervention_group(path: str) -> str:
    if path == "AGENTS.md":
        return "rule"
    if path.startswith("r-mos-backend/scripts/"):
        return "script"
    if (
        "/tests/" in path
        or "/__tests__/" in path
        or path.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
    ):
        return "test"
    return "application_or_runtime"


def main() -> int:
    classify = load_classifier()
    target = git("rev-parse", TARGET).strip()
    baseline_paths = tree_paths(BASELINE)
    target_paths = tree_paths(target)
    baseline_counts = Counter(normalized_class(p, classify) for p in baseline_paths)
    target_counts = Counter(normalized_class(p, classify) for p in target_paths)
    changed = [
        p
        for p in git("diff", "--name-only", f"{BASELINE}..{target}").splitlines()
        if p
    ]
    changed_groups = Counter(changed_group(p) for p in changed)
    code_groups = {
        "backend_application",
        "backend_tests",
        "frontend_application",
        "migrations",
        "dependency_manifests",
        "ci_or_config",
        "other",
    }
    commits = git("rev-list", "--reverse", f"{BASELINE}..{target}").splitlines()
    non_document_commits: list[dict[str, object]] = []
    for commit in commits:
        paths = [
            p
            for p in git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()
            if p
        ]
        non_doc = [p for p in paths if changed_group(p) in code_groups]
        if non_doc:
            non_document_commits.append(
                {
                    "commit": commit,
                    "subject": git("show", "-s", "--format=%s", commit).strip(),
                    "paths": non_doc,
                }
            )

    intervention_commits = git(
        "rev-list", "--reverse", f"{BREF_CANDIDATE}..{BASELINE}"
    ).splitlines()
    intervention_code_commits: list[str] = []
    intervention_document_commits: list[str] = []
    intervention_objects: set[str] = set()
    for commit in intervention_commits:
        paths = [
            p
            for p in git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", commit
            ).splitlines()
            if p
        ]
        non_docs = [
            p
            for p in paths
            if not p.startswith(("docs/", "docs-archive/"))
            and p not in {"CLAUDE.md"}
            and not p.startswith(".claude/")
        ]
        substantive = [p for p in non_docs if p != "AGENTS.md"]
        if substantive:
            intervention_code_commits.append(commit)
            intervention_objects.update(non_docs)
        else:
            intervention_document_commits.append(commit)
    changed_rules = {
        p
        for p in git(
            "diff", "--name-only", f"{BREF_CANDIDATE}..{BASELINE}", "--", "AGENTS.md"
        ).splitlines()
        if p
    }
    intervention_objects.update(changed_rules)
    intervention_object_counts = Counter(
        intervention_group(path) for path in intervention_objects
    )

    result = {
        "baseline": BASELINE,
        "target": target,
        "commits_since_baseline": len(commits),
        "changed_files": len(changed),
        "tracked_files": {"baseline": len(baseline_paths), "target": len(target_paths)},
        "category_counts": {
            "baseline": dict(sorted(baseline_counts.items())),
            "target": dict(sorted(target_counts.items())),
        },
        "unclassified": {
            "baseline": [p for p in baseline_paths if normalized_class(p, classify) == "unclassified"],
            "target": [p for p in target_paths if normalized_class(p, classify) == "unclassified"],
        },
        "changed_groups": dict(sorted(changed_groups.items())),
        "static_python": {
            "baseline": static_python_facts(BASELINE),
            "target": static_python_facts(target),
        },
        "non_document_commits": non_document_commits,
        "bref_candidate_intervention": {
            "bref_candidate": BREF_CANDIDATE,
            "baseline": BASELINE,
            "commits": len(intervention_commits),
            "application_test_script_or_rule_commits": len(
                intervention_code_commits
            ),
            "documentation_commits": len(intervention_document_commits),
            "unique_objects": len(intervention_objects),
            "object_groups": dict(sorted(intervention_object_counts.items())),
            "application_test_script_or_rule_commit_ids": intervention_code_commits,
            "documentation_commit_ids": intervention_document_commits,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["unclassified"]["baseline"] or result["unclassified"]["target"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
