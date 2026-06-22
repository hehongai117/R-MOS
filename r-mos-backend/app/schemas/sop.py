"""
SOP相关Pydantic Schema
拆包B已定义基础Schema，拆包C扩展列表查询专用Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ===== 拆包B定义的Schema（直接复用） =====
class SOPStepBase(BaseModel):
    """SOP步骤基础Schema（来自拆包B）"""
    step_index: int = Field(..., ge=1, description="步骤索引（从1开始）")
    title: str = Field(..., max_length=200, description="步骤标题")
    description: str = Field(..., description="步骤详细描述")
    target_part: Optional[str] = Field(None, description="目标部件ID")
    expected_action: str = Field(..., description="期望操作类型")
    action_params: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    is_critical: bool = Field(False, description="是否为关键步骤")
    timeout_seconds: int = Field(300, ge=10, description="超时时长（秒）")
    allow_skip: bool = Field(False, description="是否允许跳过")
    hints: Optional[List[str]] = Field(None, description="提示信息")
    tools_required: Optional[List[str]] = Field(None, description="所需工具")

class SOPStepCreate(SOPStepBase):
    """创建SOP步骤（来自拆包B）"""
    pass

class SOPStepResponse(SOPStepBase):
    """SOP步骤响应（来自拆包B）"""
    id: int
    sop_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SOPBase(BaseModel):
    """SOP基础Schema（来自拆包B）"""
    name: str = Field(..., max_length=200, description="SOP名称")
    description: Optional[str] = Field(None, description="SOP描述")
    applicable_model: str = Field(..., description="适用机器人型号")
    category: Optional[str] = Field(None, description="分类")
    difficulty_level: str = Field("medium", description="难度等级：low/medium/high")
    estimated_time: Optional[int] = Field(None, description="预估时长（秒）")
    version: Optional[str] = Field(None, max_length=20, description="SOP版本号")
    target_module: Optional[str] = Field(None, max_length=100, description="目标维护模块")

class SOPCreate(SOPBase):
    """创建SOP（来自拆包B，包含嵌套steps）"""
    robot_model_id: Optional[int] = Field(None, description="关联机器人型号ID")
    steps: List[SOPStepCreate] = Field(..., min_length=1, description="SOP步骤列表")

class SOPUpdate(BaseModel):
    """更新SOP（拆包B定义）"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_time: Optional[int] = None

class SOPResponse(SOPBase):
    """SOP完整响应（来自拆包B，包含完整steps）"""
    id: int
    created_at: datetime
    updated_at: datetime
    steps: List[SOPStepResponse]
    
    class Config:
        from_attributes = True


# ===== V2.3新增：SOP删除相关Schema =====

class SOPDeleteWarning(BaseModel):
    """SOP删除警告响应（V2.3新增）
    
    当SOP有关联Task时返回此警告，要求前端确认
    """
    can_delete: bool = Field(False, description="是否可直接删除")
    warning_type: str = Field("REFERENCED_BY_TASKS", description="警告类型")
    message: str = Field(..., description="警告消息")
    affected_tasks: List[Dict[str, Any]] = Field(..., description="受影响的Task列表")
    force_required: bool = Field(True, description="是否需要force参数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "can_delete": False,
                "warning_type": "REFERENCED_BY_TASKS",
                "message": "此SOP被3个Task引用，删除后这些Task将无法查看原SOP信息",
                "affected_tasks": [
                    {"task_id": 123, "title": "新手训练-01", "status": "completed"},
                    {"task_id": 124, "title": "新手训练-02", "status": "in_progress"},
                    {"task_id": 125, "title": "新手训练-03", "status": "pending"}
                ],
                "force_required": True
            }
        }


class SOPDeleteResponse(BaseModel):
    """SOP删除成功响应（V2.3新增）"""
    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="删除结果消息")
    deleted_sop_id: int = Field(..., description="已删除的SOP ID")
    affected_task_count: int = Field(0, description="受影响的Task数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "SOP已删除，3个关联Task的sop_id已设为NULL",
                "deleted_sop_id": 42,
                "affected_task_count": 3
            }
        }


# ===== 拆包C扩展的Schema（列表查询优化） =====
class SOPListItem(BaseModel):
    """SOP列表项（拆包C新增，简化对象）

    遵循骨架文档§4.5规范：列表查询不加载完整steps
    """
    id: int
    name: str
    category: Optional[str]
    difficulty_level: str
    step_count: int = Field(..., description="步骤数量（不加载完整steps）")
    estimated_time: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class SOPListResponse(BaseModel):
    """SOP列表响应（拆包C新增，分页容器）"""
    total: int = Field(..., description="总数量")
    items: List[SOPListItem] = Field(..., description="SOP列表")


# Phase 2: SOP adjudication format
DIFFICULTY_MAP = {"low": "beginner", "medium": "intermediate", "high": "advanced"}

class SOPAdjudicationStepResponse(BaseModel):
    stepId: str
    stepIndex: int
    title: str
    description: str
    action: str
    targetParts: List[str] = Field(default_factory=list)
    requiredTool: Optional[str] = None
    preconditions: List[Dict[str, Any]] = Field(default_factory=list)
    validations: List[Dict[str, Any]] = Field(default_factory=list)
    failureReasons: List[Dict[str, Any]] = Field(default_factory=list)
    onSuccess: Dict[str, Any] = Field(default_factory=dict)
    onFailure: Dict[str, Any] = Field(default_factory=dict)
    isIrreversible: bool = False
    fatalOnFailure: bool = False

class SOPAdjudicationResponse(BaseModel):
    sopId: str
    title: str
    version: str
    targetModule: str
    estimatedTime: int
    difficulty: str
    steps: List[SOPAdjudicationStepResponse]

class SOPAdjudicationListResponse(BaseModel):
    total: int
    items: List[SOPAdjudicationResponse]
