"""Общие фикстуры.

Каждый тест получает чистую базу: по умолчанию свежий файл SQLite во
временном каталоге, а при заданном TEST_DATABASE_URL — Postgres, в котором
таблицы удаляются до и после теста. Поэтому тесты не зависят от порядка
запуска и не требуют заранее заполненной базы.
"""

import itertools
import os

import pytest
from fastapi.testclient import TestClient

from shortener.app import create_app
from shortener.config import Settings, normalize_database_url
from shortener.db import build_engine
from shortener.models import Link

BASE_URL = "https://short.test"


def drop_tables(database_url: str) -> None:
    engine = build_engine(database_url)
    Link.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def database_url(tmp_path):
    external = os.getenv("TEST_DATABASE_URL")
    if not external:
        yield f"sqlite:///{tmp_path / 'test.db'}"
        return
    url = normalize_database_url(external)
    drop_tables(url)
    yield url
    drop_tables(url)


@pytest.fixture
def settings(database_url):
    return Settings(database_url=database_url, base_url=BASE_URL)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def make_link(client):
    """Создаёт ссылку через API и возвращает тело ответа."""
    counter = itertools.count(1)

    def make(**overrides):
        number = next(counter)
        payload = {
            "original_url": f"https://example.com/page/{number}",
            "short_name": f"link-{number}",
            **overrides,
        }
        response = client.post("/api/links", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return make
