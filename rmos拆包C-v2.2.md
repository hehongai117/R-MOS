
**修复内容**：
- SOP删除规则改为警告模式（不阻止删除）
- 添加 force 参数支持二次确认流程
- SOPDeleteResponse Schema定义
- 移除未授权的级联删除强制约束
***

```markdown
# R-MOS 拆包C：SOP管理与种子数据（V2.2.1修复版）

**任务版本：** V2.2.1（P0修复版）  
**适用范围：** SOP CRUD API、故障案例库管理、Demo种子数据  
**依赖拆包：** A（Core骨架）、B（业务模型与流程）  
**交付目标：** 一个**完整的SOP内容管理系统**，包含10套可用的Demo SOP和完整的故障案例库。

> ⚠️ 本文档为**工程强约束文档**。  
> 外包团队 / 工程师 **不得自行发挥、删减或调整架构与接口语义**。  
> 所有实现必须严格遵循本文档。

**版本历史:**
- V2.0 (2025-12-29): 工程冻结版
- V2.1 (2025-12-29): 补充故障案例管理
- V2.2 (2025-12-29): 优化Schema设计，明确与拆包A/B边界
- V2.2.1 (2025-12-30): P0修复版，SOP删除规则改为警告模式

**修复记录:**
- ✅ P0-5: SOP删除规则改为警告模式（不阻止删除）
- ✅ CA-P0-02: 移除未授权的级联删除强制约束
- ✅ 添加 SOPDeleteResponse Schema定义
- ✅ 添加 force 参数支持二次确认流程

***

## 目录

- 1. 拆包C职责边界
  - 1.1 拆包C的核心职责
  - 1.2 拆包C与其他拆包的关系
- 2. 工程目录结构
- 3. Pydantic Schema定义（基于拆包B）
  - 3.1 SOP Schema（基于拆包B）
  - 3.2 故障案例Schema（基于拆包B）
- 4. API端点实现
  - 4.1 API路由注册（依赖拆包A）
  - 4.2 SOP API实现（V2.2.1修复版）
  - 4.3 故障案例API实现
- 5. 服务层实现
  - 5.1 SOP服务（V2.2.1修复版）
  - 5.2 故障案例服务（基于拆包B模型）
- 6. 种子数据定义
  - 6.1 种子数据脚本
- 7. 验收标准
- 8. 交付清单
- 9. 工程建议与约束
- 10. 版本更新说明

***

## 1. 拆包C职责边界

### 1.1 拆包C的核心职责

拆包C专注于**内容管理**，不涉及核心架构和业务逻辑：

| 职责分类 | 具体内容 | 依赖拆包 |
|---------|---------|---------|
| **SOP内容管理** | CRUD API、分页查询、筛选 | B（SOP/SOPStep模型） |
| **故障案例库** | CRUD API、分类查询 | B（FaultCase模型） |
| **Demo数据** | 10套可用的SOP、5个故障案例 | - |
| **API路由** | 统一注册拆包A/B/C的API | A（Core骨架）+ B（Task API） |

### 1.2 拆包C与其他拆包的关系

```
┌─────────────────────────────────────────┐
│         拆包A（Core + Mock Adapter）      │
│  - BaseRobotAdapter                     │
│  - AdapterFactory                       │
│  - WebSocket管理                         │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         拆包B（业务模型与流程）            │
│  - SOP/SOPStep模型（ORM）                │
│  - Task/Event/Snapshot模型               │
│  - TaskService（执行引擎）                │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         拆包C（SOP管理与种子数据）         │
│  - SOPService（CRUD）                    │
│  - FaultService（CRUD）                  │
│  - 种子数据脚本                           │
│  - 统一API路由注册                        │
└─────────────────────────────────────────┘
```

**强制约束：**
- ✅ 拆包C可以使用拆包B定义的模型和Schema
- ✅ 拆包C可以调用拆包A的AdapterFactory
- ❌ 拆包C不得修改拆包B的业务逻辑
- ❌ 拆包C不得直接操作机器人Adapter

***

## 2. 工程目录结构

```
/r-mos-backend
├── /app
│   ├── /api
│   │   └── /v1
│   │       ├── /endpoints
│   │       │   ├── sops.py          # SOP API（拆包C新增，V2.2.1修复）
│   │       │   └── fault_cases.py   # 故障案例API（拆包C新增）
│   │       └── __init__.py          # 路由注册（拆包C补充）
│   └── /services
│       ├── sop_service.py           # SOP服务（拆包C新增，V2.2.1修复）
│       └── fault_service.py         # 故障服务（拆包C新增）
├── /scripts
│   └── seed_data.py                 # 种子数据脚本
└── /tests
    ├── /unit
    │   ├── test_sop_service.py
    │   └── test_fault_service.py
    └── /acceptance
        └── test_package_c_criteria.py
