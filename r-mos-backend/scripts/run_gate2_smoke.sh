#!/usr/bin/env bash
set -euo pipefail

print_help() {
  cat <<'EOF'
Gate-2 A-001/A-002/A-003 回归入口脚本（smoke）

用法：
  ./scripts/run_gate2_smoke.sh
  ./scripts/run_gate2_smoke.sh --e2e
  ./scripts/run_gate2_smoke.sh --e2e --audit
  ./scripts/run_gate2_smoke.sh --help

参数说明：
  --e2e     要求服务已启动在 127.0.0.1:18080；会创建 class 并断言 READ=404/WRITE=403 + 对应 error_type/code
  --audit   必须与 --e2e 同用；要求已设置 DATABASE_URL；会校验 audit_events 命中 read_access_denied 与 permission_denied（AUDIT-T006）
  --help/-h 显示帮助

前置条件：
  - 建议在后端目录运行（脚本会自动 cd 到后端根目录）
  - .venv 存在
  - --e2e 需要 uvicorn 已启动（openapi.json 返回 200）
  - --audit 需要 DATABASE_URL 指向本机 Postgres
  - 本机 HTTP 调用必须 curl --noproxy 127.0.0.1,localhost（脚本已内置）

退出码说明（码→含义，audit 相关码为 20/21/22/23/24）：
  2   参数错误（不支持参数或 --audit 未与 --e2e 同用）
  3   服务不可达（openapi 非 200）
  4   无法取得 class_id
  10  READ 状态码不符合（期望 404）
  11  WRITE 状态码不符合（期望 403）
  12  READ 字段断言失败（error_type/code）
  13  WRITE 字段断言失败（error_type/code）
  20  启用 --audit 时未设置 DATABASE_URL
  21  数据库连接失败
  22  数据库查询失败
  23  审计缺少 read_access_denied
  24  审计缺少 permission_denied
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

E2E=false
AUDIT=false
for arg in "$@"; do
  case "$arg" in
    --help|-h)
      print_help
      exit 0
      ;;
    --e2e)
      E2E=true
      ;;
    --audit)
      AUDIT=true
      ;;
    *)
      echo "错误：不支持的参数：$arg"
      echo "用法：./scripts/run_gate2_smoke.sh [--e2e] [--audit] [--help]"
      exit 2
      ;;
  esac
done

echo "Gate-2 A-001：回归入口脚本（smoke）"
echo "说明：默认仅跑 pytest 与门禁；如需端到端 curl 证据，传参 --e2e；如需审计落库断言，传参 --audit（需与 --e2e 一起使用）"

if [[ "$AUDIT" == "true" && "$E2E" != "true" ]]; then
  echo "错误：--audit 需与 --e2e 同时使用。"
  exit 2
fi

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "错误：未找到 .venv，请先创建并安装依赖。"
  exit 2
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "1) Gate-1 最小回归集合（teaching）"
pytest -q tests/unit/test_teaching_api.py -k "not_found_attempt_returns_resource_not_found_without_deny_audit or read_access_denied_records_real_resource_id or audit_permission_denied_records_deny_event or class_read_access_denied_records_real_resource_id or class_write_permission_denied_records_real_resource_id"

echo "2) deny 入口门禁"
pytest -q tests/unit/test_deny_audit_entrypoint_gate.py

echo "3) help 输出门禁"
pytest -q tests/unit/test_smoke_help_gate.py

echo "4) 附加 grep 核查（证据）"
grep -RInE "_log_deny_event|AuditEventService\\(.*\\)\\.log_event\\(|decision=['\\\"]deny['\\\"]" app | head -n 120 || true

if [[ "$E2E" == "true" ]]; then
  echo "5) 端到端证据（TeachingClass）"
  echo "要求：服务已启动在 http://127.0.0.1:18080"
  echo "创建真实 class -> student GET 404 -> student PATCH 403（curl 必须 --noproxy）"
  OPENAPI_CODE="$(curl --noproxy 127.0.0.1,localhost -sS -o /dev/null -w "%{http_code}" \
    http://127.0.0.1:18080/openapi.json 2>/dev/null || true)"
  if [[ "$OPENAPI_CODE" != "200" ]]; then
    echo "错误：服务不可达（openapi 状态码=${OPENAPI_CODE:-N/A}）。请先启动 uvicorn："
    echo "cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && uvicorn main:app --host 127.0.0.1 --port 18080"
    exit 3
  fi

  curl --noproxy 127.0.0.1,localhost -sS -X POST 'http://127.0.0.1:18080/api/v1/classes' \
    -H 'Content-Type: application/json' \
    -d '{"name":"A001端到端证据班级"}' > /tmp/a001_class.json

  CLASS_ID="$(python - <<'PY'
import json
import sys
data = json.load(open("/tmp/a001_class.json", "r", encoding="utf-8"))
cid = data.get("id")
if cid in (None, "", "None"):
    sys.exit(1)
