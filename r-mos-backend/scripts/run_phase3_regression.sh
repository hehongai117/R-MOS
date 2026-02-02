#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
RUN_LOG="$LOG_DIR/phase3-step4-run.log"

REPORT_PATH="$PROJECT_ROOT/docs/testing/TEST_REPORT.md"
PLAN_PATH="$PROJECT_ROOT/docs/testing/TEST_PLAN.md"

if [[ "$PWD" != "$ROOT_DIR" ]]; then
  echo "ERROR_CODE=RUN_DIR_INVALID"
  echo "必须在后端目录运行：$ROOT_DIR"
  exit 2
fi

if [[ ! -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  echo "ERROR_CODE=VENV_NOT_FOUND"
  echo "未找到 .venv：$ROOT_DIR/.venv"
  exit 2
fi

source "$ROOT_DIR/.venv/bin/activate"
export DATABASE_URL='postgresql+asyncpg://postgres@localhost:5432/postgres'
mkdir -p "$LOG_DIR"

update_plan_status() {
  local status="$1"
  local reason="${2:-}"
  python - <<'PY'
import os
import re
from pathlib import Path

plan_path = Path(os.environ["PLAN_PATH"])
status = os.environ["PLAN_STATUS"]
reason = os.environ.get("PLAN_REASON", "")
content = plan_path.read_text()

pattern = r"(T18-AUTO-01[^\n]*\()([A-Z]+)(\))"

def repl(match):
    return f"{match.group(1)}{status}{match.group(3)}"

if re.search(pattern, content):
    content = re.sub(pattern, repl, content, count=1)
else:
    appendix = (
        "\n### 任务18（Phase3 Step4 单命令回归）\n\n"
        f"- 用例编号：T18-AUTO-01（单命令 Phase3 回归）（{status}）\n"
        "  - 角色：开发\n"
        "  - 前置条件：后端可启动并生成诊断样本\n"
        "  - 命令：`bash r-mos-backend/scripts/run_phase3_regression.sh`\n"
        "  - 期望结果：自动完成启动、seed、采证与文档回填\n"
        "  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step4 单命令回归证据`\n"
        "  - 标签：P3\n"
    )
    content = content.rstrip() + appendix

if reason:
    content = content.rstrip() + f"\n\n- T18 失败原因：{reason}\n"

plan_path.write_text(content)
PY
}

fail() {
  local reason="$1"
  local code="$2"
  PLAN_STATUS="FAIL" PLAN_REASON="$reason" PLAN_PATH="$PLAN_PATH" update_plan_status "FAIL" "$reason"
  echo "ERROR_CODE=$reason"
  echo "LOG_PATH=$RUN_LOG"
  exit "$code"
}

rm -f "$RUN_LOG"
bash "$ROOT_DIR/scripts/run_dev.sh" >"$RUN_LOG" 2>&1 &
RUN_PID=$!

PORT=""
for _ in {1..30}; do
  if ! kill -0 "$RUN_PID" >/dev/null 2>&1; then
    tail -n 40 "$RUN_LOG" >&2 || true
    fail "BACKEND_START_FAILED" 10
  fi
  PORT="$(rg -m1 'BACKEND_PORT=' "$RUN_LOG" | sed 's/.*BACKEND_PORT=//')"
  if [[ -n "$PORT" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "$PORT" ]]; then
  fail "BACKEND_PORT_NOT_DETECTED" 11
fi

echo "BACKEND_PORT=${PORT}"

OPENAPI_STATUS="$(curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:${PORT}/openapi.json" | head -n 1 || true)"
if ! echo "$OPENAPI_STATUS" | rg -q "200"; then
  fail "OPENAPI_FAILED" 20
fi

python "$ROOT_DIR/scripts/seed_teaching_diagnosis_cases.py" --case all

fetch_diagnosis() {
  local attempt_id="$1"
  local out_file="$2"
  local url="http://127.0.0.1:${PORT}/api/v1/attempts/${attempt_id}/diagnosis"
  local status_line
  status_line="$(curl --noproxy 127.0.0.1,localhost -sS -i "$url" | head -n 1 || true)"
  if ! echo "$status_line" | rg -q "200"; then
    echo "CURL_FAILED=$url"
    fail "CURL_FAILED_${attempt_id}" 30
  fi
  curl --noproxy 127.0.0.1,localhost -sS "$url" > "$out_file"
}

TMP_23="/tmp/phase3-step4-23.json"
TMP_24="/tmp/phase3-step4-24.json"
TMP_25="/tmp/phase3-step4-25.json"

fetch_diagnosis 23 "$TMP_23"
fetch_diagnosis 24 "$TMP_24"
fetch_diagnosis 25 "$TMP_25"

rg -q '"stepIndex":1' "$TMP_23" || fail "DIAG23_STEPINDEX" 40
rg -q '"stepDiagnosisCode":"E_ERROR_OCCURRED"' "$TMP_23" || fail "DIAG23_CODE" 41
rg -q '"ruleId":"R-DIAG-001"' "$TMP_23" || fail "DIAG23_RULE" 42

rg -q '"stepIndex":1' "$TMP_24" || fail "DIAG24_STEPINDEX" 43
rg -q '"stepDiagnosisCode":"E_STEP_SKIPPED"' "$TMP_24" || fail "DIAG24_CODE" 44
rg -q '"ruleId":"R-DIAG-002"' "$TMP_24" || fail "DIAG24_RULE" 45

rg -q '"stepIndex":2' "$TMP_25" || fail "DIAG25_STEPINDEX" 46
rg -q '"stepDiagnosisCode":"E_TOO_SLOW"' "$TMP_25" || fail "DIAG25_CODE" 47
rg -q '步骤耗时偏长' "$TMP_25" || fail "DIAG25_FINDING" 48

SNIP_23="$(python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/phase3-step4-23.json").read_text())
step = next((s for s in data.get("stepDiagnoses", []) if s.get("stepIndex") == 1), {})
snippet = {
    "attemptId": data.get("attemptId"),
    "diagnosisCode": data.get("diagnosisCode"),
    "ruleId": data.get("ruleId"),
    "severity": data.get("severity"),
    "stepDiagnoses": [
        {
            "stepIndex": step.get("stepIndex"),
            "stepDiagnosisCode": step.get("stepDiagnosisCode"),
            "severity": step.get("severity"),
            "findings": step.get("findings"),
        }
    ],
}
print(json.dumps(snippet, ensure_ascii=False))
PY
)"

