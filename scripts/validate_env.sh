#!/usr/bin/env bash

set -euo pipefail

MODE="${1:-production}"

if [[ "$MODE" != "production" && "$MODE" != "staging" ]]; then
  echo "Usage: $0 [staging|production]"
  exit 1
fi

missing=0

required_vars=(
  APP_ENV
  DATABASE_URL
  AUTO_CREATE_TABLES
  SECRET_KEY
  ACCESS_TOKEN_EXPIRE_MINUTES
  FRONTEND_BASE_URL
  CORS_ORIGINS
  ADMIN_EMAILS
  PRINT_AGENT_KEY
  PRINT_JOB_MAX_ATTEMPTS
  STRIPE_KEY
  STRIPE_WEBHOOK_SECRET
  SMTP_HOST
  SMTP_PORT
  SMTP_USER
  SMTP_PASSWORD
  SMTP_FROM_EMAIL
  SMTP_USE_TLS
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "[FAIL] Missing: $var"
    missing=1
  else
    echo "[OK] $var"
  fi
done

if [[ "${AUTO_CREATE_TABLES:-}" != "false" ]]; then
  echo "[FAIL] AUTO_CREATE_TABLES must be 'false' in $MODE"
  missing=1
fi

if [[ "$MODE" == "production" ]]; then
  if [[ "${STRIPE_KEY:-}" != sk_live_* ]]; then
    echo "[WARN] STRIPE_KEY does not look like a live key (sk_live_*)"
  fi
fi

if [[ "$MODE" == "staging" ]]; then
  if [[ "${STRIPE_KEY:-}" != sk_test_* ]]; then
    echo "[WARN] STRIPE_KEY does not look like a test key (sk_test_*)"
  fi
fi

if [[ "$missing" -ne 0 ]]; then
  echo "\nEnvironment validation failed."
  exit 1
fi

echo "\nEnvironment validation passed for $MODE."
