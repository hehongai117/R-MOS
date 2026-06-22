"""
Snapshot（快照）数据模型（V2.4 故障惩罚支持）
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin, utcnow


class Snapshot(Base, TimestampMixin):
    """快照模型
    
    存储Task执行过程中机器人的完整状态
    """
    __tablename__ = "snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, comment="步骤索引")
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False, comment="快照时间")
    trigger = Column(String(50), nullable=False, comment="触发原因：step_execution/manual/error")
    
    # 机器人状态数据（JSON）
    joint_states = Column(JSON, nullable=False, comment="关节状态列表")
    sensor_data = Column(JSON, nullable=False, comment="传感器数据")
    active_faults = Column(JSON, nullable=True, comment="活动故障列表")
    
    # 元数据
    adapter_type = Column(String(50), nullable=True, comment="Adapter类型")
    # V2.4 新增：标记快照是否包含异常（故障注入等）
    is_anomaly = Column(Boolean, default=False, nullable=False, comment="是否包含异常")
    
    # 关系
    task = relationship("Task", back_populates="snapshots")
    
    def __repr__(self):
        return f"<Snapshot(id={self.id}, task_id={self.task_id}, step_index={self.step_index})>"
