"""
用户相关的Pydantic Schema

用于请求验证和响应序列化
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    TRAINEE = "trainee"


# ============ 基础Schema ============

class UserBase(BaseModel):
    """用户基础信息"""
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., min_length=1, max_length=100, description="用户名称")


# ============ 请求Schema ============

class UserCreate(UserBase):
    """用户注册请求"""
    password: str = Field(..., min_length=8, max_length=100, description="密码（至少8位）")
    role: Optional[str] = Field(default=UserRole.TRAINEE.value, description="用户角色")

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        if v is None:
            return UserRole.TRAINEE.value
        if isinstance(v, UserRole):
            return v.value
        valid_roles = [r.value for r in UserRole]
        if v not in valid_roles:
            raise ValueError(f"无效角色，可选值: {valid_roles}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "张三",
                "password": "securepassword123",
                "role": "trainee"
            }
        }


class UserUpdate(BaseModel):
    """用户更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="用户名称")
    email: Optional[EmailStr] = Field(None, description="用户邮箱")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    is_active: Optional[bool] = Field(None, description="是否激活")
    role: Optional[str] = Field(None, description="用户角色")

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        if v is None:
            return None
        if isinstance(v, UserRole):
            return v.value
        valid_roles = [r.value for r in UserRole]
        if v not in valid_roles:
            raise ValueError(f"无效角色，可选值: {valid_roles}")
        return v


class PasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码（至少8位）")


# ============ 响应Schema ============

class UserResponse(UserBase):
    """用户响应"""
    id: int
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int
