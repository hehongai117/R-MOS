#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"
REPORT_PATH="${REPO_ROOT}/docs/testing/TEST_REPORT.md"
LOG_DIR="${REPO_ROOT}/logs"
BACKEND_LOG="${LOG_DIR}/phase1-e2e-backend.log"

export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/postgres"
export NO_PROXY="127.0.0.1,localhost"

# 避免本机代理干扰本地回环地址请求
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

mkdir -p "${LOG_DIR}"

if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
  echo "未找到可用的虚拟环境：${BACKEND_DIR}/.venv"
  echo "请先创建并安装依赖后再运行本脚本"
  exit 1
fi

# shellcheck disable=SC1091
source "${BACKEND_DIR}/.venv/bin/activate"

CURL_BASE=(
  curl
  --silent
  --show-error
  --noproxy
  "${NO_PROXY}"
)

BACKEND_STARTED_BY_SCRIPT=0
BACKEND_PID=""

cleanup() {
  if [[ "${BACKEND_STARTED_BY_SCRIPT}" -eq 1 && -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

curl_request() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local response http_status body

  if [[ -n "${data}" ]]; then
    response="$("${CURL_BASE[@]}" \
      --request "${method}" \
      --header "Content-Type: application/json" \
      --data "${data}" \
      --write-out $'\n%{http_code}' \
      "${url}")"
  else
    response="$("${CURL_BASE[@]}" \
      --request "${method}" \
      --write-out $'\n%{http_code}' \
      "${url}")"
  fi

  http_status="$(printf "%s" "${response}" | tail -n1)"
  body="$(printf "%s" "${response}" | sed '$d')"

  CURL_STATUS="${http_status}"
  CURL_BODY="${body}"
}

expect_status() {
  local expected="$1"
  if [[ "${CURL_STATUS}" != "${expected}" ]]; then
    echo "请求失败：期望状态码 ${expected}，实际 ${CURL_STATUS}"
    echo "响应体：${CURL_BODY}"
    exit 1
  fi
}

backend_is_ready() {
  curl_request "GET" "http://127.0.0.1:8000/api/v1/health"
  [[ "${CURL_STATUS}" == "200" ]]
}

start_backend_if_needed() {
  if backend_is_ready; then
    echo "检测到后端已在运行：127.0.0.1:8000"
    return
  fi

  echo "未检测到后端服务，尝试由脚本启动 uvicorn..."
  echo "提示：若 8000 端口出现 EPERM，请改用 18000 手动启动后端，并在 TEST_REPORT 记录实际端口。"
  (
    cd "${BACKEND_DIR}"
    .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >"${BACKEND_LOG}" 2>&1 &
    BACKEND_PID="$!"
    echo "${BACKEND_PID}" >"${LOG_DIR}/phase1-e2e-backend.pid"
  )
  BACKEND_STARTED_BY_SCRIPT=1

  local attempts=20
  local i
  for i in $(seq 1 "${attempts}"); do
    if backend_is_ready; then
      echo "后端启动成功"
      return
    fi
    sleep 0.5
  done

  echo "后端启动失败，请查看日志：${BACKEND_LOG}"
  if [[ -f "${BACKEND_LOG}" ]]; then
    tail -n 40 "${BACKEND_LOG}" || true
  fi
  exit 1
}

parse_seed_value() {
  local seed_output="$1"
  local pattern="$2"
  printf "%s" "${seed_output}" | sed -nE "${pattern}" | head -n1
}

echo "步骤1/8：执行数据库迁移"
(
  cd "${BACKEND_DIR}"
  .venv/bin/alembic -c alembic.ini upgrade head
)

echo "步骤2/8：生成教学演示数据"
seed_output="$(
  cd "${BACKEND_DIR}" && .venv/bin/python scripts/seed_teaching_demo.py --reset
)"
printf "%s\n" "${seed_output}"

assignment_id="$(parse_seed_value "${seed_output}" 's/.*作业：.*\(([0-9]+)\).*/\1/p')"
student_id="$(parse_seed_value "${seed_output}" 's/.*内部编号 ([0-9]+).*/\1/p')"
task_id="$(parse_seed_value "${seed_output}" 's/.*任务：.*\(([0-9]+)\).*/\1/p')"

if [[ -z "${assignment_id}" || -z "${student_id}" || -z "${task_id}" ]]; then
  echo "无法从 seed 输出解析出 assignment_id / student_id / task_id"
  echo "请检查 scripts/seed_teaching_demo.py 的输出格式是否发生变化"
  exit 1
fi

echo "步骤3/8：清理执行痕迹并重置任务基线"
TASK_ID="${task_id}" .venv/bin/python - <<'PY'
import asyncio
import os
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.event import Event
from app.models.snapshot import Snapshot
from app.models.task import Task
from app.models.teaching import AssignmentAttempt


async def main() -> None:
    task_id = int(os.environ["TASK_ID"])
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        task = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if task is None:
            raise SystemExit(f"未找到 task_id={task_id}，无法继续")

        # 避免 EvidenceEngine._find_attempt 因多条未放弃尝试而崩溃
        await session.execute(
            update(AssignmentAttempt)
            .where(AssignmentAttempt.task_id == task_id, AssignmentAttempt.status != "abandoned")
            .values(status="abandoned", abandoned_at=datetime.utcnow())
        )

        # 清理执行域痕迹，确保步骤可重复执行
        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Snapshot).where(Snapshot.task_id == task_id))

        # 重置任务状态，确保 start_task 不会因状态不符而失败
        task.status = "pending"
        task.current_step_index = 0
        task.started_at = None
        task.completed_at = None
        task.final_score = None
        task.is_passed = None

        await session.commit()

    await engine.dispose()


