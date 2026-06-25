#!/usr/bin/env bash
# 测量 Phase 3 待重构后端端点的行覆盖率
set -euo pipefail
cd "$(dirname "$0")/.."
venv/bin/python -m pytest tests/ -q -o addopts='' -p no:warnings \
  --cov=app/api/v1/endpoints \
  --cov-report=term-missing \
  "$@" 2>&1 | grep -E 'endpoints/(agent|training|teaching)\.py|TOTAL|passed|skipped'
