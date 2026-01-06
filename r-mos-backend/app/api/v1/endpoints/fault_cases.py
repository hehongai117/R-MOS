"""
故障案例API端点
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.schemas.fault import (
    FaultCaseCreate,
    FaultCaseUpdate,
    FaultCaseResponse,
    FaultCaseListResponse
)
from app.services.fault_service import FaultCaseService
from app.core.database import get_db

router = APIRouter()

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
    db: AsyncSession = Depends(get_db)
):
    """创建故障案例"""
    service = FaultCaseService(db)
    fault_case = await service.create_fault_case(request)
    return fault_case

@router.put("/fault-cases/{fault_case_id}", response_model=FaultCaseResponse)
async def update_fault_case(
    fault_case_id: int,
    request: FaultCaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新故障案例"""
    service = FaultCaseService(db)
    fault_case = await service.update_fault_case(fault_case_id, request)
    return fault_case

@router.delete("/fault-cases/{fault_case_id}")
async def delete_fault_case(
    fault_case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除故障案例"""
    service = FaultCaseService(db)
    await service.delete_fault_case(fault_case_id)
    return {"message": "Fault case deleted successfully"}
