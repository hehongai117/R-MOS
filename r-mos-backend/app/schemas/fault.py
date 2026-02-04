"""
故障案例相关Pydantic Schema（V2.3修复版）
"""
import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime


def sanitize_input(value: str) -> str:
    """移除可能的脚本标签和危险字符"""
    if not value:
        return value
    # 移除 <script> 标签及其内容
    value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
    # 移除其他 HTML 标签
    value = re.sub(r'<[^>]+>', '', value)
    return value.strip()


class FaultCaseBase(BaseModel):
    """故障案例基础Schema"""
    fault_code: str = Field(..., max_length=50, description="故障代码")
    name: str = Field(..., max_length=200, description="故障名称")
    description: str = Field(..., description="故障描述")
    category: Optional[str] = Field(None, description="故障分类")
    severity: str = Field("medium", description="严重程度：low/medium/high")
    affected_parts: Optional[List[str]] = Field(None, description="受影响部件列表")
    symptoms: Optional[List[str]] = Field(None, description="故障症状")
    diagnosis_steps: Optional[List[str]] = Field(None, description="诊断步骤")
    solution_steps: Optional[List[str]] = Field(None, description="解决步骤")

    @field_validator('name', 'description', 'category', mode='before')
    @classmethod
    def clean_text_fields(cls, v):
        if isinstance(v, str):
            return sanitize_input(v)
        return v


class FaultCaseCreate(FaultCaseBase):
    """创建故障案例"""
    pass


class FaultCaseUpdate(BaseModel):
    """更新故障案例"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    affected_parts: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    diagnosis_steps: Optional[List[str]] = None
    solution_steps: Optional[List[str]] = None

    @field_validator('name', 'description', 'category', mode='before')
    @classmethod
    def clean_text_fields(cls, v):
        if isinstance(v, str):
            return sanitize_input(v)
        return v


class FaultCaseResponse(FaultCaseBase):
    """故障案例响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FaultCaseListItem(BaseModel):
    """故障案例列表项"""
    id: int
    fault_code: str
    name: str
    category: Optional[str]
    severity: str
    created_at: datetime

    # V2.3.1 修复: 添加 from_attributes 支持 ORM 对象转换
    class Config:
        from_attributes = True


class FaultCaseListResponse(BaseModel):
    """故障案例列表响应"""
    total: int
    items: List[FaultCaseListItem]
