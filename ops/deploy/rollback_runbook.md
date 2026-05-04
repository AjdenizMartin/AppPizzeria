# Rollback Runbook

Use this runbook when production incident affects ordering, payments, or print operations.

## 1) Trigger conditions

Execute rollback if one or more are true:

- sustained 5xx errors
- payment confirmation mismatch (orders not moving to `paid`)
- severe API latency or repeated healthcheck failures
- broken order write path

## 2) Immediate containment

1. Announce incident start and owner.
2. If payment path is impacted, temporarily disable Stripe webhook endpoint in Stripe dashboard.
3. Keep evidence: save logs, timestamps, and impacted order IDs.

## 3) Application rollback

1. In Railway production service, redeploy last known good deployment.
2. Confirm `/health` returns 200.
3. Execute smoke checks:

```bash
./scripts/smoke_railway.sh https://app.<your-domain>
```

## 4) Database safety

- Do not perform destructive DB actions during first response.
- Only run migration downgrade if the exact downgrade path was previously tested.
- Prefer forward fix over emergency downgrade unless data integrity is at risk.

## 5) Recovery validation

Confirm:

- register/login works
- cash checkout works
- card checkout + webhook works
- confirmation emails sent
- print queue and print agent resume normal behavior

## 6) Closure

1. Re-enable Stripe webhook if disabled.
2. Document root cause and permanent fix.
3. Add regression test or runbook improvement.
