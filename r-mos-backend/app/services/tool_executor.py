"""Gate-2 E-001：无副作用工具执行器（最小读链路）。"""
from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import SecurityViolationError


TOOL_EXECUTION_ERR_FEATURE_FLAG_DISABLED = "feature_flag_disabled"
TOOL_SECURITY_ERR_BLACKLIST = "SECURITY_BLACKLIST_KEYWORD"
TOOL_SECURITY_ERR_INJECTION = "SECURITY_INJECTION_PATTERN"
TOOL_SECURITY_ERR_INVALID_REFERENCE = "SECURITY_INVALID_REFERENCE"
TOOL_SECURITY_ERR_PARAM_RANGE = "SECURITY_PARAM_OUT_OF_RANGE"

_BLACKLIST_KEYWORDS = ("DROP TABLE", "DELETE FROM")
_INJECTION_PATTERNS = (
    re.compile(r"(?i)(<\s*script|javascript:|onerror\s*=)"),
    re.compile(r"(?i)(union\s+select|insert\s+into)"),
)
_UUID_LIKE_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_ALLOWED_DIFFICULTY = {"beginner", "intermediate", "advanced"}


class ToolExecutionPolicyError(RuntimeError):
    """写工具执行策略错误。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _iter_string_values(value: Any):
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_string_values(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_string_values(nested)


def validate_tool_request_security(
    *,
    tool_name: str,
    tool_args: dict[str, Any],
) -> None:
    """E-004 最小安全门禁：注入/引用/参数范围校验。"""
    for raw in _iter_string_values(tool_args):
        normalized_upper = raw.upper()
        for keyword in _BLACKLIST_KEYWORDS:
            if keyword in normalized_upper:
                raise SecurityViolationError(
                    code=TOOL_SECURITY_ERR_BLACKLIST,
                    message="检测到黑名单关键字，已拒绝执行",
                    details={
                        "tool_name": tool_name,
                        "keyword": keyword,
                    },
                )
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(raw):
                raise SecurityViolationError(
                    code=TOOL_SECURITY_ERR_INJECTION,
                    message="检测到注入风险模式，已拒绝执行",
                    details={
                        "tool_name": tool_name,
                        "pattern": pattern.pattern,
                    },
                )

    evidence_refs = tool_args.get("evidence_refs")
    if evidence_refs is not None:
        if not isinstance(evidence_refs, list):
            raise SecurityViolationError(
                code=TOOL_SECURITY_ERR_INVALID_REFERENCE,
                message="引用列表格式非法",
                details={"tool_name": tool_name},
            )
        for ref_id in evidence_refs:
            if not isinstance(ref_id, str) or not _UUID_LIKE_PATTERN.match(ref_id):
                raise SecurityViolationError(
                    code=TOOL_SECURITY_ERR_INVALID_REFERENCE,
                    message="引用 ID 非法或不可验证",
                    details={
                        "tool_name": tool_name,
                        "invalid_ref": ref_id,
                    },
                )

    difficulty = tool_args.get("difficulty")
    if difficulty is not None:
        if not isinstance(difficulty, str) or difficulty not in _ALLOWED_DIFFICULTY:
            raise SecurityViolationError(
                code=TOOL_SECURITY_ERR_PARAM_RANGE,
                message="参数超出允许范围",
                details={
                    "tool_name": tool_name,
                    "param": "difficulty",
                    "allowed": sorted(_ALLOWED_DIFFICULTY),
                    "actual": difficulty,
                },
            )


def build_insufficient_data_template(
    *,
    intent: str,
    tool_name: str,
    tool_args: dict[str, Any],
    execution_result: dict[str, Any],
) -> dict[str, Any] | None:
    """G-002 最小缺乏数据模板：仅在 rag.query 空命中时返回结构化提示。"""
    normalized_tool_name = tool_name.strip().lower()
    if normalized_tool_name not in {"rag.query", "ai.rag.query"}:
        return None

    hits = execution_result.get("hits")
    items = execution_result.get("items")
    status = str(execution_result.get("status") or "").strip().lower()
    no_result = (
        (isinstance(hits, list) and len(hits) == 0)
        or (isinstance(items, list) and len(items) == 0)
        or status in {"no_result", "empty"}
    )
    if not no_result:
        return None

    query_text = str(tool_args.get("input_text") or tool_args.get("query") or "").strip()
    missing_items = tool_args.get("missing_items")
    if not isinstance(missing_items, list) or not missing_items:
        missing_items = ["可验证证据", "可回放引用"]

    return {
        "status": "insufficient_data",
        "query": query_text,
        "missing_items": missing_items,
        "next_steps": [
            "补充与问题相关的过程证据",
            "确认引用是否可回放后再次发起命令",
        ],
    }


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
    normalized_tool_name = tool_name.strip().lower()
    if normalized_tool_name in {"rag.query", "ai.rag.query"}:
        # 仅用于测试稳定复现“空命中”；默认读链路不伪造命中结果。
        force_empty = bool(normalized_args.pop("force_empty", False))
        if force_empty:
            return {
                "tool_name": tool_name,
                "intent": intent,
                "skill_id": skill_id,
                "summary": f"read_stub::{tool_name}::{intent}",
                "echo_args": normalized_args,
                "hits": [],
                "items": [],
            }

        ref_ids_raw = normalized_args.get("ref_ids")
        ref_ids: list[str] = []
        if isinstance(ref_ids_raw, list):
            ref_ids = [str(item) for item in ref_ids_raw if isinstance(item, str)]

        citations = [
            {
                "ref_id": ref_id,
                "title": "RAG 引用片段",
            }
            for ref_id in ref_ids
        ]
        hits = [
            {
                "ref_id": ref_id,
                "title": "RAG 命中片段",
            }
            for ref_id in ref_ids
        ]
        return {
            "tool_name": tool_name,
            "intent": intent,
            "skill_id": skill_id,
            "summary": f"read_stub::{tool_name}::{intent}",
            "echo_args": normalized_args,
            "citations": citations,
            "hits": hits,
            "items": list(hits),
        }

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
        raise ToolExecutionPolicyError(
            TOOL_EXECUTION_ERR_FEATURE_FLAG_DISABLED,
            "critical_tool_feature_disabled",
        )

    normalized_effects = list(side_effects)
    return {
        "tool_name": tool_name,
        "intent": intent,
        "skill_id": skill_id,
        "mode": "write_stub",
        "applied_side_effects": normalized_effects,
        "summary": f"write_stub::{tool_name}::{intent}",
    }
