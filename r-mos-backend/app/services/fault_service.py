"""
故障案例服务
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from fastapi import HTTPException
import logging

from app.models.fault import FaultCase
from app.schemas.fault import (
    FaultCaseCreate,
    FaultCaseUpdate,
    FaultCaseResponse,
    FaultCaseListItem,
    FaultCaseListResponse
)

logger = logging.getLogger(__name__)

class FaultCaseService:
    """故障案例服务
    
    职责：
    - 故障案例CRUD操作
    - 列表查询与筛选
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_fault_cases(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> FaultCaseListResponse:
        """获取故障案例列表"""
        query = select(FaultCase)
        
        if category:
            query = query.where(FaultCase.category == category)
        if severity:
            query = query.where(FaultCase.severity == severity)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        fault_cases = result.scalars().all()
        
        items = [
            FaultCaseListItem(
                id=fc.id,
                fault_code=fc.fault_code,
                name=fc.name,
                category=fc.category,
                severity=fc.severity,
                created_at=fc.created_at
            )
            for fc in fault_cases
        ]
        
        return FaultCaseListResponse(total=total, items=items)
    
    async def get_fault_case(self, fault_case_id: int) -> FaultCaseResponse:
        """获取故障案例详情"""
        fault_case = await self.db.get(FaultCase, fault_case_id)
        if not fault_case:
            raise HTTPException(status_code=404, detail="Fault case not found")
        
        return FaultCaseResponse.model_validate(fault_case)
    
    async def create_fault_case(self, request: FaultCaseCreate) -> FaultCaseResponse:
        """创建故障案例"""
        # 检查fault_code唯一性
        stmt = select(FaultCase).where(FaultCase.fault_code == request.fault_code)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Fault code '{request.fault_code}' already exists"
            )
        
        fault_case = FaultCase(**request.model_dump())
        self.db.add(fault_case)
        await self.db.commit()
        await self.db.refresh(fault_case)
        
        logger.info(f"Created fault case: {fault_case.fault_code}")
        
        return FaultCaseResponse.model_validate(fault_case)
    
    async def update_fault_case(
        self,
        fault_case_id: int,
        request: FaultCaseUpdate
    ) -> FaultCaseResponse:
        """更新故障案例"""
        fault_case = await self.db.get(FaultCase, fault_case_id)
        if not fault_case:
            raise HTTPException(status_code=404, detail="Fault case not found")
        
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(fault_case, field, value)
        
        await self.db.commit()
        await self.db.refresh(fault_case)
        
        return FaultCaseResponse.model_validate(fault_case)
    
    async def delete_fault_case(self, fault_case_id: int):
        """删除故障案例"""
        fault_case = await self.db.get(FaultCase, fault_case_id)
        if not fault_case:
            raise HTTPException(status_code=404, detail="Fault case not found")
        
        await self.db.delete(fault_case)
        await self.db.commit()
        
        logger.info(f"Deleted fault case: {fault_case.fault_code}")
