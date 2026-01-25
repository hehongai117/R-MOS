"""
SOP 审计日志服务（V2.3 新增 - Phase 2）

职责：
- 创建不可变审计记录
- 支持按 task_id / trace_id 查询
- 提供执行链路重放能力
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid

from app.models.audit_log import SOPAuditLog, AuditAction, ActorType

logger = logging.getLogger(__name__)


class AuditLogService:
    """审计日志服务
    
    用法示例：
    ```python
    audit = AuditLogService(db)
    await audit.log(
        task_id=1,
        action=AuditAction.STEP_EXECUTED,
        step_index=1,
        result="success",
        actor_id="user_123"
    )
    ```
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        task_id: int,
        action: AuditAction,
        *,
        sop_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: Optional[str] = None,
        step_index: Optional[int] = None,
        result: Optional[str] = None,
        duration_ms: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        event_time: Optional[datetime] = None
    ) -> SOPAuditLog:
        """创建审计日志记录"""
        
        record = SOPAuditLog(
            task_id=task_id,
            sop_id=sop_id,
            trace_id=trace_id or str(uuid.uuid4())[:8],
            actor_type=actor_type.value,
            actor_id=actor_id or "system",
            action=action.value,
            step_index=step_index,
            result=result,
            duration_ms=duration_ms,
            message=message,
            details=details,
            error_message=error_message,
            event_time=event_time or datetime.utcnow(),
            ingest_time=datetime.utcnow()
        )
        
        self.db.add(record)
        await self.db.flush()
        
        logger.debug(
            f"[Audit] task={task_id} action={action.value} "
            f"step={step_index} result={result}"
        )
        
        return record
    
    async def log_task_event(
        self,
        task_id: int,
        action: AuditAction,
        trace_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SOPAuditLog:
        """快捷方法：记录任务级事件"""
        return await self.log(
            task_id=task_id,
            action=action,
            trace_id=trace_id,
            actor_id=actor_id,
            details=details,
            message=f"Task {action.value}"
        )
    
    async def log_step_event(
        self,
        task_id: int,
        step_index: int,
        action: AuditAction,
        result: str,
        duration_ms: Optional[int] = None,
        trace_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> SOPAuditLog:
        """快捷方法：记录步骤级事件"""
        return await self.log(
            task_id=task_id,
            action=action,
            step_index=step_index,
            result=result,
            duration_ms=duration_ms,
            trace_id=trace_id,
            actor_id=actor_id,
            details=details,
            error_message=error_message,
            message=f"Step {step_index}: {action.value} ({result})"
        )
    
    async def get_task_audit_trail(
        self,
        task_id: int,
        limit: int = 100
    ) -> List[SOPAuditLog]:
        """获取任务的完整审计轨迹"""
        result = await self.db.execute(
            select(SOPAuditLog)
            .where(SOPAuditLog.task_id == task_id)
            .order_by(SOPAuditLog.event_time)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_trace_id(
        self,
        trace_id: str
    ) -> List[SOPAuditLog]:
        """按 trace_id 查询相关记录"""
        result = await self.db.execute(
            select(SOPAuditLog)
            .where(SOPAuditLog.trace_id == trace_id)
            .order_by(SOPAuditLog.event_time)
        )
        return list(result.scalars().all())
    
    async def count_by_action(
        self,
        task_id: int,
        action: AuditAction
    ) -> int:
        """统计特定动作的数量"""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count())
            .select_from(SOPAuditLog)
            .where(
                SOPAuditLog.task_id == task_id,
                SOPAuditLog.action == action.value
            )
        )
        return result.scalar() or 0
