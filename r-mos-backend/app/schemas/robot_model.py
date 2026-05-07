"""Pydantic schemas for RobotModel CRUD operations."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RobotModelCreate(BaseModel):
    brand: str = Field(..., max_length=100, description="机器人品牌")
    model_name: str = Field(..., max_length=200, description="型号名称")
    version: str = Field(default="1.0", max_length=50, description="版本号")
    description: Optional[str] = Field(default=None, description="描述")


class RobotModelUpdate(BaseModel):
    brand: Optional[str] = Field(default=None, max_length=100)
    model_name: Optional[str] = Field(default=None, max_length=200)
    version: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern="^(private|shared)$")


class RobotModelResponse(BaseModel):
    id: int
    brand: str
    model_name: str
    version: str
    owner_teacher_id: Optional[int] = None
    visibility: str
    status: str
    description: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RobotModelListResponse(BaseModel):
    items: List[RobotModelResponse]
    total: int


class RobotAssetResponse(BaseModel):
    id: int
    robot_model_id: int
    asset_type: str
    file_path: str
    file_size: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
