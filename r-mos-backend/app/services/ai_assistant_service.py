"""AI 助手服务 — 基于当前 SOP 步骤上下文回答学生提问"""
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    """当前练习上下文"""
    sop_id: Optional[int] = None
    sop_title: Optional[str] = None
    current_step_index: Optional[int] = None
    current_step_description: Optional[str] = None
    fault_type: Optional[str] = None
    hint_level: int = 3  # 1=方向, 2=关键提示, 3=详细步骤


@dataclass
class ChatMessage:
    role: str  # user / assistant
    content: str


@dataclass
class ChatResponse:
    reply: str
    hint_level_used: int


class AIAssistantService:
    """嵌入式 AI 助手 — SOP 练习中为学生提供实时帮助"""

    def __init__(self):
        self._system_prompt = settings.AI_ASSISTANT_SYSTEM_PROMPT
        self._max_history = settings.AI_ASSISTANT_MAX_HISTORY

    async def chat(
        self,
        message: str,
        context: ChatContext,
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        """处理学生提问，根据 hint_level 控制回答深度"""
        history = (history or [])[-self._max_history:]

        system_prompt = self._build_system_prompt(context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        reply = await self._call_llm(messages)

        return ChatResponse(reply=reply, hint_level_used=context.hint_level)

    def _build_system_prompt(self, context: ChatContext) -> str:
        """构建带上下文的 system prompt"""
        parts = [self._system_prompt]

        if context.sop_title:
            parts.append(f"\n当前 SOP: {context.sop_title}")
        if context.current_step_index is not None:
            parts.append(f"当前步骤: 第 {context.current_step_index + 1} 步")
        if context.current_step_description:
            parts.append(f"步骤内容: {context.current_step_description}")
        if context.fault_type:
            parts.append(f"故障类型: {context.fault_type}")

        hint_instructions = {
            1: "\n回答要求：只给出方向性提示，不要直接告诉答案。用反问或提示引导学生思考。",
            2: "\n回答要求：给出关键提示，指出需要注意的要点，但不给出完整步骤。",
            3: "\n回答要求：给出详细的步骤说明和操作指导。",
        }
        parts.append(hint_instructions.get(context.hint_level, hint_instructions[3]))

        return "\n".join(parts)

    async def _call_llm(self, messages: list[dict]) -> str:
        """调用 LLM — 复用现有 LLM Router 逻辑"""
        try:
            from app.services.llm.router import LLMRouter
            router = LLMRouter()
            response = await router.chat(messages)
            return response.content
        except Exception as e:
            logger.warning(f"LLM call failed, using fallback: {e}")
            return "抱歉，AI 助手暂时不可用。请参考 SOP 步骤说明继续操作，或联系教师获取帮助。"
