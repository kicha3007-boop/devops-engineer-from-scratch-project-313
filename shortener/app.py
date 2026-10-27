"""Сборка FastAPI-приложения."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shortener.config import Settings, load_settings
from shortener.db import build_engine, create_tables
from shortener.monitoring import init_monitoring
from shortener.routers import debug, health, links


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Таблицы создаются при каждом старте: никаких ручных шагов с базой.
    create_tables(app.state.engine)
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        load_dotenv()
        settings = load_settings()

    init_monitoring(settings)

    app = FastAPI(title="URL Shortener", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = build_engine(settings.database_url)

    # CORS нужен только для прямых запросов браузера со страницы Vite
    # (localhost:5173) на API (localhost:8080). Разрешаем адресно.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        # Range шлёт ra-data-simple-rest при запросе списка.
        allow_headers=["Content-Type", "Range"],
        expose_headers=["Content-Range"],
    )

    app.include_router(health.router)
    app.include_router(links.router)
    if settings.debug_routes:
        app.include_router(debug.router)
    return app
