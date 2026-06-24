"""Shared HTTP retry helper with exponential backoff.

Used by all LLM providers for transient error recovery (429, 5xx, connection
errors). Permanent errors (4xx except 429) are never retried.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, TypeVar

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_RETRIES = 5
_INITIAL_BACKOFF = 2.0
_MAX_BACKOFF = 60.0

# Status codes that should trigger a retry (transient failures).
_RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# OpenAI SDK exception types that indicate transient failures. We import these
# lazily so the retry helper can be used even when the OpenAI SDK is not
# installed.
def _openai_transient_types() -> tuple[type, ...]:
    """Return the tuple of OpenAI SDK exception types considered transient.

    Only imported on first use; if openai is not installed, returns ().
    """
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        )
    except ImportError:
        return ()
    return (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)


def _extract_retry_after(response: httpx.Response, default: float) -> float:
    """Parse Retry-After header, falling back to default backoff."""
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return min(float(retry_after), _MAX_BACKOFF)
        except ValueError:
            pass
    return default


def retry_http(
    fn: Callable[[], T],
    *,
    provider_name: str,
    max_retries: int = _MAX_RETRIES,
    initial_backoff: float = _INITIAL_BACKOFF,
) -> T:
    """Execute ``fn`` with exponential-backoff retry on transient HTTP errors.

    Retries on:
      - httpx HTTPStatusError when status is in _RETRY_STATUS_CODES
      - httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError
      - httpx.PoolTimeout, httpx.ConnectTimeout
      - OpenAI SDK transient types (when openai is installed):
        APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

    Does NOT retry on permanent errors (400, 401, 403, 404, validation errors).

    Re-raises the last exception after exhausting retries.
    """
    backoff = initial_backoff
    last_exc: Exception | None = None
    openai_transient = _openai_transient_types()

    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            if status not in _RETRY_STATUS_CODES:
                # Permanent error - do not retry.
                raise
            if attempt >= max_retries:
                logger.warning(
                    "%s HTTP %d (attempt %d/%d), exhausted retries.",
                    provider_name, status, attempt, max_retries,
                )
                break
            wait = _extract_retry_after(exc.response, backoff)
            logger.warning(
                "%s HTTP %d (attempt %d/%d), retrying in %.1fs",
                provider_name, status, attempt, max_retries, wait,
            )
            time.sleep(wait)
            backoff = min(backoff * 2, _MAX_BACKOFF)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError,
                httpx.PoolTimeout, httpx.ConnectTimeout) as exc:
            last_exc = exc
            if attempt >= max_retries:
                logger.warning(
                    "%s connection error: %s (attempt %d/%d), exhausted retries.",
                    provider_name, exc, attempt, max_retries,
                )
                break
            wait = backoff
            logger.warning(
                "%s connection error: %s (attempt %d/%d), retrying in %.1fs",
                provider_name, exc, attempt, max_retries, wait,
            )
            time.sleep(wait)
            backoff = min(backoff * 2, _MAX_BACKOFF)
        except Exception as exc:
            # OpenAI SDK transient exceptions (only present when openai is
            # installed). Anything else is propagated without retry.
            if openai_transient and isinstance(exc, openai_transient):
                last_exc = exc
                if attempt >= max_retries:
                    logger.warning(
                        "%s OpenAI SDK error: %s (attempt %d/%d), exhausted retries.",
                        provider_name, exc, attempt, max_retries,
                    )
                    break
                wait = backoff
                logger.warning(
                    "%s OpenAI SDK error: %s (attempt %d/%d), retrying in %.1fs",
                    provider_name, exc, attempt, max_retries, wait,
                )
                time.sleep(wait)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            raise

    # Exhausted retries - re-raise the last exception.
    assert last_exc is not None
    raise last_exc