asyncio.run(main())
PY

echo "步骤4/8：确保后端服务可用（真实 HTTP：127.0.0.1:8000）"
start_backend_if_needed
curl_request "GET" "http://127.0.0.1:8000/api/v1/health"
expect_status "200"
health_json="${CURL_BODY}"

echo "步骤5/8：创建尝试并获取 task_id"
attempt_payload="$(printf '{"studentId": %s, "taskId": %s}' "${student_id}" "${task_id}")"
curl_request "POST" "http://127.0.0.1:8000/api/v1/assignments/${assignment_id}/attempts" "${attempt_payload}"
expect_status "201"
attempt_json="${CURL_BODY}"

attempt_id="$(.venv/bin/python - <<'PY' "${attempt_json}"
import json
import sys
data = json.loads(sys.argv[1])
print(data.get("id", ""))
PY
)"

if [[ -z "${attempt_id}" ]]; then
  echo "创建 attempt 成功但未能解析出 attempt_id"
  echo "响应体：${attempt_json}"
  exit 1
fi

curl_request "GET" "http://127.0.0.1:8000/api/v1/attempts/${attempt_id}"
expect_status "200"
attempt_detail_json="${CURL_BODY}"

task_id_from_attempt="$(.venv/bin/python - <<'PY' "${attempt_detail_json}"
import json
import sys
data = json.loads(sys.argv[1])
task_id = data.get("taskId") or data.get("task_id")
print("" if task_id is None else task_id)
PY
)"

if [[ -n "${task_id_from_attempt}" ]]; then
  task_id="${task_id_from_attempt}"
else
  echo "attempt.task_id 为空，无法继续。"
  echo "建议检查：/api/v1/assignments/${assignment_id}/attempts 的入参是否包含 taskId"
  echo "响应体：${attempt_detail_json}"
  exit 1
fi

echo "步骤6/8：启动任务并执行至少两步"
curl_request "POST" "http://127.0.0.1:8000/api/v1/tasks/${task_id}/start"
expect_status "200"
task_start_json="${CURL_BODY}"

curl_request "GET" "http://127.0.0.1:8000/api/v1/tasks/${task_id}"
expect_status "200"
task_json="${CURL_BODY}"

sop_id="$(.venv/bin/python - <<'PY' "${task_json}"
import json
import sys
data = json.loads(sys.argv[1])
print(data.get("sop_id", ""))
PY
)"

