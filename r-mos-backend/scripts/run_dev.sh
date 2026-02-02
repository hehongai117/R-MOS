#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$ROOT_DIR/.venv/bin"
LOG_DIR="$ROOT_DIR/logs"
HOST="127.0.0.1"
PRIMARY_PORT="8000"
FALLBACK_PORT="18000"

if [[ -x "$VENV_BIN/uvicorn" ]]; then
  UVICORN="$VENV_BIN/uvicorn"
else
  UVICORN="uvicorn"
fi

export PYTHONPATH="$ROOT_DIR"
mkdir -p "$LOG_DIR"

start_backend() {
  local port="$1"
  local log_file="$LOG_DIR/dev-backend-${port}.log"
  echo "启动后端：${HOST}:${port}"
  "$UVICORN" main:app --reload --host "$HOST" --port "$port" >>"$log_file" 2>&1 &
  local pid=$!
  sleep 1
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "BACKEND_PORT=${port}"
    wait "$pid"
    return $?
  fi
  if grep -qE "Operation not permitted" "$log_file"; then
    echo "端口绑定失败（EPERM），切换端口 ${FALLBACK_PORT}" >&2
    return 2
  fi
  echo "后端启动失败，请查看日志：${log_file}" >&2
  return 1
}

start_backend "$PRIMARY_PORT"
status=$?
if [ "$status" -eq 2 ]; then
  start_backend "$FALLBACK_PORT"
  exit $?
fi
exit "$status"
