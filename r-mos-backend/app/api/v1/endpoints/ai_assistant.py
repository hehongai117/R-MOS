"""AI 助手聊天端点"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai_assistant_service import (
    AIAssistantService,
    ChatContext,
    ChatMessage as ServiceChatMessage,
)

router = APIRouter()

_service = AIAssistantService()


class ChatMessageInput(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    sop_id: Optional[int] = None
    sop_title: Optional[str] = None
    current_step_index: Optional[int] = None
    current_step_description: Optional[str] = None
    fault_type: Optional[str] = None
    hint_level: int = Field(default=3, ge=1, le=3)
    history: List[ChatMessageInput] = Field(default_factory=list)
    robot_model_id: Optional[int] = None   # 全局对话：当前选中的机器人型号
    context: Optional[str] = None          # 全局对话：附加上下文信息


class AIChatResponse(BaseModel):
    reply: str
    hint_level_used: int


@router.post("/ai-assistant/chat", response_model=AIChatResponse, tags=["ai-assistant"])
async def chat_with_assistant(request: AIChatRequest, db: AsyncSession = Depends(get_db)):
    """与 AI 助手对话 — 支持 SOP 练习辅导和全局通用维保问答两种模式"""
    context = ChatContext(
        sop_id=request.sop_id,
        sop_title=request.sop_title,
        current_step_index=request.current_step_index,
        current_step_description=request.current_step_description,
        fault_type=request.fault_type,
        hint_level=request.hint_level,
        robot_model_id=request.robot_model_id,
        extra_context=request.context,
    )
    history = [
        ServiceChatMessage(role=m.role, content=m.content)
        for m in request.history
    ]
    result = await _service.chat(
        message=request.message,
        context=context,
        history=history,
        db=db,
    )
    return AIChatResponse(reply=result.reply, hint_level_used=result.hint_level_used)
