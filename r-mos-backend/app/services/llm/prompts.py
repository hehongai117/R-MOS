"""
PromptTemplateEngine - P1-2
模板区块数据结构和渲染引擎
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import json
import os


_SYSTEM_PROMPT_FALLBACK = "你是一个专业的机器人维保培训助手"
_SYSTEM_PROMPT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "config", "prompts", "system_prompt.txt"
)


def _load_system_prompt() -> str:
    """加载系统提示词，优先级：settings 覆盖 > 模板文件 > 硬编码兜底"""
    try:
        from app.core.config import settings
        default_value = "你是 R-MOS 维保学习助手，帮助学生理解机器人维保操作。"
        if settings.AI_ASSISTANT_SYSTEM_PROMPT != default_value:
            return settings.AI_ASSISTANT_SYSTEM_PROMPT
    except Exception:
        pass

    try:
        template_path = os.path.normpath(_SYSTEM_PROMPT_TEMPLATE_PATH)
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return _SYSTEM_PROMPT_FALLBACK


class BlockType(str, Enum):
    """模板区块类型"""
    SYSTEM = "system"
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    OUTPUT_CONSTRAINT = "output_constraint"
    USER = "user"


@dataclass
class SystemPromptBlock:
    """系统提示区块 - 定义智能体角色和行为"""
    role: str = field(default_factory=_load_system_prompt)
    domain: str = "机器人维护与操作"
    capabilities: list[str] = field(default_factory=lambda: [
        "提供维保操作指导",
        "诊断设备异常",
        "检索维保知识"
    ])
    safety_rules: list[str] = field(default_factory=lambda: [
        "在执行任何危险操作前必须确认",
        "遵循 SOP 操作规程"
    ])

    def to_message(self) -> dict:
        return {
            "role": "system",
            "content": self._build_content()
        }

    def _build_content(self) -> str:
        parts = [
            f"角色: {self.role}",
            f"领域: {self.domain}",
            f"能力: {', '.join(self.capabilities)}",
            f"安全规则: {'; '.join(self.safety_rules)}"
        ]
        return "\n".join(parts)


@dataclass
class ContextBlock:
    """上下文区块 - 当前任务/步骤信息"""
    task_id: Optional[str] = None
    step_index: Optional[int] = None
    step_description: Optional[str] = None
    robot_state: Optional[dict] = None
    use_context_builder: bool = True
    user_history: list[dict] = field(default_factory=list)

    def to_messages(self) -> list[dict]:
        messages = []
        if self.task_id:
            messages.append({
                "role": "system",
                "content": f"当前任务ID: {self.task_id}"
            })
        if self.step_index is not None:
            messages.append({
                "role": "system",
                "content": f"当前步骤: {self.step_index + 1}"
            })
        if self.step_description:
            messages.append({
                "role": "system",
                "content": f"步骤描述: {self.step_description}"
            })
        if self.robot_state:
            content = f"机器人状态: {json.dumps(self.robot_state, ensure_ascii=False)}"
            if (
                self.use_context_builder
                and isinstance(self.robot_state, dict)
                and "joints" in self.robot_state
                and "sensors" in self.robot_state
            ):
                try:
                    from app.services.llm.telemetry_context_builder import TelemetryContextBuilder

                    builder = TelemetryContextBuilder()
                    context = builder.build_from_payload(self.robot_state)
                    content = "机器人状态分析: " + json.dumps(
                        context.to_context_block(),
                        ensure_ascii=False,
                    )
                except Exception:
                    # 保留原始 JSON 注入作为回退路径，避免影响现有调用方。
                    pass
            messages.append({
                "role": "system",
                "content": content
            })
        return messages


@dataclass
class KnowledgeBlock:
    """知识区块 - 检索到的相关知识"""
    chunks: list[dict] = field(default_factory=list)
    max_chunks: int = 5

    def to_message(self) -> Optional[dict]:
        if not self.chunks:
            return None

        selected = self.chunks[:self.max_chunks]
        content_lines = ["相关知识参考:"]

        for i, chunk in enumerate(selected, 1):
            title = chunk.get("title", "无标题")
            content = chunk.get("content", "")[:200]
            content_lines.append(f"{i}. {title}: {content}...")

        return {
            "role": "system",
            "content": "\n".join(content_lines)
        }


@dataclass
class ToolBlock:
    """工具区块 - 可用工具定义"""
    tools: list[dict] = field(default_factory=list)

    def to_tools(self) -> list[dict]:
        return self.tools

    @staticmethod
    def create_rmos_tools() -> list[dict]:
        """创建 R-MOS 维保场景的标准工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_sop_steps",
                    "description": "获取指定 SOP 的步骤列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sop_id": {"type": "integer", "description": "SOP ID"}
                        },
                        "required": ["sop_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge",
                    "description": "搜索维保知识库",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "diagnose_issue",
                    "description": "根据机器人状态诊断问题",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "error_code": {"type": "string", "description": "错误码"},
                            "symptoms": {"type": "array", "items": {"type": "string"}, "description": "症状列表"}
                        },
                        "required": ["symptoms"]
                    }
                }
            }
        ]