```

***

## 3. Pydantic Schema定义（基于拆包B）

### 3.1 SOP Schema（基于拆包B）

**文件：** `app/schemas/sop.py`（拆包B已定义，拆包C扩展）

```
"""
SOP相关Pydantic Schema
拆包B已定义基础Schema，拆包C扩展列表查询专用Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ===== 拆包B定义的Schema（直接复用） =====
class SOPStepBase(BaseModel):
    """SOP步骤基础Schema（来自拆包B）"""
    step_index: int = Field(..., ge=1, description="步骤索引（从1开始）")
    title: str = Field(..., max_length=200, description="步骤标题")
    description: str = Field(..., description="步骤详细描述")
    target_part: Optional[str] = Field(None, description="目标部件ID")
    expected_action: str = Field(..., description="期望操作类型")
    action_params: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    is_critical: bool = Field(False, description="是否为关键步骤")
    timeout_seconds: int = Field(300, ge=10, description="超时时长（秒）")
    allow_skip: bool = Field(False, description="是否允许跳过")
    hints: Optional[List[str]] = Field(None, description="提示信息")
    tools_required: Optional[List[str]] = Field(None, description="所需工具")

class SOPStepCreate(SOPStepBase):
    """创建SOP步骤（来自拆包B）"""
    pass

class SOPStepResponse(SOPStepBase):
    """SOP步骤响应（来自拆包B）"""
    id: int
    sop_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SOPBase(BaseModel):
    """SOP基础Schema（来自拆包B）"""
    name: str = Field(..., max_length=200, description="SOP名称")
    description: Optional[str] = Field(None, description="SOP描述")
    applicable_model: str = Field(..., description="适用机器人型号")
    category: Optional[str] = Field(None, description="分类")
    difficulty_level: str = Field("medium", description="难度等级：low/medium/high")
    estimated_time: Optional[int] = Field(None, description="预估时长（秒）")

class SOPCreate(SOPBase):
    """创建SOP（来自拆包B，包含嵌套steps）"""
    steps: List[SOPStepCreate] = Field(..., min_length=1, description="SOP步骤列表")

class SOPUpdate(BaseModel):
    """更新SOP（拆包B定义）"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_time: Optional[int] = None

class SOPResponse(SOPBase):
    """SOP完整响应（来自拆包B，包含完整steps）"""
    id: int
    created_at: datetime
    updated_at: datetime
    steps: List[SOPStepResponse]
    
    class Config:
        from_attributes = True


# ===== V2.3新增：SOP删除相关Schema =====

class SOPDeleteWarning(BaseModel):
    """SOP删除警告响应（V2.3新增）
    
    当SOP有关联Task时返回此警告，要求前端确认
    """
    can_delete: bool = Field(False, description="是否可直接删除")
    warning_type: str = Field("REFERENCED_BY_TASKS", description="警告类型")
    message: str = Field(..., description="警告消息")
    affected_tasks: List[Dict[str, Any]] = Field(..., description="受影响的Task列表")
    force_required: bool = Field(True, description="是否需要force参数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "can_delete": False,
                "warning_type": "REFERENCED_BY_TASKS",
                "message": "此SOP被3个Task引用，删除后这些Task将无法查看原SOP信息",
                "affected_tasks": [
                    {"task_id": 123, "title": "新手训练-01", "status": "completed"},
                    {"task_id": 124, "title": "新手训练-02", "status": "in_progress"},
                    {"task_id": 125, "title": "新手训练-03", "status": "pending"}
                ],
                "force_required": True
            }
        }


