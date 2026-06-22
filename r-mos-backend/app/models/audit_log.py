"""
SOP 执行审计日志模型（V2.3 新增 - Phase 2）

记录 SOP 执行过程中的关键事件：
- 人（actor_id）
- 时（event_time）
- 步（step_index）
- 结果（result）

特点：
- 不可变（immutable）- 一旦写入不可修改
- 可追溯（traceable）- 每条记录都有 trace_id
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime
from enum import Enum
from .base import Base, utcnow


class AuditAction(str, Enum):
    """审计动作类型"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMEOUT = "task_timeout"
    
    STEP_STARTED = "step_started"
    STEP_EXECUTED = "step_executed"
    STEP_SKIPPED = "step_skipped"
    STEP_FAILED = "step_failed"
    STEP_RETRIED = "step_retry"
    
    FAULT_INJECTED = "fault_injected"
    FAULT_CLEARED = "fault_cleared"
    
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_FAILED = "snapshot_failed"


class ActorType(str, Enum):
    """操作者类型"""
    USER = "user"
    SYSTEM = "system"
    SCHEDULER = "scheduler"


class SOPAuditLog(Base):
    """SOP 执行审计日志
    
    不可变记录，用于：
    - 责任追溯
    - 执行回放
    - 合规审计
    """
    __tablename__ = "sop_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联
    task_id = Column(
        Integer, 
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联任务 ID"
    )
    sop_id = Column(
        Integer,
        ForeignKey("sops.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联 SOP ID（可能已删除）"
    )
    
    # 追踪
    trace_id = Column(String(64), nullable=False, index=True, comment="请求追踪 ID")
    
    # 操作者
    actor_type = Column(String(20), nullable=False, default="user", comment="操作者类型")
    actor_id = Column(String(100), nullable=True, comment="操作者 ID（用户 ID 或系统名）")
    
    # 动作
    action = Column(String(50), nullable=False, index=True, comment="审计动作")
    step_index = Column(Integer, nullable=True, comment="步骤索引（如适用）")
    
    # 结果
    result = Column(String(50), nullable=True, comment="执行结果")
    duration_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")
    
    # 详情
    message = Column(Text, nullable=True, comment="人类可读消息")
    details = Column(JSON, nullable=True, comment="结构化详情")
    error_message = Column(Text, nullable=True, comment="错误信息（如有）")
    
    # 时间戳
    event_time = Column(
        DateTime, 
        nullable=False, 
        default=utcnow,
        index=True,
        comment="事件发生时间"
    )
    ingest_time = Column(
        DateTime, 
        nullable=False, 
        default=utcnow,
        comment="记录入库时间"
    )
    
    def __repr__(self):
        return f"<SOPAuditLog(id={self.id}, task_id={self.task_id}, action={self.action})>"
