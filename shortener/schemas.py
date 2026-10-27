"""Схемы входных и выходных данных API.

Вся валидация запроса описана здесь, в обработчиках проверок нет:
FastAPI сам отвечает 422 с подробностями в поле ``detail``.
"""

import json
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    NonNegativeInt,
    field_validator,
)

from shortener.models import ORIGINAL_URL_MAX_LENGTH, SHORT_NAME_MAX_LENGTH


def ensure_http_url(value: str) -> str:
    """Проверяет, что это абсолютный http(s)-адрес, и возвращает его как есть.

    HttpUrl нормализует строку (например, дописывает «/»), а пользователю
    нужно получить обратно ровно то, что он прислал.
    """
    HttpUrl(value)
    return value


def empty_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


OriginalUrl = Annotated[
    str,
    Field(min_length=1, max_length=ORIGINAL_URL_MAX_LENGTH),
    AfterValidator(ensure_http_url),
]

ShortName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=SHORT_NAME_MAX_LENGTH,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Латиница, цифры, «-» и «_»",
    ),
]


class LinkCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_url: OriginalUrl
    # Пустое имя в форме UI означает «придумай сам».
    short_name: Annotated[ShortName | None, BeforeValidator(empty_to_none)] = (
        None
    )


class LinkUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_url: OriginalUrl
    short_name: ShortName


class LinkRead(BaseModel):
    id: int
    original_url: str
    short_name: str
    short_url: str
    created_at: datetime | None = None


SortField = Literal["id", "short_name", "original_url"]
SortOrder = Literal["ASC", "DESC"]


class ListParams(BaseModel):
    """Query-параметры списка в формате react-admin (ra-data-simple-rest).

    ``range=[start,end]`` — границы включительно: первая страница
    из 10 записей запрашивается как ``range=[0,9]``.
    ``sort=["id","ASC"]`` — поле и направление сортировки.
    """

    range: tuple[NonNegativeInt, NonNegativeInt] | None = None
    sort: tuple[SortField, SortOrder] | None = None

    @field_validator("range", "sort", mode="before")
    @classmethod
    def parse_json(cls, value: Any) -> Any:
        # Поле-кортеж FastAPI собирает как повторяющийся параметр
        # (?range=a&range=b), поэтому строка приходит списком из одного
        # элемента.
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as error:
                raise ValueError("ожидается JSON-массив") from error
        return value

    @field_validator("range")
    @classmethod
    def check_order(cls, value: tuple[int, int] | None):
        if value is not None and value[1] < value[0]:
            raise ValueError("конец диапазона меньше начала")
        return value