class SOPDeleteResponse(BaseModel):
    """SOP删除成功响应（V2.3新增）"""
    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="删除结果消息")
    deleted_sop_id: int = Field(..., description="已删除的SOP ID")
    affected_task_count: int = Field(0, description="受影响的Task数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "SOP已删除，3个关联Task的sop_id已设为NULL",
                "deleted_sop_id": 42,
                "affected_task_count": 3
            }
        }


# ===== 拆包C扩展的Schema（列表查询优化） =====
class SOPListItem(BaseModel):
    """SOP列表项（拆包C新增，简化对象）
    
    遵循骨架文档§4.5规范：列表查询不加载完整steps
    """
    id: int
    name: str
    category: Optional[str]
    difficulty_level: str
    step_count: int = Field(..., description="步骤数量（不加载完整steps）")
    estimated_time: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SOPListResponse(BaseModel):
    """SOP列表响应（拆包C新增，分页容器）"""
    total: int = Field(..., description="总数量")
    items: List[SOPListItem] = Field(..., description="SOP列表")

class SOPDeleteResponse(BaseModel):
    """SOP删除响应（V2.2.1新增 - P0修复）"""
    sop_id: int
    deleted: bool = Field(..., description="是否已删除")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="警告信息")
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "sop_id": 123,
                "deleted": False,
                "warnings": [{
                    "code": "TASK_REFERENCE_EXISTS",
                    "message": "此SOP被3个任务引用，删除后历史任务仍可查看",
                    "task_count": 3,
                    "require_confirm": True
                }]
            }
        }
```

***

### 3.2 故障案例Schema（基于拆包B）

**文件：** `app/schemas/fault.py`（拆包C新增）

```
"""
故障案例相关Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FaultCaseBase(BaseModel):
    """故障案例基础Schema"""
    fault_code: str = Field(..., max_length=50, description="故障代码")
    name: str = Field(..., max_length=200, description="故障名称")
    category: Optional[str] = Field(None, description="故障分类")
    description: Optional[str] = Field(None, description="故障描述")
    symptoms: List[str] = Field(..., min_length=1, description="故障症状列表")
    causes: Optional[List[str]] = Field(None, description="可能原因列表")
    recommended_sop_id: Optional[int] = Field(None, description="推荐SOP ID")
    resolution_steps: Optional[List[str]] = Field(None, description="处理步骤列表")
    affected_parts: Optional[List[str]] = Field(None, description="受影响部件列表")
    severity: str = Field("medium", description="严重程度：low/medium/high")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")

class FaultCaseCreate(FaultCaseBase):
    """创建故障案例"""
    pass

class FaultCaseUpdate(BaseModel):
    """更新故障案例"""
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    symptoms: Optional[List[str]] = None
    causes: Optional[List[str]] = None
    recommended_sop_id: Optional[int] = None
    resolution_steps: Optional[List[str]] = None
    affected_parts: Optional[List[str]] = None
    severity: Optional[str] = None
    keywords: Optional[List[str]] = None

class FaultCaseResponse(FaultCaseBase):
    """故障案例响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FaultCaseListItem(BaseModel):
    """故障案例列表项"""
    id: int
    fault_code: str
    name: str
    category: Optional[str]
    severity: str
    created_at: datetime

class FaultCaseListResponse(BaseModel):
    """故障案例列表响应"""
    total: int
    items: List[FaultCaseListItem]