print(cid)
PY
)" || {
  echo "错误：创建班级后未获得有效 class_id（/tmp/a001_class.json）"
  exit 4
}

  if ! READ_CODE="$(curl --noproxy 127.0.0.1,localhost -sS -o /tmp/a001_read.json -w "%{http_code}" \
    "http://127.0.0.1:18080/api/v1/classes/${CLASS_ID}" \
    -H 'X-RMOS-Role: student' -H 'X-User-ID: 2002')"; then
    echo "错误：READ 越权请求执行失败"
    exit 10
  fi

  if ! WRITE_CODE="$(curl --noproxy 127.0.0.1,localhost -sS -o /tmp/a001_write.json -w "%{http_code}" \
    -X PATCH "http://127.0.0.1:18080/api/v1/classes/${CLASS_ID}" \
    -H 'Content-Type: application/json' \
    -H 'X-RMOS-Role: student' -H 'X-User-ID: 2002' \
    -d '{"name":"A001越权修改不应成功"}')"; then
    echo "错误：WRITE 越权请求执行失败"
    exit 11
  fi

  if [[ "$READ_CODE" != "404" ]]; then
    echo "错误：READ 状态码不符合（期望 404，实际 ${READ_CODE}）"
    exit 10
  fi
  if [[ "$WRITE_CODE" != "403" ]]; then
    echo "错误：WRITE 状态码不符合（期望 403，实际 ${WRITE_CODE}）"
    exit 11
  fi

  if ! python - <<'PY'
import json
import sys

path = "/tmp/a001_read.json"
data = json.load(open(path, "r", encoding="utf-8"))
details = data.get("details") or {}
inner = details.get("details") or {}
error_type = data.get("error_type")
code = details.get("code")
action = inner.get("action")
resource_type = inner.get("resource_type")
resource_id = inner.get("resource_id")
reason = inner.get("reason")
if error_type != "ReadAccessDeniedError" or code != "READ_ACCESS_DENIED":
    print("错误：READ 返回体字段不符合预期")
    print(f"  error_type={error_type}")
    print(f"  code={code}")
    print(f"  action={action}")
    print(f"  resource_type={resource_type}")
    print(f"  resource_id={resource_id}")
    print(f"  reason={reason}")
    sys.exit(1)
print(f"read: error_type={error_type} code={code} action={action} resource_type={resource_type} resource_id={resource_id} reason={reason}")
PY
  then
    exit 12
  fi

  if ! python - <<'PY'
import json
import sys

path = "/tmp/a001_write.json"
data = json.load(open(path, "r", encoding="utf-8"))
details = data.get("details") or {}
inner = details.get("details") or {}
error_type = data.get("error_type")
code = details.get("code")
action = inner.get("action")
resource_type = inner.get("resource_type")
resource_id = inner.get("resource_id")
reason = inner.get("reason")
if error_type != "WriteAccessDeniedError" or code != "WRITE_ACCESS_DENIED":
    print("错误：WRITE 返回体字段不符合预期")
    print(f"  error_type={error_type}")
    print(f"  code={code}")
    print(f"  action={action}")
    print(f"  resource_type={resource_type}")
    print(f"  resource_id={resource_id}")
    print(f"  reason={reason}")
    sys.exit(1)
print(f"write: error_type={error_type} code={code} action={action} resource_type={resource_type} resource_id={resource_id} reason={reason}")
PY
  then
    exit 13
  fi

  echo "class_id=${CLASS_ID}"
  echo "read_status=${READ_CODE} write_status=${WRITE_CODE}"
  echo "已生成：/tmp/a001_class.json /tmp/a001_read.json /tmp/a001_write.json"

  if [[ "$AUDIT" == "true" ]]; then
    echo "6) 审计落库断言（AUDIT-T006）"
    if [[ -z "${DATABASE_URL:-}" ]]; then
      echo "错误：启用 --audit 但未设置 DATABASE_URL。"
      exit 20
    fi
    DB_DSN="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql://}"
    CLASS_ID="$CLASS_ID" DB_DSN="$DB_DSN" python - <<'PY'
import asyncio
import asyncpg
import os
import sys

class_id = os.environ.get("CLASS_ID", "").strip()
dsn = os.environ.get("DB_DSN", "").strip()

if not class_id or not dsn:
    print("错误：审计断言环境变量缺失（class_id 或 DB_DSN）")
    sys.exit(22)


async def main():
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:
        print(f"错误：数据库连接失败：{exc}")
        sys.exit(21)

    try:
        rows = await conn.fetch(
            """
            select action, resource_type, resource_id, decision
            from audit_events
            where decision='deny' and resource_type='TeachingClass' and resource_id=$1
            order by id desc limit 10
            """,
            str(class_id),
        )
    except Exception as exc:
        await conn.close()
        print(f"错误：审计查询失败：{exc}")
        sys.exit(22)

    await conn.close()
    actions = {row["action"] for row in rows}
    print(f"audit: resource_id={class_id} actions={sorted(actions)} count={len(rows)}")

    if "read_access_denied" not in actions:
        print("错误：未命中 action=read_access_denied")
        sys.exit(23)
    if "permission_denied" not in actions:
        print("错误：未命中 action=permission_denied")
        sys.exit(24)
    print("审计断言：PASS（AUDIT-T006）")


asyncio.run(main())
PY
  fi
fi

echo "全部通过：PASS"
