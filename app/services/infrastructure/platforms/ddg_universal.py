import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from ddgs import DDGS

from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedPost

logger = logging.getLogger(__name__)

class DDGUniversalAdapter(PlatformAdapter):
    """Universal scraper using DuckDuckGo search to bypass platform rate limits and 403s.

    Translates platform queries into site-specific dorks (e.g., site:linkedin.com/posts).
    """

    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name
        super().__init__()

        # Map platform names to their DDG site query prefixes
        self._site_map = {
            "reddit": "site:reddit.com/r",
            "linkedin": "site:linkedin.com/posts",
            "instagram": "site:instagram.com/p",
            "indiehackers": "site:indiehackers.com/post",
            "hackernews": "site:news.ycombinator.com",
            "github": "site:github.com",
        }
        self.subreddits = []

    def set_subreddits(self, subreddits: list[str]) -> None:
        """Store subreddits to be used during search (only applicable if platform is reddit)."""
        self.subreddits = subreddits

    def _search_sync(self, query: str, limit: int) -> list[dict[str, str]]:
        """Synchronous DDGS search."""
        try:
            return list(DDGS().text(query, max_results=limit))
        except Exception as e:
            logger.error("[%s] DDGS search failed for %s: %s", self.platform_name, query, e)
            return []

    async def search_posts(self, keywords: list[str], *, limit: int = 50, sort: str = "relevance", time_filter: str = "week", fetch_comments: bool = False) -> list[UnifiedPost]:
        site = self._site_map.get(self.platform_name)
        if not site:
            logger.error("[%s] Unsupported platform in DDGUniversalAdapter", self.platform_name)
            return []

        if not keywords:
            return []

        # For reddit, if subreddits are specified, build a custom site constraint
        if self.platform_name == "reddit" and getattr(self, "subreddits", None):
            # Create e.g. (site:reddit.com/r/foo OR site:reddit.com/r/bar)
            site_parts = " OR ".join(f"site:reddit.com/r/{sub.strip()}" for sub in self.subreddits[:5]) # Limit to 5 to avoid overly long queries
            site = f"({site_parts})"

        # DuckDuckGo fails on very long queries (e.g. 10 keywords joined by OR)
        # To guarantee results, we'll do individual searches for the top 3 most important keywords
        # and merge the results.
        top_keywords = keywords[:3]

        loop = asyncio.get_running_loop()
        all_raw_results = []

        for kw in top_keywords:
            query = f'{site} "{kw}"'
            logger.info("[%s] Running DDG search: %s", self.platform_name, query)

            # Divide the limit so we don't fetch way too much overall
            per_kw_limit = max(5, limit // len(top_keywords))
            try:
                raw_results = await loop.run_in_executor(None, self._search_sync, query, per_kw_limit)
                all_raw_results.extend(raw_results)
            except Exception as e:
                logger.error("[%s] Search failed for kw %s: %s", self.platform_name, kw, e)

        # Deduplicate by URL
        seen_urls = set()
        posts = []

        for res in all_raw_results:
            url = res.get("href", "")
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            title = res.get("title", "")
            body = res.get("body", "")

            # Generate a consistent ID since DDG doesn't provide the native post ID
            post_id = f"ddg-{self.platform_name}-{hash(url)}"

            posts.append(UnifiedPost(
                platform=self.platform_name,
                external_id=post_id,
                author="unknown",
                author_id="unknown",
                title=title,
                body=body,
                url=url,
                subreddit=None,
                hashtags=[],
                upvotes=0,
                comments_count=0,
                shares=0,
                views=0,
                created_at=datetime.now(UTC),
                media_urls=[],
                raw_data=res
            ))

        logger.info("[%s] DDG search returned %d deduplicated results", self.platform_name, len(posts))
        return posts

    async def get_post_comments(self, post_id: str, *, limit: int = 20) -> list[Any]:
        return []

    async def get_trending(self, *, topic: str | None = None, limit: int = 25) -> list[UnifiedPost]:
        return []

    async def health_check(self) -> bool:
        return True
