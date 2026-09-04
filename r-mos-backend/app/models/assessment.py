"""
Assessment provider and external assessment models.
"""
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, JSON

from app.models.base import TZDateTime, Base, utcnow


class AssessmentProvider(Base):
    __tablename__ = "assessment_providers"

    id = Column(String(64), primary_key=True)
    provider_name = Column(String(200), nullable=False)
    provider_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")
    endpoint_uri = Column(String(500), nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_email = Column(String(200), nullable=True)

    # 审计 M-01 / 董事会裁定 §9-2：补归属维度。
    # `created_by_user_id` 为 NULL 的历史行视为**系统内置公共内容**，仅管理员可改。
    # `school_name` 为多租户准备维度，**当前不参与授权判定**（正式方案见路线图 S-2）。
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="创建者用户 ID；NULL 表示系统内置内容",
    )
    school_name = Column(String(200), nullable=True, index=True, comment="所属学校（租户维度预留）")
    created_at = Column(TZDateTime, default=utcnow, nullable=False)
    updated_at = Column(TZDateTime, default=utcnow, onupdate=utcnow, nullable=False)


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
    report_time = Column(TZDateTime, nullable=False)
    ingest_time = Column(TZDateTime, default=utcnow, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    status_updated_at = Column(TZDateTime, default=utcnow, nullable=False)
    evidence_bundle_ids = Column(JSON, nullable=True)
    incident_ids = Column(JSON, nullable=True)
    observation_ids = Column(JSON, nullable=True)

    # 审计 M-01 / 董事会裁定 §9-2：补归属维度。
    # `created_by_user_id` 为 NULL 的历史行视为**系统内置公共内容**，仅管理员可改。
    # `school_name` 为多租户准备维度，**当前不参与授权判定**（正式方案见路线图 S-2）。
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="创建者用户 ID；NULL 表示系统内置内容",
    )
    school_name = Column(String(200), nullable=True, index=True, comment="所属学校（租户维度预留）")


class AssessmentAuditEvent(Base):
    __tablename__ = "assessment_audit_events"

    id = Column(String(64), primary_key=True)
    assessment_id = Column(String(64), nullable=False, index=True)
    action = Column(String(20), nullable=False)
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(String(100), nullable=False)
    reason_code = Column(String(50), nullable=False)
    reason_note = Column(String(500), nullable=True)
    event_time = Column(TZDateTime, nullable=False)
    ingest_time = Column(TZDateTime, default=utcnow, nullable=False)
    trace_id = Column(String(100), nullable=False)
