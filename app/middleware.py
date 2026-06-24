"""FastAPI middleware: rate limiting, request tracing, logging."""
import hashlib
import ipaddress
import logging
import time
import uuid
from collections import defaultdict
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

MAX_STORE_KEYS = 10_000

RATE_LIMITS = {
    "default": (500, 60),       # 500 requests per 60 seconds
    "scan": (50, 60),           # 50 scans per 60 seconds
    "generate": (100, 60),      # 100 generations per 60 seconds
    "auth": (50, 300),          # 50 auth attempts per 5 minutes
}

SLOW_ENDPOINTS = {
    "/v1/scans": "scan",
    "/v1/drafts/replies": "generate",
    "/v1/drafts/posts": "generate",
    "/v1/brand/": "generate",
    "/v1/personas/generate": "generate",
    "/v1/discovery/keywords/generate": "generate",
    "/v1/discovery/subreddits/discover": "generate",
    "/v1/auth/register": "auth",
    "/v1/auth/oauth-complete": "auth",
}


class RateLimitBackend(Protocol):
    """Storage backend for the sliding-window rate limiter.

    The in-memory default is process-local and therefore only correct for
    single-worker deployments (the current Railway setup). A shared backend
    (e.g. Redis) can be swapped in via ``set_rate_limit_backend`` without
    touching the middleware.
    """

    def hit(self, key: str, max_requests: int, window: float) -> float | None:
        """Record one request. Return None when allowed, else retry-after seconds."""
        ...

    def reset(self) -> None: ...


class InMemoryRateLimitBackend:
    def __init__(self, max_keys: int = MAX_STORE_KEYS) -> None:
        self._store: defaultdict[str, list[float]] = defaultdict(list)
        self._max_keys = max_keys

    def hit(self, key: str, max_requests: int, window: float) -> float | None:
        now = time.time()

        # Prune expired entries for this key
        self._store[key] = [t for t in self._store[key] if t > now - window]

        # Periodically clean up the store to prevent unbounded memory growth
        if len(self._store) > self._max_keys:
            expired_keys = [
                k for k, v in self._store.items()
                if not v or max(v) < now - 300  # no activity in 5 min
            ]
            for k in expired_keys:
                del self._store[k]

        if len(self._store[key]) >= max_requests:
            earliest = min(self._store[key])
            return window - (now - earliest) + 1

        self._store[key].append(now)
        return None

    def reset(self) -> None:
        self._store.clear()


_backend: RateLimitBackend = InMemoryRateLimitBackend()


def set_rate_limit_backend(backend: RateLimitBackend) -> None:
    global _backend
    _backend = backend


def reset_rate_limit_store() -> None:
    """Clear rate limit state, primarily for isolated test runs."""
    _backend.reset()


def _is_trusted_proxy_ip(ip_str: str) -> bool:
    """Return True when ``ip_str`` is a private / loopback / link-local address.

    Forwarding headers (X-Forwarded-For, X-Real-IP) are only honored when the
    *direct* connection comes from a trusted proxy. This prevents attackers
    from spoofing arbitrary client IPs to evade rate limiting (Issue: PR review).
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def _get_client_ip(request: Request) -> str:
    """Resolve the real client IP, accounting for reverse proxies.

    Only trusts forwarding headers (X-Forwarded-For, X-Real-IP) when the direct
    connection comes from a private/loopback address (i.e. an internal proxy).
    When the direct connection is a public IP, the proxy headers are ignored
    to prevent IP-spoofing-based rate-limit evasion (Issue: PR review).
    """
    direct_ip = request.client.host if request.client else ""
    headers_trusted = bool(direct_ip) and _is_trusted_proxy_ip(direct_ip)

    if headers_trusted:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For is a comma-separated list; the leftmost entry is
            # the original client. Strip whitespace and take the first valid IP.
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
    return direct_ip or "unknown"


def _rate_limit_key(request: Request) -> str:
    """Derive a privacy-preserving rate limit key from auth header or IP."""
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        # Hash the token instead of using raw suffix — prevents token leakage
        return hashlib.sha256(auth_header.encode("utf-8")).hexdigest()[:16]
    return _get_client_ip(request)


def _resolve_limit_type(path: str, method: str) -> str:
    """Match path with prefix support for rate limit categories."""
    for prefix, limit_type in SLOW_ENDPOINTS.items():
        if path.startswith(prefix):
            # Stricter scan/generate limits only apply to mutating requests
            if limit_type in ("scan", "generate") and method != "POST":
                return "default"
            return limit_type
    return "default"


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)",
            extra={"request_id": request_id},
        )
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        key = _rate_limit_key(request)
        limit_type = _resolve_limit_type(request.url.path, request.method)
        max_requests, window = RATE_LIMITS[limit_type]

        retry_after = _backend.hit(f"{key}:{limit_type}", max_requests, window)
        if retry_after is not None:
            logger.warning(f"Rate limit hit: {key}:{limit_type} ({limit_type})")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Limit: {max_requests} per {window}s. Please wait."},
                headers={"Retry-After": str(int(retry_after))},
            )

        return await call_next(request)
