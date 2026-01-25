#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$ROOT_DIR/.venv/bin"

if [[ -x "$VENV_BIN/uvicorn" ]]; then
  UVICORN="$VENV_BIN/uvicorn"
else
  UVICORN="uvicorn"
fi

export PYTHONPATH="$ROOT_DIR"
exec "$UVICORN" main:app --reload
