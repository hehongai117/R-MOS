"""
Tool executor service tests.
"""
from __future__ import annotations

from app.services.tool_executor import execute_read_tool


def test_tool_executor_read_tool_normal_flow_with_refs():
    result = execute_read_tool(
        intent="knowledge_query",
        tool_name="rag.query",
        skill_id="kb.search",
        tool_args={
            "query": "ABB IRB1200",
            "ref_ids": [
                "123e4567-e89b-12d3-a456-426614174000",
                "123e4567-e89b-12d3-a456-426614174001",
            ],
        },
    )

    assert result["tool_name"] == "rag.query"
    assert len(result["hits"]) == 2
    assert len(result["citations"]) == 2
    assert result["summary"].startswith("read_stub::rag.query")