if [[ -z "${sop_id}" ]]; then
  echo "未能从 /api/v1/tasks/${task_id} 解析出 sop_id"
  echo "响应体：${task_json}"
  exit 1
fi

curl_request "GET" "http://127.0.0.1:8000/api/v1/sops/${sop_id}"
expect_status "200"
sop_json="${CURL_BODY}"

step_lines=()
while IFS= read -r line; do
  step_lines+=("${line}")
done < <(.venv/bin/python - <<'PY' "${sop_json}"
import json
import sys
data = json.loads(sys.argv[1])
steps = sorted(data.get("steps", []), key=lambda s: s.get("step_index", 0))
if len(steps) < 2:
    raise SystemExit("SOP 步骤少于 2，无法满足验收要求")
for step in steps[:2]:
    idx = step["step_index"]
    action = step["expected_action"]
    print(f"{idx} {action}")
PY
)

if [[ "${#step_lines[@]}" -lt 2 ]]; then
  echo "未能获取到至少两个可执行步骤"
  exit 1
fi

step_responses=()
for line in "${step_lines[@]}"; do
  step_index="${line%% *}"
  action="${line#* }"
  step_payload="$(printf '{"step_index": %s, "action": "%s"}' "${step_index}" "${action}")"
  curl_request "POST" "http://127.0.0.1:8000/api/v1/tasks/${task_id}/step" "${step_payload}"
  expect_status "200"
  step_responses+=("${CURL_BODY}")
done

echo "步骤7/8：尝试触发报告接口（兼容 GET/POST 差异）"
curl_request "POST" "http://127.0.0.1:8000/api/v1/tasks/${task_id}/report" "{}"
if [[ "${CURL_STATUS}" == "200" ]]; then
  task_report_json="${CURL_BODY}"
elif [[ "${CURL_STATUS}" == "405" ]]; then
  curl_request "GET" "http://127.0.0.1:8000/api/v1/tasks/${task_id}/report"
  expect_status "200"
  task_report_json="${CURL_BODY}"
else
  echo "报告接口返回异常状态码：${CURL_STATUS}"
  echo "响应体：${CURL_BODY}"
  exit 1
fi

echo "步骤8/8：验证 evidence 摘要字段"
curl_request "GET" "http://127.0.0.1:8000/api/v1/attempts/${attempt_id}/evidence"
expect_status "200"
evidence_json="${CURL_BODY}"

.venv/bin/python - <<'PY' "${evidence_json}"
import json
import sys

data = json.loads(sys.argv[1])
summary = data.get("summary") or {}
required = ["total_steps", "error_count", "skip_count", "duration_ms"]
missing = [key for key in required if key not in summary]
if missing:
    raise SystemExit(f"evidence.summary 缺少关键字段：{missing}")
PY

health_pretty="$(.venv/bin/python -m json.tool <<<"${health_json}")"
attempt_pretty="$(.venv/bin/python -m json.tool <<<"${attempt_detail_json}")"
evidence_pretty="$(.venv/bin/python -m json.tool <<<"${evidence_json}")"

timestamp="$(date -u "+%Y-%m-%dT%H:%M:%SZ")"
commit_hash="$(git -C "${REPO_ROOT}" rev-parse --short HEAD)"

{
  echo ""
  echo "### Phase1 P0 自动验收（${timestamp}）"
  echo ""
  echo "- 提交：\`${commit_hash}\`"
  echo "- 命令：\`cd ${BACKEND_DIR} && bash scripts/run_phase1_e2e.sh\`"
  echo "- 关键 ID：assignment_id=\`${assignment_id}\`，student_id=\`${student_id}\`，task_id=\`${task_id}\`，attempt_id=\`${attempt_id}\`"
  echo ""
  echo "**health**"
  echo '```json'
  echo "${health_pretty}"
  echo '```'
  echo ""
  echo "**attempt**"
  echo '```json'
  echo "${attempt_pretty}"
  echo '```'
  echo ""
  echo "**evidence**"
  echo '```json'
  echo "${evidence_pretty}"
  echo '```'
} >>"${REPORT_PATH}"

echo "Phase1 P0 自动验收完成"
echo "报告已追加到：${REPORT_PATH}"
