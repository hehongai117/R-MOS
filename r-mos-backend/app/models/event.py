"""
Event（事件）数据模型（V2.3完整版）
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from .base import Base, TimestampMixin


class EventType(str, Enum):
    """事件类型枚举（V2.3完整版）"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PAUSED = "task_paused"          # V2.1.2补充
    TASK_RESUMED = "task_resumed"        # V2.1.2补充
    STEP_EXECUTED = "step_executed"
    STEP_SKIPPED = "step_skipped"        # V2.1.2补充
    STEP_BLOCKED = "step_blocked"         # 安全中断
    STEP_WARNING = "step_warning"        # 步骤警告
    FAULT_DETECTED = "fault_detected"
    FAULT_CLEARED = "fault_cleared"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_FAILED = "snapshot_failed"  # V2.1.2补充


class Event(Base, TimestampMixin):
    """事件模型
    
    记录Task执行过程中的所有事件
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True, comment="事件类型")
    step_index = Column(Integer, nullable=True, comment="步骤索引")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="事件时间")
    
    # 操作详情
    action = Column(String(100), nullable=True, comment="执行的操作")
    target = Column(String(100), nullable=True, comment="操作目标")
    parameters = Column(JSON, nullable=True, comment="操作参数")
    
    # 结果
    result = Column(String(50), nullable=True, comment="执行结果")
    duration_ms = Column(Integer, nullable=True, comment="执行耗时（毫秒）")
    
    # 错误信息
    is_error = Column(Boolean, default=False, nullable=False, comment="是否为错误")
    error_message = Column(Text, nullable=True, comment="错误消息")
    
    # 关系
    task = relationship("Task", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, task_id={self.task_id}, type={self.event_type})>"
