from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, Index, JSON, String

from app.models.base import Base, TimestampMixin


class RobotPartManifest(TimestampMixin, Base):
    __tablename__ = "robot_part_manifests"
    __table_args__ = (
        Index("ix_robot_part_manifests_project", "project_id"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), ForeignKey("robot_projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    manifest_version = Column(String(32), nullable=False)
    tree_json = Column(JSON, nullable=False)
    mapping_json = Column(JSON, nullable=False)
    viewer_manifest_json = Column(JSON, nullable=False)