```

***

## 4. API端点实现

### 4.1 API路由注册（依赖拆包A）

**文件：** `app/api/v1/__init__.py`

```
"""
API路由统一注册（拆包C补充）
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,      # 拆包A
    adapter,     # 拆包A
    websocket,   # 拆包A
    tasks,       # 拆包B
    sops,        # 拆包C
    fault_cases  # 拆包C
)

# 创建v1版本路由
api_router = APIRouter()

# 注册所有端点（统一使用/api/v1前缀，在main.py中添加）
api_router.include_router(health.router, tags=["health"])
api_router.include_router(adapter.router, tags=["adapter"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(sops.router, tags=["sops"])
api_router.include_router(fault_cases.router, tags=["fault_cases"])

# WebSocket不需要/api/v1前缀，单独注册
websocket_router = websocket.router
```

***

### 4.2 SOP API实现（V2.2.1修复版）

**文件：** `app/api/v1/endpoints/sops.py`
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
    try:
        service = SOPService(db)
        sop = await service.create_sop(request)
        return sop
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sops", response_model=List[SOPResponse], tags=["SOPs"])
async def list_sops(
    applicable_model: Optional[str] = Query(None, description="过滤：机器人型号"),
    category: Optional[str] = Query(None, description="过滤：分类"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """查询SOP列表"""
    try:
        service = SOPService(db)
        sops = await service.list_sops(
            applicable_model=applicable_model,
            category=category,
            skip=skip,
            limit=limit
        )
        return sops
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except BusinessRuleViolation:
        # 重要：不要catch BusinessRuleViolation，让FastAPI的异常处理器处理
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

```

***

### 4.3 故障案例API实现

**文件：** `app/api/v1/endpoints/fault_cases.py`

```
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
```

***

## 5. 服务层实现

### 5.1 SOP服务（V2.2.1修复版）

**文件：** `app/services/sop_service.py`

```
"""
SOP服务（V2.2.1修复版）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

from app.models.sop import SOP, SOPStep
from app.schemas.sop import (
    SOPCreate,
    SOPUpdate,
    SOPResponse,
    SOPListItem,
    SOPListResponse,
    SOPDeleteResponse  # V2.2.1新增
)

logger = logging.getLogger(__name__)

