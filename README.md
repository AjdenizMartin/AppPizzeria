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
npm ci
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
npm ci
npm run build
cd ..
python -m uvicorn app.main:app --reload
```

URLs:

- Frontend cliente: `http://127.0.0.1:8000/`
- Panel admin: `http://127.0.0.1:8000/admin`

En este modo el backend sirve `frontend-react/dist` como SPA.


## Instalacion unica (app + frontend + print agent)

Si quieres dejar todo listo con una sola instalacion (dependencias, build React, migraciones y servicio de impresion):

```bash
./scripts/install_all_in_one.sh
```

Este instalador:
- crea/actualiza `.env`
- genera `PRINT_AGENT_KEY` segura si falta
- instala backend en `.venv`
- compila `frontend-react/dist`
- ejecuta `alembic upgrade head`
- opcionalmente instala/actualiza `pizzeria-print-agent` con `systemd`

Despues, para arrancar API:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Para arranque diario (migraciones + chequeo print agent + API):

```bash
./scripts/run_all.sh
```

Para detener todo (API local + print agent):

```bash
./scripts/stop_all.sh
```

## Stripe

- Checkout: `POST /create-checkout-session`
- Webhook: `POST /stripe/webhook`
- Rutas React usadas por Stripe:
  - success: `/order-confirmation/:orderId?method=card`
  - cancel: `/checkout`

## Calidad

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check app tests migrations print_agent scripts
.venv/bin/pytest -q
.venv/bin/alembic heads

cd frontend-react
npm ci
npm run build
npm run lint
cd ..
```

## Produccion (Railway + PostgreSQL)

- Usar `APP_ENV=production`.
- Usar `DATABASE_URL` de PostgreSQL (no SQLite).
- Usar migraciones Alembic: no depender de `AUTO_CREATE_TABLES`.
- Usar inicialmente la URL publica de Railway en `FRONTEND_BASE_URL` y `CORS_ORIGINS`.
- Cambiar a dominio real cuando DNS/TLS esten listos.
- El arranque productivo ejecuta migraciones antes de levantar API con:
  - `scripts/start_production.sh`
- Stripe webhook: `/stripe/webhook`
- SMTP real y print agent fisico se configuran en la fase de staging/prod.

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
APP_ENV=production \
AUTO_CREATE_TABLES=false \
DATABASE_URL=postgresql://user:pass@localhost:5432/pizzeria_test \
FRONTEND_BASE_URL=https://example.com \
CORS_ORIGINS=https://example.com \
SECRET_KEY=test-secret-key-that-is-not-default \
STRIPE_KEY=sk_test_dummy \
STRIPE_WEBHOOK_SECRET=whsec_test_dummy \
PRINT_AGENT_KEY=test-print-key \
ADMIN_EMAILS=owner@example.com \
.venv/bin/python scripts/validate_predeploy.py
```

Railway:

1. Crear servicio backend y vincular PostgreSQL en Railway.
2. Configurar variables con referencia en `.env.production.example`.
3. Build command (si lo usas manual): `pip install .`
4. Start command recomendado: `sh ./scripts/start_production.sh`
5. El script ejecuta:
   - `alembic upgrade head`
   - `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Stripe webhook (produccion):
   - URL: `https://app.tudominio.com/stripe/webhook`
   - Evento: `checkout.session.completed`
7. Frontend React se sirve desde `frontend-react/dist` cuando existe build en la imagen.
8. Healthcheck rápido:
   - `GET /health` debe responder `{"status":"healthy"}`
9. Smoke de checkout:
   - crear pedido
   - crear checkout session
   - simular/recibir webhook
   - verificar pedido `accepted` y print job `pending`

Print agent en restaurante (local):

1. Configurar `PRINT_AGENT_KEY` igual en backend y agente.
2. En el equipo del restaurante, usar archivo env (ejemplo):
   - `/etc/pizzeria-print-agent.env`
   - `PRINT_AGENT_API_URL=https://app.tudominio.com`
   - `PRINT_AGENT_KEY=...`
   - `PRINT_AGENT_TICKET_WIDTH=42` para papel 80mm
3. Ejecutar como servicio (`systemd`) con reinicio automático.
4. Verificar flujo:
   - pedido `accepted` -> `print_jobs` pending
   - agente hace `pull`/`complete`
   - pedido pasa a `printed`

Backup / restore básico:

1. Activar backups automáticos de PostgreSQL en Railway.
2. Validar restore en staging al menos una vez.
3. Mantener snapshots antes de cambios estructurales.

Runbook de incidentes:

1. Stripe caído:
   - Checkout puede fallar al crear sesión.
   - Mantener cash checkout operativo.
   - Revisar `STRIPE_KEY`/estado Stripe y reintentar.
2. Impresora caída:
   - Ver `print_jobs` en `failed` o reintentos.
   - Usar acción admin `reprint`.
   - Reiniciar servicio print agent y revisar red/USB.
3. SMTP caído:
   - Pedidos siguen operando (emails son best-effort).
   - Revisar `SMTP_*` y logs de `email_service`.
4. DB caída:
   - API/health fallarán.
   - validar conexión Railway Postgres y reinicio de servicio.
   - restaurar desde snapshot si aplica.
