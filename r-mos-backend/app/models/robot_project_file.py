from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, Index, JSON, String

from app.models.base import Base, TimestampMixin


class RobotProjectFile(TimestampMixin, Base):
    __tablename__ = "robot_project_files"
    __table_args__ = (
        Index("ix_robot_project_files_project_kind", "project_id", "file_kind"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), ForeignKey("robot_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(256), nullable=False)
    relative_path = Column(String(512), nullable=False)
    file_kind = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(128), nullable=True)
    sha256 = Column(String(128), nullable=True, index=True)
    storage_path = Column(String(512), nullable=False)
    classification_json = Column(JSON, nullable=True)
