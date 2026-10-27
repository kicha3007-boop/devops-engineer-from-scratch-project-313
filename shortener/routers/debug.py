"""Отладочные маршруты. Подключаются только при ENABLE_DEBUG_ROUTES=true.

Нужны, чтобы вызвать настоящую необработанную ошибку и убедиться,
что событие дошло до Bugsink (Sentry SDK).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/debug", tags=["debug"])


class DebugError(RuntimeError):
    """Намеренная ошибка для проверки мониторинга."""


@router.get("/error")
def raise_error() -> None:
    raise DebugError("Проверка Bugsink: намеренная ошибка из /api/debug/error")
