"""AUTH-GATE 架构门禁：白名单锁定 + 客户端身份头零读取。

`tests/unit/test_auth_boundary.py` 验证的是**运行时行为**（匿名访问被拒）。
本文件补两条**静态不变量**，防止行为测试无法察觉的回归：

1. `AUTH-GATE-02`：公开路由白名单被逐条钉死。
   仅靠"匿名访问非白名单路由必须 401"是不够的——往白名单里**加**一条真实存在
   的路由会让它合法地变成公开，而所有行为测试都会照常通过。把白名单钉在测试里，
   任何增删都必须同时改这个文件，从而强制一次人工评审。

2. `AUTH-GATE-08`：生产代码不得再读客户端身份头。
   `X-RMOS-Role` / `X-User-ID` 曾被用于权限分支与审计操作者（AUTH-104）。
   身份现在只来自服务端令牌，这两个头只能作为非安全元数据。

范式沿用 `tests/unit/test_deny_audit_entrypoint_gate.py`（ALLOWLIST + 正则扫描），
不引入新框架。
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.public_routes import PUBLIC_ROUTES

# 2026-08-21 用户逐条签字的白名单；2026-08-22 经用户确认加入 /auth/logout。
# 依据：docs/adr/ADR-2026-08-21-authn-default-deny-and-object-ownership.md 的 D1。
# 改这里等于改系统的认证边界——必须先更新 ADR 并取得批准。
APPROVED_PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/schools"),
    ("GET", "/api/v1/schools/{school_name}/teachers"),
}

# 只匹配**真正的读取语法**，而不是散文里的提及。
# 这样解释"为什么移除"的注释与文档字符串不会误报，也就不需要维护文件白名单
# ——文件白名单会随重构漂移，而语法特征不会。
_HEADER_NAME = r"X-RMOS-Role|X-User-ID"
_HEADER_READ = re.compile(
    r"Header\s*\([^)]*(?:" + _HEADER_NAME + r")"           # FastAPI: Header(alias="X-User-ID")
    r"|headers\s*\.\s*get\s*\(\s*[\"\'](?:" + _HEADER_NAME + r")"   # request.headers.get("X-User-ID")
    r"|headers\s*\[\s*[\"\'](?:" + _HEADER_NAME + r")"                 # request.headers["X-User-ID"]
)


def _iter_python_files(app_root: Path):
    for path in app_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_public_route_whitelist_is_pinned() -> None:
    """AUTH-GATE-02：白名单必须与已批准集合逐条一致。"""
    added = sorted(PUBLIC_ROUTES - APPROVED_PUBLIC_ROUTES)
    removed = sorted(APPROVED_PUBLIC_ROUTES - PUBLIC_ROUTES)
    assert not added, (
        "公开路由白名单新增了未批准的条目——这会扩大匿名可访问面。\n"
        f"新增：{added}\n"
        "如确需公开，请先更新 ADR-2026-08-21-authn-default-deny-and-object-ownership 的 D1 "
        "并取得批准，再同步本文件的 APPROVED_PUBLIC_ROUTES。"
    )
    assert not removed, (
        "公开路由白名单移除了已批准条目，可能打断登录/注册等流程。\n"
        f"缺失：{removed}"
    )


def test_production_code_does_not_read_client_identity_headers() -> None:
    """AUTH-GATE-08：`app/` 下不得再有客户端身份头的读取点。"""
    app_root = Path(__file__).resolve().parents[2] / "app"
    violations: list[str] = []

    for file_path in _iter_python_files(app_root):
        rel = file_path.relative_to(app_root)
        for idx, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            if _HEADER_READ.search(line):
                violations.append(f"app/{rel}:{idx}: {line.strip()[:100]}")

    assert not violations, (
        "生产代码出现客户端身份头的读取点（AUTH-104 已禁止）。\n"
        "身份与角色只能来自 get_current_actor 解析出的 ActorContext。\n" + "\n".join(violations)
    )


def test_identity_header_detector_actually_detects() -> None:
    """探测器自检：正则若失效，上面的门禁会静默常绿，等于没有门禁。"""
    positives = [
        'x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),',
        'x_rmos_role: str | None = Header(default=None, alias="X-RMOS-Role")',
        'actor_user_id = request.headers.get("X-User-ID")',
        "role = request.headers['X-RMOS-Role']",
    ]
    for line in positives:
        assert _HEADER_READ.search(line), f"应被判定为读取点却漏掉：{line}"

    negatives = [
        "# 改造前这里从客户端 X-User-ID 头兜底，现已移除",
        "    `X-RMOS-Role` 头所携带的那个值，只是现在来自服务端令牌而非客户端。",
    ]
    for line in negatives:
        assert not _HEADER_READ.search(line), f"散文提及不应被判定为读取点：{line}"
