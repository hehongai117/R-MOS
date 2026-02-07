"""
认证相关 API（Gate-1 / A-001）。
"""
from __future__ import annotations

from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, is_strong_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse


router = APIRouter()


def _error_response(
    request: Request,
    *,
    status_code: int,
    error_type: str,
    code: str,
    message: str,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", str(id(request)))
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "error_type": error_type,
            "message": message,
            "details": {
                "code": code,
                "message": message,
                "details": {},
            },
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": trace_id,
        },
    )


def _issue_token(prefix: str) -> str:
    """生成最小可用会话令牌。"""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


@router.post("/auth/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = payload.email.lower()
    existing_user_result = await db.execute(
        select(User.id).where(func.lower(User.email) == normalized_email)
    )
    if existing_user_result.scalar_one_or_none() is not None:
        return _error_response(
            request,
            status_code=400,
            error_type="UserAlreadyExists",
            code="USER_001",
            message="邮箱已存在",
        )

    if not is_strong_password(payload.password):
        return _error_response(
            request,
            status_code=400,
            error_type="WeakPassword",
            code="USER_002",
            message="密码强度不足",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterResponse(user_id=user.id, email=user.email, message="注册成功")


@router.post("/auth/login", response_model=TokenResponse, status_code=200)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = payload.email.lower()
    user_result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = user_result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        return _error_response(
            request,
            status_code=401,
            error_type="AuthenticationFailed",
            code="AUTH_001",
            message="邮箱或密码错误",
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=_issue_token("access"),
        refresh_token=_issue_token("refresh"),
        expires_in=900,
    )
