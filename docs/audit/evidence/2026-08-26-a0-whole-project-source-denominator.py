#!/usr/bin/env python3
"""Enumerate and classify every Git-tracked R-MOS file at the A0 baseline."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import PurePosixPath


DEFAULT_BASELINE = "29d2a5889e3b320a3e777e3d8c19efbbe31c0294"


def classify(path: str) -> str:
    pure = PurePosixPath(path)
    name = pure.name
    suffix = pure.suffix.lower()
    parts = pure.parts

    if suffix == ".md":
        return "documents_markdown"
    if suffix in {".docx", ".doc", ".xlsx", ".xls", ".pdf", ".pptx", ".ppt"}:
        return "documents_binary"
    if "tests" in parts or "e2e" in parts or re.search(r"test[^/]*\.(py|ts|tsx)$", name):
        return "tests"
    if "alembic" in parts and (
        "versions" in parts or name in {"env.py", "script.py.mako"}
    ):
        return "migrations"
    if path.startswith("docs/audit/evidence/") and suffix == ".py":
        return "audit_evidence_scripts"
    if any(part in {"app", "src", "schemas"} for part in parts) or name == "main.py":
        return "application"
    if any(part in {"public", "robot-assets", "storage", "modules"} for part in parts):
        return "assets_modules"
    if suffix in {".glb", ".stl", ".urdf", ".obj", ".dae", ".png", ".jpg", ".jpeg", ".svg"}:
        return "assets_modules"
    if "scripts" in parts or suffix == ".sh":
        return "scripts"
    if name in {
        "package-lock.json", "package.json", "requirements.txt", "Dockerfile",
        "Makefile", ".gitattributes", ".gitignore", ".coveragerc", ".coverage",
        ".npmrc", ".nvmrc", ".python-version",
    }:
        return "config_dependency_generated"
    if name.startswith("docker-compose") or name.endswith((".config.js", ".config.ts")):
        return "config_dependency_generated"
    if name in {".env.example", ".env.demo"}:
        return "config_dependency_generated"
    if suffix in {
        ".ini", ".toml", ".yaml", ".yml", ".json", ".conf", ".cjs",
        ".xml", ".html", ".txt",
    }:
        return "config_dependency_generated"
    return "unclassified"


def main() -> int:
    baseline = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASELINE
    output = subprocess.check_output(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", baseline],
        text=True,
    )
    paths = [line for line in output.splitlines() if line]
    counts = Counter(classify(path) for path in paths)
    unclassified = [path for path in paths if classify(path) == "unclassified"]
    result = {
        "baseline": baseline,
        "tracked_files": len(paths),
        "categories": dict(sorted(counts.items())),
        "unclassified": unclassified,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main())
