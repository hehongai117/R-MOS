"""公开路由白名单——默认拒绝认证的唯一豁免入口。

安全边界文件。系统对 `/api/v1` 下的路由默认要求有效令牌（见
`app.services.authz_guard.enforce_authenticated`），只有登记在本文件中的
(方法, 路由模板) 组合才允许匿名访问。

**新增条目必须经过安全评审并在 ADR 中留痕。**
当前清单由 `docs/adr/ADR-2026-08-21-authn-default-deny-and-object-ownership.md`
的 D1 定义，2026-08-21 经用户逐条确认。

路径必须写 FastAPI 的**路由模板**（含 `{param}` 占位符），不是具体请求路径。
"""
from __future__ import annotations

PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # 存活探针，不返回业务数据
        ("GET", "/api/v1/health"),
        # 注册入口
        ("POST", "/api/v1/auth/register"),
        # 登录入口
        ("POST", "/api/v1/auth/login"),
        # 刷新入口，自带刷新令牌校验
        ("POST", "/api/v1/auth/refresh"),
        # 注册页学校自动补全（RegisterPage 用裸 axios，天然不带令牌）
        ("GET", "/api/v1/schools"),
        # 学生注册时选择导师；email 字段须服务端脱敏后返回（AUTH-SCHOOLS-PII）
        ("GET", "/api/v1/schools/{school_name}/teachers"),
    }
)

# 明确排除、不得擅自加入的条目（加入需另行单独审批）：
# - GET /api/v1/robots/{robot_id}/assets/{file_path:path}
#   须等 ADR-AUTHN D3 拆出"已发布公开资产"专用只读路径后再评审。
# - POST /api/v1/auth/logout
#   注销必须能定位到具体令牌主体。
