"""Таблицы базы данных."""

from datetime import datetime

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel

ORIGINAL_URL_MAX_LENGTH = 2048
SHORT_NAME_MAX_LENGTH = 64


class Link(SQLModel, table=True):
    __tablename__ = "links"
    # Уникальность short_name держит сама база: при гонке двух запросов
    # второй получит IntegrityError, а не тихий дубль.
    __table_args__ = (
        UniqueConstraint("short_name", name="uq_links_short_name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    original_url: str = Field(max_length=ORIGINAL_URL_MAX_LENGTH)
    short_name: str = Field(max_length=SHORT_NAME_MAX_LENGTH)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