@dataclass
class OutputConstraintBlock:
    """输出约束区块 - JSON 格式要求"""
    schema: Optional[dict] = None
    response_format: str = "text"  # text | json | structured

    def to_message(self) -> Optional[dict]:
        if self.response_format == "json" and self.schema:
            return {
                "role": "system",
                "content": f"请以 JSON 格式输出，schema: {json.dumps(self.schema)}"
            }
        return None


class PromptTemplateEngine:
    """
    提示词模板渲染引擎

    用法:
        engine = PromptTemplateEngine()
        messages = engine.render(
            user_message="帮我诊断机器人无法移动的问题",
            context=ContextBlock(task_id="task-001", step_index=2),
            knowledge_chunks=[...],
            output_format="json"
        )
    """

    def __init__(self):
        self.system_block = SystemPromptBlock()
        self.tool_block = ToolBlock()

    def render(
        self,
        user_message: str,
        context: Optional[ContextBlock] = None,
        knowledge_chunks: Optional[list[dict]] = None,
        output_format: str = "text",
        output_schema: Optional[dict] = None,
    ) -> list[dict]:
        """
        渲染完整的消息列表

        Args:
            user_message: 用户消息
            context: 上下文区块
            knowledge_chunks: 知识区块内容
            output_format: 输出格式 (text/json/structured)
            output_schema: JSON schema (当 output_format=json 时)

        Returns:
            list[dict]: 渲染后的 messages 列表
        """
        messages = []

        # 1. 系统提示
        messages.append(self.system_block.to_message())

        # 2. 上下文
        if context:
            messages.extend(context.to_messages())

        # 3. 知识
        if knowledge_chunks:
            kb = KnowledgeBlock(chunks=knowledge_chunks)
            kb_msg = kb.to_message()
            if kb_msg:
                messages.append(kb_msg)

        # 4. 输出约束
        oc = OutputConstraintBlock(
            schema=output_schema,
            response_format=output_format
        )
        oc_msg = oc.to_message()
        if oc_msg:
            messages.append(oc_msg)

        # 5. 用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def render_with_tools(
        self,
        user_message: str,
        context: Optional[ContextBlock] = None,
        knowledge_chunks: Optional[list[dict]] = None,
    ) -> tuple[list[dict], list[dict]]:
        """
        渲染包含工具调用的消息

        Returns:
            (messages, tools): 消息列表和工具定义
        """
        messages = self.render(
            user_message=user_message,
            context=context,
            knowledge_chunks=knowledge_chunks,
        )

        tools = self.tool_block.create_rmos_tools()

        return messages, tools

    def render_teaching(
        self,
        user_message: str,
        task_id: str,
        step_index: int,
        step_description: str,
        robot_state: Optional[dict] = None,
    ) -> list[dict]:
        """渲染教学场景的提示词"""
        context = ContextBlock(
            task_id=task_id,
            step_index=step_index,
            step_description=step_description,
            robot_state=robot_state
        )

        # 教学场景使用更简洁的输出
        return self.render(
            user_message=user_message,
            context=context,
            output_format="text"
        )


# 全局实例
prompt_engine = PromptTemplateEngine()
