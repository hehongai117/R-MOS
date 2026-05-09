"""场景列表端点 — 基于 fault_sop_mappings 提供练习场景"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.sop import SOP

router = APIRouter()


class ScenarioItem(BaseModel):
    id: int
    fault_type: str
    sop_id: int
    sop_title: Optional[str] = None
    difficulty: str  # beginner / intermediate / advanced
    priority: int

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    items: List[ScenarioItem]
    total: int


@router.get("/scenarios", response_model=ScenarioListResponse, tags=["scenarios"])
async def list_scenarios(
    difficulty: Optional[str] = Query(None, description="难度筛选: beginner/intermediate/advanced"),
    fault_type: Optional[str] = Query(None, description="故障类型筛选"),
    robot_model_id: Optional[int] = Query(None, description="机器人型号ID筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取可用练习场景列表"""
    query = (
        select(FaultSOPMapping, SOP.name.label("sop_title"))
        .join(SOP, FaultSOPMapping.sop_id == SOP.id, isouter=True)
        .order_by(FaultSOPMapping.priority.desc(), FaultSOPMapping.difficulty)
    )

    if difficulty:
        query = query.where(FaultSOPMapping.difficulty == difficulty)
    if fault_type:
        query = query.where(FaultSOPMapping.fault_type == fault_type)
    if robot_model_id is not None:
        query = query.where(FaultSOPMapping.robot_model_id == robot_model_id)

    result = await db.execute(query)
    rows = result.all()

    items = [
        ScenarioItem(
            id=row.FaultSOPMapping.id,
            fault_type=row.FaultSOPMapping.fault_type,
            sop_id=row.FaultSOPMapping.sop_id,
            sop_title=row.sop_title,
            difficulty=row.FaultSOPMapping.difficulty,
            priority=row.FaultSOPMapping.priority,
        )
        for row in rows
    ]

    return ScenarioListResponse(items=items, total=len(items))
