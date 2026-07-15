"""Shared RapidAPI HTTP client with retry logic and rate limiting."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter. Guarded by _throttle_lock — without it, two
# concurrent coroutines could both pass the "under quota" check before either
# appends, under-throttling by up to 2x (a TOCTOU race on the same event loop).
_request_timestamps: dict[str, list[float]] = {}
_throttle_lock = asyncio.Lock()

# Circuit breaker: once a host returns 429, skip all further requests
# for that host for this process lifetime (quota is exhausted).
_circuit_broken_hosts: dict[str, float] = {}
_CIRCUIT_BREAK_DURATION = 300  # 5 minutes before retrying a broken host


class RapidAPIError(Exception):
    """Raised when a RapidAPI call fails."""
    def __init__(self, status_code: int, message: str, api_host: str):
        self.status_code = status_code
        self.api_host = api_host
        super().__init__(f"RapidAPI [{api_host}] {status_code}: {message}")


class RapidAPIClient:
    """Async HTTP client for RapidAPI marketplace APIs.

    Handles authentication, retries, and rate limiting.
    All platform adapters use this shared client.
    """

    BASE_URL = "https://{host}"
    MAX_RETRIES = 1           # 1 retry only (fail fast on quota exhaustion)
    RETRY_DELAY = 2.0         # base delay for retries
    REQUESTS_PER_MINUTE = 10  # safety throttle per host

    def __init__(self, api_host: str, *, api_key: str | None = None, timeout: float = 12.0):
        self.api_host = api_host
        self.timeout = timeout
        settings = get_settings()
        self._api_key = api_key or (settings.rapidapi_key.get_secret_value() if settings.rapidapi_key else None)
        if not self._api_key:
            raise ValueError(
                "RAPIDAPI_KEY is not set. Get a free key at https://rapidapi.com "
                "and add RAPIDAPI_KEY=your-key to your .env file."
            )

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-rapidapi-key": self._api_key,
            "x-rapidapi-host": self.api_host,
        }

    @property
    def _cache_key(self) -> str:
        """Unique key for rate limits and circuit breakers (host + key)."""
        # Obfuscate key in memory, just need it to be unique per credential
        key_suffix = f"{self._api_key[-4:]}" if self._api_key else "none"
        return f"{self.api_host}:{key_suffix}"

    async def _throttle(self) -> None:
        """Simple rate limiter: max N requests per minute per host."""
        key = self._cache_key
        while True:
            async with _throttle_lock:
                now = time.monotonic()
                # Remove timestamps older than 60 seconds
                timestamps = [t for t in _request_timestamps.get(key, []) if now - t < 60]
                if len(timestamps) < self.REQUESTS_PER_MINUTE:
                    timestamps.append(now)
                    _request_timestamps[key] = timestamps
                    return
                _request_timestamps[key] = timestamps
                wait = 60 - (now - timestamps[0])

            # Sleep outside the lock so waiting on this host doesn't block
            # throttle checks for other hosts/keys, then re-check on wake —
            # another coroutine may have taken the freed-up slot meanwhile.
            if wait > 0:
                logger.info("Rate limit: waiting %.1fs for %s", wait, key)
                await asyncio.sleep(wait)

    def _is_circuit_broken(self) -> bool:
        """Check if this host+key circuit breaker is active."""
        key = self._cache_key
        broken_at = _circuit_broken_hosts.get(key)
        if broken_at is None:
            return False
        if time.monotonic() - broken_at > _CIRCUIT_BREAK_DURATION:
            # Circuit breaker expired — allow retrying
            del _circuit_broken_hosts[key]
            logger.info("Circuit breaker reset for %s — retrying", key)
            return False
        return True

    async def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a GET request to a RapidAPI endpoint.

        Args:
            endpoint: API path (e.g., "/search" or "/user/posts").
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            RapidAPIError: On non-200 responses after retries.
        """
        return await self._request("GET", endpoint, params=params, extra_headers=extra_headers)

    async def post(
        self,
        endpoint: str,
        *,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a POST request to a RapidAPI endpoint. Same retry/circuit-breaker as :meth:`get`.

        Raises:
            RapidAPIError: On non-200 responses after retries.
        """
        return await self._request("POST", endpoint, json_body=json_body, extra_headers=extra_headers)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        # Circuit breaker: immediately fail if host is known to be exhausted
        if self._is_circuit_broken():
            raise RapidAPIError(429, "API quota exhausted (circuit breaker active)", self.api_host)

        await self._throttle()

        url = f"https://{self.api_host}{endpoint}"
        headers = {**self._get_headers(), **(extra_headers or {})}

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method, url, headers=headers, params=params or {}, json=json_body
                    )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:  # Rate limited
                    if attempt < self.MAX_RETRIES:
                        wait = self.RETRY_DELAY * (2 ** attempt)
                        logger.warning("Rate limited by %s, waiting %.1fs (attempt %d)", self.api_host, wait, attempt + 1)
                        await asyncio.sleep(wait)
                        continue
                    # Exhausted retries — trip the circuit breaker
                    key = self._cache_key
                    _circuit_broken_hosts[key] = time.monotonic()
                    logger.warning(
                        "Circuit breaker tripped for %s — skipping all requests for %ds",
                        key, _CIRCUIT_BREAK_DURATION,
                    )
                    raise RapidAPIError(429, "Rate limited — circuit breaker tripped", self.api_host)

                if response.status_code >= 500:  # Server error, retry
                    wait = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning("Server error %d from %s, retrying in %.1fs", response.status_code, self.api_host, wait)
                    await asyncio.sleep(wait)
                    continue

                # Client error (400, 403, 404) — don't retry
                error_body = response.text[:500]
                raise RapidAPIError(response.status_code, error_body, self.api_host)

            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                raise RapidAPIError(0, str(e), self.api_host) from e

        raise RapidAPIError(0, f"Max retries exceeded: {last_error}", self.api_host)

