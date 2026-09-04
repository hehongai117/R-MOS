"""
Observation model.
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey

from app.models.base import TZDateTime, Base, utcnow


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(64), primary_key=True)
    observation_type = Column(String(50), nullable=False, index=True)
    robot_id = Column(String(100), nullable=False, index=True)
    task_id = Column(Integer, nullable=True)
    observed_time = Column(TZDateTime, nullable=False)
    event_time = Column(TZDateTime, nullable=True)
    ingest_time = Column(TZDateTime, default=utcnow, nullable=False)
    human_summary = Column(String(500), nullable=True)
    machine_code = Column(String(100), nullable=True)
    metrics = Column(JSON, nullable=True)
    payload_uri = Column(String(500), nullable=True)
    payload_hash = Column(String(64), nullable=True)

    # 审计 M-01 / 董事会裁定 §9-2：补归属维度。
    # `created_by_user_id` 为 NULL 的历史行视为系统内置公共内容，仅管理员可改。
    # `school_name` 仅为多租户准备维度，当前不参与授权判定；正式方案见路线图 S-2。
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="创建者用户 ID；NULL 表示系统内置内容",
    )
    school_name = Column(String(200), nullable=True, index=True, comment="所属学校（租户维度预留）")
