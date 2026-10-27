"""Работа с таблицей ссылок: все запросы к базе собраны здесь."""

import secrets
import string

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from shortener.models import Link

GENERATED_NAME_LENGTH = 12
GENERATE_ATTEMPTS = 5
ALPHABET = string.ascii_letters + string.digits


class ShortNameTaken(Exception):
    """short_name уже занят: сработало ограничение уникальности в базе."""

    def __init__(self, short_name: str):
        super().__init__(short_name)
        self.short_name = short_name


def generate_short_name() -> str:
    return "".join(
        secrets.choice(ALPHABET) for _ in range(GENERATED_NAME_LENGTH)
    )


def count_links(session: Session) -> int:
    return session.exec(select(func.count()).select_from(Link)).one()


def list_links(
    session: Session,
    offset: int = 0,
    limit: int | None = None,
    sort: tuple[str, str] = ("id", "ASC"),
) -> list[Link]:
    field, order = sort
    column = getattr(Link, field)
    ordering = column.desc() if order == "DESC" else column.asc()
    # id вторым ключом: страницы стабильны и при одинаковых значениях.
    query = select(Link).order_by(ordering, Link.id).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return list(session.exec(query).all())


def get_link(session: Session, link_id: int) -> Link | None:
    return session.get(Link, link_id)


def find_by_short_name(session: Session, short_name: str) -> Link | None:
    query = select(Link).where(Link.short_name == short_name)
    return session.exec(query).first()


def save_link(session: Session, link: Link) -> Link:
    """Сохраняет ссылку; конфликт имени ловит ограничение базы."""
    # Запоминаем имя до commit: после rollback объект перечитается
    # из базы и вернёт прежнее значение.
    short_name = link.short_name
    session.add(link)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ShortNameTaken(short_name) from error
    session.refresh(link)
    return link


def create_link(
    session: Session, original_url: str, short_name: str | None
) -> Link:
    if short_name is not None:
        return save_link(
            session, Link(original_url=original_url, short_name=short_name)
        )
    # Имя не задано: генерируем случайное, при редком совпадении — ещё раз.
    for _ in range(GENERATE_ATTEMPTS - 1):
        candidate = Link(
            original_url=original_url, short_name=generate_short_name()
        )
        try:
            return save_link(session, candidate)
        except ShortNameTaken:
            continue
    return save_link(
        session,
        Link(original_url=original_url, short_name=generate_short_name()),
    )


def update_link(
    session: Session, link: Link, original_url: str, short_name: str
) -> Link:
    link.original_url = original_url
    link.short_name = short_name
    return save_link(session, link)


def delete_link(session: Session, link: Link) -> None:
    session.delete(link)
    session.commit()
