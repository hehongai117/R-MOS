"""
计时中间件测试 (Task B4 — Phase4)

验收标准：
1. 当中间件挂载到 FastAPI test app 时，响应包含 X-Process-Time 且值为合法 float
2. 默认情况下（PERF_TIMING 未设置）main.py 的 app 响应不含 X-Process-Time 头
"""
import os
import importlib
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# --------------------------------------------------------------------------
# 1. 中间件功能测试 — 手动挂载，验证 X-Process-Time 存在且为合法 float
# --------------------------------------------------------------------------

class TestTimingMiddlewareEnabled:
    """显式挂载中间件后的行为。"""

    @pytest.fixture(scope="class")
    def client_with_middleware(self):
        """创建一个带有 TimingMiddleware 的最小 FastAPI 测试应用。"""
        from app.core.timing_middleware import TimingMiddleware

        mini_app = FastAPI()

        @mini_app.get("/ping")
        async def ping():
            return {"ok": True}

        mini_app.add_middleware(TimingMiddleware)
        return TestClient(mini_app)

    def test_x_process_time_header_present(self, client_with_middleware):
        """响应头必须包含 X-Process-Time。"""
        resp = client_with_middleware.get("/ping")
        assert resp.status_code == 200
        assert "x-process-time" in resp.headers

    def test_x_process_time_is_valid_float(self, client_with_middleware):
        """X-Process-Time 必须是可解析的非负浮点数（毫秒）。"""
        resp = client_with_middleware.get("/ping")
        raw = resp.headers.get("x-process-time", "")
        value = float(raw)          # 解析失败则 ValueError → 测试失败
        assert value >= 0.0

    def test_body_not_corrupted(self, client_with_middleware):
        """中间件不得改变响应体。"""
        resp = client_with_middleware.get("/ping")
        assert resp.json() == {"ok": True}


# --------------------------------------------------------------------------
# 2. 默认关闭测试 — PERF_TIMING 未设置时 main app 不含 X-Process-Time
# --------------------------------------------------------------------------

class TestTimingMiddlewareDefaultOff:
    """PERF_TIMING 未设置时，正式 app 响应中不得出现 X-Process-Time。"""

    @pytest.fixture(scope="class")
    def main_client(self):
        """在确保 PERF_TIMING 未设置的前提下，导入 main.app 并创建 TestClient。"""
        # 确保环境变量未设置
        os.environ.pop("PERF_TIMING", None)

        # 重新导入以确保以干净状态加载（若已导入则直接使用缓存版本亦可）
        import main as main_module
        return TestClient(main_module.app, raise_server_exceptions=False)

    def test_no_x_process_time_on_health(self, main_client):
        """健康检查端点不得包含 X-Process-Time 头。"""
        resp = main_client.get("/api/v1/health")
        assert "x-process-time" not in resp.headers

    def test_no_x_process_time_on_root(self, main_client):
        """根路径不得包含 X-Process-Time 头。"""
        resp = main_client.get("/")
        assert "x-process-time" not in resp.headers

    def test_no_timing_middleware_in_stack(self):
        """main.py 的 middleware stack 不得含有 TimingMiddleware 实例（reload 证明守卫本身生效）。"""
        import sys

        saved = os.environ.pop("PERF_TIMING", None)
        try:
            # 强制重新执行模块级守卫：若 main 已被缓存，直接 import 不会重跑
            # module-level 的 if os.getenv("PERF_TIMING")=="1" 条件；reload 才能证明
            # 守卫本身在 PERF_TIMING 未设置时确实跳过了 TimingMiddleware 注册。
            if "main" in sys.modules:
                importlib.reload(sys.modules["main"])
            import main as main_module  # noqa: PLC0415

            from app.core.timing_middleware import TimingMiddleware
            middleware_classes = [
                m.cls if hasattr(m, "cls") else type(m)
                for m in main_module.app.user_middleware
            ]
            assert TimingMiddleware not in middleware_classes, (
                "TimingMiddleware 不应在 PERF_TIMING 未设置时出现在 middleware stack 中"
            )
        finally:
            # 恢复调用前的环境变量状态（无论断言是否通过）
            if saved is not None:
                os.environ["PERF_TIMING"] = saved
