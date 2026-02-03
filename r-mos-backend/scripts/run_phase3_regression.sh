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

pattern = r"(T18-AUTO-01[^\n]*)([（(])([A-Z]+)([)）])"

def repl(match):
    return f"{match.group(1)}{match.group(2)}{status}{match.group(4)}"

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

content = re.sub(r"^\\- T18 失败原因：.*$", "", content, flags=re.M)

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
  if [[ -f "$RUN_LOG" ]]; then
    echo "LOG_TAIL_BEGIN"
    tail -n 30 "$RUN_LOG" || true
    echo "LOG_TAIL_END"
  fi
  exit "$code"
}

PORT=""
PORT_SOURCE=""

start_backend() {
  rm -f "$RUN_LOG"
  bash "$ROOT_DIR/scripts/run_dev.sh" >"$RUN_LOG" 2>&1 &
  RUN_PID=$!

  for _ in {1..30}; do
    if ! kill -0 "$RUN_PID" >/dev/null 2>&1; then
      tail -n 40 "$RUN_LOG" >&2 || true
      fail "BACKEND_START_FAILED" 10
    fi
    PORT="$(grep -m1 -E 'BACKEND_PORT=' "$RUN_LOG" | sed 's/.*BACKEND_PORT=//' || true)"
    if [[ -n "$PORT" ]]; then
      break
    fi
    sleep 1
  done

  if [[ -z "$PORT" ]]; then
    fail "BACKEND_PORT_NOT_DETECTED" 11
  fi

  PORT_SOURCE="script"
  echo "BACKEND_PORT=${PORT}"
}

for candidate in 8000 18000; do
  if lsof -nP -iTCP:${candidate} -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="${candidate}"
    PORT_SOURCE="existing"
    echo "BACKEND_PORT=${PORT}"
    break
  fi
done

if [[ -z "$PORT" ]]; then
  start_backend
fi

OPENAPI_HDR="/tmp/phase3-step4-openapi.hdr"
OPENAPI_BODY="/tmp/phase3-step4-openapi.body"
if ! curl --noproxy 127.0.0.1,localhost -sS -D "$OPENAPI_HDR" -o "$OPENAPI_BODY" "http://127.0.0.1:${PORT}/openapi.json"; then
  if [[ "$PORT_SOURCE" == "existing" ]]; then
    start_backend
    if ! curl --noproxy 127.0.0.1,localhost -sS -D "$OPENAPI_HDR" -o "$OPENAPI_BODY" "http://127.0.0.1:${PORT}/openapi.json"; then
      fail "OPENAPI_FAILED" 20
    fi
  else
    fail "OPENAPI_FAILED" 20
  fi
fi
OPENAPI_STATUS="$(sed -n '1p' "$OPENAPI_HDR" 2>/dev/null || true)"
if ! echo "$OPENAPI_STATUS" | grep -qE "200"; then
  fail "OPENAPI_FAILED" 20
fi

SEED_OUTPUT="$(python "$ROOT_DIR/scripts/seed_teaching_diagnosis_cases.py" --case all 2>&1)"
echo "$SEED_OUTPUT"
ATTEMPT_ERROR="$(echo "$SEED_OUTPUT" | grep -nE 'case=error' | sed -nE 's/.*attempt_id=([0-9]+).*/\1/p' | head -n 1)"
ATTEMPT_SKIP="$(echo "$SEED_OUTPUT" | grep -nE 'case=skip' | sed -nE 's/.*attempt_id=([0-9]+).*/\1/p' | head -n 1)"
ATTEMPT_SLOW="$(echo "$SEED_OUTPUT" | grep -nE 'case=slow' | sed -nE 's/.*attempt_id=([0-9]+).*/\1/p' | head -n 1)"

if [[ -z "$ATTEMPT_ERROR" || -z "$ATTEMPT_SKIP" || -z "$ATTEMPT_SLOW" ]]; then
  fail "SEED_PARSE_FAILED" 25
fi

fetch_diagnosis() {
  local attempt_id="$1"
  local out_file="$2"
  local url="http://127.0.0.1:${PORT}/api/v1/attempts/${attempt_id}/diagnosis"
  local hdr_file="/tmp/phase3-step4-${attempt_id}.hdr"
  local status_line
  if ! curl --noproxy 127.0.0.1,localhost -sS -D "$hdr_file" -o "$out_file" "$url"; then
    echo "CURL_FAILED=$url"
    fail "CURL_FAILED_${attempt_id}" 30
  fi
  status_line="$(sed -n '1p' "$hdr_file" 2>/dev/null || true)"
  if ! echo "$status_line" | grep -qE "200"; then
    echo "CURL_FAILED=$url"
    fail "CURL_FAILED_${attempt_id}" 30
  fi
}

