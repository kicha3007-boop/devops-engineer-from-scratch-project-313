"""Проверка живости: по ней смотрят healthcheck Docker и хостинг."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["health"])


@router.get("/ping", response_class=PlainTextResponse)
def ping() -> str:
    return "pong"
