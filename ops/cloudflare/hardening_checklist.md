# Cloudflare Hardening Checklist

## DNS and TLS

- [ ] `app.<your-domain>` points to Railway production target
- [ ] `staging.<your-domain>` points to Railway staging target
- [ ] SSL mode set to **Full (strict)**
- [ ] Always Use HTTPS enabled
- [ ] Automatic HTTPS Rewrites enabled

## Security

- [ ] WAF managed rules enabled
- [ ] Bot protection enabled
- [ ] Rate limiting rule for high-risk paths (auth, checkout, webhook)
- [ ] Optional country/IP allow-list for admin routes if needed

## Reliability

- [ ] Health check endpoint (`/health`) excluded from aggressive blocking
- [ ] Cache rules do not cache API JSON responses
- [ ] React assets at `/assets` and backend static files at `/static` can be cached safely

## Verification

- [ ] Browser validates lock icon and correct certificate
- [ ] API calls from frontend succeed (no CORS mismatch)
- [ ] Stripe webhook reaches backend without Cloudflare blocking
