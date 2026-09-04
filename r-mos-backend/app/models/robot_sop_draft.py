from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, JSON, String

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

    # 审计 M-01 / 董事会裁定 §9-2：补归属维度。
    # `created_by_user_id` 为 NULL 的历史行视为**系统内置公共内容**，仅管理员可改
    # （`ensure_write_owner` 对无主对象的既定处置）。
    # `school_name` 为多租户准备维度（CLAUDE.md 口径），**当前不参与授权判定**，
    # 正式租户隔离见路线图 S-2——勿因该列存在而误认为跨租户隔离已实施。
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="创建者用户 ID；NULL 表示系统内置内容",
    )
    school_name = Column(String(200), nullable=True, index=True, comment="所属学校（租户维度预留）")
