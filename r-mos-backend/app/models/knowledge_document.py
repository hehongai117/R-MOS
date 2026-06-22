"""Knowledge document model with tags for mixed RAG retrieval."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from datetime import datetime
from .base import Base, TimestampMixin


class KnowledgeDocument(Base, TimestampMixin):
    """A knowledge document with fault/SOP tags and status lifecycle."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档全文")
    doc_type = Column(String(50), default="manual", comment="manual/guide/spec")
    fault_tags = Column(JSON, default=list, comment='关联故障标签 ["E001_OVERHEAT"]')
    sop_tags = Column(JSON, default=list, comment='关联SOP标签')
    status = Column(String(20), default="PENDING", index=True, comment="PENDING/APPROVED/EXPIRED")
    risk_level = Column(String(5), default="R0", comment="风险等级")
    uploaded_by = Column(Integer, nullable=True, comment="上传用户 ID")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联机器人型号 ID",
    )
    generation_status = Column(
        String(20), default="manual",
        comment="生成状态: manual/ai_draft/published",
    )
