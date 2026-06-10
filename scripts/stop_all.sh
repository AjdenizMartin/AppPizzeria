#!/usr/bin/env bash
set -euo pipefail

echo "=== Pizzeria App: Stop helper ==="

echo
echo "[1/2] Stopping local uvicorn processes for this project..."
if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  pkill -f "uvicorn app.main:app" || true
  echo "Stopped uvicorn app.main:app"
else
  echo "No uvicorn app.main:app process found."
fi

echo
echo "[2/2] Stopping print agent service (if available)..."
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q "^pizzeria-print-agent.service"; then
    if systemctl is-active --quiet pizzeria-print-agent; then
      sudo systemctl stop pizzeria-print-agent
      echo "Stopped pizzeria-print-agent service."
    else
      echo "pizzeria-print-agent service is already stopped."
    fi
  else
    echo "pizzeria-print-agent.service not installed on this machine."
  fi
else
  echo "systemctl not found. Skipping service stop."
fi

echo
echo "Done."
