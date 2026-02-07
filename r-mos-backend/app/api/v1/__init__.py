"""
API路由统一注册（拆包C补充）
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    audit,
    admin,
    skills,
    health,      # 拆包A
    adapter,     # 拆包A
    websocket,   # 拆包A
    tasks,       # 拆包B
    sops,        # 拆包C
    fault_cases, # 拆包C
    incidents,
    observations,
    evidence,
    assessments,
    teaching,
)

# 创建v1版本路由
api_router = APIRouter()

# 注册所有端点（统一使用/api/v1前缀，在main.py中添加）
# 注：各endpoint内部已定义完整路径（如 /tasks, /sops），无需再加prefix
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(skills.router, tags=["skills"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(adapter.router, tags=["adapter"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(sops.router, tags=["sops"])
api_router.include_router(fault_cases.router, tags=["fault_cases"])
api_router.include_router(incidents.router, tags=["incidents"])
api_router.include_router(observations.router, tags=["observations"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(assessments.router, tags=["assessments"])
api_router.include_router(teaching.router, tags=["teaching"])

# WebSocket不需要/api/v1前缀，单独注册
websocket_router = websocket.router
