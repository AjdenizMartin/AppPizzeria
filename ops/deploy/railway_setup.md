# Railway Setup (Staging + Production)

## 1) Create projects

Create two Railway projects:

- `pizzeria-staging`
- `pizzeria-prod`

Each project must contain:

- App service built from this repo Dockerfile
- Dedicated PostgreSQL service

## 2) Variable loading

- Staging: load values from `.env.staging.example`
- Production: load values from `.env.production.example`

Then run:

```bash
./scripts/validate_env.sh staging
./scripts/validate_env.sh production
```

## 3) Deploy command

App starts via Docker CMD:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

No extra start command required.

## 4) Migrations

After each deploy:

```bash
alembic upgrade head
```

Verify:

```bash
alembic current
```

## 5) Smoke checks

```bash
./scripts/smoke_railway.sh https://staging.<your-domain>
./scripts/smoke_railway.sh https://app.<your-domain>
```
