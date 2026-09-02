#!/usr/bin/env python3
"""Board-approval-only A0 database and runtime-route fingerprint probes.

The script has no default action. Running ``db`` opens a read-only transaction
to the exact allowlisted local database and performs a schema-only pg_dump.
Running ``routes`` imports the FastAPI application without starting lifespan or
a listening socket. Neither mode writes an output file.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import pathlib
import subprocess
import sys
from typing import Any

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url


ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND = ROOT / "r-mos-backend"
DEFAULT_ENV = pathlib.Path("/Users/xuhehong/Desktop/r-mos/r-mos-backend/.env")
ALLOWED_HOST = "localhost"
ALLOWED_PORT = 5432
ALLOWED_DATABASE = "rmos"
ALLOWED_DRIVERS = {"postgresql", "postgresql+asyncpg"}


def validate_database_url(url: URL) -> URL:
    port = url.port or ALLOWED_PORT
    if url.drivername not in ALLOWED_DRIVERS:
        raise RuntimeError(f"database driver is not allowlisted: {url.drivername}")
    if url.host != ALLOWED_HOST or port != ALLOWED_PORT or url.database != ALLOWED_DATABASE:
        raise RuntimeError(
            "database target is not the exact allowlisted local target: "
            f"host={url.host!r} port={port!r} database={url.database!r}"
        )
    return url


def load_database_url(env_file: pathlib.Path) -> URL:
    values = dotenv_values(env_file)
    raw = values.get("DATABASE_URL")
    if not raw:
        raise RuntimeError(f"DATABASE_URL is missing from {env_file}")
    return validate_database_url(make_url(raw))


def safe_target(url: URL) -> dict[str, Any]:
    return {
        "driver": url.drivername,
        "host": url.host,
        "port": url.port or ALLOWED_PORT,
        "database": url.database,
    }


async def database_fingerprint(env_file: pathlib.Path) -> dict[str, Any]:
    import asyncpg

    url = load_database_url(env_file)
    connection = await asyncpg.connect(
        host=url.host,
        port=url.port or ALLOWED_PORT,
        user=url.username,
        password=url.password,
        database=url.database,
    )
    try:
        async with connection.transaction(readonly=True):
            server_version = await connection.fetchval("show server_version")
            extensions = [
                dict(row)
                for row in await connection.fetch(
                    "select extname, extversion from pg_extension order by extname"
                )
            ]
            tables = [
                row["tablename"]
                for row in await connection.fetch(
                    "select tablename from pg_tables "
                    "where schemaname='public' order by tablename"
                )
            ]
            alembic_versions = (
                [
                    row["version_num"]
                    for row in await connection.fetch(
                        "select version_num from alembic_version order by version_num"
                    )
                ]
                if "alembic_version" in tables
                else []
            )
    finally:
        await connection.close()

    dump_env = os.environ.copy()
    if url.password is not None:
        dump_env["PGPASSWORD"] = url.password
    dump_command = [
        "pg_dump",
        "--host",
        str(url.host),
        "--port",
        str(url.port or ALLOWED_PORT),
        "--username",
        str(url.username),
        "--dbname",
        str(url.database),
        "--schema=public",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
    ]
    completed = subprocess.run(
        dump_command,
        check=False,
        capture_output=True,
        env=dump_env,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "pg_dump failed before fingerprinting: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return {
        "probe": "P-A0-DB-01",
        "target": safe_target(url),
        "read_transaction": "READ ONLY",
        "server_version": server_version,
        "extensions": extensions,
        "public_tables": tables,
        "alembic_versions": alembic_versions,
        "schema_dump": {
            "scope": "public schema only; no owner; no privileges; no rows",
            "bytes": len(completed.stdout),
            "sha256": hashlib.sha256(completed.stdout).hexdigest(),
            "exit_code": completed.returncode,
        },
    }


def route_fingerprint(env_file: pathlib.Path) -> dict[str, Any]:
    values = dotenv_values(env_file)
    load_database_url(env_file)
    for key, value in values.items():
        if value is not None:
            os.environ[key] = value
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from app.core import logging as app_logging

    app_logging.setup_logging = lambda: None
    logging.getLogger().handlers.clear()
    import main

    routes = [
        {
            "type": type(route).__name__,
            "path": getattr(route, "path", None),
            "methods": sorted(getattr(route, "methods", []) or []),
        }
        for route in main.app.routes
    ]
    routes.sort(key=lambda item: (item["type"], item["path"] or "", item["methods"]))
    encoded = json.dumps(
        routes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "probe": "P-A0-ROUTE-01",
        "lifespan_executed": False,
        "listening_socket_started": False,
        "application_file_logging_disabled_before_import": True,
        "route_count": len(routes),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "routes": routes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one board-approved A0 fingerprint probe."
    )
    parser.add_argument("mode", choices=("db", "routes"))
    parser.add_argument("--env-file", type=pathlib.Path, default=DEFAULT_ENV)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "db":
        result = asyncio.run(database_fingerprint(args.env_file))
    else:
        result = route_fingerprint(args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
