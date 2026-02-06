"""
R-MOS Backend 应用入口（V2.2完整版）

⚠️ 强制约束：
- 所有HTTP API路由必须添加 /api/v1 前缀
- WebSocket路由不添加前缀（直接/ws/robot/status）
- 必须配置CORS、异常处理、日志中间件
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    AdapterConnectionError,
    AccessDeniedError,
    BusinessRuleViolation,
    ResourceNotFoundError,
)
from app.adapters.factory import AdapterFactory
from app.api.v1 import api_router, websocket_router

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    
    启动时：
    - 初始化并连接Adapter
    - 记录启动日志
    
    关闭时：
    - 断开Adapter连接
    - 清理资源
    """
    # 启动事件
    logger.info("R-MOS Backend 启动中...")
    try:
        adapter = await AdapterFactory.get_adapter()
        logger.info(f"Adapter已连接: {adapter.__class__.__name__}")
    except Exception as e:
        logger.error(f"Adapter连接失败: {e}")
        raise
    
    yield
    
    # 关闭事件
    logger.info("R-MOS Backend 关闭中...")
    await AdapterFactory.close_adapter()
    logger.info("Adapter已断开")


# 创建FastAPI应用
app = FastAPI(
    title="R-MOS Backend",
    version="2.2.0",
    description="Robot Maintenance Operating System - MVP Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ===== 中间件配置 =====

# CORS中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:3000", "http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件（V2.3 增强：Trace ID 支持）
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求，注入 Trace ID"""
    import uuid
    from datetime import datetime
    
    # 生成 Trace ID
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id
    request.state.start_time = datetime.utcnow()
    
    logger.info(f"[{trace_id}] 收到请求: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # 计算耗时
    duration_ms = (datetime.utcnow() - request.state.start_time).total_seconds() * 1000
    logger.info(f"[{trace_id}] 响应状态: {response.status_code} ({duration_ms:.1f}ms)")
    
    # 在响应头中返回 Trace ID
    response.headers["X-Trace-ID"] = trace_id
    return response


# ===== 异常处理器 =====

@app.exception_handler(BusinessRuleViolation)
async def business_rule_violation_handler(request: Request, exc: BusinessRuleViolation):
    """业务规则违反异常处理（409 Conflict）"""
    return JSONResponse(
        status_code=409,
        content={
            "status_code": 409,
            "error_type": "BusinessRuleViolation",
            "message": exc.message,
            "details": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": str(id(request))
        }
    )


@app.exception_handler(AdapterConnectionError)
async def adapter_connection_error_handler(request: Request, exc: AdapterConnectionError):
    """Adapter连接错误处理（503 Service Unavailable）"""
    return JSONResponse(
        status_code=503,
        content={
            "status_code": 503,
            "error_type": "AdapterConnectionError",
            "message": "机器人Adapter连接失败",
            "details": {
                "code": "ADAPTER_NOT_CONNECTED",
                "message": str(exc),
                "details": {}
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": str(id(request))
        }
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    """资源不存在统一映射（404 Not Found）。"""
    trace_id = getattr(request.state, "trace_id", str(id(request)))
    return JSONResponse(
        status_code=404,
        content={
            "status_code": 404,
            "error_type": "ResourceNotFoundError",
            "message": "资源不存在",
            "details": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "资源不存在",
                "details": {
                    "resource_type": exc.resource_type,
                    "resource_id": str(exc.resource_id),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": trace_id,
        },
    )


@app.exception_handler(AccessDeniedError)
async def access_denied_handler(request: Request, exc: AccessDeniedError):
    """对象级越权统一映射（READ=404, WRITE=403）。"""
    trace_id = getattr(request.state, "trace_id", str(id(request)))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error_type": type(exc).__name__,
            "message": exc.message,
            "details": {
                "code": exc.error_code,
                "message": exc.message,
                "details": {
                    "action": exc.action,
                    "reason": exc.reason,
                    "resource_type": exc.resource_type,
                    "resource_id": exc.resource_id,
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": trace_id,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """标准HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error_type": "HTTPException",
            "message": exc.detail,
            "details": None,
            "timestamp": None,
            "request_id": str(id(request))
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证错误处理（422 Unprocessable Entity）"""
    trace_id = getattr(request.state, "trace_id", str(id(request)))
    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "error_type": "ValidationError",
            "message": "请求参数验证失败",
            "details": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数格式错误",
                "details": exc.errors()
            },
            "timestamp": None,
            "request_id": trace_id
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """通用异常兜底处理器（500 Internal Server Error）
    
    V2.3 新增：捕获所有未处理的异常，返回标准 JSON 格式，
    避免直接暴露 500 错误堆栈给前端。
    """
    from datetime import datetime
    
    trace_id = getattr(request.state, "trace_id", str(id(request)))
    logger.error(f"[{trace_id}] 未处理异常: {type(exc).__name__}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "error_type": "InternalServerError",
            "message": "服务器内部错误，请稍后重试",
            "details": {
                "code": "INTERNAL_ERROR",
                "message": "请联系管理员并提供 Trace ID",
                "details": {}
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": trace_id
        }
    )


# ===== 路由注册（V2.2强制约束）=====

# HTTP API路由（添加 /api/v1 前缀）
app.include_router(api_router, prefix="/api/v1")
logger.info("HTTP API路由已注册: /api/v1")

# WebSocket路由（不添加前缀）
app.include_router(websocket_router)
logger.info("WebSocket路由已注册: /ws")


# ===== 根路径 =====

@app.get("/", tags=["Root"])
async def root():
    """根路径，返回API信息"""
    return {
        "service": "R-MOS Backend",
        "version": "2.2.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# ===== 启动配置 =====

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
