"""
ConversationService - P1-8-2
对话记录 CRUD 服务
"""
import json
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationTurn

logger = logging.getLogger(__name__)


class ConversationService:
    """对话记录服务"""

    async def create_turn(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        task_id: Optional[str] = None,
        step_index: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> ConversationTurn:
        """
        创建对话记录

        Args:
            db: 数据库会话
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 对话内容
            task_id: 任务 ID (可选)
            step_index: 步骤索引 (可选)
            metadata: 元数据 (可选)

        Returns:
            创建的对话记录
        """
        turn = ConversationTurn(
            session_id=session_id,
            role=role,
            content=content,
            task_id=task_id,
            step_index=step_index,
            metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )

        db.add(turn)
        await db.commit()
        await db.refresh(turn)

        return turn

    async def get_by_session(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 100,
    ) -> list[ConversationTurn]:
        """
        按会话查询对话记录

        Args:
            db: 数据库会话
            session_id: 会话 ID
            limit: 返回数量

        Returns:
            对话记录列表
        """
        result = await db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.created_at)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_by_task(
        self,
        db: AsyncSession,
        task_id: str,
        limit: int = 100,
    ) -> list[ConversationTurn]:
        """
        按任务查询对话记录

        Args:
            db: 数据库会话
            task_id: 任务 ID
            limit: 返回数量

        Returns:
            对话记录列表
        """
        result = await db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.task_id == task_id)
            .order_by(ConversationTurn.created_at)
            .limit(limit)
        )

        return list(result.scalars().all())


# 全局实例
conversation_service = ConversationService()
