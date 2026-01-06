"""
Adapter管理API（V2.2完整版）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.adapters.factory import AdapterFactory
from app.adapters.schemas import RobotInfo, RobotStructure, FaultInjectionResult

router = APIRouter()


class FaultInjectionRequest(BaseModel):
    """故障注入请求（V2.2新增Schema）"""
    fault_code: str = Field(..., description="故障代码: E001-E005")
    target_part: str = Field(..., description="目标部件ID")
    severity: str = Field("medium", description="严重程度: low/medium/high")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fault_code": "E001_OVERHEAT",
                "target_part": "knee_right",
                "severity": "high"
            }
        }


@router.get("/adapter/info", response_model=RobotInfo, tags=["Adapter"])
async def get_adapter_info():
    """获取Adapter和机器人基础信息"""
    try:
        adapter = await AdapterFactory.get_adapter()
        return await adapter.get_robot_info()
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Adapter未连接")


@router.get("/adapter/structure", response_model=RobotStructure, tags=["Adapter"])
async def get_robot_structure():
    """获取机器人结构描述"""
    try:
        adapter = await AdapterFactory.get_adapter()
        return await adapter.get_robot_structure()
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Adapter未连接")


@router.post("/adapter/inject-fault", response_model=FaultInjectionResult, tags=["Adapter"])
async def inject_fault(request: FaultInjectionRequest):
    """故障注入（V2.2完整实现）
    
    支持的故障代码：
    - E001_OVERHEAT: 过热（温度+30℃，扭矩-30%）
    - E002_STALL: 卡死（速度=0，位置冻结）
    - E003_VOLTAGE_DROP: 电压下降（电池-50%，扭矩-50%）
    - E004_SENSOR_FAILURE: 传感器故障（数据噪声）
    - E005_JOINT_LOOSE: 关节松动（位置噪声，扭矩-70%）
    """
    try:
        adapter = await AdapterFactory.get_adapter()
        return await adapter.inject_fault(
            fault_code=request.fault_code,
            target_part=request.target_part,
            severity=request.severity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Adapter未连接")


@router.delete("/adapter/fault/{fault_code}", tags=["Adapter"])
async def clear_fault(fault_code: str):
    """清除指定故障"""
    try:
        adapter = await AdapterFactory.get_adapter()
        success = await adapter.clear_fault(fault_code)
        if success:
            return {"message": f"故障 {fault_code} 已清除"}
        else:
            raise HTTPException(status_code=404, detail=f"故障 {fault_code} 不存在")
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Adapter未连接")


@router.get("/adapter/faults", response_model=List[str], tags=["Adapter"])
async def get_active_faults():
    """获取当前所有活动故障"""
    try:
        adapter = await AdapterFactory.get_adapter()
        return await adapter.get_active_faults()
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Adapter未连接")
