"""Отправка ошибок в Bugsink через Sentry SDK (Bugsink совместим с ним)."""

import sentry_sdk

from shortener.config import Settings


def init_monitoring(settings: Settings) -> bool:
    """Включает Sentry SDK, если задан SENTRY_DSN. DSN в коде не хранится."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        # Bugsink принимает только ошибки, трассировки ему не нужны.
        traces_sample_rate=0,
        send_default_pii=False,
    )
    return True
