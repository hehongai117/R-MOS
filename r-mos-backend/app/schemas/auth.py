"""
认证相关的Pydantic Schema

用于登录、Token等请求和响应
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# ============ 请求Schema ============

class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
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


# ============ 响应Schema ============

class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问Token")
    refresh_token: str = Field(..., description="刷新Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class MessageResponse(BaseModel):
    """消息响应"""
    message: str = Field(..., description="消息内容")
    success: bool = Field(default=True, description="是否成功")
