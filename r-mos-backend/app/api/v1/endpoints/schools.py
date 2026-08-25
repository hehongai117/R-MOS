"""学校搜索和教师列表端点（公开，无需认证）。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.school import School
from app.models.user import User

router = APIRouter(prefix="/schools", tags=["schools"])


def _mask_email(email: str) -> str:
    """把邮箱脱敏成"首字符 + 掩码 + 域名"（AUTH-SCHOOLS-PII）。

    本路由是公开白名单成员（学生注册时要选导师），改造前直接返回教师完整邮箱，
    任何人只要知道学校名就能枚举全校教师邮箱。

    保留首字符与域名：注册页需要靠它区分同名教师，而批量采集价值归零。
    完整邮箱只对已认证且有权的调用者可见（本路由不提供）。
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


@router.get("")
async def search_schools(
    q: str = Query("", description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """搜索学校名称（公开接口，用于注册页自动补全）。"""
    stmt = select(School.id, School.name, School.province)
    if q.strip():
        stmt = stmt.where(School.name.contains(q.strip()))
    stmt = stmt.order_by(School.name).limit(limit)

    result = await db.execute(stmt)
    items = [{"id": r.id, "name": r.name, "province": r.province} for r in result.fetchall()]
    return {"items": items}


@router.get("/{school_name}/teachers")
async def list_school_teachers(
    school_name: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定学校的教师列表（公开接口，用于学生注册时选择教师）。"""
    school_exists = (
        await db.execute(select(School.id).where(School.name == school_name))
    ).scalar_one_or_none()
    if school_exists is None:
        return {"items": []}

    stmt = (
        select(User.id, User.full_name, User.email)
        .where(User.role == "teacher", User.school_name == school_name)
        .order_by(User.id)
    )
    result = await db.execute(stmt)
    items = [
        {"id": r.id, "full_name": r.full_name or "", "email": _mask_email(r.email)}
        for r in result.fetchall()
    ]
    return {"items": items}
