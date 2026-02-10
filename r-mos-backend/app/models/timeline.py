"""Gate-3 I-001：Timeline 基础模型（时间轴/片段/对齐映射）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String

from .base import Base


class MultimodalTimeline(Base):
    """时间轴主表。"""

    __tablename__ = "multimodal_timelines"
    __table_args__ = (
        Index("ix_timeline_scope", "scope_type", "scope_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(64), nullable=False, index=True)
    scope_id = Column(String(64), nullable=False, index=True)
    trace_id = Column(String(64), nullable=True, index=True)
    created_by_user_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class TimelineSegment(Base):
    """时间轴片段表。"""

    __tablename__ = "timeline_segments"
    __table_args__ = (
        Index("ix_segments_timeline_start", "timeline_id", "start_ts_ms"),
    )

    id = Column(Integer, primary_key=True, index=True)
    timeline_id = Column(Integer, ForeignKey("multimodal_timelines.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_type = Column(String(32), nullable=False, index=True)
    ref_id = Column(String(64), nullable=True, index=True)
    start_ts_ms = Column(BigInteger, nullable=False, index=True)
    end_ts_ms = Column(BigInteger, nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AlignmentMap(Base):
    """引用与时间轴片段对齐映射。"""

    __tablename__ = "alignment_map"
    __table_args__ = (
        Index("ix_alignment_anchor", "timeline_id", "anchor_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    timeline_id = Column(Integer, ForeignKey("multimodal_timelines.id", ondelete="CASCADE"), nullable=False, index=True)
    anchor_key = Column(String(128), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("timeline_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    ref_id = Column(String(64), nullable=True, index=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
