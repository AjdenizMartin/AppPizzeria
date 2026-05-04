#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python no encontrado en $PYTHON_BIN"
  echo "Activa tu entorno o define PYTHON_BIN antes de ejecutar."
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared no está instalado."
  echo "Instálalo con: brew install cloudflared"
  exit 1
fi

echo "Iniciando backend en http://$HOST:$PORT ..."
"$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload >/tmp/pizzeria_uvicorn.log 2>&1 &
UVICORN_PID=$!

cleanup() {
  if ps -p "$UVICORN_PID" >/dev/null 2>&1; then
    kill "$UVICORN_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

sleep 2

echo
echo "Backend y frontend disponibles localmente en:"
echo "http://$HOST:$PORT/"
echo
echo "Abriendo túnel público (Cloudflare)..."
echo "Comparte la URL https://*.trycloudflare.com que aparecerá abajo."
echo "Pulsa Ctrl+C para cerrar túnel y servidor."
echo

cloudflared tunnel --url "http://$HOST:$PORT"