TMP_ERROR="/tmp/phase3-step4-${ATTEMPT_ERROR}.json"
TMP_SKIP="/tmp/phase3-step4-${ATTEMPT_SKIP}.json"
TMP_SLOW="/tmp/phase3-step4-${ATTEMPT_SLOW}.json"

fetch_diagnosis "$ATTEMPT_ERROR" "$TMP_ERROR"
fetch_diagnosis "$ATTEMPT_SKIP" "$TMP_SKIP"
fetch_diagnosis "$ATTEMPT_SLOW" "$TMP_SLOW"

grep -qE '"stepIndex":1' "$TMP_ERROR" || fail "DIAG_ERROR_STEPINDEX" 40
grep -qE '"stepDiagnosisCode":"E_ERROR_OCCURRED"' "$TMP_ERROR" || fail "DIAG_ERROR_CODE" 41
grep -qE '"ruleId":"R-DIAG-001"' "$TMP_ERROR" || fail "DIAG_ERROR_RULE" 42

grep -qE '"stepIndex":1' "$TMP_SKIP" || fail "DIAG_SKIP_STEPINDEX" 43
grep -qE '"stepDiagnosisCode":"E_STEP_SKIPPED"' "$TMP_SKIP" || fail "DIAG_SKIP_CODE" 44
grep -qE '"ruleId":"R-DIAG-002"' "$TMP_SKIP" || fail "DIAG_SKIP_RULE" 45

grep -qE '"stepIndex":2' "$TMP_SLOW" || fail "DIAG_SLOW_STEPINDEX" 46
grep -qE '"stepDiagnosisCode":"E_TOO_SLOW"' "$TMP_SLOW" || fail "DIAG_SLOW_CODE" 47
grep -qF '步骤耗时偏长' "$TMP_SLOW" || fail "DIAG_SLOW_FINDING" 48

SNIP_ERROR="$(TMP_ERROR="$TMP_ERROR" python - <<'PY'
import json
import os
from pathlib import Path
data = json.loads(Path(os.environ["TMP_ERROR"]).read_text())
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

SNIP_SKIP="$(TMP_SKIP="$TMP_SKIP" python - <<'PY'
import json
import os
from pathlib import Path
data = json.loads(Path(os.environ["TMP_SKIP"]).read_text())
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

SNIP_SLOW="$(TMP_SLOW="$TMP_SLOW" python - <<'PY'
import json
import os
from pathlib import Path
data = json.loads(Path(os.environ["TMP_SLOW"]).read_text())
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

export OPENAPI_STATUS PORT SNIP_ERROR SNIP_SKIP SNIP_SLOW REPORT_PATH ATTEMPT_ERROR ATTEMPT_SKIP ATTEMPT_SLOW
python - <<'PY'
import os
from datetime import datetime, timezone
from pathlib import Path

report_path = Path(os.environ["REPORT_PATH"])
port = os.environ["PORT"]
openapi_status = os.environ["OPENAPI_STATUS"]
snip_error = os.environ["SNIP_ERROR"]
snip_skip = os.environ["SNIP_SKIP"]
snip_slow = os.environ["SNIP_SLOW"]
attempt_error = os.environ["ATTEMPT_ERROR"]
attempt_skip = os.environ["ATTEMPT_SKIP"]
attempt_slow = os.environ["ATTEMPT_SLOW"]

start = "<!-- PHASE3_STEP4_START -->"
end = "<!-- PHASE3_STEP4_END -->"

block = f"""{start}
### Phase3 Step4 单命令回归证据

- 运行时间：{datetime.now(timezone.utc).isoformat()}
- 后端端口：`{port}`
- attempt_id：error={attempt_error} skip={attempt_skip} slow={attempt_slow}

#### 最新一次运行

**openapi**
```
{openapi_status}
```

**diagnosis（attempt_id={attempt_error}）**
```
{snip_error}
```

**diagnosis（attempt_id={attempt_skip}）**
```
{snip_skip}
```

**diagnosis（attempt_id={attempt_slow}）**
```
{snip_slow}
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
echo "SUMMARY: ATTEMPT_ERROR=${ATTEMPT_ERROR} DIAG=E_ERROR_OCCURRED"
echo "SUMMARY: ATTEMPT_SKIP=${ATTEMPT_SKIP} DIAG=E_STEP_SKIPPED"
echo "SUMMARY: ATTEMPT_SLOW=${ATTEMPT_SLOW} DIAG=E_TOO_SLOW"
