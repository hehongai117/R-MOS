"""浏览器 E2E 前置健检：账号可登录、SOP 裁决脚本非空、场景列表非空。

失败即退出非零并指明缺哪类数据——把"种子不全"从 Playwright 超时降级为秒级明确报错。

设计说明：
  登录响应为 TokenResponse（access_token / role / default_route 等），
  **无 user_id**，故不依赖 student_id。
  改用两个无需 user_id 的端点做数据健检：
    1. GET /sops/adjudication  — 返回 {total, items}，不需 Authorization
    2. GET /scenarios          — 返回 {total, items}，不需 Authorization
  这两类数据是黄金路径"选场景→选 SOP→训练"的核心依赖，
  非空即可断定 CI 种子播种成功、学生黄金路径有数据可跑。

用法：
  BACKEND_URL=http://localhost:8000 python scripts/e2e_preflight.py
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000") + "/api/v1"


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _get(path: str, token: str | None = None) -> dict:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def main() -> int:
    failures: list[str] = []

    # ── 健康检查 ───────────────────────────────────────────────
    try:
        health_req = urllib.request.Request(
            os.environ.get("BACKEND_URL", "http://localhost:8000") + "/api/v1/health"
        )
        with urllib.request.urlopen(health_req, timeout=10) as r:
            json.load(r)
        print("[PASS] backend /health 响应正常")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] backend /health 无响应: {exc}")
        return 1

    # ── 学生登录 ───────────────────────────────────────────────
    # 登录响应为 TokenResponse（无 user_id 字段），只验证能拿到 access_token
    try:
        auth = _post("/auth/login", {"email": "student1@rmos.demo", "password": "Student@123"})
        token = auth["access_token"]
        role = auth.get("role", "unknown")
        print(f"[PASS] student1 登录成功 (role={role})")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] student1 登录: {exc} —— 先跑 seed_demo_full.py")
        return 1

    # ── SOP 裁决脚本非空 ──────────────────────────────────────
    # GET /sops/adjudication 不需要 Authorization；返回 {total, items}
    try:
        sop_resp = _get("/sops/adjudication")
        sop_list = sop_resp if isinstance(sop_resp, list) else sop_resp.get("items", [])
        if sop_list:
            print(f"[PASS] SOP 裁决脚本 ×{len(sop_list)}")
        else:
            failures.append("SOP 裁决脚本列表为空（检查 seed_adjudication_sops.py 是否在 seed_demo_full 中被调用）")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"GET /sops/adjudication 请求失败: {exc}")

    # ── 场景列表非空 ──────────────────────────────────────────
    # GET /scenarios 不需要 Authorization；返回 {total, items}
    try:
        sc_resp = _get("/scenarios")
        sc_list = sc_resp if isinstance(sc_resp, list) else sc_resp.get("items", [])
        if sc_list:
            print(f"[PASS] 场景列表 ×{len(sc_list)}")
        else:
            failures.append("场景列表为空（检查 seed 的 FaultSOPMapping 数据是否插入）")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"GET /scenarios 请求失败: {exc}")

    # ── 汇总 ──────────────────────────────────────────────────
    for f in failures:
        print(f"[FAIL] {f}")
    status_str = "通过 ✅" if not failures else f"失败 {len(failures)} 项 ❌"
    print(f"== preflight: {status_str} ==")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
