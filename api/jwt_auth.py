"""JWT layer on top of the X-API-Key auth.

Flow:
    1. Client POSTs ``/auth/token`` with ``X-API-Key: <key>`` and gets back
       a HS256 JWT signed with ``settings.jwt_secret``.
    2. Client calls ``/forecast`` or ``/alerts`` with either
       ``X-API-Key: <key>`` *or* ``Authorization: Bearer <jwt>``.

The X-API-Key path stays — JWT is additive, not a replacement, so existing
curl examples and clients keep working.

If ``JWT_SECRET`` is unset, the ``/auth/token`` endpoint returns 503; the
JWT bearer auth degrades to "ignore" and the X-API-Key gate alone is used.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException, status

from hanoi_air.config import get_settings


class JwtUnavailable(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT not configured: set JWT_SECRET to enable token issuance.",
        )


def issue_token(api_key: str, scopes: list[str] | None = None) -> dict[str, Any]:
    """Mint a HS256 JWT for an already-validated API key."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise JwtUnavailable()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.jwt_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": api_key,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": settings.jwt_issuer,
    }
    if scopes:
        payload["scopes"] = scopes
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_ttl_minutes * 60,
        "issued_at": now.isoformat(),
    }


def verify_bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """Return the JWT ``sub`` claim if a valid bearer is present, else None.

    Returning ``None`` (instead of raising) lets callers fall back to the
    X-API-Key gate so both auth modes work side-by-side. A *present but
    invalid* token still raises 401 — we never silently accept a bad token.
    """
    settings = get_settings()
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    if not settings.jwt_secret:
        # Header supplied a bearer but the server is not configured for JWT.
        # Fall through to API-key auth rather than failing hard.
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT: {exc}.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return str(payload.get("sub") or "default")
