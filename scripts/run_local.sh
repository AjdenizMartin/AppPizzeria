#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
FRONTEND_DIST_DIR="${FRONTEND_DIST_DIR:-$ROOT_DIR/frontend-react/dist}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python no encontrado en: $PYTHON_BIN"
  echo "Activa tu entorno virtual o define PYTHON_BIN."
  exit 1
fi

if [[ ! -d "$FRONTEND_DIST_DIR" || ! -f "$FRONTEND_DIST_DIR/index.html" ]]; then
  echo "No se encontró build de frontend en: $FRONTEND_DIST_DIR"
  echo "Genera el build con:"
  echo "  cd frontend-react && npm ci && npm run build"
  exit 1
fi

UVICORN_ARGS=(app.main:app --host "$HOST" --port "$PORT")
if [[ "$RELOAD" == "true" ]]; then
  UVICORN_ARGS+=(--reload)
fi

echo "Levantando app local..."
echo "Backend/API: http://$HOST:$PORT"
echo "Cliente:     http://$HOST:$PORT/"
echo "Admin:       http://$HOST:$PORT/admin"
echo

exec "$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}"
