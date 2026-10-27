# Деплой приложения на PaaS (Devops)

[![hexlet-check](https://github.com/kicha3007-boop/devops-engineer-from-scratch-project-313/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/kicha3007-boop/devops-engineer-from-scratch-project-313/actions/workflows/hexlet-check.yml)
[![ci](https://github.com/kicha3007-boop/devops-engineer-from-scratch-project-313/actions/workflows/ci.yml/badge.svg)](https://github.com/kicha3007-boop/devops-engineer-from-scratch-project-313/actions/workflows/ci.yml)

Сокращатель ссылок на FastAPI + PostgreSQL с готовым UI, мониторингом ошибок через
Bugsink и образом, в котором Caddy и бэкенд работают в одном контейнере.

Учебный проект Хекслета: https://ru.hexlet.io/programs/devops-engineer-from-scratch

> **Публичного деплоя нет.** У автора нет облачных аккаунтов, поэтому приложение
> не развёрнуто на Render, а Bugsink работает локально в Docker Compose. Всё
> запускается одной командой на своей машине (см. «Быстрый старт»), а образ
> готов к Render без изменений — инструкция в разделе
> [«Как задеплоить на Render самому»](#как-задеплоить-на-render-самому).

![UI сокращателя ссылок](assets/ui.png)

## Стек

- Python 3.12+, [uv](https://docs.astral.sh/uv/), FastAPI, SQLModel, psycopg 3
- PostgreSQL 17
- Caddy 2 — раздаёт UI и проксирует API внутри того же контейнера
- UI — npm-пакет [`@hexlet/project-devops-deploy-crud-frontend`](https://www.npmjs.com/package/@hexlet/project-devops-deploy-crud-frontend) (react-admin)
- Sentry SDK → [Bugsink](https://www.bugsink.com/) (локально в Docker)
- pytest, Ruff, GitHub Actions

## Быстрый старт (только Docker)

```bash
git clone https://github.com/kicha3007-boop/devops-engineer-from-scratch-project-313.git
cd devops-engineer-from-scratch-project-313
docker compose up --build
```

- UI: <http://localhost:8090>
- Проверка живости: `curl http://localhost:8090/ping` → `pong`

Compose поднимает Postgres и образ приложения: снаружи слушает Caddy (порт хоста
`8090` → `80` в контейнере), бэкенд работает внутри на `127.0.0.1:8080`. Таблицы
создаются при старте приложения. Порт меняется переменной `APP_PORT`.

Остановить и удалить данные: `docker compose --profile monitoring down -v`.

## Локальная разработка

Нужны uv и Node.js 20.19+ / 22.12+ (для UI).

```bash
make install            # uv sync + npm ci
cp .env.example .env    # настройки для make run / make dev
make db                 # Postgres из compose на localhost:5432
make run                # бэкенд на http://localhost:8080
make dev                # бэкенд :8080 + UI (Vite) :5173 через concurrently
make test               # pytest
make lint               # ruff
```

`make dev` открывает UI на <http://localhost:5173>: штатно UI ходит в `/api` того же
адреса, а Vite проксирует запросы на `:8080`. Для прямых запросов браузера со
страницы `:5173` на `:8080` настроен CORS (см. ниже).

Тесты по умолчанию используют отдельный файл SQLite на каждый тест. Чтобы
прогнать их на Postgres (как в CI), задайте `TEST_DATABASE_URL`:

```bash
docker compose exec db psql -U shortener -c 'CREATE DATABASE shortener_test'
TEST_DATABASE_URL=postgres://shortener:shortener@localhost:5432/shortener_test make test
```

## API

| Метод и путь | Что делает | Успех | Ошибки |
|---|---|---|---|
| `GET /ping` | проверка живости, текст `pong` | `200` | — |
| `GET /api/links` | список ссылок, заголовок `Content-Range` | `200` | `422` — неверный `range`/`sort` |
| `POST /api/links` | создать ссылку | `201` | `422` — невалидное тело, `409` — имя занято |
| `GET /api/links/{id}` | одна ссылка | `200` | `404` |
| `PUT /api/links/{id}` | заменить `original_url` и `short_name` | `200` | `404`, `422`, `409` |
| `DELETE /api/links/{id}` | удалить ссылку, тела нет | `204` | `404` |
| `GET /r/{short_name}` | редирект на `original_url` (заголовок `Location`) | `302` | `404` |

Все ошибки — JSON с полем `detail`: строка для `404`/`409`, список
подробностей проверки для `422`.

```bash
curl -i -X POST http://localhost:8090/api/links \
  -H 'Content-Type: application/json' \
  -d '{"original_url": "https://example.com/long-url", "short_name": "exmpl"}'

# HTTP/1.1 201 Created
# {"id":1,"original_url":"https://example.com/long-url","short_name":"exmpl",
#  "short_url":"http://localhost:8090/r/exmpl","created_at":"2026-10-27T11:20:07.464243Z"}

curl -i http://localhost:8090/r/exmpl
# HTTP/1.1 302 Found
# location: https://example.com/long-url
```

Правила полей:

- `original_url` — абсолютный `http(s)`-адрес до 2048 символов, возвращается как прислан;
- `short_name` — латиница, цифры, `-`, `_`, до 64 символов. В `POST` можно не
  передавать (или передать пустым) — сервер сгенерирует 12 случайных символов;
- уникальность `short_name` держит ограничение `uq_links_short_name` в базе;
  нарушение ловится как `IntegrityError` и превращается в `409`;
- `short_url` собирается из переменной `BASE_URL`, `created_at` проставляет база.

### Пагинация и сортировка

Параметры в формате react-admin (`ra-data-simple-rest`), которым пользуется UI:

- `range=[start,end]` — **границы включительно**: `range=[0,9]` — первые 10 записей;
- `sort=["field","ASC|DESC"]` — поле `id`, `short_name` или `original_url`.

В заголовке `Content-Range` — реально отданные позиции и общее число записей:

```text
GET /api/links?range=[0,9]     →  Content-Range: links 0-9/42
GET /api/links?range=[40,49]   →  Content-Range: links 40-41/42
GET /api/links?range=[50,59]   →  Content-Range: links */42   (пустая страница)
GET /api/links                 →  все записи, Content-Range: links 0-41/42
```

### CORS

Открыт адресно для `http://localhost:5173` (переменная `CORS_ORIGINS`): методы
`GET`, `POST`, `PUT`, `DELETE`, заголовки `Content-Type` и `Range` (его шлёт
react-admin), браузеру разрешено читать `Content-Range`. Чужие origin заголовков
CORS не получают, их preflight-запросы отклоняются. В образе с Caddy UI и API
живут на одном адресе, поэтому там CORS не участвует.

Проверено в Chrome со страницы `http://localhost:5173` при `make dev`: прямой
`fetch("http://localhost:8080/api/links")` читает `Content-Range`, `POST` проходит
preflight `OPTIONS` и возвращает `201`.

## Образ: Caddy + бэкенд в одном контейнере

```text
браузер → :PORT (Caddy)
            ├─ /api/*, /r/*, /ping → uvicorn 127.0.0.1:8080 (путь не меняется)
            └─ всё остальное      → UI из /app/public (try_files → index.html)
```

- [`Dockerfile`](Dockerfile) — многоэтапная сборка: UI берётся из `dist` npm-пакета,
  бинарник Caddy — из официального образа, зависимости Python ставит uv по `uv.lock`.
- [`Caddyfile`](Caddyfile) — слушает `:{$PORT}` (по умолчанию `80`).
- [`docker/start.sh`](docker/start.sh) — запускает оба процесса; если любой
  падает, гасит второй и завершает контейнер, чтобы платформа его перезапустила.

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_URL` | строка подключения; `postgres://` и `postgresql://` приводятся к `postgresql+psycopg://` | **обязательна** |
| `BASE_URL` | публичный адрес для `short_url` | `http://localhost:8080` |
| `PORT` | порт Caddy в контейнере | `80` |
| `SENTRY_DSN` | DSN Bugsink/Sentry; пусто — мониторинг выключен | — |
| `APP_ENV` | окружение в событиях мониторинга | `development` |
| `CORS_ORIGINS` | разрешённые origin через запятую | `http://localhost:5173` |
| `ENABLE_DEBUG_ROUTES` | включает `GET /api/debug/error` для проверки мониторинга | `false` |

Секретов в репозитории нет: в [`.env.example`](.env.example) и
[`docker-compose.yml`](docker-compose.yml) только значения для локального стенда.

## Мониторинг ошибок: локальный Bugsink

Bugsink совместим с Sentry SDK, приложение подключает его через
`sentry-sdk[fastapi]`, DSN читается из `SENTRY_DSN`
([`shortener/monitoring.py`](shortener/monitoring.py)).

```bash
# 1. Поднять приложение и Bugsink (профиль monitoring)
docker compose --profile monitoring up --build -d

# 2. Создать проект в Bugsink и получить DSN (через его REST API)
make bugsink-project
#   SENTRY_DSN=http://<ключ>@bugsink:8000/1   ← для приложения в compose

# 3. Перезапустить приложение с DSN и отладочной ручкой
SENTRY_DSN='http://<ключ>@bugsink:8000/1' ENABLE_DEBUG_ROUTES=true \
  docker compose --profile monitoring up -d app

# 4. Вызвать ошибку через Caddy
curl -i http://localhost:8090/api/debug/error     # HTTP/1.1 500
```

Bugsink: <http://localhost:8000>, вход `admin@example.com` / `admin` (только для
локального стенда, меняется через `BUGSINK_ADMIN`).

### Подтверждение: событие дошло

Ошибка `DebugError` из `GET /api/debug/error` попала в Bugsink как issue
`URL-SHORTENER-1` с окружением `local-docker`. Полный ответ REST API Bugsink —
в [`assets/bugsink-event.txt`](assets/bugsink-event.txt).

![Событие в локальном Bugsink](assets/bugsink-event.png)

## Как задеплоить на Render самому

Образ уже рассчитан на Render: порт берётся из `PORT`, строка `postgres://` от
Render нормализуется, адрес для коротких ссылок и DSN приходят из окружения.

1. **База.** New → PostgreSQL (Free). Скопируйте *Internal Database URL*.
2. **Сервис.** New → Web Service → этот репозиторий; *Language* — Docker,
   *Instance Type* — Free. Render соберёт образ по `Dockerfile`.
3. **Переменные окружения** сервиса:
   - `PORT=80` — Render передаёт трафик в Caddy;
   - `DATABASE_URL=<Internal Database URL>`;
   - `BASE_URL=https://<имя-сервиса>.onrender.com` — без `localhost`;
   - `SENTRY_DSN=<DSN проекта в Bugsink>` — облачного или своего;
   - `APP_ENV=production`.
4. **Health Check Path** — `/ping`.
5. После деплоя: открыть корень (UI), `curl https://<сервис>.onrender.com/ping` →
   `pong`, создать ссылку и проверить редирект `/r/<имя>` → `302`.
6. Проверка мониторинга: временно задать `ENABLE_DEBUG_ROUTES=true`, открыть
   `/api/debug/error`, убедиться, что событие появилось в Bugsink, и выключить
   переменную обратно.

HTTPS обеспечивает Render, в контейнер запросы приходят по HTTP — поэтому в
`Caddyfile` автоматический HTTPS выключен.

## Структура

```text
main.py                  точка входа: app = create_app()
shortener/
  app.py                 сборка FastAPI: lifespan (создание таблиц), CORS, роутеры
  config.py              настройки из окружения, нормализация DATABASE_URL
  db.py                  движок, сессии, create_tables
  models.py              таблица links (UniqueConstraint на short_name)
  schemas.py             pydantic-схемы запросов/ответов, range и sort
  repository.py          запросы к базе
  monitoring.py          Sentry SDK → Bugsink
  routers/
    links.py             ресурс «ссылка»: /api/links и /r/{short_name}
    health.py            /ping
    debug.py             /api/debug/error (только при ENABLE_DEBUG_ROUTES)
tests/                   pytest: CRUD, ошибки, пагинация, сортировка, CORS, настройки
Dockerfile, Caddyfile, docker/start.sh, docker-compose.yml
scripts/bugsink-project.sh  создание проекта в локальном Bugsink
.github/workflows/ci.yml    ruff + pytest на Postgres, сборка и smoke-тест образа
```

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
