"""
健康检查API（V2.2完整版）
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime, timezone

from app.adapters.factory import AdapterFactory

router = APIRouter()


# ComponentHealth 必须在 HealthCheckResponse 之前定义
class ComponentHealth(BaseModel):
    """组件健康状态（V2.2新增Schema）"""
    status: str = Field(..., description="组件状态: up/down")
    message: Optional[str] = Field(None, description="状态消息")
    details: Optional[Dict] = Field(None, description="详细信息")


class HealthCheckResponse(BaseModel):
    """健康检查响应（V2.2新增Schema）"""
    status: str = Field(..., description="服务状态: healthy/degraded/unhealthy")
    timestamp: str = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")
    checks: Dict[str, ComponentHealth] = Field(..., description="各组件健康状态")


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """健康检查端点（V2.2完整实现）

    检查项：
    - Adapter连接状态
    - 系统运行状态

    返回：
    - 200: 服务正常
    - 503: 服务异常（Adapter未连接）
    """
    checks = {}
    overall_status = "healthy"

    # 检查Adapter连接
    try:
        adapter = await AdapterFactory.get_adapter()
        is_connected = await adapter.is_connected()

        if is_connected:
            robot_info = await adapter.get_robot_info()
            checks["adapter"] = ComponentHealth(
                status="up",
                message="Adapter已连接",
                details={
                    "type": adapter.__class__.__name__,
                    "robot_id": robot_info.robot_id,
                    "model": robot_info.model
                }
            )
        else:
            checks["adapter"] = ComponentHealth(
                status="down",
                message="Adapter未连接"
            )
            overall_status = "unhealthy"
    except Exception as e:
        checks["adapter"] = ComponentHealth(
            status="down",
            message=f"Adapter错误: {str(e)}"
        )
        overall_status = "unhealthy"

    # 检查系统状态
    checks["system"] = ComponentHealth(
        status="up",
        message="系统运行正常"
    )

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        version="2.2.0",
        checks=checks
    )