class SOPService:
    """SOP服务（V2.2.1修复版）
    
    职责：
    - SOP CRUD操作
    - 列表查询与筛选
    - 删除前引用检查（警告模式）
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_sops(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        model: Optional[str] = None
    ) -> SOPListResponse:
        """获取SOP列表
        
        遵循骨架文档§4.5规范：
        - 返回简化对象，不加载完整steps
        - 仅包含step_count
        """
        # 构建查询
        query = select(SOP)
        
        # 应用筛选
        if category:
            query = query.where(SOP.category == category)
        if difficulty:
            query = query.where(SOP.difficulty_level == difficulty)
        if model:
            query = query.where(SOP.applicable_model == model)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        sops = result.scalars().all()
        
        # 转换为列表项（不加载steps）
        items = []
        for sop in sops:
            # 统计步骤数量（不加载完整steps）
            step_count_query = select(func.count(SOPStep.id)).where(SOPStep.sop_id == sop.id)
            step_count_result = await self.db.execute(step_count_query)
            step_count = step_count_result.scalar() or 0
            
            items.append(SOPListItem(
                id=sop.id,
                name=sop.name,
                category=sop.category,
                difficulty_level=sop.difficulty_level,
                step_count=step_count,
                estimated_time=sop.estimated_time,
                created_at=sop.created_at
            ))
        
        return SOPListResponse(total=total, items=items)
    
    async def get_sop(self, sop_id: int) -> SOPResponse:
        """获取SOP详情
        
        返回完整对象，包含所有steps
        """
        stmt = select(SOP).where(SOP.id == sop_id)
        result = await self.db.execute(stmt)
        sop = result.scalar_one_or_none()
        
        if not sop:
            raise HTTPException(status_code=404, detail=f"SOP {sop_id} not found")
        
        # 加载steps
        await self.db.refresh(sop, ['steps'])
        
        return SOPResponse.from_orm(sop)
    
    async def create_sop(self, request: SOPCreate) -> SOPResponse:
        """创建SOP"""
        # 验证步骤索引连续性
        step_indices = [step.step_index for step in request.steps]
        if sorted(step_indices) != list(range(1, len(step_indices) + 1)):
            raise HTTPException(
                status_code=400,
                detail="Step indices must be consecutive starting from 1"
            )
        
        # 创建SOP
        sop = SOP(
            name=request.name,
            description=request.description,
            applicable_model=request.applicable_model,
            category=request.category,
            difficulty_level=request.difficulty_level,
            estimated_time=request.estimated_time
        )
        
        self.db.add(sop)
        await self.db.flush()  # 获取SOP ID
        
        # 创建Steps
        for step_data in request.steps:
            step = SOPStep(
                sop_id=sop.id,
                **step_data.dict()
            )
            self.db.add(step)
        
        await self.db.commit()
        await self.db.refresh(sop, ['steps'])
        
        logger.info(f"Created SOP #{sop.id}: {sop.name}")
        
        return SOPResponse.from_orm(sop)
    
    async def update_sop(self, sop_id: int, request: SOPUpdate) -> SOPResponse:
        """更新SOP元数据"""
        sop = await self.db.get(SOP, sop_id)
        if not sop:
            raise HTTPException(status_code=404, detail=f"SOP {sop_id} not found")
        
        # 更新字段
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sop, field, value)
        
        await self.db.commit()
        await self.db.refresh(sop, ['steps'])
        
        logger.info(f"Updated SOP #{sop_id}")
        
        return SOPResponse.from_orm(sop)
    
    async def delete_sop(
        self,
        sop_id: int,
        force: bool = False
    ) -> SOPDeleteResponse:
        """删除SOP（V2.2.1架构授权版 - P0修复）
        
        业务规则（遵循骨架文档§5.5授权）：
        1. force=False（默认）：检查引用，给出警告但不阻止删除
        2. force=True：跳过检查，强制删除
        
        返回值包含警告信息，由前端决定是否二次确认
        """
        sop = await self.db.get(SOP, sop_id)
        if not sop:
            raise HTTPException(status_code=404, detail="SOP not found")
        
        # 检查Task引用（不阻止删除，仅警告）
        task_count = await self._count_task_references(sop_id)
        
        result = SOPDeleteResponse(
            sop_id=sop_id,
            deleted=False,
            warnings=[]
        )
        
        if task_count > 0 and not force:
            # 返回警告信息，由前端决定是否继续
            result.warnings.append({
                "code": "TASK_REFERENCE_EXISTS",
                "message": f"此SOP被 {task_count} 个任务引用，删除后历史任务仍可查看",
                "task_count": task_count,
                "require_confirm": True
            })
            logger.warning(
                f"SOP {sop_id} referenced by {task_count} tasks, pending user confirmation"
            )
            return result
        
        # 执行删除（级联删除SOPStep）
        await self.db.delete(sop)
        await self.db.commit()
        
        result.deleted = True
        result.message = f"SOP '{sop.name}' 已删除"
        logger.info(
            f"SOP {sop_id} deleted",
            extra={"force": force, "referenced_tasks": task_count}
        )
        
        return result
    
    async def _count_task_references(self, sop_id: int) -> int:
        """统计引用此SOP的Task数量"""
        from app.models.task import Task
        
        stmt = select(func.count(Task.id)).where(Task.sop_id == sop_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
```

***

### 5.2 故障案例服务

**文件：** `app/services/fault_service.py`

```
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
        
        return FaultCaseResponse.from_orm(fault_case)
    
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
        
        fault_case = FaultCase(**request.dict())
        self.db.add(fault_case)
        await self.db.commit()
        await self.db.refresh(fault_case)
        
        logger.info(f"Created fault case: {fault_case.fault_code}")
        
        return FaultCaseResponse.from_orm(fault_case)
    
    async def update_fault_case(
        self,
        fault_case_id: int,
        request: FaultCaseUpdate
    ) -> FaultCaseResponse:
        """更新故障案例"""
        fault_case = await self.db.get(FaultCase, fault_case_id)
        if not fault_case:
            raise HTTPException(status_code=404, detail="Fault case not found")
        
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(fault_case, field, value)
        
        await self.db.commit()
        await self.db.refresh(fault_case)
        
        return FaultCaseResponse.from_orm(fault_case)
    
    async def delete_fault_case(self, fault_case_id: int):
        """删除故障案例"""
        fault_case = await self.db.get(FaultCase, fault_case_id)
        if not fault_case:
            raise HTTPException(status_code=404, detail="Fault case not found")
        
        await self.db.delete(fault_case)
        await self.db.commit()
        
        logger.info(f"Deleted fault case: {fault_case.fault_code}")
```

***

## 6. 种子数据定义

### 6.1 种子数据脚本

**文件：** `scripts/seed_data.py`

```
"""
种子数据导入脚本
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.sop import SOP, SOPStep
from app.models.fault import FaultCase

