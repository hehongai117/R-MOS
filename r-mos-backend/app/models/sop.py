"""
SOP（标准操作流程）数据模型（V2.1.2 P0修复版）
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class SOP(Base, TimestampMixin):
    """SOP主表
    
    存储标准操作流程的元数据
    
    ✅ V2.1.2修正：移除cascade删除，保护历史数据
    """
    __tablename__ = "sops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True, comment="SOP名称")
    description = Column(Text, nullable=True, comment="SOP描述")
    applicable_model = Column(String(100), nullable=False, index=True, comment="适用机器人型号")
    category = Column(String(50), nullable=True, comment="分类")
    difficulty_level = Column(String(20), default="medium", comment="难度等级：low/medium/high")
    estimated_time = Column(Integer, nullable=True, comment="预估时长（秒）")
    version = Column(String(20), nullable=True, comment="SOP版本号")
    target_module = Column(String(100), nullable=True, comment="目标维护模块")
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联机器人型号 ID",
    )

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

    # V2.1.2修正：移除级联删除，保护历史数据
    steps = relationship(
        "SOPStep", 
        back_populates="sop", 
        cascade="save-update, merge",
        lazy="selectin"  # V2.3.1修复: 支持异步session中的关系加载
    )
    tasks = relationship("Task", back_populates="sop")
    
    def __repr__(self):
        return f"<SOP(id={self.id}, name={self.name})>"


class SOPStep(Base, TimestampMixin):
    """SOP步骤表
    
    存储SOP的具体执行步骤
    """
    __tablename__ = "sop_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, comment="步骤索引（从1开始）")
    title = Column(String(200), nullable=False, comment="步骤标题")
    description = Column(Text, nullable=False, comment="步骤描述")
    target_part = Column(String(100), nullable=True, comment="目标部件ID")
    expected_action = Column(String(50), nullable=False, comment="期望操作")
    action_params = Column(JSON, nullable=True, comment="操作参数（JSON）")
    validation_rules = Column(JSON, nullable=True, comment="验证规则（JSON）")
    is_critical = Column(Boolean, default=False, comment="是否为关键步骤")
    severity_level = Column(String(20), default="WARN", comment="严重程度等级：INFO/WARN/SAFETY_HALT")
    timeout_seconds = Column(Integer, default=300, comment="超时时长（秒）")
    allow_skip = Column(Boolean, default=False, comment="是否允许跳过")
    hints = Column(JSON, nullable=True, comment="提示信息（JSON）")
    tools_required = Column(JSON, nullable=True, comment="所需工具列表（JSON）")
    # 三段式引导（2026-08-17）
    phase = Column(String(20), nullable=False, server_default="execute",
                   comment="阶段：prep/execute/verify")
    group_path = Column(String(200), nullable=True, comment="模块/子装配路径，如 torso/sub_a")
    step_view = Column(JSON, nullable=True, comment="作者化 3D 构图（相机/可见集/高亮/爆炸）")
    required_parts = Column(JSON, nullable=True, comment="本步所需物料 [{bom_code,name,qty,note}]")
    
    # 关系
    sop = relationship("SOP", back_populates="steps")
    
    def __repr__(self):
        return f"<SOPStep(id={self.id}, sop_id={self.sop_id}, index={self.step_index})>"
