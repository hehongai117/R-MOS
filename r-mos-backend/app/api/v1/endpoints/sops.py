"""
SOP API端点（V2.3完整版）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.schemas.sop import (
    SOPCreate,
    SOPResponse,
    SOPDeleteWarning,
    SOPDeleteResponse
)
from app.services.sop_service import SOPService
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError

router = APIRouter()


@router.post("/sops", response_model=SOPResponse, status_code=201, tags=["SOPs"])
async def create_sop(
    request: SOPCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建SOP
    
    示例请求：
    ```json
    {
      "name": "膝关节检查流程",
      "description": "用于日常维护的膝关节检查标准流程",
      "applicable_model": "MOCK_HUMANOID_V1",
      "category": "maintenance",
      "difficulty_level": "medium",
      "estimated_time": 600,
      "steps": [
        {
          "step_index": 1,
          "title": "检查关节温度",
          "description": "使用红外测温仪检查膝关节温度",
          "target_part": "knee_right",
          "expected_action": "measure_temperature",
          "is_critical": true,
          "timeout_seconds": 60,
          "allow_skip": false
        }
      ]
    }
    ```
    """
    service = SOPService(db)
    sop = await service.create_sop(request)
    return sop


@router.get("/sops/{sop_id}", response_model=SOPResponse, tags=["SOPs"])
async def get_sop(
    sop_id: int,
    db: AsyncSession = Depends(get_db)
):
    """查询单个SOP（含步骤）"""
    try:
        service = SOPService(db)
        sop = await service.get_sop(sop_id)
        return sop
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sops", tags=["SOPs"])
async def list_sops(
    applicable_model: Optional[str] = Query(None, description="过滤：机器人型号"),
    category: Optional[str] = Query(None, description="过滤：分类"),
    robot_model_id: Optional[int] = Query(None, description="过滤：机器人型号ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """查询SOP列表，返回分页格式 {items, total}"""
    service = SOPService(db)
    return await service.list_sops(
        applicable_model=applicable_model,
        category=category,
        robot_model_id=robot_model_id,
        skip=skip,
        limit=limit
    )


@router.get("/sops/{sop_id}/delete-impact", response_model=SOPDeleteWarning, tags=["SOPs"])
async def check_sop_delete_impact(
    sop_id: int,
    db: AsyncSession = Depends(get_db)
):
    """检查删除SOP的影响（V2.3新增 - 前端二次确认用）
    
    前端调用流程：
    1. 用户点击删除按钮
    2. 前端调用此接口：GET /api/v1/sops/{id}/delete-impact
    3. 如果返回 force_required=true：
       - 显示警告对话框："此SOP被X个Task引用..."
       - 用户确认后：调用 DELETE /api/v1/sops/{id}?force=true
    4. 如果返回 force_required=false：
       - 直接调用 DELETE /api/v1/sops/{id}
    
    示例响应：
    ```json
    {
      "can_delete": false,
      "warning_type": "REFERENCED_BY_TASKS",
      "message": "此SOP被3个Task引用，删除后这些Task将无法查看原SOP信息",
      "affected_tasks": [
        {"task_id": 123, "title": "新手训练-01", "status": "completed"},
        {"task_id": 124, "title": "新手训练-02", "status": "in_progress"}
      ],
      "force_required": true
    }
    ```
    """
    try:
        service = SOPService(db)
        warning = await service.check_delete_impact(sop_id)
        return warning
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/sops/{sop_id}", response_model=SOPDeleteResponse, tags=["SOPs"])
async def delete_sop(
    sop_id: int,
    force: bool = Query(
        False,
        description="是否强制删除（忽略关联Task）。如有关联Task且force=false，将返回409错误"
    ),
    db: AsyncSession = Depends(get_db)
):
    """删除SOP（V2.3修复版 - 实现骨架§5.5规则）
    
    ⚠️ 重要说明：
    - 如SOP被Task引用且force=false → 返回409错误
    - 前端应先调用 GET /sops/{id}/delete-impact 检查影响
    - 用户确认后传入force=true执行删除
    
    删除行为：
    - 物理删除SOP及其所有步骤
    - 关联Task的sop_id字段设为NULL（保留历史记录）
    
    示例：
    ```bash
    # 1. 检查影响
    curl http://localhost:8000/api/v1/sops/42/delete-impact
    
    # 2. 如有警告，强制删除
    curl -X DELETE "http://localhost:8000/api/v1/sops/42?force=true"
    ```
    
    成功响应：
    ```json
    {
      "success": true,
      "message": "SOP已删除，3个关联Task的sop_id已设为NULL",
      "deleted_sop_id": 42,
      "affected_task_count": 3
    }
    ```
    
    409错误响应：
    ```json
    {
      "status_code": 409,
      "error_type": "BusinessRuleViolation",
      "message": "此SOP被3个Task引用，删除需要force=true参数",
      "details": {
        "code": "SOP_REFERENCED_BY_TASKS",
        "affected_task_count": 3,
        "affected_tasks": [...],
        "force_required": true
      }
    }
    ```
    """
    try:
        service = SOPService(db)
        result = await service.delete_sop(sop_id, force=force)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
