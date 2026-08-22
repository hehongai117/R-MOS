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
        # 登出入口。与 /auth/refresh 同类：靠请求体里的 refresh token 自证身份，
        # 不需要 access token。若要求 access token，则 access token 过期后就无法
        # 吊销 refresh token —— 那是安全负收益。2026-08-22 用户确认加入。
        ("POST", "/api/v1/auth/logout"),
        # 注册页学校自动补全（RegisterPage 用裸 axios，天然不带令牌）
        ("GET", "/api/v1/schools"),
        # 学生注册时选择导师；email 字段须服务端脱敏后返回（AUTH-SCHOOLS-PII）
        ("GET", "/api/v1/schools/{school_name}/teachers"),
    }
)

# 判定规则（用于评审新增申请）：
# 只有「自带凭据校验、且不依赖 access token」的端点才可能入选——
# 即认证入口（register/login）与令牌交换入口（refresh/logout，凭请求体里的
# refresh token 自证身份），加上不返回业务数据的探针与注册流程必需的公开查询。
# 任何读写业务数据、教学数据、任务、训练、证据、机器人、适配器或管理的入口一律不得入选。
#
# 明确排除、不得擅自加入的条目（加入需另行单独审批）：
# - GET /api/v1/robots/{robot_id}/assets/{file_path:path}
#   须等 ADR-AUTHN D3 拆出"已发布公开资产"专用只读路径后再评审。
