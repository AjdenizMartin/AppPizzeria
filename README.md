# 🍕 Pizzeria App

Aplicación full-stack para restaurantes de delivery.  
Incluye storefront público, panel admin, pagos con Stripe y flujo operativo de impresión de tickets para cocina.

## Qué Resuelve

Este proyecto está pensado como base **adaptable por negocio** (no como marketplace multirestaurante).

- Catálogo y carrito con experiencia tipo delivery app.
- Checkout con Stripe.
- Backoffice para gestionar productos y pedidos.
- Cola de impresión con reintentos para operación real en restaurante.

## Funcionalidades Principales

### Cliente (frontend público)

- Navegación por categorías con búsqueda.
- Carrito persistente en navegador.
- Creación de pedido previa al pago.
- Redirección a Stripe Checkout.

### Admin (frontend privado)

- Registro/login con JWT.
- CRUD de productos con imagen.
- Edición de producto en modal.
- Gestión de estados del pedido.
- Reimpresión manual de pedidos.

### Operación (impresión)

- Cola `print_jobs` con estados `pending/printing/printed/failed`.
- Reintentos controlados por `PRINT_JOB_MAX_ATTEMPTS`.
- Agente local (`print_agent/agent.py`) para PC/tablet del restaurante.
- Autoarranque Linux vía `systemd`.

## Arquitectura

### Backend

- FastAPI + SQLAlchemy + SQLite
- Autenticación JWT
- Routers principales:
  - `/auth`
  - `/products` y `/admin/products`
  - `/orders` y `/admin/orders`
  - `/create-checkout-session`
  - `/print-agent/*`

### Frontend

- HTML + CSS + JavaScript vanilla
- Vistas:
  - `frontend/index.html` (tienda)
  - `frontend/admin.html` (panel admin)

### Agente de impresión

- Proceso local con polling seguro usando `X-Print-Agent-Key`.
- Consume trabajos de impresión y reporta éxito/fallo al backend.

## Flujo de Pedido

`created -> paid -> accepted -> printing -> printed -> ready -> delivered`

Estados alternativos: `failed`, `cancelled`.

Al pasar a `accepted`, se encola automáticamente un trabajo de impresión.

## Estructura del Proyecto

```text
pizzeria-app/
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── static/
├── frontend/
├── print_agent/
├── ops/systemd/
├── tests/
├── .env.example
└── pyproject.toml
```

## Requisitos

- Python 3.11+
- `pip`
- Cuenta Stripe (modo test para desarrollo)
- (Opcional) Linux con `systemd` para autoarranque del print agent

## Puesta en Marcha Rápida

### 1) Clonar repositorio

```bash
git clone https://github.com/AjdenizMartin/AppPizzeria.git
cd AppPizzeria
```

### 2) Crear entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Instalar dependencias

```bash
pip install -e ".[dev]"
```

### 4) Configurar variables de entorno

```bash
cp .env.example .env
```

Variables mínimas recomendadas en `.env`:

```env
STRIPE_KEY=sk_test_xxx
SECRET_KEY=change-me-in-production
ADMIN_EMAILS=owner@example.com
FRONTEND_BASE_URL=http://127.0.0.1:5500
ACCESS_TOKEN_EXPIRE_MINUTES=120
PRINT_AGENT_KEY=shared_secret_for_printer_agent
PRINT_JOB_MAX_ATTEMPTS=3
```

### 5) Levantar backend

```bash
python -m uvicorn app.main:app --reload
```

API docs disponibles en: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 6) Levantar frontend

```bash
cd frontend
python -m http.server 5500
```

App cliente: [http://127.0.0.1:5500](http://127.0.0.1:5500)

Panel admin: [http://127.0.0.1:5500/admin.html](http://127.0.0.1:5500/admin.html)

## Operación de Impresión

### Ejecutar print agent manualmente

```bash
PRINT_AGENT_KEY=shared_secret_for_printer_agent \
python print_agent/agent.py --agent-id kitchen-tablet-1
```

Modo prueba sin impresora física:

```bash
PRINT_AGENT_KEY=shared_secret_for_printer_agent \
python print_agent/agent.py --output-file /tmp/print_tickets.txt
```

### Autoarranque con systemd (Linux)

```bash
chmod +x ops/systemd/install_print_agent_service.sh
./ops/systemd/install_print_agent_service.sh /opt/pizzeria-app restaurant
```

Configura secretos runtime:

```bash
sudo nano /etc/pizzeria-print-agent.env
```

Comandos operativos:

```bash
sudo systemctl restart pizzeria-print-agent.service
sudo systemctl status pizzeria-print-agent.service
sudo journalctl -u pizzeria-print-agent.service -f
```

Guía extendida: [ops/systemd/README.md](ops/systemd/README.md)

## Testing y Calidad

```bash
pytest -q
ruff check app tests
```

## Credenciales Admin

- El primer usuario registrado se convierte en admin.
- Cualquier email incluido en `ADMIN_EMAILS` también obtiene permisos de admin.

## Seguridad (mínimo recomendado)

- Nunca subir `.env` a Git.
- Usar claves Stripe secret (`sk_...`) válidas por entorno.
- Cambiar `SECRET_KEY` en producción.
- Proteger `PRINT_AGENT_KEY` y rotarla por cliente/restaurante.

## Próximos Pasos Sugeridos

- Webhook de Stripe para confirmar pago de forma server-to-server.
- Persistencia robusta para producción (PostgreSQL).
- Integración directa con impresoras ESC/POS.
- Métricas y alertas operativas (errores de impresión, pedidos atascados).

## Autor

**Angel Deniz**  
GitHub: [@AjdenizMartin](https://github.com/AjdenizMartin)
