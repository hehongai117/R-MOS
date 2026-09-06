from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, JSON, String, Integer

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
    # 审计 C-AUTH-03：机器人项目此前**无任何归属字段**，他校用户可读他人上传的
    # 手册与资产。按 M-01／裁定 §9-2 已确立的先例补归属维度：
    # `created_by_user_id` 为 NULL 的历史行视为系统内置内容，仅管理员可见；
    # `school_name` 是租户维度，此处**参与可见性过滤**（与教学表的预留不同）。
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="上传者用户 ID；NULL 表示系统内置内容",
    )
    school_name = Column(String(200), nullable=True, index=True, comment="所属学校")
    ingest_summary_json = Column(JSON, nullable=True)
