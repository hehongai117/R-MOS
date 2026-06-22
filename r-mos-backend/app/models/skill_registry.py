"""
Skill 治理模型（Gate-2 / G2-001）。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint

from .base import TZDateTime, Base, utcnow


class Skill(Base):
    """Skill 注册与版本主表。Extended with 5 governance fields (Phase 0 Week 2)"""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="ux_skills_skill_version"),
        Index("ix_skills_status_risk", "status", "risk_level"),
    )

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False)
    name = Column(String(200), nullable=False)
    created_by_user_id = Column(String(64), nullable=True, index=True)
    risk_level = Column(String(16), nullable=False)
    side_effects = Column(JSON, nullable=False, default=list)
    allowlist_resources = Column(JSON, nullable=False, default=list)
    feature_flag = Column(String(128), nullable=True)
    rollback_strategy = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    description = Column(Text, nullable=True)
    created_at = Column(TZDateTime, nullable=False, default=utcnow, index=True)
    updated_at = Column(TZDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Phase 0: Extended fields (5 new governance fields)
    # 1. Evidence requirements
    evidence_requirements = Column(JSON, nullable=True)
    # 2. Approval workflow
    approval_workflow = Column(JSON, nullable=True)
    # 3. Policy rules
    policy_rules = Column(JSON, nullable=True)
    # 4. Execution timeout
    execution_timeout_ms = Column(Integer, nullable=True)
    # 5. Deprecated at
    deprecated_at = Column(TZDateTime, nullable=True)


class SkillReview(Base):
    """Skill 审核记录表。"""

    __tablename__ = "skill_reviews"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(128), nullable=False, index=True)
    version = Column(String(32), nullable=False, index=True)
    reviewer_user_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(TZDateTime, nullable=False, default=utcnow, index=True)


class SkillRelease(Base):
    """Skill 发布记录表。"""

    __tablename__ = "skill_releases"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(128), nullable=False, index=True)
    version = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="published", index=True)
    released_by_user_id = Column(String(64), nullable=True, index=True)
    release_notes = Column(Text, nullable=True)
    created_at = Column(TZDateTime, nullable=False, default=utcnow, index=True)
