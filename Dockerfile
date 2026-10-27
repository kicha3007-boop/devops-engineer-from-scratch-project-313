# syntax=docker/dockerfile:1
# Один образ для Render и для локального запуска: внутри Caddy (вход, :PORT)
# раздаёт UI и проксирует API на uvicorn (127.0.0.1:8080).

# --- UI: готовая сборка из npm-пакета Хекслета -------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

# --- Caddy: берём только статический бинарник --------------------------------
FROM caddy:2-alpine AS caddy

# --- uv: менеджер зависимостей Python ----------------------------------------
FROM ghcr.io/astral-sh/uv:0.11 AS uv

# --- Итоговый образ ----------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PORT=80 \
    BACKEND_PORT=8080

WORKDIR /app

COPY --from=uv /uv /usr/local/bin/uv
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy

# Сначала только зависимости: этот слой пересобирается редко.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project \
    && rm /usr/local/bin/uv

COPY --from=frontend \
    /build/node_modules/@hexlet/project-devops-deploy-crud-frontend/dist/ \
    /app/public/
COPY Caddyfile /etc/caddy/Caddyfile
COPY docker/start.sh /usr/local/bin/start-app
COPY main.py ./
COPY shortener ./shortener

RUN chmod +x /usr/local/bin/start-app

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '80') + '/ping', timeout=2)"

CMD ["start-app"]
