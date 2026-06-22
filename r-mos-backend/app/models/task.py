"""
Task（任务）数据模型（V2.3完整版）
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from .base import Base, TimestampMixin


class TaskStatus(str, Enum):
    """任务状态枚举（V2.3 增强）
    
    状态流转规则：
    - PENDING → IN_PROGRESS（开始）
    - IN_PROGRESS → PAUSED / COMPLETED / FAILED
    - PAUSED → IN_PROGRESS / CANCELLED
    - PENDING / PAUSED → CANCELLED
    - FAILED / COMPLETED / CANCELLED / TIMEOUT 为终态
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"  # V2.3 新增


class Task(Base, TimestampMixin):
    """任务模型（V2.3完整版）
    
    ⚠️ V2.3关键修正：
    - sop_id改为nullable=True（允许NULL）
    - 外键改为ondelete="SET NULL"（SOP删除后不级联删除Task）
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="任务标题")
    
    # ✅ V2.3修正：允许sop_id为NULL（SOP删除后）
    sop_id = Column(
        Integer,
        ForeignKey("sops.id", ondelete="SET NULL"),
        nullable=True,  # 关键修改
        index=True,
        comment="关联SOP ID（可为NULL）"
    )

    # Teaching domain references (Phase 1+)
    assignment_id = Column(
        Integer,
        ForeignKey("assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联教学作业 ID（可为NULL）"
    )
    guidance_policy_id = Column(
        Integer,
        ForeignKey("guidance_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联引导策略 ID（可为NULL）"
    )
    
    user_id = Column(Integer, nullable=True, comment="执行用户ID")
    # V2.3修正：使用 String 而不是 SQLEnum，与迁移文件保持一致
    status = Column(
        String(20), 
        default=TaskStatus.PENDING.value,  # 使用枚举值作为默认值
        nullable=False,
        comment="任务状态"
    )
    current_step_index = Column(Integer, default=0, nullable=False, comment="当前步骤索引")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    paused_at = Column(DateTime(timezone=True), nullable=True, comment="暂停时间")  # V2.3新增
    time_limit = Column(Integer, nullable=True, comment="时间限制（秒）")
    pass_score = Column(Integer, default=70, nullable=False, comment="及格分数")
    final_score = Column(Integer, nullable=True, comment="最终得分")
    is_passed = Column(Boolean, nullable=True, comment="是否通过")
    
    # 关系
    sop = relationship("SOP", back_populates="tasks")
    assignment = relationship("Assignment", back_populates="tasks")
    guidance_policy = relationship("GuidancePolicy", back_populates="tasks")
    events = relationship("Event", back_populates="task", cascade="all, delete-orphan", lazy="selectin")
    snapshots = relationship("Snapshot", back_populates="task", cascade="all, delete-orphan", lazy="selectin")
    attempts = relationship("AssignmentAttempt", back_populates="task")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"
