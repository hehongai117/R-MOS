"""学校白名单模型。"""
from sqlalchemy import Column, Integer, String, DateTime, func

from app.models.base import TZDateTime, Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    province = Column(String(50), nullable=True)
    created_at = Column(TZDateTime, server_default=func.now())
