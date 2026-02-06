"""
Gate-1 B-002：deny 审计入口门禁测试。

目标：
- 禁止在 app 目录散落出现 deny 审计写入字面量
- 仅允许 access_control.py 作为 deny 审计入口文件
"""
from __future__ import annotations

import re
from pathlib import Path


ALLOWLIST = {
    Path("app/services/access_control.py"),
}


def _iter_python_files(app_root: Path):
    for path in app_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _relative(path: Path, root: Path) -> Path:
    return path.relative_to(root.parent)


def test_deny_audit_entrypoint_is_singleton():
    backend_root = Path(__file__).resolve().parents[2]
    app_root = backend_root / "app"

    deny_literal = re.compile(r"decision\\s*=\\s*['\\\"]deny['\\\"]")
    violations: list[str] = []

    for file_path in _iter_python_files(app_root):
        rel = _relative(file_path, app_root)
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        is_allowlisted = rel in ALLOWLIST

        if not is_allowlisted:
            for idx, line in enumerate(lines, start=1):
                if deny_literal.search(line):
                    violations.append(f"{rel}:{idx} 出现 deny 字面量: {line.strip()}")

        if not is_allowlisted and ".log_event(" in text and "decision" in text and "deny" in text:
            hit_lines = [
                str(i)
                for i, line in enumerate(lines, start=1)
                if ".log_event(" in line or "decision" in line or "deny" in line
            ][:6]
            violations.append(
                f"{rel} 出现疑似散落 deny 写入组合（行 {', '.join(hit_lines)}）"
            )

    assert violations == [], "发现 deny 审计散落入口:\\n" + "\\n".join(violations)
