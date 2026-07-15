"""Supabase client module for database operations.

This module provides a singleton Supabase client and FastAPI dependency
for use throughout the application.
"""

import contextlib
import logging
from collections.abc import Generator
from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get or create the singleton Supabase client instance.

    Returns:
        Configured Supabase client instance.

    Raises:
        ValueError: If Supabase URL or secret key is not configured.
    """
    settings = get_settings()

    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is not configured")

    access_key = settings.supabase_secret_key.get_secret_value()
    if not access_key and settings.environment == "development" and settings.supabase_publishable_key:
        access_key = settings.supabase_publishable_key
        logger.warning(
            "SUPABASE_SECRET_KEY is not configured; using SUPABASE_PUBLISHABLE_KEY for development DB access. "
            "Sign-in can work locally, but admin-only auth flows such as /v1/auth/register still require the service role key."
        )

    if not access_key:
        raise ValueError("SUPABASE_SECRET_KEY is not configured")

    client = create_client(settings.supabase_url, access_key)

    # Force HTTP/1.1 on the PostgREST session to avoid stale-connection
    # errors. supabase-py v2 defaults to HTTP/2 for the postgrest client,
    # but HTTP/2 connection pooling breaks against Supabase's CDN — idle
    # pooled connections get closed server-side, and the next use of the
    # pool raises httpx.RemoteProtocolError("Server disconnected") from
    # deep inside httpcore._sync.http2._read_incoming_data. This surfaces
    # to end users as intermittent 500s on any endpoint that reads from
    # the DB (dashboard, auto-pipeline list, notifications polling).
    # HTTP/1.1 uses shorter-lived connections with Keep-Alive and doesn't
    # exhibit the same pool-staleness issue in long-running dev servers.
    _force_http11_on_postgrest(client)

    return client


def _force_http11_on_postgrest(client: Client) -> None:
    """Swap the PostgREST session's httpx client for one pinned to HTTP/1.1.

    Preserves the original session's base_url, headers, and timeout so
    auth and query routing keep working. The old session is closed so we
    don't leak its connection pool.

    This intentionally reaches into postgrest-py's internal ``.session``
    attribute because supabase-py does not expose a public transport hook for
    the DB client. We only patch PostgREST here: the stale-connection failures
    in this app were isolated to database traffic, while the other Supabase
    sub-clients were not exhibiting the same issue. The replacement session is
    stored on the process-wide singleton for the server lifetime.
    """
    existing = client.postgrest.session
    new_session = httpx.Client(
        base_url=existing.base_url,
        headers=existing.headers,
        timeout=existing.timeout,
        http2=False,
    )
    # Don't let cleanup of the old session block the hot-path.
    with contextlib.suppress(Exception):
        existing.close()
    client.postgrest.session = new_session


def get_supabase() -> Generator[Client, None, None]:
    """FastAPI dependency that yields the Supabase client.

    Yields:
        Supabase client instance for use in route handlers.

    Example:
        @router.get("/items")
        def list_items(supabase: Client = Depends(get_supabase)):
            result = supabase.table("items").select("*").execute()
            return result.data
    """
    client = get_supabase_client()
    try:
        yield client
    finally:
        # Supabase client doesn't require explicit cleanup
        pass


def get_supabase_optional() -> Client | None:
    """Like ``get_supabase``, but returns ``None`` instead of raising.

    FastAPI resolves ``Depends()`` parameters before a route's body runs, so
    a route that depends on ``get_supabase`` can't catch a construction
    failure (e.g. missing SUPABASE_URL) itself — it propagates as a bare 500
    before the handler ever executes. /health and /ready use this instead so
    a misconfigured Supabase client produces a graceful degraded/503
    response. Tests overriding ``get_supabase`` should override this too.
    """
    try:
        return get_supabase_client()
    except Exception:
        return None
