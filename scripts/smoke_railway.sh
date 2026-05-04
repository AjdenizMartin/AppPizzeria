#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <base-url> <admin-jwt-token>"
  echo "Example: $0 https://my-app.up.railway.app eyJhbGciOi..."
  exit 1
fi

BASE_URL="${1%/}"
ADMIN_TOKEN="$2"

echo "Running smoke checks against: ${BASE_URL}"

check_json_endpoint() {
  local path="$1"
  local label="$2"
  local code
  code=$(curl -sS -o /tmp/pizzeria_smoke_response.json -w "%{http_code}" "${BASE_URL}${path}")
  if [ "$code" != "200" ]; then
    echo "[FAIL] ${label} (${path}) returned ${code}"
    cat /tmp/pizzeria_smoke_response.json
    exit 1
  fi
  echo "[OK] ${label} (${path})"
}

check_admin_json_endpoint() {
  local path="$1"
  local label="$2"
  local code
  code=$(curl -sS -o /tmp/pizzeria_smoke_response.json -w "%{http_code}" \
    "${BASE_URL}${path}" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")
  if [ "$code" != "200" ]; then
    echo "[FAIL] ${label} (${path}) returned ${code}"
    cat /tmp/pizzeria_smoke_response.json
    exit 1
  fi
  echo "[OK] ${label} (${path})"
}

check_json_endpoint "/health" "Health"
check_admin_json_endpoint "/metrics" "Metrics JSON"
check_admin_json_endpoint "/ops/status" "Ops status"

prom_code=$(curl -sS -o /tmp/pizzeria_smoke_prom.txt -w "%{http_code}" \
  "${BASE_URL}/metrics/prometheus" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [ "$prom_code" != "200" ]; then
  echo "[FAIL] Prometheus metrics returned ${prom_code}"
  cat /tmp/pizzeria_smoke_prom.txt
  exit 1
fi

if ! grep -q "app_requests_total" /tmp/pizzeria_smoke_prom.txt; then
  echo "[FAIL] Prometheus payload missing app_requests_total"
  cat /tmp/pizzeria_smoke_prom.txt
  exit 1
fi
echo "[OK] Prometheus metrics"

reset_code=$(curl -sS -o /tmp/pizzeria_smoke_reset.json -w "%{http_code}" \
  -X POST "${BASE_URL}/admin/metrics/reset" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [ "$reset_code" != "200" ]; then
  echo "[FAIL] Admin metrics reset returned ${reset_code}"
  cat /tmp/pizzeria_smoke_reset.json
  exit 1
fi
echo "[OK] Admin metrics reset"

echo "Smoke checks passed."
