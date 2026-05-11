"""Hybrid live/demo Hanoi air quality forecasting toolkit."""

import os as _os

from .logging_setup import configure_logging as _configure_logging

# Auto-configure once at import time; entrypoints can call configure_logging
# again explicitly to change level/format.
_configure_logging(level=_os.getenv("HANOI_AIR_LOG_LEVEL", "INFO"))

__all__ = ["__version__", "configure_logging"]
__version__ = "0.2.0"

# Re-export for ergonomic `from hanoi_air import configure_logging`
configure_logging = _configure_logging
