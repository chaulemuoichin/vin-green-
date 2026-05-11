"""FastAPI middleware configuration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hanoi_air.config import get_settings


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI app.
    
    Reads allowed origins from settings.cors_allowed_origins env var.
    Default: allow localhost for development.
    """
    settings = get_settings()
    
    # Parse allowed origins (comma-separated)
    allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",")]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Page-Count"],
    )
