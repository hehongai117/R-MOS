from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Column, Enum, Index, JSON, String

from app.models.base import Base, TimestampMixin


class RobotProjectStatus(StrEnum):
    UPLOADED = "uploaded"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"


class RobotProject(TimestampMixin, Base):
    __tablename__ = "robot_projects"
    __table_args__ = (
        Index("ix_robot_projects_brand_model", "brand", "model"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    robot_key = Column(String(128), nullable=False, unique=True, index=True)
    brand = Column(String(128), nullable=False, index=True)
    model = Column(String(128), nullable=False, index=True)
    version = Column(String(64), nullable=True)
    status = Column(Enum(RobotProjectStatus, native_enum=False), nullable=False)
    source_package_path = Column(String(512), nullable=False)
    ingest_summary_json = Column(JSON, nullable=True)