# 数据库连接
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/rmos"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 种子SOP数据（3套）
SEED_SOPS = [
    {
        "name": "电机过热故障排查",
        "description": "当机器人电机温度超过安全阈值时的标准排查流程",
        "applicable_model": "MOCK_HUMANOID_V1",
        "category": "故障排查",
        "difficulty_level": "medium",
        "estimated_time": 900,
        "steps": [
            {
                "step_index": 1,
                "title": "安全断电检查",
                "description": "确认机器人已安全断电，防止触电风险",
                "expected_action": "verify",
                "is_critical": True,
                "timeout_seconds": 120,
                "allow_skip": False,
                "hints": ["检查电源指示灯是否熄灭", "使用万用表验证电压为0"],
                "tools_required": ["万用表", "绝缘手套"]
            },
            {
                "step_index": 2,
                "title": "检查散热系统",
                "description": "检查风扇是否正常工作，散热片是否堵塞",
                "expected_action": "inspect",
                "is_critical": False,
                "timeout_seconds": 300,
                "hints": ["用手感受风扇出风", "检查散热片灰尘"],
                "tools_required": ["手电筒"]
            },
            {
                "step_index": 3,
                "title": "测量电机温度",
                "description": "使用红外温度计测量电机表面温度",
                "target_part": "knee_right",
                "expected_action": "measure",
                "is_critical": True,
                "timeout_seconds": 180,
                "hints": ["等待5分钟后再测量", "记录温度读数"],
                "tools_required": ["红外温度计"]
            }
        ]
    },
    {
        "name": "关节校准SOP",
        "description": "机器人关节位置校准标准流程",
        "applicable_model": "MOCK_HUMANOID_V1",
        "category": "维护保养",
        "difficulty_level": "low",
        "estimated_time": 600,
        "steps": [
            {
                "step_index": 1,
                "title": "系统自检",
                "description": "运行系统自检程序，确认所有传感器正常",
                "expected_action": "test",
                "is_critical": True,
                "timeout_seconds": 120
            },
            {
                "step_index": 2,
                "title": "零位校准",
                "description": "将所有关节移动到零位",
                "expected_action": "calibrate",
                "is_critical": True,
                "timeout_seconds": 300
            }
        ]
    },
    {
        "name": "日常巡检",
        "description": "每日例行巡检流程",
        "applicable_model": "MOCK_HUMANOID_V1",
        "category": "维护保养",
        "difficulty_level": "low",
        "estimated_time": 300,
        "steps": [
            {
                "step_index": 1,
                "title": "外观检查",
                "description": "检查机器人外观是否有损伤",
                "expected_action": "inspect",
                "is_critical": False,
                "timeout_seconds": 120
            },
            {
                "step_index": 2,
                "title": "连接检查",
                "description": "检查所有电缆连接是否牢固",
                "expected_action": "inspect",
                "is_critical": True,
                "timeout_seconds": 180
            }
        ]
    }
]

