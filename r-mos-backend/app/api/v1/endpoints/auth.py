"""
认证相关 API（Gate-1 / A-001）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, hash_token, is_strong_password, verify_password
from app.models.access_token import AccessToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.identity.session_initializer import SessionInitializer
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
logger = logging.getLogger(__name__)


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    from app.models.school import School

    normalized_email = payload.email.lower()

    # 1. 邮箱唯一性检查
    existing_user_result = await db.execute(
        select(User.id).where(func.lower(User.email) == normalized_email)
    )
    if existing_user_result.scalar_one_or_none() is not None:
        return _error_response(
            request, status_code=400, error_type="UserAlreadyExists",
            code="USER_001", message="邮箱已存在",
        )

    # 2. 密码强度
    if not is_strong_password(payload.password):
        return _error_response(
            request, status_code=400, error_type="WeakPassword",
            code="USER_002", message="密码强度不足",
        )

    # 3. 角色校验
    if payload.role not in ("student", "teacher"):
        return _error_response(
            request, status_code=400, error_type="InvalidRole",
            code="USER_003", message="角色必须为 student 或 teacher",
        )

    # 4. 学校白名单校验
    school_exists = (
        await db.execute(select(School.id).where(School.name == payload.school_name))
    ).scalar_one_or_none()
    if school_exists is None:
        return _error_response(
            request, status_code=400, error_type="InvalidSchool",
            code="USER_004", message="学校名称不在系统名录中，请检查输入",
        )

    # 5. 学生必须绑定教师
    teacher_id = None
    if payload.role == "student":
        if not payload.teacher_id:
            return _error_response(
                request, status_code=400, error_type="TeacherRequired",
                code="USER_005", message="学生注册必须选择一位教师",
            )
        teacher_result = await db.execute(
            select(User).where(
                User.id == payload.teacher_id,
                User.role == "teacher",
                User.school_name == payload.school_name,
            )
        )
        teacher = teacher_result.scalar_one_or_none()
        if teacher is None:
            return _error_response(
                request, status_code=400, error_type="InvalidTeacher",
                code="USER_006", message="所选教师不存在或不属于该学校",
            )
        teacher_id = payload.teacher_id

    # 6. 创建用户
    is_teacher = payload.role == "teacher"
    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        school_name=payload.school_name,
        teacher_id=teacher_id,
        onboarding_completed=not is_teacher,  # 教师需完成 onboarding
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 7. 自动签发 token（复用已有的辅助函数）
    access_token, refresh_token = _issue_token_pair()
    now = datetime.now(timezone.utc)
    db.add(
        AccessToken(
            user_id=user.id,
            access_token_hash=hash_token(access_token),
            issued_at=now,
            expires_at=now + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS),
            is_revoked=False,
        )
    )
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

    # 8. 确定默认路由
    if is_teacher:
        default_route = "/onboarding/robots"
    else:
        default_route = "/dashboard"

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        message="注册成功",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
        role=user.role,
        default_route=default_route,
        onboarding_completed=user.onboarding_completed,
    )


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
    now = datetime.now(timezone.utc)
    user.last_login_at = now
    db.add(
        AccessToken(
            user_id=user.id,
            access_token_hash=hash_token(access_token),
            issued_at=now,
            expires_at=now + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS),
            is_revoked=False,
        )
    )
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

    # UF-01-c: Get user role and default route
    user_role = getattr(user, 'role', 'student')
    default_route = _get_default_route(user)
    welcome_summary = None
    unfinished_session = None
    try:
        initializer = SessionInitializer(db)
        session_context = await initializer.initialize_session(user.id)
        welcome_summary = session_context.welcome_summary
        unfinished_session = session_context.unfinished_session
    except Exception as exc:  # pragma: no cover - login should not fail on context init
        logger.warning(f"[UF-02-a] Session init skipped for user {user.id}: {exc}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
        role=user_role,
        default_route=default_route,
        welcome_summary=welcome_summary,
        unfinished_session=unfinished_session,
        onboarding_completed=getattr(user, 'onboarding_completed', True),
    )


def _get_default_route(user) -> str:
    """根据角色和 onboarding 状态获取默认跳转路由"""
    if user.role == "teacher" and not getattr(user, "onboarding_completed", True):
        return "/onboarding/robots"
    routes = {
        "student": "/dashboard",
        "teacher": "/workbench/teaching",
        "admin": "/admin/console",
    }
    return routes.get(user.role, "/dashboard")


@router.post("/auth/refresh", response_model=TokenResponse, status_code=200)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
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
        AccessToken(
            user_id=session.user_id,
            access_token_hash=hash_token(new_access_token),
            issued_at=now,
            expires_at=now + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS),
            is_revoked=False,
        )
    )
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

    # Get user info for role
    user_result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    user = user_result.scalar_one_or_none()
    user_role = getattr(user, 'role', 'student') if user else 'student'
    default_route = _get_default_route(user) if user else "/dashboard"

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
        role=user_role,
        default_route=default_route,
        onboarding_completed=getattr(user, 'onboarding_completed', True) if user else True,
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
        now = datetime.now(timezone.utc)
        session.revoked_at = now

        access_tokens_result = await db.execute(
            select(AccessToken).where(
                AccessToken.user_id == session.user_id,
                AccessToken.is_revoked.is_(False),
            )
        )
        for access_token in access_tokens_result.scalars().all():
            access_token.is_revoked = True
            access_token.revoked_at = now

        await db.commit()

    return MessageResponse(message="登出成功", success=True)
