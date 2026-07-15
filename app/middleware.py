"""FastAPI middleware: rate limiting, request tracing, logging."""
import hashlib
import ipaddress
import logging
import threading
import time
import uuid
from collections import defaultdict
from typing import Protocol

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.log_context import bind_request_context, clear_request_context

logger = logging.getLogger(__name__)
log = structlog.get_logger("app.middleware")

# Cap on accepted incoming X-Request-ID length. Anything longer (or containing
# whitespace/newlines) is treated as untrusted and replaced with a fresh UUID
# to prevent header/log injection.
MAX_REQUEST_ID_LEN = 128

MAX_STORE_KEYS = 10_000

RATE_LIMITS = {
    "default": (500, 60),       # 500 requests per 60 seconds
    "scan": (50, 60),           # 50 scans per 60 seconds
    "generate": (100, 60),      # 100 generations per 60 seconds
    "auth": (50, 300),          # 50 auth attempts per 5 minutes
    # Loose bucket for browser-sourced logs. Client errors can be bursty
    # (a render loop throwing on every paint) so we keep this permissive
    # and well above the default to avoid starving real traffic.
    "client_log": (120, 60),    # 120 client events per 60 seconds
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
        # ponytail: single lock covers the whole store, not per-key — fine at
        # this store's size/QPS; per-key locks only if this becomes a hot path.
        self._lock = threading.Lock()

    def hit(self, key: str, max_requests: int, window: float) -> float | None:
        now = time.time()

        with self._lock:
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
        with self._lock:
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
    # Dedicated loose bucket for client telemetry — bursty browser errors
    # must not trip the default limiter and block real API traffic.
    if path.startswith("/v1/telemetry/client-event"):
        return "client_log"
    for prefix, limit_type in SLOW_ENDPOINTS.items():
        if path.startswith(prefix):
            # Stricter scan/generate limits only apply to mutating requests
            if limit_type in ("scan", "generate") and method != "POST":
                return "default"
            return limit_type
    return "default"


def _resolve_request_id(request: Request) -> str:
    """Return a request id, honoring a sane incoming ``X-Request-ID`` header.

    An incoming header is only trusted when it is reasonably short and free of
    whitespace/newlines; otherwise we generate a fresh full UUID. This avoids
    header/log injection while still allowing upstream proxies/services to
    propagate trace ids. The full (untruncated) UUID is used for production
    uniqueness.
    """
    incoming = request.headers.get("x-request-id")
    if incoming:
        incoming = incoming.strip()
        if incoming and len(incoming) <= MAX_REQUEST_ID_LEN and not any(c.isspace() for c in incoming):
            return incoming
    return str(uuid.uuid4())


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = _resolve_request_id(request)
        request.state.request_id = request_id
        # Bind request_id onto the structlog contextvar scope so EVERY log line
        # emitted during this request — including the RateLimitMiddleware 429
        # path, which runs AFTER tracing in the execution chain — carries it.
        # Cleared in finally so context never leaks across requests.
        bind_request_context(request_id, route=request.url.path)
        log.info("request.start", method=request.method, path=request.url.path)
        start = time.time()
        try:
            response = await call_next(request)
            # Identity fields (user_id/workspace_id) are bound onto request.state
            # by deps (get_current_user / get_current_workspace). project_id is
            # bound onto contextvars by get_active_project; contextvars propagate
            # through BaseHTTPMiddleware's call_next since both run in the same
            # asyncio task. Read project_id from contextvars with request.state
            # as a fallback.
            import structlog.contextvars as _ctxvars

            _cv = _ctxvars.get_contextvars()
            # Prefer the matched route template over raw path to avoid
            # high-cardinality / user-controlled path segments in logs.
            route = getattr(request.scope.get("route"), "path", request.url.path)
            log.info(
                "request.complete",
                method=request.method,
                path=route,
                status_code=response.status_code,
                latency_ms=round((time.time() - start) * 1000, 2),
                user_id=getattr(request.state, "user_id", None),
                workspace_id=getattr(request.state, "workspace_id", None),
                project_id=_cv.get("project_id") or getattr(request.state, "project_id", None),
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_context()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        key = _rate_limit_key(request)
        limit_type = _resolve_limit_type(request.url.path, request.method)
        max_requests, window = RATE_LIMITS[limit_type]

        retry_after = _backend.hit(f"{key}:{limit_type}", max_requests, window)
        if retry_after is not None:
            log.warning(
                "rate_limited",
                limit_type=limit_type,
                max_requests=max_requests,
                window=window,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Limit: {max_requests} per {window}s. Please wait."},
                headers={"Retry-After": str(int(retry_after))},
            )

        return await call_next(request)