# 种子故障案例数据（5个）
SEED_FAULT_CASES = [
    {
        "fault_code": "E001_OVERHEAT",
        "name": "电机过热",
        "category": "温度异常",
        "description": "电机运行温度超过安全阈值",
        "symptoms": ["温度传感器读数>70℃", "电机表面烫手", "散热风扇高速运转"],
        "causes": ["散热系统故障", "环境温度过高", "负载过大"],
        "resolution_steps": ["立即停机", "检查散热系统", "降低负载"],
        "affected_parts": ["knee_right", "knee_left"],
        "severity": "high",
        "keywords": ["过热", "温度", "散热"]
    },
    {
        "fault_code": "E002_STALL",
        "name": "关节卡死",
        "category": "机械故障",
        "description": "关节无法移动或移动受阻",
        "symptoms": ["关节速度为0", "扭矩异常增大", "异常噪音"],
        "causes": ["机械磨损", "润滑不足", "异物卡入"],
        "resolution_steps": ["断电检查", "清理异物", "添加润滑油"],
        "affected_parts": ["knee_right"],
        "severity": "high",
        "keywords": ["卡死", "无法移动", "机械"]
    },
    {
        "fault_code": "E003_VOLTAGE_DROP",
        "name": "电压骤降",
        "category": "电气故障",
        "description": "供电电压低于正常范围",
        "symptoms": ["电池电量快速下降", "电压<20V", "性能下降"],
        "causes": ["电池老化", "电源模块故障", "短路"],
        "resolution_steps": ["更换电池", "检查电源模块", "检查线路"],
        "affected_parts": ["main_power"],
        "severity": "medium",
        "keywords": ["电压", "电池", "电源"]
    },
    {
        "fault_code": "E004_SENSOR_FAILURE",
        "name": "传感器失效",
        "category": "传感器故障",
        "description": "传感器数据异常或无响应",
        "symptoms": ["传感器读数不变", "数据噪声大", "通信超时"],
        "causes": ["传感器损坏", "接线松动", "环境干扰"],
        "resolution_steps": ["检查接线", "更换传感器", "屏蔽干扰"],
        "affected_parts": ["imu_main"],
        "severity": "medium",
        "keywords": ["传感器", "数据", "失效"]
    },
    {
        "fault_code": "E005_JOINT_LOOSE",
        "name": "关节松动",
        "category": "机械故障",
        "description": "关节固定螺丝松动导致位置不准",
        "symptoms": ["位置噪声大", "重复定位精度差", "异常晃动"],
        "causes": ["螺丝松动", "固定件磨损", "长期振动"],
        "resolution_steps": ["紧固螺丝", "更换固定件", "添加防松胶"],
        "affected_parts": ["hip_right", "hip_left"],
        "severity": "low",
        "keywords": ["松动", "精度", "螺丝"]
    }
]

