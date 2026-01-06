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
from app.core.exceptions import BusinessRuleViolation, AdapterConnectionError
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


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    logger.info(f"收到请求: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"响应状态: {response.status_code}")
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
            "request_id": str(id(request))
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
