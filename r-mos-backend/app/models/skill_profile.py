"""
UF-10: Student Skill Profile Models
学员技能画像模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import TZDateTime, Base, TimestampMixin


class StudentSkillProfile(Base, TimestampMixin):
    """学员技能画像表 - UF-10-a-1"""
    __tablename__ = "student_skill_profiles"

    id = Column(Integer, primary_key=True, index=True)

    # 关联用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    user = relationship("User", backref="skill_profile")

    # 综合技能等级 (1-5)
    overall_level = Column(Integer, nullable=False, default=1)

    # 统计
    total_sessions = Column(Integer, nullable=False, default=0)
    total_duration = Column(Integer, nullable=False, default=0)  # 累计训练秒数
    last_trained_at = Column(TZDateTime, nullable=True)

    # 五维评分 (0-100)
    score_safety = Column(Numeric(5, 2), nullable=True)       # 安全规范执行
    score_procedure = Column(Numeric(5, 2), nullable=True)     # 步骤规范性
    score_precision = Column(Numeric(5, 2), nullable=True)     # 操作精度
    score_efficiency = Column(Numeric(5, 2), nullable=True)    # 时间效率
    score_tools = Column(Numeric(5, 2), nullable=True)         # 工具使用规范

    # 认证状态
    cert_l1_passed = Column(Boolean, nullable=False, default=False)
    cert_l2_passed = Column(Boolean, nullable=False, default=False)
    cert_l3_eligible = Column(Boolean, nullable=False, default=False)


class StudentWeakStep(Base, TimestampMixin):
    """学员薄弱步骤表 - UF-10-a-2"""
    __tablename__ = "student_weak_steps"

    id = Column(Integer, primary_key=True, index=True)

    # 关联用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", backref="weak_steps")

    # 步骤信息
    step_id = Column(String(50), nullable=False)
    sop_id = Column(String(50), nullable=True)

    # 统计
    fail_count = Column(Integer, nullable=False, default=0)
    last_failed_at = Column(TZDateTime, nullable=True)
    fail_tags = Column(JSON, nullable=True)  # ["tool_error", "value_out_of_range", "sequence_wrong"]

    # 解决状态
    is_resolved = Column(Boolean, nullable=False, default=False)

    # 唯一约束
    __table_args__ = (
        # 复合主键实际上用 id，这里用唯一索引
        {'sqlite_autoincrement': True},
    )
