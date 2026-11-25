#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
fi

echo "Starting FastAPI backend on http://127.0.0.1:8000 ..."
(cd "$BACKEND_DIR" && "$PYTHON_BIN" -m uvicorn main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

cleanup() {
  echo "Stopping FastAPI backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

if command -v npm >/dev/null 2>&1; then
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Installing frontend npm packages..."
    (cd "$FRONTEND_DIR" && npm install)
  fi
  echo "Starting Vite React dashboard on http://localhost:5173 ..."
  (cd "$FRONTEND_DIR" && npm run dev)
else
  echo "npm not found. Backend API running at http://127.0.0.1:8000"
  wait "$BACKEND_PID"
fi

