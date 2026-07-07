"""Enhanced search integrations with optional Supabase-backed caching."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.db.tables.search_cache import get_cached_search_result, upsert_search_result
from app.schemas.v1.search import SearchCitation, SearchItem, SearchResponse
from app.services.product.reddit_discovery import RedditDiscoveryService
from app.services.product.twitter_discovery import TwitterDiscoveryService

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)


def make_search_cache_key(workspace_id: int, provider: str, query: str, params: dict[str, Any] | None = None) -> str:
    payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "query": query.strip().lower(),
        "params": params or {},
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class EnhancedSearchService:
    """Search facade for Reddit, X/Twitter, and web fact-checking."""

    def __init__(self, db: Client, workspace_id: int) -> None:
        self.db = db
        self.workspace_id = workspace_id
        self.settings = get_settings()

    def _cached_response(
        self,
        *,
        provider: str,
        query: str,
        cache_key: str,
        use_cache: bool,
    ) -> SearchResponse | None:
        if not use_cache or not self.settings.enable_enhanced_search:
            return None
        try:
            cached = get_cached_search_result(self.db, cache_key)
        except Exception:
            logger.debug("Search cache lookup failed for %s", cache_key, exc_info=True)
            return None
        if not cached:
            return None
        result = cached.get("result") or {}
        return SearchResponse(
            provider=provider,
            query=query,
            cache_key=cache_key,
            cached=True,
            results=[SearchItem.model_validate(item) for item in result.get("results", [])],
            citations=[SearchCitation.model_validate(item) for item in result.get("citations", [])],
        )

    def _store_response(self, response: SearchResponse) -> None:
        if self.settings.search_cache_ttl_seconds <= 0:
            return
        try:
            upsert_search_result(
                self.db,
                workspace_id=self.workspace_id,
                provider=response.provider,
                query=response.query,
                cache_key=response.cache_key,
                result={
                    "results": [item.model_dump(mode="json") for item in response.results],
                    "citations": [item.model_dump(mode="json") for item in response.citations],
                },
                ttl_seconds=self.settings.search_cache_ttl_seconds,
            )
        except Exception:
            logger.debug("Search cache write failed for %s", response.cache_key, exc_info=True)

    def search_reddit(
        self,
        query: str,
        *,
        subreddits: list[str] | None = None,
        limit: int = 10,
        use_cache: bool = True,
    ) -> SearchResponse:
        provider = "reddit"
        cache_key = make_search_cache_key(
            self.workspace_id,
            provider,
            query,
            {"subreddits": subreddits or [], "limit": limit},
        )
        if cached := self._cached_response(provider=provider, query=query, cache_key=cache_key, use_cache=use_cache):
            return cached

        service = RedditDiscoveryService()
        posts = service.search_posts([query], subreddits=subreddits or None, limit=limit)
        results = [
            SearchItem(
                title=post.title,
                url=post.permalink,
                source=f"r/{post.subreddit}",
                snippet=post.body[:500],
                author=post.author,
                score=post.score,
                comments_count=post.num_comments,
                created_at=post.created_at,
                raw={"post_id": post.post_id, "platform": "reddit"},
            )
            for post in posts[:limit]
        ]
        response = SearchResponse(provider=provider, query=query, cache_key=cache_key, cached=False, results=results)
        self._store_response(response)
        return response

    def search_x(self, query: str, *, limit: int = 10, use_cache: bool = True) -> SearchResponse:
        provider = "x"
        cache_key = make_search_cache_key(self.workspace_id, provider, query, {"limit": limit})
        if cached := self._cached_response(provider=provider, query=query, cache_key=cache_key, use_cache=use_cache):
            return cached

        posts = TwitterDiscoveryService().search_tweets([query], limit=limit)
        results = [
            SearchItem(
                title=post.title or post.body[:80] or "X conversation",
                url=post.url,
                source=post.community or "x",
                snippet=post.body[:500],
                author=post.author,
                score=post.score,
                comments_count=post.num_comments,
                created_at=post.created_at if isinstance(post.created_at, datetime) else None,
                raw={"post_id": post.post_id, "platform": post.platform},
            )
            for post in posts[:limit]
        ]
        response = SearchResponse(provider=provider, query=query, cache_key=cache_key, cached=False, results=results)
        self._store_response(response)
        return response

    def search_web(self, query: str, *, limit: int = 10, use_cache: bool = True) -> SearchResponse:
        provider = "web"
        cache_key = make_search_cache_key(self.workspace_id, provider, query, {"limit": limit})
        if cached := self._cached_response(provider=provider, query=query, cache_key=cache_key, use_cache=use_cache):
            return cached

        results: list[SearchItem] = []
        citations: list[SearchCitation] = []
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=limit):
                    title = str(item.get("title") or item.get("href") or "Web result")
                    url = str(item.get("href") or item.get("url") or "")
                    snippet = str(item.get("body") or item.get("snippet") or "")
                    if not url:
                        continue
                    results.append(SearchItem(title=title, url=url, source="web", snippet=snippet, raw=dict(item)))
                    citations.append(SearchCitation(title=title, url=url, snippet=snippet[:300] if snippet else None))
        except Exception:
            logger.warning("Web search failed for query %r", query, exc_info=True)

        response = SearchResponse(
            provider=provider,
            query=query,
            cache_key=cache_key,
            cached=False,
            results=results[:limit],
            citations=citations[:limit],
        )
        self._store_response(response)
        return response
