"""API authentication and authorization.

Two auth modes are supported, additive:

    1. ``X-API-Key: <key>`` — validated against ``settings.api_keys`` (CSV).
    2. ``Authorization: Bearer <jwt>`` — HS256 JWT minted at /auth/token.

When ``API_KEYS`` is unset the API is fully open (development mode).
When set, either auth mode is sufficient. Both modes share rate-limit
buckets — slowapi keys on the X-API-Key value, falling back to the
JWT subject and finally "anonymous".
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from api.jwt_auth import verify_bearer_token
from hanoi_air.config import get_settings


def _valid_api_keys() -> list[str]:
    settings = get_settings()
    if not settings.api_keys:
        return []
    return [key.strip() for key in settings.api_keys.split(",") if key.strip()]


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Accept either an X-API-Key or a bearer JWT.

    Returns the authenticated principal (api key or JWT subject).
    Raises 401 if neither mode succeeds *and* keys are configured.
    """
    settings = get_settings()

    # Dev mode — no keys configured at all.
    if not settings.api_keys:
        return "default"

    # Path 1: bearer JWT. verify_bearer_token returns None when no bearer
    # header is present (or the server has no JWT secret), or raises 401
    # when a bearer header is *present but invalid*.
    subject = verify_bearer_token(authorization=authorization)
    if subject is not None:
        return subject

    # Path 2: X-API-Key.
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header or Bearer JWT.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if x_api_key not in _valid_api_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_api_key


def verify_api_key_only(
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """Strict X-API-Key check (no bearer fallback).

    Used by ``/auth/token`` so callers cannot mint a JWT using another JWT.
    """
    settings = get_settings()
    if not settings.api_keys:
        return "default"
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if x_api_key not in _valid_api_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_api_key


def get_api_key_for_rate_limit(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
) -> str:
    """Extract a rate-limit bucket key.

    Prefers the X-API-Key value. Falls back to a short JWT prefix so that
    bearer-only clients are still tracked separately from anonymous.
    """
    if x_api_key:
        return x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            return f"jwt:{token[:16]}"
    return "anonymous"
