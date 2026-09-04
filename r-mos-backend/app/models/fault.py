"""
Fault（故障案例）数据模型
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, JSON
from .base import Base, TimestampMixin


class FaultCase(Base, TimestampMixin):
    """故障案例模型（由拆包C管理）"""
    __tablename__ = "fault_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    fault_code = Column(String(50), nullable=False, unique=True, index=True, comment="故障代码")
    name = Column(String(200), nullable=False, comment="故障名称")
    description = Column(Text, nullable=False, comment="故障描述")
    category = Column(String(50), nullable=True, comment="故障分类")
    severity = Column(String(20), default="medium", comment="严重程度")
    
    # 故障影响定义
    affected_parts = Column(JSON, nullable=True, comment="受影响部件列表")
    symptoms = Column(JSON, nullable=True, comment="故障症状")
    diagnosis_steps = Column(JSON, nullable=True, comment="诊断步骤")
    solution_steps = Column(JSON, nullable=True, comment="解决步骤")

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
    
    def __repr__(self):
        return f"<FaultCase(id={self.id}, code={self.fault_code})>"
