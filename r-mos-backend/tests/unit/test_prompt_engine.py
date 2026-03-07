"""
P1-2-4: PromptTemplateEngine 单元测试
"""
import pytest
from app.services.llm.prompts import (
    PromptTemplateEngine,
    SystemPromptBlock,
    ContextBlock,
    KnowledgeBlock,
    ToolBlock,
    OutputConstraintBlock,
)


# ============ SystemPromptBlock 测试 ============

def test_system_prompt_block_default():
    """测试默认系统提示"""
    block = SystemPromptBlock()
    msg = block.to_message()

    assert msg["role"] == "system"
    assert "机器人维保培训助手" in msg["content"]
    assert "安全规则" in msg["content"]


def test_system_prompt_block_custom():
    """测试自定义系统提示"""
    block = SystemPromptBlock(
        role="高级维保工程师",
        domain="工业机器人维修",
        capabilities=["故障诊断", "性能优化"],
        safety_rules=["必须断电操作"]
    )
    msg = block.to_message()

    assert "高级维保工程师" in msg["content"]
    assert "工业机器人维修" in msg["content"]
    assert "故障诊断" in msg["content"]


# ============ ContextBlock 测试 ============

def test_context_block_empty():
    """测试空上下文"""
    block = ContextBlock()
    msgs = block.to_messages()
    assert msgs == []


def test_context_block_full():
    """测试完整上下文"""
    block = ContextBlock(
        task_id="task-001",
        step_index=3,
        step_description="检查电机状态",
        robot_state={"joint_1": 25.5, "joint_2": 30.0}
    )
    msgs = block.to_messages()

    assert len(msgs) == 4
    assert any("task-001" in m["content"] for m in msgs)
    assert any("3" in m["content"] for m in msgs)


# ============ KnowledgeBlock 测试 ============

def test_knowledge_block_empty():
    """测试空知识块"""
    block = KnowledgeBlock()
    msg = block.to_message()
    assert msg is None


def test_knowledge_block_with_chunks():
    """测试知识块"""
    chunks = [
        {"title": "电机维护", "content": "定期检查电机温度"},
        {"title": "齿轮保养", "content": "每1000小时加注润滑脂"}
    ]
    block = KnowledgeBlock(chunks=chunks, max_chunks=1)
    msg = block.to_message()

    assert msg is not None
    assert "电机维护" in msg["content"]
    assert "齿轮保养" not in msg["content"]  # 超过 max_chunks


# ============ ToolBlock 测试 ============

def test_tool_block_create_rmos_tools():
    """测试创建 R-MOS 工具"""
    tools = ToolBlock.create_rmos_tools()

    assert len(tools) == 3
    assert tools[0]["function"]["name"] == "get_sop_steps"
    assert tools[1]["function"]["name"] == "search_knowledge"
    assert tools[2]["function"]["name"] == "diagnose_issue"


# ============ OutputConstraintBlock 测试 ============

def test_output_constraint_text():
    """测试文本输出约束"""
    block = OutputConstraintBlock(response_format="text")
    msg = block.to_message()
    assert msg is None


def test_output_constraint_json():
    """测试 JSON 输出约束"""
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
    block = OutputConstraintBlock(response_format="json", schema=schema)
    msg = block.to_message()

    assert msg is not None
    assert "JSON" in msg["content"]
    assert "answer" in msg["content"]


# ============ PromptTemplateEngine 测试 ============

def test_prompt_engine_empty():
    """测试空渲染"""
    engine = PromptTemplateEngine()
    messages = engine.render(user_message="Hello")

    assert len(messages) == 2  # system + user
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hello"


def test_prompt_engine_with_context():
    """测试带上下文的渲染"""
    engine = PromptTemplateEngine()
    context = ContextBlock(task_id="task-001", step_index=1)

    messages = engine.render(
        user_message="下一步是什么？",
        context=context
    )

    # system + context + user
    assert len(messages) >= 2
    assert any("task-001" in m["content"] for m in messages)


def test_prompt_engine_with_knowledge():
    """测试带知识的渲染"""
    engine = PromptTemplateEngine()
    chunks = [{"title": "test", "content": "test content"}]

    messages = engine.render(
        user_message="如何维护？",
        knowledge_chunks=chunks
    )

    assert any("test content" in m["content"] for m in messages)


def test_prompt_engine_with_json_output():
    """测试 JSON 输出格式"""
    engine = PromptTemplateEngine()
    schema = {"type": "object"}

    messages = engine.render(
        user_message="返回JSON",
        output_format="json",
        output_schema=schema
    )

    assert any("JSON" in m["content"] for m in messages)


def test_prompt_engine_with_tools():
    """测试带工具的渲染"""
    engine = PromptTemplateEngine()

    messages, tools = engine.render_with_tools(
        user_message="搜索电机知识",
        context=ContextBlock(task_id="task-001")
    )

    assert len(messages) >= 2
    assert len(tools) == 3


def test_prompt_engine_teaching():
    """测试教学场景渲染"""
    engine = PromptTemplateEngine()

    messages = engine.render_teaching(
        user_message="帮我完成这个步骤",
        task_id="task-001",
        step_index=2,
        step_description="检查润滑油",
        robot_state={"oil_level": "low"}
    )

    assert len(messages) >= 2
    assert any("task-001" in m["content"] for m in messages)
    assert any("润滑油" in m["content"] for m in messages)


def test_prompt_engine_singleton():
    """测试全局单例"""
    from app.services.llm import prompt_engine

    messages = prompt_engine.render(user_message="test")
    assert len(messages) == 2
