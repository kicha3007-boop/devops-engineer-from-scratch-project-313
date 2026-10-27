#!/usr/bin/env bash
# Запускает в одном контейнере бэкенд (uvicorn) и прокси (Caddy).
# Если любой из процессов завершился, гасим второй и выходим с ошибкой,
# чтобы Docker/Render перезапустили контейнер целиком.
set -uo pipefail

BACKEND_PORT="${BACKEND_PORT:-8080}"
PORT="${PORT:-80}"

if [ "$PORT" = "$BACKEND_PORT" ]; then
    echo "PORT ($PORT) совпадает с BACKEND_PORT: Caddy и uvicorn не уживутся" >&2
    exit 1
fi

uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
    --proxy-headers --forwarded-allow-ips 127.0.0.1 &
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &

stop_all() {
    kill -TERM $(jobs -p) 2>/dev/null
}
trap stop_all TERM INT

wait -n
status=$?
stop_all
wait
exit "$status"
