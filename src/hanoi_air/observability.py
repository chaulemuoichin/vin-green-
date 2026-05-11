"""Error tracking + observability bootstrap.

Currently wires Sentry SDK. Future phases will add Prometheus metrics here.

Sentry is opt-in via ``SENTRY_DSN`` env var. If unset, ``init_sentry`` is a
no-op. The SDK is imported lazily so production images that don't ship Sentry
do not crash.
"""

from __future__ import annotations

import os
from typing import Literal

from .logging_setup import get_logger

logger = get_logger(__name__)

_initialized = False


def init_sentry(
    *,
    service: Literal["api", "worker", "dashboard", "cli"],
    environment: str | None = None,
    traces_sample_rate: float = 0.05,
) -> bool:
    """Initialise Sentry for the given process role.

    Returns True if Sentry was configured, False otherwise. Safe to call
    multiple times — only the first call has effect.
    """
    global _initialized
    if _initialized:
        return True

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.debug("SENTRY_DSN not set; skipping Sentry init for service={s}", s=service)
        return False

    try:
        import sentry_sdk  # type: ignore
        from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore
    except ImportError:
        logger.warning("sentry-sdk not installed; SENTRY_DSN set but skipping init")
        return False

    integrations = [
        LoggingIntegration(level=None, event_level=None),  # let loguru drive
    ]

    # Optional service-specific integrations.
    if service == "api":
        try:
            from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore
            from sentry_sdk.integrations.starlette import StarletteIntegration  # type: ignore

            integrations.extend([StarletteIntegration(), FastApiIntegration()])
        except ImportError:
            pass
    elif service == "worker":
        try:
            from sentry_sdk.integrations.celery import CeleryIntegration  # type: ignore

            integrations.append(CeleryIntegration())
        except ImportError:
            pass

    sentry_sdk.init(
        dsn=dsn,
        environment=environment or os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("HANOI_AIR_RELEASE", "0.2.0"),
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,  # don't leak request bodies / coords
        integrations=integrations,
    )
    # Tag every event with the service so we can filter in the UI.
    sentry_sdk.set_tag("service", service)

    _initialized = True
    logger.info("Sentry initialised for service={s}", s=service)
    return True
