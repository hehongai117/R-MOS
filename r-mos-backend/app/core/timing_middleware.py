"""
AI 管线端到端计时中间件 (Task B4 — Phase4)

默认关闭：仅在 PERF_TIMING=1 时通过 main.py 条件注册。
未注册时对任何请求/响应/性能零影响。

启用后行为：
- 在响应头写入 X-Process-Time（单位：毫秒，保留2位小数）
- 向日志写一条结构化 INFO 行，包含 route / method / status / ms

用法（main.py）：
    import os
    if os.getenv("PERF_TIMING") == "1":
        from app.core.timing_middleware import TimingMiddleware
        app.add_middleware(TimingMiddleware)
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的服务端处理耗时。

    响应头：
        X-Process-Time: <float ms>   e.g. "42.31"

    日志（INFO 级）：
        TIMING route=/api/v1/... method=POST status=200 ms=42.31
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 写响应头
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}"

        # 结构化日志
        logger.info(
            "TIMING route=%s method=%s status=%d ms=%.2f",
            request.url.path,
            request.method,
            response.status_code,
            elapsed_ms,
        )

        return response
