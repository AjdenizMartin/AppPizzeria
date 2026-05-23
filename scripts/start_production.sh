#!/usr/bin/env sh
set -eu

echo "[start] running Alembic migrations..."
alembic upgrade head

echo "[start] starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
