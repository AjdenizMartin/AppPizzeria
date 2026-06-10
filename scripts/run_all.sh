#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "=== Pizzeria App: Daily run helper ==="
echo "Root: $ROOT_DIR"

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "ERROR: .venv not found. Run ./scripts/install_all_in_one.sh first."
  exit 1
fi

source "$ROOT_DIR/.venv/bin/activate"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "WARN: .env not found in project root. App may fail to start."
fi

echo
echo "[1/4] Running migrations..."
alembic upgrade head

echo
echo "[2/4] Checking print agent service..."
if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet pizzeria-print-agent; then
    echo "OK: pizzeria-print-agent is active."
  else
    echo "WARN: pizzeria-print-agent is not active."
    echo "      Start it with: sudo systemctl start pizzeria-print-agent"
  fi
else
  echo "INFO: systemctl not found on this machine. Skipping service check."
fi

echo
echo "[3/4] Frontend build check..."
if [[ -d "$ROOT_DIR/frontend-react/dist" ]]; then
  echo "OK: frontend-react/dist exists."
else
  echo "WARN: frontend-react/dist missing."
  echo "      Build it with:"
  echo "      cd frontend-react && npm ci && npm run build"
fi

echo
echo "[4/4] Starting backend..."
echo "URL: http://127.0.0.1:${PORT}"
echo "Admin: http://127.0.0.1:${PORT}/admin"
echo

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
