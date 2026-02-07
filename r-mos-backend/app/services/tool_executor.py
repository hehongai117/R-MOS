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


def execute_write_tool_stub(
    *,
    intent: str,
    tool_name: str,
    skill_id: str | None,
    side_effects: list[str],
) -> dict[str, Any]:
    """执行最小写工具桩（不触发外部 IO）。

    约束：
    - 仅用于审批通过后的最小闭环
    - 仅返回确定性结果，不访问外部系统
    """
    normalized_effects = list(side_effects)
    return {
        "tool_name": tool_name,
        "intent": intent,
        "skill_id": skill_id,
        "mode": "write_stub",
        "applied_side_effects": normalized_effects,
        "summary": f"write_stub::{tool_name}::{intent}",
    }
