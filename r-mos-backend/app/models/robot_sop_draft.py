from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, JSON, String

from app.models.base import Base, TimestampMixin


class RobotSOPDraftReviewStatus(StrEnum):
    DRAFT_PENDING_REVIEW = "draft_pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RobotSOPDraft(TimestampMixin, Base):
    __tablename__ = "robot_sop_drafts"
    __table_args__ = (
        Index("ix_robot_sop_drafts_project_status", "project_id", "review_status"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), ForeignKey("robot_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(String(128), nullable=False, index=True)
    draft_json = Column(JSON, nullable=False)
    citations_json = Column(JSON, nullable=True)
    review_status = Column(
        Enum(RobotSOPDraftReviewStatus, native_enum=False),
        nullable=False,
        default=RobotSOPDraftReviewStatus.DRAFT_PENDING_REVIEW,
    )
