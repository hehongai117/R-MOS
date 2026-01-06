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
