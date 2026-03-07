"""
用户模型（Gate-1 / A-001）。
V0.2 UF-01: 新增 role, teacher_id, class_id, hint_level 字段
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """认证用户表。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(512), nullable=False)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)

    # UF-01-a: 新增字段
    role = Column(String(20), nullable=False, default="student", index=True)  # student/teacher/admin
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 导师ID
    class_id = Column(Integer, nullable=True, index=True)  # 所属班级ID
    hint_level = Column(Integer, nullable=False, default=3)  # 提示级别 1-5

    # 关系
    teacher = relationship("User", remote_side=[id], backref="students")
