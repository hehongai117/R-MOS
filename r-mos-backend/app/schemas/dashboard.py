"""
仪表盘相关Pydantic Schema

用于仪表盘统计数据展示
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    # 任务统计
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    in_progress_tasks: int = Field(..., description="进行中任务数")
    pending_tasks: int = Field(..., description="待开始任务数")

    # SOP统计
    total_sops: int = Field(..., description="SOP总数")

    # 用户统计
    total_users: int = Field(..., description="用户总数")
    active_users: int = Field(..., description="活跃用户数")

    # 成绩统计
    average_score: Optional[float] = Field(None, description="平均得分")
    pass_rate: Optional[float] = Field(None, description="通过率（百分比）")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tasks": 150,
                "completed_tasks": 100,
                "in_progress_tasks": 20,
                "pending_tasks": 30,
                "total_sops": 15,
                "total_users": 50,
                "active_users": 45,
                "average_score": 82.5,
                "pass_rate": 85.0
            }
        }


class RecentTask(BaseModel):
    """最近任务"""
    id: int
    title: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    final_score: Optional[int] = None


class ScoreTrend(BaseModel):
    """得分趋势数据点"""
    date: str = Field(..., description="日期（YYYY-MM-DD）")
    average_score: float = Field(..., description="当日平均得分")
    task_count: int = Field(..., description="当日完成任务数")


class DashboardRecentTasks(BaseModel):
    """最近任务列表"""
    items: List[RecentTask]


class DashboardScoreTrends(BaseModel):
    """得分趋势"""
    items: List[ScoreTrend]
    period_days: int = Field(..., description="统计周期（天）")
