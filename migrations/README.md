# Migraciones de Base de Datos

Este directorio contiene las migraciones de Alembic para gestionar el esquema de la base de datos.

## Comandos

```bash
# Crear una nueva migración
alembic revision --autogenerate -m "description"

# Aplicar migraciones pendientes
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial de migraciones
alembic history

# Ver estado actual
alembic current
```

## Desarrollo Local (SQLite)

En desarrollo local, las migraciones usarán SQLite automáticamente gracias a `DATABASE_URL` en `.env`.

## Producción (PostgreSQL)

En producción (Railway), configurar `DATABASE_URL` con la conexión a PostgreSQL.
