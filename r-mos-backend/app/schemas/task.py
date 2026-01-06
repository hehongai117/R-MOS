"""
Task相关Pydantic Schema（V2.3完整版）

V2.3.1 修复：
- 添加 status 字段验证器，自动将字符串转换为 TaskStatus 枚举
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """创建Task请求"""
    title: str = Field(..., max_length=200, description="任务标题")
    sop_id: int = Field(..., gt=0, description="SOP ID")
    user_id: Optional[int] = Field(None, description="执行用户ID")
    time_limit: Optional[int] = Field(None, ge=60, description="时间限制（秒）")
    pass_score: int = Field(70, ge=0, le=100, description="及格分数")


class TaskResponse(BaseModel):
    """Task响应"""
    id: int
    title: str
    sop_id: Optional[int] = Field(None, description="SOP ID（可能为NULL，若SOP已删除）")
    user_id: Optional[int]
    status: TaskStatus
    current_step_index: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    paused_at: Optional[datetime]
    time_limit: Optional[int]
    pass_score: int
    final_score: Optional[int]
    is_passed: Optional[bool]
    created_at: datetime
    updated_at: datetime

    # V2.3.1 修复: 自动将字符串转换为 TaskStatus 枚举
    @field_validator('status', mode='before')
    @classmethod
    def convert_status_to_enum(cls, v):
        """将数据库中的字符串状态转换为枚举类型"""
        if isinstance(v, str):
            return TaskStatus(v)
        return v

    class Config:
        from_attributes = True


class StepExecutionRequest(BaseModel):
    """执行步骤请求"""
    step_index: int = Field(..., ge=1, description="步骤索引")
    action: str = Field(..., description="执行的操作")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    notes: Optional[str] = Field(None, description="备注")


class StepExecutionResponse(BaseModel):
    """执行步骤响应（V2.3强制约束）
    
    ⚠️ 前端必须处理所有字段，用于驱动任务执行流程
    ⚠️ 修改任何字段前必须通知前端团队
    """
    task_id: int = Field(..., description="任务ID")
    step_index: int = Field(..., ge=1, description="已执行步骤索引")
    status: str = Field(..., description="执行状态：success/failed/skipped")
    message: str = Field(..., description="执行结果消息")
    
    # 强制返回字段（拆包D依赖）
    snapshot_id: Optional[int] = Field(None, description="快照ID（如已创建）")
    next_step_index: Optional[int] = Field(None, ge=1, description="下一步骤索引（如未完成）")
    is_task_completed: bool = Field(False, description="任务是否已完成")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": 123,
                "step_index": 2,
                "status": "success",
                "message": "步骤'检查关节温度'执行成功",
                "snapshot_id": 456,
                "next_step_index": 3,
                "is_task_completed": False
            }
        }
