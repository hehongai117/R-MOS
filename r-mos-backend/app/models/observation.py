"""
Observation model.
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON

from app.models.base import Base, utcnow


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(64), primary_key=True)
    observation_type = Column(String(50), nullable=False, index=True)
    robot_id = Column(String(100), nullable=False, index=True)
    task_id = Column(Integer, nullable=True)
    observed_time = Column(DateTime(timezone=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=True)
    ingest_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    human_summary = Column(String(500), nullable=True)
    machine_code = Column(String(100), nullable=True)
    metrics = Column(JSON, nullable=True)
    payload_uri = Column(String(500), nullable=True)
    payload_hash = Column(String(64), nullable=True)
