# Required Environment Variables (Staging + Production)

Use different values per environment.

## Core

- `APP_ENV` (`staging` or `production`)
- `DATABASE_URL` (PostgreSQL)
- `AUTO_CREATE_TABLES=false`
- `SECRET_KEY` (high entropy)
- `ACCESS_TOKEN_EXPIRE_MINUTES`

## Frontend + CORS

- `FRONTEND_BASE_URL`
- `CORS_ORIGINS`

## Admin and operations

- `ADMIN_EMAILS`
- `PRINT_AGENT_KEY`
- `PRINT_JOB_MAX_ATTEMPTS`

## Stripe

- `STRIPE_KEY`
- `STRIPE_WEBHOOK_SECRET`

## SMTP

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_USE_TLS`

## Observability thresholds

- `PRINT_FAILURE_ALERT_THRESHOLD`
- `ERROR_RATE_ALERT_THRESHOLD`
- `CRITICAL_EVENTS_HISTORY_LIMIT`
