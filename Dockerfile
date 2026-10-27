# --- frontend: compile Tailwind + Flowbite CSS -----------------------------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY tailwind.config.js ./
COPY static/src ./static/src
COPY templates ./templates
COPY apps ./apps
RUN npm run build

# --- base: shared Python setup ----------------------------------------------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/

# --- dev ---------------------------------------------------------------------
FROM base AS dev
RUN pip install --no-cache-dir -r requirements/dev.txt
COPY . .
EXPOSE 8000

# --- prod ----------------------------------------------------------------
FROM base AS prod
RUN pip install --no-cache-dir -r requirements/prod.txt
COPY . .
COPY --from=frontend /app/static/dist ./static/dist
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
# collectstatic runs at container start (not build time) since it needs
# runtime env vars (SECRET_KEY, DATABASE_URL) that aren't available to `docker build`.
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 60"]
