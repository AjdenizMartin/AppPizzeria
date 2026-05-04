#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${1:-./backups}"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/pizzeria_${TS}.dump"

echo "Creating backup: $OUT_FILE"
pg_dump --format=custom --no-owner --no-privileges --dbname="$DATABASE_URL" --file="$OUT_FILE"

echo "Backup completed: $OUT_FILE"
