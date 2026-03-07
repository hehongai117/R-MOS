"""
Report相关Pydantic Schema（V2.3完整版）
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class ScoreBreakdown(BaseModel):
    """评分细分"""
    professionalism: float = Field(..., description="专业性得分（0-25）")
    compliance: float = Field(..., description="规范性得分（0-25）")
    efficiency: float = Field(..., description="效率得分（0-25）")
    safety: float = Field(..., description="安全性得分（0-25）")


class StepScore(BaseModel):
    """步骤得分"""
    step_index: int
    step_title: str
    score: float
    max_score: float
    deductions: List[Dict[str, Any]]
    remarks: Optional[str] = None


class TaskReport(BaseModel):
    """任务报告"""
    task_id: int
    task_title: str
    sop_name: Optional[str] = Field(None, description="SOP名称（可能为NULL）")
    user_id: Optional[int]
    started_at: datetime
    completed_at: datetime
    total_duration_seconds: int
    expected_duration_seconds: Optional[int]
    final_score: float
    pass_score: float
    is_passed: bool
    score_breakdown: ScoreBreakdown
    step_scores: List[StepScore]
    total_steps: int
    completed_steps: int
    skipped_steps: int
    error_count: int
    recommendations: List[str]
    generated_at: datetime


# ============ P2-2: LLM Evaluation Report Schema ============

class LLMEvaluationSection(BaseModel):
    """LLM 生成的评估报告章节"""
    summary: str = Field(..., description="总体评估摘要")
    strengths: List[str] = Field(..., description="学员优势分析")
    improvement_areas: List[str] = Field(..., description="待改进领域")
    root_cause_analysis: str = Field(..., description="问题根本原因分析")
    personalized_suggestions: List[str] = Field(..., description="个性化学习建议")
    next_learning_plan: str = Field(..., description="下一步学习计划")


# ============ P2-3: Peer Comparison Schema ============

class PeerComparisonSection(BaseModel):
    """同伴对比部分"""
    student_level: str = Field(..., description="学员级别")
    group_stats: Dict[str, Any] = Field(..., description="同级别群体统计")
    student_stats: Dict[str, Any] = Field(..., description="学员个人统计")
    comparison: Dict[str, Any] = Field(..., description="对比结果")


class LLMEvaluationReport(BaseModel):
    """LLM 增强的评估报告 - P2-2

    在基础 TaskReport 基础上增加 LLM 生成的叙述性内容：
    - 原因分析
    - 个性化建议
    - 下一步学习计划
    """
    # 基础报告数据
    task_id: int
    task_title: str
    sop_name: Optional[str] = None
    user_id: Optional[int]
    started_at: datetime
    completed_at: datetime
    total_duration_seconds: int
    expected_duration_seconds: Optional[int]
    final_score: float
    pass_score: float
    is_passed: bool
    score_breakdown: ScoreBreakdown
    step_scores: List[StepScore]
    total_steps: int
    completed_steps: int
    skipped_steps: int
    error_count: int
    recommendations: List[str]
    generated_at: datetime

    # LLM 增强内容
    llm_evaluation: Optional[LLMEvaluationSection] = Field(
        default=None,
        description="LLM 生成的评估内容（需要 LLM 服务可用）"
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="LLM 提供商（如 openai, anthropic）"
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="使用的 LLM 模型"
    )

    # P2-3: 同伴对比
    peer_comparison: Optional[PeerComparisonSection] = Field(
        default=None,
        description="同伴对比（需要足够数据）"
    )
