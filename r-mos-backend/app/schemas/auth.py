"""
认证相关的Pydantic Schema

用于登录、Token等请求和响应
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


# ============ 请求Schema ============

class LoginRequest(BaseModel):
    """登录请求"""
    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., description="密码")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str = Field(..., description="刷新Token")


class RegisterRequest(BaseModel):
    """注册请求。"""

    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(default=None, description="用户姓名")
    role: str = Field(..., description="角色: student 或 teacher")
    school_name: str = Field(..., description="学校全称（必须在白名单中）")
    teacher_id: Optional[int] = Field(default=None, description="绑定教师ID（学生必填）")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "StrongPass123",
                "full_name": "R-MOS User",
                "role": "student",
                "school_name": "北京理工大学",
                "teacher_id": 18,
            }
        }


# ============ 响应Schema ============

class TokenResponse(BaseModel):
    """Token响应 - V0.2 UF-01-c 新增 role 和 default_route"""
    access_token: str = Field(..., description="访问Token")
    refresh_token: str = Field(..., description="刷新Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    role: str = Field(default="student", description="用户角色: student | teacher | admin")
    default_route: str = Field(..., description="默认跳转路由")
    welcome_summary: Optional[str] = Field(default=None, description="登录欢迎摘要")
    unfinished_session: Optional[dict[str, Any]] = Field(default=None, description="未完成训练会话")
    onboarding_completed: bool = Field(default=True, description="是否完成 onboarding")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "role": "student",
                "default_route": "/dashboard"
            }
        }


class MessageResponse(BaseModel):
    """消息响应"""
    message: str = Field(..., description="消息内容")
    success: bool = Field(default=True, description="是否成功")


class RegisterResponse(BaseModel):
    """注册响应（含自动登录 token）。"""

    user_id: int = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    message: str = Field(default="注册成功", description="提示消息")
    access_token: str = Field(..., description="访问Token")
    refresh_token: str = Field(..., description="刷新Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    role: str = Field(..., description="用户角色")
    default_route: str = Field(..., description="默认跳转路由")
    onboarding_completed: bool = Field(..., description="是否完成 onboarding")