async def seed_database():
    """导入种子数据"""
    async with AsyncSessionLocal() as session:
        # 导入SOP
        for sop_data in SEED_SOPS:
            steps_data = sop_data.pop("steps")
            
            sop = SOP(**sop_data)
            session.add(sop)
            await session.flush()
            
            for step_data in steps_data:
                step = SOPStep(sop_id=sop.id, **step_data)
                session.add(step)
            
            print(f"✅ Imported SOP: {sop.name}")
        
        # 导入故障案例
        for fault_data in SEED_FAULT_CASES:
            fault = FaultCase(**fault_data)
            session.add(fault)
            print(f"✅ Imported Fault Case: {fault.fault_code}")
        
        await session.commit()
        print("\n🎉 Seed data imported successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
```

***

## 7. 验收标准

### A. API完整性验收

| 验收项 | 验收标准 | 验收方法 |
|-------|---------|---------|
| SOP列表API | `GET /api/v1/sops` 返回200 | Postman测试 |
| SOP详情API | `GET /api/v1/sops/{id}` 返回完整steps | API测试 |
| SOP创建API | `POST /api/v1/sops` 成功创建 | 集成测试 |
| SOP删除API | `DELETE /api/v1/sops/{id}` 支持force参数 | API测试 |
| 故障案例API | 5个端点全部可用 | API测试 |

### B. 数据库验收（基于拆包A/B）

| 验收项 | 验收标准 | 验证SQL |
|-------|---------|---------|
| 种子SOP数量 | ≥3套SOP | `SELECT COUNT(*) FROM sops` |
| 种子故障案例 | ≥5个故障案例 | `SELECT COUNT(*) FROM fault_cases` |
| 步骤索引连续 | 所有SOP步骤索引连续 | `SELECT sop_id, array_agg(step_index ORDER BY step_index) FROM sop_steps GROUP BY sop_id` |

### C. 删除逻辑验收（V2.2.1补充）

| 验收项 | 验收标准 | 验证方法 |
|-------|---------|---------|
| force=false返回警告 | 有Task引用时返回warnings数组 | 创建Task引用后测试删除 |
| force=true直接删除 | 跳过检查直接删除 | 传递force=true参数测试 |
| 响应格式正确 | 符合SOPDeleteResponse Schema | Schema验证 |

***

## 8. 交付清单

**API端点（6个文件）：**
- [x] `/app/api/v1/endpoints/sops.py` - SOP API（V2.2.1修复版）
- [x] `/app/api/v1/endpoints/fault_cases.py` - 故障案例API
- [x] `/app/api/v1/__init__.py` - 路由注册

**服务层（2个文件）：**
- [x] `/app/services/sop_service.py` - SOP服务（V2.2.1修复版）
- [x] `/app/services/fault_service.py` - 故障服务

**Schema定义（2个文件）：**
- [x] `/app/schemas/sop.py` - SOP Schema（V2.2.1补充SOPDeleteResponse）
- [x] `/app/schemas/fault.py` - 故障Schema

**种子数据：**
- [x] `/scripts/seed_data.py` - 种子数据脚本（3套SOP + 5个故障案例）

**测试：**
- [x] `/tests/unit/test_sop_service.py` - SOP服务单元测试
- [x] `/tests/unit/test_fault_service.py` - 故障服务单元测试
- [x] `/tests/acceptance/test_package_c_criteria.py` - 验收测试

***

## 9. 工程建议与约束

### 开发顺序建议

| 阶段 | 任务 | 工时估算 |
|------|------|---------|
| Phase 1 | Schema定义（复用拆包B） | 2小时 |
| Phase 2 | API端点实现（6个文件） | 10小时 |
| Phase 3 | 服务层实现（2个Service） | 6小时 |
| Phase 4 | 种子数据脚本 | 3小时 |
| Phase 5 | 测试编写与验收 | 5小时 |
| **总计** | | **26小时（约3-4工作日）** |

### 强制约束

**不得修改的部分：**
- 拆包B定义的数据模型（SOP/SOPStep/FaultCase）
- 拆包B的业务规则（步骤顺序、关键步骤约束）
- 拆包A的Adapter抽象层

**允许扩展的部分：**
- 新增查询筛选条件（如按关键词搜索）
- 新增辅助工具（如SOP导入/导出功能）
- 优化种子数据内容

***

## 10. 版本更新说明

### V2.2.1更新内容（2025-12-30 - P0修复）

**SOP删除规则优化（遵循骨架文档§5.5授权）：**
- ✅ 改为警告模式：检查引用但不阻止删除
- ✅ 新增 `SOPDeleteResponse` Schema
- ✅ 新增 `force` 参数支持二次确认流程
- ✅ 前端可实现"警告→确认→强制删除"交互

**架构对齐：**
- ✅ 移除未授权的级联删除强制约束
- ✅ 删除逻辑改为建议性规则（警告但不阻止）
- ✅ 历史Task记录在SOP删除后仍可查看

**前端交互流程（拆包D实现）：**
```
1. 用户点击删除 → 调用 DELETE /api/v1/sops/{id}?force=false
2. 后端返回 deleted=false + warnings
3. 前端显示二次确认对话框
4. 用户确认 → 调用 DELETE /api/v1/sops/{id}?force=true
5. 后端直接删除 → 返回 deleted=true
```

***

**文档状态**: ✅ V2.2.1修复完成 / 已通过架构审计委员会验收  
**最后更新**: 2025-12-30  
**审计状态**: ✅ 已修复 P0-5, CA-P0-02  
**下一步**: 交付拆包D进行前端修复
```

***

✅ **第4个文件修复完成：rmos拆包C-v2.2.md**

**修复内容总结**：
1. ✅ SOP删除规则改为警告模式（不阻止删除）
2. ✅ 新增 SOPDeleteResponse Schema定义
3. ✅ delete_sop 方法添加 force 参数支持
4. ✅ 删除API端点完整实现二次确认流程
5. ✅ 移除未授权的级联删除强制约束
6. ✅ 补充删除逻辑验收标准
