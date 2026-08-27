#!/usr/bin/env python3
"""A1 双源清点：对每类对象各取一条静态源和一条运行时源，输出差集。

用法（必须用标准解释器，且先注入 .env）：

    cd <worktree>/r-mos-backend
    set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
    unset CORS_ORIGINS   # 该字段在环境变量形态下不是 JSON，pydantic-settings 会拒绝解析
    /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
        ../docs/audit/evidence/2026-08-26-a1-dual-source-inventory.py <输出 JSON>

退出码：0 = 所有类别差集已解释；1 = 出现未解释差集。

口径（必须与报告一致，改动口径必须同时改报告）：
- 静态源只看源码文件，排除 venv、__pycache__、node_modules、构建产物；
- 后端路由的静态源是 AST 装饰器，不是正则（正则会把多行装饰器和 .pyc 数进去）；
- 运行时源是 import main 之后的真实注册表 / SQLAlchemy metadata / 数据库 / alembic 版本图；
- 测试与前端构建图的枚举需要外部命令，不在本脚本内，见同批证据文档第 4 节。
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import pathlib
import re
import sys

HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
BE = pathlib.Path.cwd()  # 必须在 r-mos-backend/ 下运行


def _iter_app_sources() -> list[pathlib.Path]:
    """app/ 下全部源码，外加后端根目录的 .py（真实启动入口 main.py 就在根上，
    只扫 app/ 会漏掉它注册的根路由）。"""
    files = [
        f
        for f in sorted((BE / "app").rglob("*.py"))
        if "__pycache__" not in f.parts and "venv" not in f.parts
    ]
    return sorted(BE.glob("*.py")) + files


def static_routes() -> list[dict]:
    """静态源：AST 扫描 app/ 下的路由装饰器（排除 tests、alembic、scripts）。"""
    rows: list[dict] = []
    for f in _iter_app_sources():
        parts = f.relative_to(BE).parts
        if "tests" in parts or parts[0] in {"alembic", "scripts"}:
            continue
        module = ".".join(f.relative_to(BE).with_suffix("").parts)
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                call = dec if isinstance(dec, ast.Call) else None
                attr = call.func if call else dec
                if not isinstance(attr, ast.Attribute):
                    continue
                if attr.attr not in HTTP_VERBS | {"websocket"}:
                    continue
                path = None
                if call and call.args and isinstance(call.args[0], ast.Constant):
                    path = call.args[0].value
                rows.append(
                    {
                        "module": module,
                        "func": node.name,
                        "verb": attr.attr,
                        "decorator_path": path,
                        "line": node.lineno,
                    }
                )
    return rows


def static_tables() -> dict[str, str]:
    """静态源：AST 扫描 __tablename__ 与 Table("name", ...)。"""
    found: dict[str, str] = {}
    for f in _iter_app_sources():
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "__tablename__"
                        and isinstance(node.value, ast.Constant)
                    ):
                        found.setdefault(node.value.value, str(f.relative_to(BE)))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Table"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                found.setdefault(node.args[0].value, str(f.relative_to(BE)))
    return found


async def database_facts(url: str) -> dict:
    import asyncpg

    conn = await asyncpg.connect(re.sub(r"^postgresql\+asyncpg", "postgresql", url))
    try:
        tables = [
            r["tablename"]
            for r in await conn.fetch(
                "select tablename from pg_tables where schemaname='public' order by 1"
            )
        ]
        version = (
            [r["version_num"] for r in await conn.fetch("select version_num from alembic_version")]
            if "alembic_version" in tables
            else []
        )
        roles = [r["name"] for r in await conn.fetch("select name from roles order by id")]
        # 行数必须用精确 count(*)。pg_stat_user_tables.n_live_tup 是统计估算值，
        # 未 ANALYZE 时会停留在陈旧快照上——本审计初版据此得出「58 张空表」，
        # 经异源复核精确计数后实为 28 张，差 30 张表。估算值只作为漂移提示保留。
        row_counts = {}
        for name in tables:
            if name == "alembic_version":
                continue
            row_counts[name] = await conn.fetchval(f'select count(*) from public."{name}"')
        estimates = {
            r["relname"]: r["n_live_tup"]
            for r in await conn.fetch("select relname, n_live_tup from pg_stat_user_tables")
        }
        users = row_counts.get("users", 0)
    finally:
        await conn.close()
    return {
        "tables": tables,
        "alembic_version": version,
        "roles": roles,
        "row_counts": row_counts,
        "stat_estimates": estimates,
        "user_rows": users,
    }


def main() -> int:
    out_path = sys.argv[1]
    sys.path.insert(0, str(BE))

    static_route_rows = static_routes()
    static_table_map = static_tables()

    import main as backend_main  # 运行时源：真实注册表

    from app.models.base import Base

    runtime_routes = []
    for route in backend_main.app.routes:
        endpoint = getattr(route, "endpoint", None)
        runtime_routes.append(
            {
                "kind": type(route).__name__,
                "path": getattr(route, "path", None),
                "methods": sorted(getattr(route, "methods", []) or []),
                "module": getattr(endpoint, "__module__", None),
                "func": getattr(endpoint, "__name__", None),
            }
        )

    def strip_app(module: str) -> str:
        return module[4:] if module.startswith("app.") else module

    static_http = {
        (strip_app(r["module"]), r["func"], r["verb"].upper())
        for r in static_route_rows
        if r["verb"] != "websocket"
    }
    static_ws = {
        (strip_app(r["module"]), r["func"]) for r in static_route_rows if r["verb"] == "websocket"
    }
    runtime_http, runtime_ws, runtime_other = set(), set(), []
    for r in runtime_routes:
        if r["kind"] == "APIRoute":
            for method in r["methods"]:
                if method in {"HEAD", "OPTIONS"} and len(r["methods"]) > 1:
                    continue
                runtime_http.add((strip_app(r["module"] or ""), r["func"], method))
        elif r["kind"] == "APIWebSocketRoute":
            runtime_ws.add((strip_app(r["module"] or ""), r["func"]))
        else:
            runtime_other.append(r["path"])

    # 迁移：静态版本文件 vs alembic 版本图
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BE / "alembic.ini"))
    cfg.set_main_option("script_location", str(BE / "alembic"))
    script_dir = ScriptDirectory.from_config(cfg)
    migration_files = [p for p in (BE / "alembic/versions").glob("*.py") if p.name != "__init__.py"]
    revisions = list(script_dir.walk_revisions())

    db = asyncio.run(database_facts(os.environ["DATABASE_URL"]))

    # 后端模块可达性：磁盘模块 vs 启动后已导入模块
    disk_modules = {}
    for f in _iter_app_sources():
        module = ".".join(f.relative_to(BE).with_suffix("").parts)
        disk_modules[module[:-9] if module.endswith(".__init__") else module] = str(
            f.relative_to(BE)
        )
    # 根目录模块（main）不以 app. 开头，按模块名与 sys.modules 直接取交集，避免误判为未导入
    loaded = set(disk_modules) & set(sys.modules)

    metadata_tables = set(Base.metadata.tables)
    result = {
        "baseline": "29d2a5889e3b320a3e777e3d8c19efbbe31c0294",
        "routes": {
            "static_http": len(static_http),
            "runtime_http": len(runtime_http),
            "static_only": sorted(static_http - runtime_http),
            "runtime_only": sorted(runtime_http - static_http),
            "static_ws": sorted(static_ws),
            "runtime_ws": sorted(runtime_ws),
            "runtime_total": len(runtime_routes),
            "framework_routes": sorted(runtime_other),
        },
        "tables": {
            "static_ast": sorted(static_table_map),
            "runtime_metadata": sorted(metadata_tables),
            "database": db["tables"],
            "static_only": sorted(set(static_table_map) - metadata_tables),
            "metadata_only": sorted(metadata_tables - set(static_table_map)),
            "database_only": sorted(set(db["tables"]) - metadata_tables),
            "metadata_not_in_database": sorted(metadata_tables - set(db["tables"])),
        },
        "migrations": {
            "files": len(migration_files),
            "graph_nodes": len(revisions),
            "heads": list(script_dir.get_heads()),
            "base": script_dir.get_base(),
            "database_version": db["alembic_version"],
        },
        "backend_modules": {
            "on_disk": len(disk_modules),
            "imported_at_startup": len(set(disk_modules) & loaded),
            "not_imported": sorted(set(disk_modules) - loaded),
        },
        "database_state": {
            "roles": db["roles"],
            "user_rows": db["user_rows"],
            "row_counts": db["row_counts"],
            "nonempty_count": sum(1 for n in db["row_counts"].values() if n > 0),
            "empty_count": sum(1 for n in db["row_counts"].values() if n == 0),
            "stale_estimates": sorted(
                name
                for name, n in db["row_counts"].items()
                if db["stat_estimates"].get(name, 0) != n
            ),
            "table_count": len(db["tables"]),
        },
        "route_modules": sorted(
            {strip_app(r["module"] or "") for r in runtime_routes if r["kind"] == "APIRoute"}
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    unexplained = (
        result["routes"]["static_only"]
        or result["routes"]["runtime_only"]
        or result["tables"]["static_only"]
        or result["tables"]["metadata_only"]
        or result["tables"]["metadata_not_in_database"]
        or [t for t in result["tables"]["database_only"] if t != "alembic_version"]
        or (result["migrations"]["files"] != result["migrations"]["graph_nodes"])
        or (len(result["migrations"]["heads"]) != 1)
        or (result["migrations"]["heads"] != result["migrations"]["database_version"])
    )
    print(
        f'路由 静态{result["routes"]["static_http"]} / 运行时{result["routes"]["runtime_http"]}'
        f' 差集{len(result["routes"]["static_only"]) + len(result["routes"]["runtime_only"])}'
        f' | 表 静态{len(result["tables"]["static_ast"])} / metadata{len(metadata_tables)}'
        f' / 数据库{len(db["tables"])} 差集{result["tables"]["database_only"]}'
        f' | 迁移 文件{result["migrations"]["files"]} / 图{len(revisions)}'
        f' heads={result["migrations"]["heads"]} 库={db["alembic_version"]}'
        f' | 模块 磁盘{len(disk_modules)} / 启动已导入{len(set(disk_modules) & loaded)}'
        f' | 数据 非空{result["database_state"]["nonempty_count"]}'
        f' / 空{result["database_state"]["empty_count"]}'
        f'（估算失真 {len(result["database_state"]["stale_estimates"])} 张）'
    )
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
