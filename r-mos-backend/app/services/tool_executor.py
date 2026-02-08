"""Gate-2 E-001：无副作用工具执行器（最小读链路）。"""
from __future__ import annotations

from typing import Any


def _is_disabled_critical_tool(tool_name: str, skill_id: str | None) -> bool:
    """最小风险策略：critical 故障注入工具默认禁用。"""
    normalized_tool_name = tool_name.strip().lower()
    normalized_skill_id = (skill_id or "").strip().lower()
    return normalized_tool_name == "adapter.inject_fault" or normalized_skill_id == "adapter.inject_fault"


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
    if _is_disabled_critical_tool(tool_name, skill_id):
        raise RuntimeError("feature_flag_disabled")

    normalized_effects = list(side_effects)
    return {
        "tool_name": tool_name,
        "intent": intent,
        "skill_id": skill_id,
        "mode": "write_stub",
        "applied_side_effects": normalized_effects,
        "summary": f"write_stub::{tool_name}::{intent}",
    }
