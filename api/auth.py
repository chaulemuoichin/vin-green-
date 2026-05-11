"""API authentication and authorization."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from hanoi_air.config import get_settings


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """
    Verify API key from X-API-Key header.
    
    Raises:
        HTTPException: If API key is missing or invalid (401 Unauthorized)
    """
    settings = get_settings()
    
    # If no API keys configured, allow all requests
    if not settings.api_keys:
        return "default"
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check against configured API keys
    api_keys = [key.strip() for key in settings.api_keys.split(",")]
    if x_api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return x_api_key


def get_api_key_for_rate_limit(x_api_key: str | None = Header(None)) -> str:
    """
    Extract API key for rate limiting. Used by slowapi.
    """
    return x_api_key or "anonymous"
