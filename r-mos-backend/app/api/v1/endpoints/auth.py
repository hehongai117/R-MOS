"""
认证相关 API（Gate-1 / A-001）。
"""
from __future__ import annotations

from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, hash_token, is_strong_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)


router = APIRouter()
ACCESS_TOKEN_EXPIRES_SECONDS = 900
REFRESH_TOKEN_EXPIRES_SECONDS = 7 * 24 * 60 * 60


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


def _issue_token_pair() -> tuple[str, str]:
    """一次性生成 access/refresh 令牌。"""
    return _issue_token("access"), _issue_token("refresh")


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

    access_token, refresh_token = _issue_token_pair()
    now = datetime.utcnow()
    user.last_login_at = now
    db.add(
        RefreshToken(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(seconds=REFRESH_TOKEN_EXPIRES_SECONDS),
            is_revoked=False,
        )
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
    )


@router.post("/auth/refresh", response_model=TokenResponse, status_code=200)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    token_hash_value = hash_token(payload.refresh_token)
    session_result = await db.execute(
        select(RefreshToken).where(RefreshToken.refresh_token_hash == token_hash_value)
    )
    session = session_result.scalar_one_or_none()

    is_invalid = (
        session is None
        or session.is_revoked
        or session.revoked_at is not None
        or session.expires_at <= now
    )
    if is_invalid:
        return _error_response(
            request,
            status_code=401,
            error_type="InvalidRefreshToken",
            code="AUTH_004",
            message="刷新令牌无效或已失效",
        )

    session.is_revoked = True
    session.revoked_at = now

    new_access_token, new_refresh_token = _issue_token_pair()
    db.add(
        RefreshToken(
            user_id=session.user_id,
            refresh_token_hash=hash_token(new_refresh_token),
            issued_at=now,
            expires_at=now + timedelta(seconds=REFRESH_TOKEN_EXPIRES_SECONDS),
            is_revoked=False,
        )
    )
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
    )


@router.post("/auth/logout", response_model=MessageResponse, status_code=200)
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash_value = hash_token(payload.refresh_token)
    session_result = await db.execute(
        select(RefreshToken).where(RefreshToken.refresh_token_hash == token_hash_value)
    )
    session = session_result.scalar_one_or_none()

    if session is not None and not session.is_revoked:
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        await db.commit()

    return MessageResponse(message="登出成功", success=True)
