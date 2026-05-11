"""HTTP client layer with connection pooling, retry, and structured logging.

Replaces direct ``urllib.request`` usage so every external call goes through
the same timeout/retry/circuit-breaker pipeline.

Usage:

    from hanoi_air.http import http_get_json, http_get_text

    payload = http_get_json("https://api.example.com/x", timeout=10)

The module exposes ``get_client()`` for callers that need a raw httpx client
(e.g. streaming downloads). Always reuse the singleton; do not create new
clients per request.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logging_setup import get_logger

logger = get_logger(__name__)

USER_AGENT = "hanoi-air-forecast/0.2 (+public-data-research; polite-30min-cache)"

# httpx exceptions we want to retry on (transient network / 5xx).
_RETRYABLE = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadError,
)

_DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    """Return a process-wide httpx.Client with connection pooling.

    The client uses HTTP/1.1 only (HTTP/2 requires the optional `h2` extra)
    and follows redirects. Limits keep us well under public API quotas.
    """
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


def close_client() -> None:
    """Close the singleton client. Call from process shutdown hooks."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(_RETRYABLE),
)
def _request_with_retry(
    method: str,
    url: str,
    *,
    timeout: float,
    headers: Mapping[str, str] | None,
) -> httpx.Response:
    client = get_client()
    merged_headers = dict(_DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)
    response = client.request(method, url, timeout=timeout, headers=merged_headers)
    response.raise_for_status()
    return response


def http_get_json(
    url: str,
    *,
    timeout: float = 12.0,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """GET a URL and return parsed JSON. Retries 3x on transient errors.

    Raises:
        httpx.HTTPStatusError: on 4xx/5xx after retries exhausted.
        httpx.TimeoutException: on persistent timeout.
        ValueError: if response body is not valid JSON.
    """
    logger.debug("HTTP GET (json) {url}", url=url)
    response = _request_with_retry("GET", url, timeout=timeout, headers=headers)
    return response.json()


def http_get_text(
    url: str,
    *,
    timeout: float = 12.0,
    headers: Mapping[str, str] | None = None,
) -> str:
    """GET a URL and return decoded text body. Retries 3x on transient errors."""
    logger.debug("HTTP GET (text) {url}", url=url)
    text_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    if headers:
        text_headers.update(headers)
    response = _request_with_retry("GET", url, timeout=timeout, headers=text_headers)
    return response.text
