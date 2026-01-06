"""
Fault（故障案例）数据模型
"""
from sqlalchemy import Column, Integer, String, Text, JSON
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
    
    def __repr__(self):
        return f"<FaultCase(id={self.id}, code={self.fault_code})>"
