"""AnalysisTask ORM model — tracks AI analysis jobs for robot models."""
import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AnalysisTaskType(str, enum.Enum):
    PDF_EXTRACT = "pdf_extract"
    CAD_PARSE = "cad_parse"
    SOP_GENERATE = "sop_generate"
    FULL = "full"


class AnalysisTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTask(Base, TimestampMixin):
    """AI 分析任务记录。"""
    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, index=True)
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    task_type = Column(Enum(AnalysisTaskType, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="任务类型")
    status = Column(
        Enum(AnalysisTaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=AnalysisTaskStatus.PENDING,
        nullable=False, index=True, comment="任务状态",
    )
    input_document_ids = Column(JSON, default=list, comment="输入文档 ID 列表")
    output_summary = Column(JSON, nullable=True, comment="分析结果摘要")
    error_message = Column(Text, nullable=True, comment="失败原因")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")

    robot_model = relationship("RobotModel")

    def __repr__(self):
        return f"<AnalysisTask(id={self.id}, type={self.task_type}, status={self.status})>"
