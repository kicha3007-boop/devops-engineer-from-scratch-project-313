PORT ?= 8080

.PHONY: install run backend frontend dev test lint lint-fix format \
	db compose-up compose-down monitoring bugsink-project

install:
	uv sync
	npm ci

# Бэкенд на 8080. Нужен DATABASE_URL (см. .env.example или `make db`).
run:
	uv run uvicorn main:app --host 0.0.0.0 --port $(PORT)

backend:
	uv run uvicorn main:app --host 0.0.0.0 --port $(PORT) --reload

FRONTEND_PKG = node_modules/@hexlet/project-devops-deploy-crud-frontend

# UI на http://localhost:5173, /api проксируется на API_URL (по умолчанию :8080).
# На Windows штатная команда пакета молча завершается (она вызывает npm
# без shell), поэтому там запускаем тот же `vite preview` напрямую.
frontend:
ifeq ($(OS),Windows_NT)
	npm --prefix $(FRONTEND_PKG) run preview
else
	npx start-hexlet-devops-deploy-crud-frontend
endif

# Бэкенд и UI (Vite на 5173) вместе. Цели вызываются отдельно,
# поэтому dev не запускает сам себя.
dev:
	npx concurrently --kill-others --names backend,frontend \
		"$(MAKE) backend" "$(MAKE) frontend"

test:
	uv run pytest

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

# Только Postgres из compose — для make run / make dev на хосте.
db:
	docker compose up -d db

compose-up:
	docker compose up --build

compose-down:
	docker compose --profile monitoring down -v

# Приложение + локальный Bugsink (http://localhost:8000).
monitoring:
	docker compose --profile monitoring up --build -d

# Создать проект в локальном Bugsink и напечатать DSN для .env.
bugsink-project:
	sh scripts/bugsink-project.sh
