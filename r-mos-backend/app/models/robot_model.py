"""RobotModel and TeacherRobotBinding ORM models."""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class RobotVisibility(str, enum.Enum):
    PRIVATE = "private"
    SHARED = "shared"


class RobotStatus(str, enum.Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    READY = "ready"


class RobotModel(Base, TimestampMixin):
    """机器人型号目录表。"""
    __tablename__ = "robot_models"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False, index=True, comment="品牌")
    model_name = Column(String(200), nullable=False, index=True, comment="型号名称")
    version = Column(String(50), default="1.0", comment="版本号")
    owner_teacher_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="创建者教师 ID（null 表示系统内置）",
    )
    visibility = Column(
        Enum(RobotVisibility, values_callable=lambda x: [e.value for e in x]),
        default=RobotVisibility.PRIVATE,
        nullable=False, comment="可见性: private/shared",
    )
    status = Column(
        Enum(RobotStatus, values_callable=lambda x: [e.value for e in x]),
        default=RobotStatus.DRAFT,
        nullable=False, comment="状态: draft/analyzing/ready",
    )
    description = Column(Text, nullable=True, comment="机器人描述")
    thumbnail_path = Column(String(500), nullable=True, comment="缩略图相对路径")

    assets = relationship("RobotAsset", back_populates="robot_model", cascade="all, delete-orphan")
    bindings = relationship("TeacherRobotBinding", back_populates="robot_model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RobotModel(id={self.id}, brand={self.brand}, model={self.model_name})>"


class TeacherRobotBinding(Base, TimestampMixin):
    """教师与机器人的绑定关系（选配表）。"""
    __tablename__ = "teacher_robot_bindings"
    __table_args__ = (
        UniqueConstraint("teacher_id", "robot_model_id", name="uq_teacher_robot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="教师用户 ID",
    )
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="机器人型号 ID",
    )
    binding_type = Column(
        String(20), nullable=False, default="owner",
        comment="绑定类型: owner/shared_ref",
    )
    robot_model = relationship("RobotModel", back_populates="bindings")

    def __repr__(self):
        return f"<TeacherRobotBinding(teacher={self.teacher_id}, robot={self.robot_model_id})>"
