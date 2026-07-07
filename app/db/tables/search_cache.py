"""Search cache table helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

SEARCH_CACHE_TABLE = "search_cache"


def _get_search_row_by_key(db: Client, cache_key: str) -> dict[str, Any] | None:
    result = db.table(SEARCH_CACHE_TABLE).select("*").eq("cache_key", cache_key).execute()
    return result.data[0] if result.data else None


def get_cached_search_result(db: Client, cache_key: str) -> dict[str, Any] | None:
    row = _get_search_row_by_key(db, cache_key)
    if not row:
        return None
    expires_at = row.get("expires_at")
    if expires_at:
        try:
            expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError:
            return None
        if expires <= datetime.now(UTC):
            return None
    return row


def upsert_search_result(
    db: Client,
    *,
    workspace_id: int,
    provider: str,
    query: str,
    cache_key: str,
    result: dict[str, Any],
    ttl_seconds: int,
) -> dict[str, Any] | None:
    expires_at = datetime.now(UTC) + timedelta(seconds=max(ttl_seconds, 0))
    payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "query": query,
        "cache_key": cache_key,
        "result": result,
        "expires_at": expires_at.isoformat(),
    }
    existing = _get_search_row_by_key(db, cache_key)
    if existing:
        response = db.table(SEARCH_CACHE_TABLE).update(payload).eq("cache_key", cache_key).execute()
    else:
        response = db.table(SEARCH_CACHE_TABLE).insert(payload).execute()
    return response.data[0] if response.data else None
