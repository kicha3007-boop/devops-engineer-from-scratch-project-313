"""Подключение к базе данных и сессии SQLModel."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from shortener.models import Link


def build_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        # TestClient и uvicorn обращаются к SQLite из разных потоков.
        connect_args["check_same_thread"] = False
    return create_engine(
        database_url, connect_args=connect_args, pool_pre_ping=True
    )


def create_tables(engine: Engine) -> None:
    """Создаёт недостающие таблицы и ограничения. Безопасно при повторе.

    Вызывается из lifespan при каждом старте приложения, поэтому
    руками ничего готовить в базе не нужно.
    """
    Link.metadata.create_all(engine)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session
