"""AI 助手服务 — 基于当前 SOP 步骤上下文回答学生提问"""
import logging
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    robot_model_id: Optional[int] = None   # 全局对话：当前选中的机器人型号
    extra_context: Optional[str] = None    # 全局对话：附加上下文信息


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
        db: AsyncSession | None = None,
    ) -> ChatResponse:
        """处理学生提问，根据 hint_level 控制回答深度"""
        history = (history or [])[-self._max_history:]

        system_prompt = await self._build_system_prompt(context, db)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        reply = await self._call_llm(messages)

        return ChatResponse(reply=reply, hint_level_used=context.hint_level)

    async def _build_system_prompt(self, context: ChatContext, db: AsyncSession | None = None) -> str:
        """构建带上下文的 system prompt。

        - 有 sop_id：SOP 练习辅导模式（原有逻辑）
        - 无 sop_id：通用维保助手模式（注入知识库内容）
        """
        if context.sop_id is None:
            # 通用维保助手模式 — 注入知识库上下文
            parts = [
                "你是 R-MOS 机器人维保智能助手。",
                "你必须严格基于下方【知识库资料】回答用户问题。",
                "如果知识库中没有相关信息，请明确告知用户当前知识库暂无该内容。",
                "回答简洁专业，必要时列出步骤。",
            ]
            if context.extra_context:
                parts.append(f"\n上下文信息：{context.extra_context}")

            # 查询知识库
            kb_content = await self._fetch_knowledge(context.robot_model_id, db)
            if kb_content:
                parts.append(f"\n【知识库资料】\n{kb_content}")
            else:
                parts.append("\n【知识库资料】\n暂无该机器人的知识库文档。")

            return "\n".join(parts)

        # SOP 练习辅导模式（原有逻辑）
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

    async def _fetch_knowledge(self, robot_model_id: int | None, db: AsyncSession | None) -> str:
        """从知识库查询当前机器人的文档内容，拼接为上下文文本。"""
        if not robot_model_id or not db:
            return ""
        try:
            from app.models.knowledge_document import KnowledgeDocument
            query = (
                select(KnowledgeDocument.title, KnowledgeDocument.content)
                .where(KnowledgeDocument.robot_model_id == robot_model_id)
                .order_by(KnowledgeDocument.id)
                .limit(20)
            )
            result = await db.execute(query)
            docs = result.all()
            if not docs:
                return ""

            MAX_KB_CHARS = 6000
            chunks = []
            total = 0
            for title, content in docs:
                if not content:
                    continue
                snippet = content[:500]
                entry = f"### {title}\n{snippet}"
                if total + len(entry) > MAX_KB_CHARS:
                    break
                chunks.append(entry)
                total += len(entry)
            return "\n\n".join(chunks)
        except Exception as e:
            logger.warning("知识库查询失败: %s", e)
            return ""

    async def _call_llm(self, messages: list[dict]) -> str:
        """调用 LLM — 使用 DeepSeek 作为主模型"""
        try:
            from app.services.llm.router import LLMRouter, LLMProvider
            router = LLMRouter()
            response = await router.chat(
                messages,
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_BASIC,
                temperature=0.3,
                max_tokens=2048,
            )
            return response.content
        except Exception as e:
            logger.warning(f"LLM call failed, using fallback: {e}")
            return "抱歉，AI 助手暂时不可用。请参考 SOP 步骤说明继续操作，或联系教师获取帮助。"
