"""Fault type → SOP mapping model."""
from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base, TimestampMixin


class FaultSOPMapping(Base, TimestampMixin):
    """Maps fault types to their corresponding SOPs."""
    __tablename__ = "fault_sop_mappings"

    id = Column(Integer, primary_key=True, index=True)
    fault_type = Column(String(50), nullable=False, index=True, comment="故障类型编码")
    sop_id = Column(
        Integer,
        ForeignKey("sops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联 SOP ID",
    )
    difficulty = Column(String(20), nullable=False, comment="难度: beginner/intermediate/advanced")
    priority = Column(Integer, default=1, comment="优先级（同 fault_type 多 SOP 时）")
