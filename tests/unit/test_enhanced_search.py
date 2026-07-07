from __future__ import annotations

from app.db.tables.search_cache import get_cached_search_result, upsert_search_result
from app.services.search.service import make_search_cache_key


def test_search_cache_key_is_stable() -> None:
    first = make_search_cache_key(1, "web", "Refund policy", {"limit": 10})
    second = make_search_cache_key(1, "web", "refund policy", {"limit": 10})
    different = make_search_cache_key(1, "web", "refund policy", {"limit": 20})

    assert first == second
    assert first != different


def test_search_cache_roundtrip(mock_supabase) -> None:
    cache_key = make_search_cache_key(1, "web", "query", {"limit": 5})
    upsert_search_result(
        mock_supabase,
        workspace_id=1,
        provider="web",
        query="query",
        cache_key=cache_key,
        result={"results": [{"title": "A", "url": "https://example.com", "source": "web"}]},
        ttl_seconds=60,
    )

    cached = get_cached_search_result(mock_supabase, cache_key)

    assert cached is not None
    assert cached["provider"] == "web"
    assert cached["result"]["results"][0]["title"] == "A"
