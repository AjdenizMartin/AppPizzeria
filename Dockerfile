FROM node:22.13-alpine AS frontend-builder
WORKDIR /build/frontend-react

COPY frontend-react/package*.json ./
RUN npm ci

COPY frontend-react/ ./
RUN npm run build


FROM python:3.13-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

RUN useradd -m -u 10001 appuser

COPY pyproject.toml README.md ./
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini
COPY print_agent/ ./print_agent/
COPY scripts/start_production.sh ./scripts/start_production.sh

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY --from=frontend-builder /build/frontend-react/dist ./frontend-react/dist

RUN chown -R appuser:appuser /app && chmod -R u=rwX,go=rX /app

USER appuser

EXPOSE 8000
CMD ["sh", "./scripts/start_production.sh"]
