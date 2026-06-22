"""
Assessment provider and external assessment models.
"""
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON

from app.models.base import Base, utcnow


class AssessmentProvider(Base):
    __tablename__ = "assessment_providers"

    id = Column(String(64), primary_key=True)
    provider_name = Column(String(200), nullable=False)
    provider_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")
    endpoint_uri = Column(String(500), nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_email = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ExternalAssessment(Base):
    __tablename__ = "external_assessments"

    id = Column(String(64), primary_key=True)
    provider_id = Column(String(64), nullable=False, index=True)
    provider_type = Column(String(20), nullable=False)
    assessment_type = Column(String(20), nullable=False, index=True)
    provider_assessment_id = Column(String(200), nullable=True)
    report_uri = Column(String(500), nullable=False)
    report_hash = Column(String(64), nullable=False)
    report_hash_algo = Column(String(20), nullable=False, default="sha256")
    report_format = Column(String(20), nullable=False)
    report_time = Column(DateTime(timezone=True), nullable=False)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    status_updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_bundle_ids = Column(JSON, nullable=True)
    incident_ids = Column(JSON, nullable=True)
    observation_ids = Column(JSON, nullable=True)


class AssessmentAuditEvent(Base):
    __tablename__ = "assessment_audit_events"

    id = Column(String(64), primary_key=True)
    assessment_id = Column(String(64), nullable=False, index=True)
    action = Column(String(20), nullable=False)
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(String(100), nullable=False)
    reason_code = Column(String(50), nullable=False)
    reason_note = Column(String(500), nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=False)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    trace_id = Column(String(100), nullable=False)
