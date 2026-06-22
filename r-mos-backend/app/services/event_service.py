"""
Event服务（V2.3新增）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

from app.models.event import Event, EventType

logger = logging.getLogger(__name__)


class EventService:
    """Event服务
    
    职责：
    - 统一创建Event记录
    - Event查询与过滤
    - Event流式导出
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_event(
        self,
        task_id: int,
        event_type: str,
        step_index: Optional[int] = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        duration_ms: Optional[int] = None,
        is_error: bool = False,
        error_message: Optional[str] = None
    ) -> Event:
        """创建Event（V2.3统一方法）
        
        ⚠️ 强制约束：
        - 所有Event创建必须通过此方法
        - 自动记录timestamp
        - 自动flush到数据库
        """
        event = Event(
            task_id=task_id,
            event_type=event_type,
            step_index=step_index,
            timestamp=datetime.now(timezone.utc),
            action=action,
            target=target,
            parameters=parameters,
            result=result,
            duration_ms=duration_ms,
            is_error=is_error,
            error_message=error_message
        )
        
        self.db.add(event)
        await self.db.flush()
        
        logger.info(f"Event创建: task_id={task_id}, type={event_type}, event_id={event.id}")
        return event
    
    async def get_task_events(
        self,
        task_id: int,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[Event]:
        """查询Task的Event列表
        
        Args:
            task_id: 任务ID
            event_type: 事件类型过滤（可选）
            limit: 返回数量限制（可选）
        """
        query = select(Event).where(Event.task_id == task_id)
        
        if event_type:
            query = query.where(Event.event_type == event_type)
        
        query = query.order_by(Event.timestamp)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
