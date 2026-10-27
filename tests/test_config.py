import dataclasses

import pytest
from fastapi.testclient import TestClient

from shortener import monitoring
from shortener.app import create_app
from shortener.config import ConfigError, load_settings, normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgres://u:p@db:5432/app?sslmode=disable",
            "postgresql+psycopg://u:p@db:5432/app?sslmode=disable",
        ),
        ("postgresql://u:p@db/app", "postgresql+psycopg://u:p@db/app"),
        ("postgresql+psycopg://u:p@db/app", "postgresql+psycopg://u:p@db/app"),
        ("sqlite:///local.db", "sqlite:///local.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


def test_load_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db/app")
    monkeypatch.setenv("BASE_URL", "https://short.example.com/")
    monkeypatch.setenv("SENTRY_DSN", "https://key@bugsink.example/1")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")

    settings = load_settings()

    assert settings.database_url == "postgresql+psycopg://u:p@db/app"
    assert settings.base_url == "https://short.example.com"
    assert settings.sentry_dsn == "https://key@bugsink.example/1"
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert settings.debug_routes is True


def test_load_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    optional = ("BASE_URL", "SENTRY_DSN", "CORS_ORIGINS", "ENABLE_DEBUG_ROUTES")
    for name in optional:
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.base_url == "http://localhost:8080"
    assert settings.sentry_dsn is None
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.debug_routes is False


def test_debug_route_is_disabled_by_default(client):
    assert client.get("/api/debug/error").status_code == 404


def test_debug_route_raises_when_enabled(settings):
    app = create_app(dataclasses.replace(settings, debug_routes=True))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/debug/error")

    assert response.status_code == 500


def test_monitoring_is_off_without_dsn(settings, monkeypatch):
    calls = []
    monkeypatch.setattr(monitoring.sentry_sdk, "init", calls.append)

    assert monitoring.init_monitoring(settings) is False
    assert calls == []


def test_monitoring_uses_dsn_from_settings(settings, monkeypatch):
    calls = []
    monkeypatch.setattr(
        monitoring.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs)
    )
    dsn = "http://key@bugsink:8000/1"

    enabled = monitoring.init_monitoring(
        dataclasses.replace(settings, sentry_dsn=dsn)
    )

    assert enabled is True
    assert calls[0]["dsn"] == dsn