SNIP_24="$(python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/phase3-step4-24.json").read_text())
step = next((s for s in data.get("stepDiagnoses", []) if s.get("stepIndex") == 1), {})
snippet = {
    "attemptId": data.get("attemptId"),
    "diagnosisCode": data.get("diagnosisCode"),
    "ruleId": data.get("ruleId"),
    "severity": data.get("severity"),
    "stepDiagnoses": [
        {
            "stepIndex": step.get("stepIndex"),
            "stepDiagnosisCode": step.get("stepDiagnosisCode"),
            "severity": step.get("severity"),
            "findings": step.get("findings"),
        }
    ],
}
print(json.dumps(snippet, ensure_ascii=False))
PY
)"

SNIP_25="$(python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/phase3-step4-25.json").read_text())
step = next((s for s in data.get("stepDiagnoses", []) if s.get("stepIndex") == 2), {})
snippet = {
    "attemptId": data.get("attemptId"),
    "diagnosisCode": data.get("diagnosisCode"),
    "ruleId": data.get("ruleId"),
    "severity": data.get("severity"),
    "stepDiagnoses": [
        {
            "stepIndex": step.get("stepIndex"),
            "stepDiagnosisCode": step.get("stepDiagnosisCode"),
            "severity": step.get("severity"),
            "findings": step.get("findings"),
        }
    ],
}
print(json.dumps(snippet, ensure_ascii=False))
PY
)"

export OPENAPI_STATUS PORT SNIP_23 SNIP_24 SNIP_25 REPORT_PATH
python - <<'PY'
import os
from datetime import datetime
from pathlib import Path

report_path = Path(os.environ["REPORT_PATH"])
port = os.environ["PORT"]
openapi_status = os.environ["OPENAPI_STATUS"]
snip_23 = os.environ["SNIP_23"]
snip_24 = os.environ["SNIP_24"]
snip_25 = os.environ["SNIP_25"]

start = "<!-- PHASE3_STEP4_START -->"
end = "<!-- PHASE3_STEP4_END -->"

block = f"""{start}
### Phase3 Step4 单命令回归证据

- 运行时间：{datetime.utcnow().isoformat()}Z
- 后端端口：`{port}`

**openapi**
```
{openapi_status}
```

**diagnosis（attempt_id=23）**
```
{snip_23}
```

**diagnosis（attempt_id=24）**
```
{snip_24}
```

**diagnosis（attempt_id=25）**
```
{snip_25}
```
{end}"""

content = report_path.read_text()
if start in content and end in content:
    prefix = content.split(start)[0].rstrip()
    suffix = content.split(end)[1].lstrip()
    content = prefix + "\n\n" + block + "\n\n" + suffix
else:
    content = content.rstrip() + "\n\n" + block + "\n"

report_path.write_text(content)
PY

PLAN_STATUS="PASS" PLAN_REASON="" PLAN_PATH="$PLAN_PATH" update_plan_status "PASS" ""

echo "SUMMARY: BACKEND_PORT=${PORT}"
echo "SUMMARY: DIAG23=E_ERROR_OCCURRED"
echo "SUMMARY: DIAG24=E_STEP_SKIPPED"
echo "SUMMARY: DIAG25=E_TOO_SLOW"
