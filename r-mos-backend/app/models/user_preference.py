"""
P2-4: User Preference Model
用户偏好设置模型
"""

from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class UserPreference(Base, TimestampMixin):
    """用户偏好设置表"""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # AI 指导模式: "full_time" | "on_demand" | "silent"
    guidance_mode = Column(String(50), nullable=False, default="on_demand")

    # 其他偏好设置（JSON 格式）
    preferences = Column(JSON, nullable=True, default=dict)

    # user 关系
    user = relationship("User", backref="preference")
