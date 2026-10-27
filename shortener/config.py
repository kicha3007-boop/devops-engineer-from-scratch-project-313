"""Настройки приложения: всё берётся из переменных окружения (12 factor)."""

import os
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)
TRUTHY = {"1", "true", "yes", "on"}


class ConfigError(RuntimeError):
    """Обязательная настройка не задана или задана неверно."""


def normalize_database_url(url: str) -> str:
    """Приводит DATABASE_URL к диалекту SQLAlchemy с драйвером psycopg 3.

    Хостинги (Render, Heroku) отдают строку вида ``postgres://…``,
    а SQLAlchemy знает только ``postgresql://``. Явно указываем драйвер
    ``psycopg``, иначе SQLAlchemy попробует искать psycopg2.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def parse_list(raw: str | None, default: tuple[str, ...]) -> list[str]:
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    base_url: str = DEFAULT_BASE_URL
    sentry_dsn: str | None = None
    environment: str = "development"
    cors_origins: list[str] = field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS)
    )
    debug_routes: bool = False


def load_settings() -> Settings:
    """Читает настройки из окружения. Без DATABASE_URL работать нельзя."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ConfigError(
            "Переменная окружения DATABASE_URL не задана: "
            "скопируйте .env.example в .env или передайте её явно"
        )
    return Settings(
        database_url=normalize_database_url(database_url),
        base_url=os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        sentry_dsn=os.getenv("SENTRY_DSN") or None,
        environment=os.getenv("APP_ENV", "development"),
        cors_origins=parse_list(
            os.getenv("CORS_ORIGINS"), DEFAULT_CORS_ORIGINS
        ),
        debug_routes=os.getenv("ENABLE_DEBUG_ROUTES", "").lower() in TRUTHY,
    )
