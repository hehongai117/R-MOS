"""Gate-2 E-001：无副作用工具执行器（最小读链路）。"""
from __future__ import annotations

from typing import Any


def execute_read_tool(
    *,
    intent: str,
    tool_name: str,
    skill_id: str | None,
    tool_args: dict[str, Any],
) -> dict[str, Any]:
    """执行最小读工具路径。

    约束：
    - 仅返回确定性结果
    - 不触发外部 IO
    """
    normalized_args = dict(tool_args)
    summary = f"read_stub::{tool_name}::{intent}"
    return {
        "tool_name": tool_name,
        "intent": intent,
        "skill_id": skill_id,
        "summary": summary,
        "echo_args": normalized_args,
    }
