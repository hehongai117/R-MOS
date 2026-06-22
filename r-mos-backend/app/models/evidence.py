"""
Evidence bundle and item models.
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, utcnow


class EvidenceBundle(Base):
    __tablename__ = "evidence_bundles"

    id = Column(String(64), primary_key=True)
    bundle_type = Column(String(50), nullable=False, index=True)
    bundle_hash = Column(String(64), nullable=False, index=True)
    bundle_hash_algo = Column(String(20), nullable=False, default="sha256")
    observed_time_start = Column(DateTime(timezone=True), nullable=False)
    observed_time_end = Column(DateTime(timezone=True), nullable=True)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_sealed = Column(Boolean, default=False, nullable=False)
    sealed_at = Column(DateTime(timezone=True), nullable=True)
    human_summary = Column(String(500), nullable=True)
    machine_tags = Column(JSON, nullable=True)

    items = relationship("EvidenceItem", back_populates="bundle", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(String(64), primary_key=True)
    bundle_id = Column(String(64), ForeignKey("evidence_bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False)
    content_uri = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=False)
    content_hash_algo = Column(String(20), nullable=False, default="sha256")
    content_mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    observed_time = Column(DateTime(timezone=True), nullable=False)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    human_summary = Column(String(500), nullable=True)
    machine_code = Column(String(100), nullable=True)
    machine_tags = Column(JSON, nullable=True)

    bundle = relationship("EvidenceBundle", back_populates="items")
