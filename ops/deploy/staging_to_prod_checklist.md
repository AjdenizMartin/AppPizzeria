# Staging -> Production Checklist

## A) Staging readiness

- [ ] Latest code deployed to `pizzeria-staging`
- [ ] `alembic upgrade head` executed in staging
- [ ] `./scripts/smoke_railway.sh https://staging.<your-domain>` passed
- [ ] Stripe test checkout confirmed
- [ ] Stripe staging webhook confirmed (`checkout.session.completed`)
- [ ] SMTP staging email delivered
- [ ] Print agent staging/prod-like device test passed
- [ ] Admin flow test passed (status transitions + reprint)

## B) Production preflight

- [ ] Production env vars validated with `./scripts/validate_env.sh production`
- [ ] DNS records in Cloudflare verified
- [ ] SSL Full (strict) confirmed
- [ ] Railway healthcheck passing before release
- [ ] Rollback owner assigned
- [ ] Go-live window and observers assigned

## C) Production release

- [ ] Deploy approved commit to `pizzeria-prod`
- [ ] `alembic upgrade head` executed in production
- [ ] `./scripts/smoke_railway.sh https://app.<your-domain>` passed
- [ ] Stripe live webhook active and verified
- [ ] Live email delivery verified
- [ ] Physical print flow verified on restaurant host

## D) Post-release (24-48h)

- [ ] Monitor Railway logs for 5xx and webhook errors
- [ ] Monitor `/ops/status` and `/metrics`
- [ ] Capture first incident report if any anomaly appears
- [ ] Confirm stable order throughput with client
