# syntax=docker/dockerfile:1

# ---- Stage 1: build the Vue SPA ----
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python base with dependencies ----
FROM python:3.11-slim AS backend-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Dev target: used by docker-compose (source is bind-mounted) ----
FROM backend-base AS dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- Production image: bundles backend + compiled SPA (last stage = default) ----
FROM backend-base AS prod
COPY backend/ ./
# The compiled SPA is served at the site root by WhiteNoise (see settings.SPA_DIR).
COPY --from=frontend-build /app/dist ./spa
# Collect Django/DRF static assets. No DB connection happens here.
RUN SECRET_KEY=build-only DATABASE_URL=postgres://u:p@localhost/db \
    python manage.py collectstatic --noinput
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
