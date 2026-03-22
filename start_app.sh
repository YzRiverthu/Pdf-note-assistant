#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8765}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

detect_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  echo "未找到可用的 Python 解释器，请先安装 Python 3.10+。" >&2
  exit 1
}

PYTHON_BIN="${PYTHON_BIN:-$(detect_python)}"

is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

print_port_hint() {
  local name="$1"
  local port="$2"
  echo "${name} 端口 ${port} 已被占用。"
  echo "可选处理方式："
  echo "1. 关闭占用进程：lsof -nP -iTCP:${port} -sTCP:LISTEN"
  echo "2. 改用其他端口，例如：BACKEND_PORT=8865 FRONTEND_PORT=8081 bash start_app.sh"
}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

if is_port_in_use "${BACKEND_PORT}"; then
  print_port_hint "后端" "${BACKEND_PORT}"
  exit 1
fi

if is_port_in_use "${FRONTEND_PORT}"; then
  print_port_hint "前端" "${FRONTEND_PORT}"
  exit 1
fi

echo "启动 OCR 后端: http://${BACKEND_HOST}:${BACKEND_PORT}"
"${PYTHON_BIN}" -m uvicorn backend.paddle_ocr_server:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" &
BACKEND_PID=$!

echo "启动前端静态服务: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
"${PYTHON_BIN}" -m http.server "${FRONTEND_PORT}" --bind "${FRONTEND_HOST}" --directory frontend &
FRONTEND_PID=$!

echo
echo "前端地址: http://${FRONTEND_HOST}:${FRONTEND_PORT}/"
echo "OCR 接口: http://${BACKEND_HOST}:${BACKEND_PORT}/ocr"
echo
echo "按 Ctrl+C 停止全部服务"

wait
