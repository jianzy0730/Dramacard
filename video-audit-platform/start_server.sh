#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

FRONTEND_PORT="${FRONTEND_PORT:-8000}"
BACKEND_PORT="${VIDEO_AUDIT_PORT:-5000}"
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "--> 清理旧进程"
pkill -f "python -m video_audit_platform" || true
pkill -f "python appp_api.py" || true
pkill -f "python3 -m http.server ${FRONTEND_PORT}" || true
sleep 1

echo "--> 启动后端 http://localhost:${BACKEND_PORT}"
python -m video_audit_platform &
BACKEND_PID=$!

echo "--> 启动前端 ${FRONTEND_URL}"
python3 -m http.server "${FRONTEND_PORT}" &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "--> 停止服务"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

sleep 2
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${FRONTEND_URL}" >/dev/null 2>&1 || true
fi

echo "--> 后端 PID: ${BACKEND_PID}"
echo "--> 前端 PID: ${FRONTEND_PID}"
echo "--> 浏览器地址: ${FRONTEND_URL}"

wait
