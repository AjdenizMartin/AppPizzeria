# Production Runbook (Railway + Cloudflare)

This runbook is the source of truth for real client go-live.

## 1) Environments

Create and maintain **two Railway projects**:

- `pizzeria-staging`
- `pizzeria-prod`

Rules:

- Never share database between environments.
- Never share secrets between environments.
- Promote only validated changes from staging to production.

## 2) Railway Services

For each environment:

1. Create app service from this repository (Dockerfile build).
2. Add PostgreSQL service.
3. Set environment variables (see `.env.production.example` and `ops/deploy/required_env.md`).
4. Keep `AUTO_CREATE_TABLES=false`.
5. Confirm healthcheck path is `/health`.

## 3) Database Migration Policy

Run migrations manually on each environment:

```bash
alembic upgrade head
```

Order of execution:

1. staging
2. production

Validation:

```bash
alembic current
alembic heads
```

Expected: current revision matches latest head.

## 4) Domain and Network (Cloudflare)

Use Cloudflare-managed DNS and TLS:

- `staging.<your-domain>` -> staging Railway app
- `app.<your-domain>` -> production Railway app

Apply:

- SSL/TLS mode: Full (strict)
- Always Use HTTPS: ON
- Automatic HTTPS Rewrites: ON
- WAF managed rules: ON
- Bot Fight Mode (or equivalent): ON

Set strict app CORS:

- staging: `CORS_ORIGINS=https://staging.<your-domain>`
- prod: `CORS_ORIGINS=https://app.<your-domain>`

## 5) Stripe and Email

Stripe:

- staging uses test keys
- production uses live keys
- webhook endpoint per environment:
  - `https://staging.<your-domain>/stripe/webhook`
  - `https://app.<your-domain>/stripe/webhook`
- event: `checkout.session.completed`

Email (SMTP):

- Use transactional provider account.
- Use sender under client domain.
- SPF, DKIM, DMARC must be configured before go-live.

## 6) Print Agent (Day 1)

Install and enable on the restaurant Linux host:

```bash
./ops/systemd/install_print_agent_service.sh /opt/pizzeria-app restaurant
```

Set `/etc/pizzeria-print-agent.env` with production values:

- `PRINT_AGENT_API_URL=https://app.<your-domain>`
- `PRINT_AGENT_KEY=<production print agent key>`
- unique `PRINT_AGENT_ID` per device

Verify:

```bash
sudo systemctl status pizzeria-print-agent.service
sudo journalctl -u pizzeria-print-agent.service -f
```

## 7) Smoke and Release Validation

After each deploy:

```bash
./scripts/smoke_railway.sh https://<env-domain>
```

Must pass:

- `/health`
- `/metrics`
- `/ops/status`
- `/metrics/prometheus`

Then execute business validations:

1. register/login
2. cash checkout + confirmation email
3. card checkout + Stripe webhook + confirmation email
4. admin order flow and reprint
5. physical print from kitchen device

## 8) Go-Live Window

During production go-live:

1. Freeze non-critical changes.
2. Deploy approved revision.
3. Run smoke checks.
4. Run one live order test end-to-end.
5. Monitor logs and `/ops/status` for 24-48h.

## 9) Rollback

If incident happens:

1. Roll back Railway service to previous stable deployment.
2. Keep database unchanged unless a migration-specific rollback was pre-validated.
3. If payment-related issue, temporarily disable Stripe webhook endpoint.
4. Keep print agent running if backend API is healthy.

See: `ops/deploy/rollback_runbook.md`.
