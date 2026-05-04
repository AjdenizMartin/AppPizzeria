# Pizzeria App

Aplicacion de pedidos para pizzeria con backend FastAPI, frontend React, Stripe y cola de impresion.

## Frontend oficial

El frontend comercial y mantenido es `frontend-react/`.

- React es la unica interfaz activa del proyecto.
- El backend puede servir el build de React si existe `frontend-react/dist`.
- El frontend vanilla anterior ya no forma parte del flujo oficial.

## Stack

- Backend: FastAPI + SQLAlchemy
- Base de datos local por defecto: SQLite
- Frontend: React + TypeScript + Vite
- Pagos: Stripe Checkout + webhook
- Impresion: `print_agent`

## Variables base

```env
DATABASE_URL=sqlite:///./pizzeria.db
STRIPE_KEY=sk_test_replace_me
STRIPE_WEBHOOK_SECRET=whsec_replace_me_optional
SECRET_KEY=change-me-in-production
ADMIN_EMAILS=owner@example.com
FRONTEND_BASE_URL=http://127.0.0.1:5173
ACCESS_TOKEN_EXPIRE_MINUTES=120
PRINT_AGENT_KEY=shared_secret_for_printer_agent
PRINT_JOB_MAX_ATTEMPTS=3
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## Desarrollo local

### Opcion A: React + backend separados

Terminal 1:

```bash
python -m uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd frontend-react
npm install
npm run dev
```

URLs:

- Frontend cliente: `http://127.0.0.1:5173`
- Panel admin: `http://127.0.0.1:5173/admin`
- API backend: `http://127.0.0.1:8000`

`.env` del backend:

```env
FRONTEND_BASE_URL=http://127.0.0.1:5173
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Si quieres fijar la API desde Vite, usa `frontend-react/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

### Opcion B: backend sirviendo el build de React

```bash
cd frontend-react
npm install
npm run build
cd ..
python -m uvicorn app.main:app --reload
```

URLs:

- Frontend cliente: `http://127.0.0.1:8000/`
- Panel admin: `http://127.0.0.1:8000/admin`

En este modo el backend sirve `frontend-react/dist` como SPA.

## Stripe

- Checkout: `POST /create-checkout-session`
- Webhook: `POST /stripe/webhook`
- Rutas React usadas por Stripe:
  - success: `/order-confirmation/:orderId?method=card`
  - cancel: `/checkout`

## Calidad

```bash
cd frontend-react && npm install && npm run build
cd ..
.venv/bin/pytest -q
.venv/bin/ruff check app tests
```

## Produccion (Railway + PostgreSQL)

- Usar `APP_ENV=production`.
- Usar `DATABASE_URL` de PostgreSQL (no SQLite).
- Usar migraciones Alembic: no depender de `AUTO_CREATE_TABLES`.
- Configurar dominio real en `FRONTEND_BASE_URL` y `CORS_ORIGINS` restringido.

Variables minimas:

```env
APP_ENV=production
DATABASE_URL=postgresql://...
AUTO_CREATE_TABLES=false
SECRET_KEY=<strong-random-secret>
STRIPE_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_BASE_URL=https://app.tudominio.com
CORS_ORIGINS=https://app.tudominio.com
ADMIN_EMAILS=owner@tudominio.com
PRINT_AGENT_KEY=<strong-random-secret>
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=orders@tudominio.com
SMTP_USE_TLS=true
```

Checklist predeploy:

```bash
python scripts/validate_predeploy.py
alembic upgrade head
```

Railway:

1. Crear servicio backend y vincular PostgreSQL.
2. Configurar variables del bloque anterior.
3. Build command: `pip install .`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Ejecutar migraciones antes de go-live: `alembic upgrade head`.
6. Stripe webhook (produccion): `https://app.tudominio.com/stripe/webhook` con evento `checkout.session.completed`.
7. Frontend React se sirve desde `frontend-react/dist` cuando existe build en la imagen.
