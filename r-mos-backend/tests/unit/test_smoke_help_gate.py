"""Gate-2 A-007：--help 输出一致性门禁测试（防回退）。"""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_smoke_help_contains_expected_markers() -> None:
    """验证 --help 输出包含关键参数与退出码标记。"""
    repo_root = Path(__file__).resolve().parents[2]
    cmd = 'bash -lc "./scripts/run_gate2_smoke.sh --help"'
    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        shell=True,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "FAIL：--help 退出码非0，"
        f"stderr={result.stderr.strip()[:200]}"
    )

    required = [
        "--e2e",
        "--audit",
        "--help",
        "退出码说明",
        "  2",
        "  3",
        "  4",
        "  10",
        "  11",
        "  12",
        "  13",
        "  20",
        "  21",
        "  22",
        "  23",
        "  24",
    ]
    missing = [key for key in required if key not in (result.stdout or "")]
    assert missing == [], "FAIL：--help 缺少关键字：" + "，".join(missing)
