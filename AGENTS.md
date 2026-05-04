# Proyecto Pizzeria App - Convenciones y Guía de Desarrollo

## Estructura del Proyecto

```
pizzeria-app/
├── app/
│   ├── api/              # Router principal que agrega todos los routers
│   ├── core/             # Configuración, seguridad, dependencias
│   ├── database/         # Modelos SQLAlchemy y conexión DB
│   ├── routers/          # Endpoints organizados por dominio
│   ├── schemas/          # Pydantic schemas para validación
│   ├── services/         # Lógica de negocio
│   └── static/          # Archivos estáticos (imágenes, etc.)
├── frontend/             # Frontend React (futuro) / HTML+JS vanilla (actual)
├── print_agent/          # Agente de impresión para cocina
├── ops/                  # Scripts de operación (systemd, deploy)
├── scripts/              # Scripts auxiliares
├── tests/                # Tests con pytest
└── migrations/           # Migraciones Alembic (próximamente)
```

## Convenciones de Código

### Python

- **Line length**: 100 caracteres máximo
- **Imports**: Standard library → Third-party → Local (separados por línea)
- **Naming**:
  - Clases: `PascalCase` (ej: `OrderCreate`)
  - Funciones/variables: `snake_case` (ej: `create_order`)
  - Constantes: `SCREAMING_SNAKE_CASE` (ej: `ALLOWED_ORDER_TRANSITIONS`)
  - Private: `_leading_underscore`

### Type Hints

- Usar type hints en todas las funciones públicas
- Usar `X | None` en lugar de `Optional[X]` (Python 3.10+)
- Tipos de colección: `list[X]`, `dict[K, V]` en lugar de `List`, `Dict`

### Base de Datos

- Modelos en `app/database/models.py`
- Un archivo por servicio en `app/services/`
- Usar transacciones explícitas cuando haya múltiples operaciones
- Siempre usar `db.flush()` antes de acceder a IDs generados

### API Endpoints

- REST conventions:
  - `GET /products` - Lista
  - `POST /products` - Crear
  - `GET /products/{id}` - Detalle
  - `PATCH /products/{id}` - Actualizar parcialmente
  - `DELETE /products/{id}` - Eliminar
- Prefijo `/admin/` para endpoints protegidos
- HTTP status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found

### Errores

- Lanzar excepciones específicas (`ValueError`, `LookupError`)
- Capturar en routers y convertir a `HTTPException`
- No exponer stack traces en producción

## Comandos de Desarrollo

```bash
# Instalar dependencias
pip install -e ".[dev]"

# Ejecutar servidor de desarrollo
python -m uvicorn app.main:app --reload

# Ejecutar tests
pytest -q

# Lint y format
ruff check app tests
ruff format app tests

# Migraciones (cuando estén configuradas)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Ramas y Commits

### Branch Naming

```
feature/nombre-feature
fix/nombre-fix
refactor/nombre-refactor
docs/nombre-docs
```

### Commit Messages

Formato: `<tipo>(<scope>): <descripción>`

Tipos:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `refactor`: Refactorización
- `docs`: Documentación
- `test`: Tests
- `chore`: Mantenimiento

Ejemplos:
```
feat(auth): agregar registro con JWT
fix(orders): corregir transición de estado inválida
docs(readme): actualizar instrucciones de deploy
```

## Testing

- Un archivo `tests/test_*.py` por módulo
- Usar fixtures de `tests/conftest.py`
- Mocks para servicios externos (email, Stripe)
- Tests independientes (no dependen de orden de ejecución)

## Variables de Entorno

### Requeridas para desarrollo

```env
DATABASE_URL=sqlite:///./pizzeria.db
SECRET_KEY=dev-secret-key-change-me
STRIPE_KEY=sk_test_xxx
FRONTEND_BASE_URL=http://127.0.0.1:5500
```

### Requeridas para producción

```env
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=<generar-con-openssl-rand-base64-32>
STRIPE_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
PRINT_AGENT_KEY=<generar-random>
SMTP_HOST=smtp.example.com
SMTP_USER=user@example.com
SMTP_PASSWORD=app-password
```

## Dependencias del Proyecto

### Core
- `fastapi` - Framework web
- `sqlalchemy` - ORM
- `pydantic` - Validación de datos

### Auth
- `python-jose` - JWT
- `passlib` - Hashing de passwords

### External
- `stripe` - Pagos
- `python-multipart` - Form data

### Dev
- `pytest` - Testing
- `ruff` - Linting
- `httpx` - HTTP client para tests
