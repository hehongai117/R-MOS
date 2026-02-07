"""Gate-2 帮助输出一致性门禁测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_smoke_help_output_contains_required_keywords() -> None:
    """验证 --help 输出包含关键参数与退出码，防止帮助文本回退。"""
    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", "-lc", "./scripts/run_gate2_smoke.sh --help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "执行 --help 失败，应返回 0。\n"
        f"实际退出码：{result.returncode}\n"
        f"stderr：{result.stderr}"
    )

    expected_keywords = [
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

    for keyword in expected_keywords:
        assert keyword in result.stdout, f"帮助输出缺少关键字：{keyword}"
