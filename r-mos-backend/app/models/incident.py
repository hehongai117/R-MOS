"""
Incident model.
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON

from app.models.base import Base, utcnow


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True)
    robot_id = Column(String(100), nullable=False, index=True)
    task_id = Column(Integer, nullable=True)
    incident_type = Column(String(50), nullable=False, index=True)
    incident_level = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    event_time_start = Column(DateTime(timezone=True), nullable=False)
    event_time_end = Column(DateTime(timezone=True), nullable=True)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    human_summary = Column(String(500), nullable=True)
    machine_tags = Column(JSON, nullable=True)
    related_observation_ids = Column(JSON, nullable=True)
    related_evidence_bundle_ids = Column(JSON, nullable=True)
