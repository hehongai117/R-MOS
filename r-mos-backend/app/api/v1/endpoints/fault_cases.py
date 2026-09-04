"""
故障案例API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.schemas.fault import (
    FaultCaseCreate,
    FaultCaseUpdate,
    FaultCaseResponse,
    FaultCaseListResponse
)
from app.models.fault import FaultCase
from app.services.fault_service import FaultCaseService
from app.core.database import get_db
from app.services.ownership import ensure_role_for_write, ensure_write_owner
from app.services.authz_guard import ActorContext, get_current_actor

router = APIRouter()


async def _load_fault_case_or_404(db: AsyncSession, fault_case_id: int) -> FaultCase:
    """取故障案例供归属校验；不存在则 404（与守卫的 403 区分开）。"""
    fault_case = await db.get(FaultCase, fault_case_id)
    if fault_case is None:
        raise HTTPException(status_code=404, detail=f"Fault case {fault_case_id} not found")
    return fault_case


@router.get("/fault-cases", response_model=FaultCaseListResponse)
async def list_fault_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="分类筛选"),
    severity: Optional[str] = Query(None, description="严重程度筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取故障案例列表"""
    service = FaultCaseService(db)
    result = await service.list_fault_cases(
        skip=skip,
        limit=limit,
        category=category,
        severity=severity
    )
    return result

@router.get("/fault-cases/{fault_case_id}", response_model=FaultCaseResponse)
async def get_fault_case(
    fault_case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取故障案例详情"""
    service = FaultCaseService(db)
    fault_case = await service.get_fault_case(fault_case_id)
    return fault_case

@router.post("/fault-cases", response_model=FaultCaseResponse, status_code=201)
async def create_fault_case(
    request: FaultCaseCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """创建故障案例"""
    # 审计 M-01 / 裁定 §9-2：建者即所有者，此前无身份注入且表无归属字段。
    await ensure_role_for_write(
        db, http_request, actor, "teacher", "admin",
        action="create_fault_case", resource_type="FaultCase",
    )
    service = FaultCaseService(db)
    fault_case = await service.create_fault_case(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )
    return fault_case

@router.put("/fault-cases/{fault_case_id}", response_model=FaultCaseResponse)
async def update_fault_case(
    fault_case_id: int,
    request: FaultCaseUpdate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """更新故障案例"""
    # 审计 M-01 / 裁定 §9-2：归属字段已补齐，由角色制过渡改为对象级校验。
    # 历史行 `created_by_user_id` 为 NULL＝系统内置内容，仅管理员可改。
    fault_case_obj = await _load_fault_case_or_404(db, fault_case_id)
    await ensure_write_owner(
        db, http_request, actor, fault_case_obj.created_by_user_id,
        action="update_fault_case", resource_type="FaultCase", resource_id=fault_case_id,
    )
    service = FaultCaseService(db)
    fault_case = await service.update_fault_case(fault_case_id, request)
    return fault_case

@router.delete("/fault-cases/{fault_case_id}")
async def delete_fault_case(
    fault_case_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """删除故障案例"""
    # 审计 M-01 / 裁定 §9-2：归属字段已补齐，由角色制过渡改为对象级校验。
    # 历史行 `created_by_user_id` 为 NULL＝系统内置内容，仅管理员可改。
    fault_case_obj = await _load_fault_case_or_404(db, fault_case_id)
    await ensure_write_owner(
        db, http_request, actor, fault_case_obj.created_by_user_id,
        action="delete_fault_case", resource_type="FaultCase", resource_id=fault_case_id,
    )
    service = FaultCaseService(db)
    await service.delete_fault_case(fault_case_id)
    return {"message": "Fault case deleted successfully"}
