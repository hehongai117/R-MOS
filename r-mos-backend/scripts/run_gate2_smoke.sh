#!/usr/bin/env bash
set -euo pipefail

echo "Gate-2 A-001：回归入口脚本（smoke）"
echo "说明：默认仅跑 pytest 与门禁；如需端到端 curl 证据，传参 --e2e（要求服务已在 127.0.0.1:18080 启动）"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

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

echo "3) 附加 grep 核查（证据）"
grep -RInE "_log_deny_event|AuditEventService\\(.*\\)\\.log_event\\(|decision=['\\\"]deny['\\\"]" app | head -n 120 || true

if [[ "${1:-}" == "--e2e" ]]; then
  echo "4) 端到端证据（TeachingClass）"
  echo "要求：服务已启动在 http://127.0.0.1:18080"
  echo "创建真实 class -> student GET 404 -> student PATCH 403（curl 必须 --noproxy）"
  curl --noproxy 127.0.0.1,localhost -sS -X POST 'http://127.0.0.1:18080/api/v1/classes' \
    -H 'Content-Type: application/json' \
    -d '{"name":"A001端到端证据班级"}' > /tmp/a001_class.json

  python - <<'PY'
import json
data=json.load(open("/tmp/a001_class.json","r",encoding="utf-8"))
print("class_id=", data.get("id"))
PY

  CLASS_ID="$(python - <<'PY'
import json
print(json.load(open("/tmp/a001_class.json","r",encoding="utf-8")).get("id"))
PY
)"
  curl --noproxy 127.0.0.1,localhost -sS -o /tmp/a001_read.json -w "%{http_code}\n" \
    "http://127.0.0.1:18080/api/v1/classes/${CLASS_ID}" \
    -H 'X-RMOS-Role: student' -H 'X-User-ID: 2002'

  curl --noproxy 127.0.0.1,localhost -sS -o /tmp/a001_write.json -w "%{http_code}\n" \
    -X PATCH "http://127.0.0.1:18080/api/v1/classes/${CLASS_ID}" \
    -H 'Content-Type: application/json' \
    -H 'X-RMOS-Role: student' -H 'X-User-ID: 2002' \
    -d '{"name":"A001越权修改不应成功"}'

  echo "已生成：/tmp/a001_class.json /tmp/a001_read.json /tmp/a001_write.json"
fi

echo "全部通过：PASS"
