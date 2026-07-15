import asyncio
import contextlib
import logging
import random
from datetime import UTC, datetime
from typing import Any

import httpx

from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedPost

logger = logging.getLogger(__name__)


class NativeMultiScraper(PlatformAdapter):
    """Native multi-source scraper implementing free native APIs without RapidAPI."""

    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name
        self._available = True
        self.subreddits: list[str] = []
        # Base class init
        super().__init__()

    def set_subreddits(self, subreddits: list[str]) -> None:
        """Store subreddits to be used during search."""
        self.subreddits = subreddits

    async def search_posts(self, keywords: list[str], *, limit: int = 50, sort: str = "relevance", time_filter: str = "week", fetch_comments: bool = False) -> list[UnifiedPost]:
        """Route to the correct native implementation based on platform_name."""
        if self.platform_name == "hackernews":
            return await self._scrape_hackernews(keywords, limit)
        elif self.platform_name == "github":
            return await self._search_github_issues(keywords, limit)
        elif self.platform_name == "reddit_native":
            return await self._scrape_reddit_subreddit(keywords, limit)
        elif self.platform_name == "indiehackers":
            return await self._scrape_indiehackers_posts(keywords, limit)
        else:
            logger.error("[%s] Unsupported native platform", self.platform_name)
            return []

    async def get_post_comments(self, post_id: str, *, limit: int = 20) -> list[Any]:
        # For simplicity, returning empty comments for now, as we focus on opportunities
        return []

    async def get_trending(self, *, topic: str | None = None, limit: int = 25) -> list[UnifiedPost]:
        return []

    async def health_check(self) -> bool:
        return True

    # -------------------------------------------------------------------------
    # HackerNews (Algolia)
    # -------------------------------------------------------------------------
    async def _scrape_hackernews(self, keywords: list[str], limit: int) -> list[UnifiedPost]:
        query = " OR ".join(keywords)
        import urllib.parse
        query_encoded = urllib.parse.quote_plus(query)
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={query_encoded}&tags=story&hitsPerPage={limit}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    logger.warning("[hackernews] Search failed: HTTP %s", response.status_code)
                    return []
                data = response.json()
            except Exception as e:
                logger.exception("[hackernews] API error: %s", e)
                return []

        results = []
        for hit in data.get('hits', []):
            try:
                object_id = str(hit.get('objectID'))
                title = hit.get('title', '')
                url_link = hit.get('url') or f"https://news.ycombinator.com/item?id={object_id}"
                points = int(hit.get('points') or 0)
                comments = int(hit.get('num_comments') or 0)

                created_at_str = hit.get('created_at')
                created_at = datetime.now(UTC)
                if created_at_str:
                    with contextlib.suppress(Exception):
                        # e.g. "2023-01-01T12:00:00Z"
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                results.append(UnifiedPost(
                    platform="hackernews",
                    external_id=object_id,
                    author=hit.get('author', 'unknown'),
                    author_id=hit.get('author', 'unknown'),
                    title=title,
                    body="",  # HN doesn't return full body here usually
                    url=url_link,
                    subreddit=None,
                    hashtags=hit.get('_tags', []),
                    upvotes=points,
                    comments_count=comments,
                    shares=0,
                    views=0,
                    created_at=created_at,
                    media_urls=[],
                    raw_data=hit
                ))
            except Exception as e:
                logger.debug("Failed to parse HN hit: %s", e)

        return results

    # -------------------------------------------------------------------------
    # GitHub Issues
    # -------------------------------------------------------------------------
    async def _search_github_issues(self, keywords: list[str], limit: int) -> list[UnifiedPost]:
        query = " ".join(keywords) + " is:issue"
        import urllib.parse
        query_encoded = urllib.parse.quote_plus(query)
        url = f"https://api.github.com/search/issues?q={query_encoded}&per_page={limit}&sort=created"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SocialAI-Scraper'
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.get(url, headers=headers, timeout=10.0)
                    if response.status_code == 403:
                        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        if remaining == 0:
                            wait_time = max(reset_time - datetime.now(UTC).timestamp(), 0)
                            if wait_time < 10:
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.warning("[github] Rate limit exceeded, reset in %s s", wait_time)
                                return []
                    if response.status_code != 200:
                        logger.warning("[github] Search failed: HTTP %s", response.status_code)
                        return []

                    data = response.json()
                    break
                except Exception as e:
                    logger.exception("[github] API error attempt %s: %s", attempt, e)
                    if attempt == 2:
                        return []
                    await asyncio.sleep(2 ** attempt)

        if 'items' not in data:
            return []

        results = []
        for item in data['items']:
            try:
                object_id = str(item.get('id', item.get('number')))
                created_at_str = item.get('created_at')
                created_at = datetime.now(UTC)
                if created_at_str:
                    with contextlib.suppress(Exception):
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                labels = [label['name'] for label in item.get('labels', [])]

                results.append(UnifiedPost(
                    platform="github",
                    external_id=object_id,
                    author=item.get('user', {}).get('login', 'unknown'),
                    author_id=str(item.get('user', {}).get('id', '')),
                    title=item.get('title', ''),
                    body=item.get('body', ''),
                    url=item.get('html_url', ''),
                    subreddit=None,
                    hashtags=labels,
                    upvotes=0, # issues don't have upvotes in search easily
                    comments_count=item.get('comments', 0),
                    shares=0,
                    views=0,
                    created_at=created_at,
                    media_urls=[],
                    raw_data=item
                ))
            except Exception as e:
                logger.debug("Failed to parse GitHub item: %s", e)

        return results

    # -------------------------------------------------------------------------
    # Reddit (Native JSON)
    # -------------------------------------------------------------------------
    async def _scrape_reddit_subreddit(self, keywords: list[str], limit: int) -> list[UnifiedPost]:
        # Using native search across all subreddits
        query = " OR ".join(keywords)
        url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort=new"

        headers = {
            'User-Agent': f'reddit-scraper-native/{random.randint(1000,9999)} (Linux x64)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url, headers=headers, timeout=15.0)
                    if response.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if response.status_code != 200:
                        logger.warning("[reddit_native] Search failed: HTTP %s", response.status_code)
                        return []

                    data = response.json()
                    break
                except Exception as e:
                    logger.exception("[reddit_native] API error attempt %s: %s", attempt, e)
                    if attempt == 2:
                        return []
                    await asyncio.sleep(2 ** attempt)

        results = []
        for child in data.get('data', {}).get('children', []):
            try:
                post = child.get('data', {})
                object_id = post.get('id')
                if not object_id:
                    continue

                created_utc = post.get('created_utc')
                created_at = datetime.fromtimestamp(created_utc, UTC) if created_utc else datetime.now(UTC)

                results.append(UnifiedPost(
                    platform="reddit",
                    external_id=object_id,
                    author=post.get('author', 'unknown'),
                    author_id=post.get('author', 'unknown'),
                    title=post.get('title', ''),
                    body=post.get('selftext', ''),
                    url=f"https://reddit.com{post.get('permalink')}",
                    subreddit=post.get('subreddit'),
                    hashtags=[],
                    upvotes=post.get('score', 0),
                    comments_count=post.get('num_comments', 0),
                    shares=0,
                    views=0,
                    created_at=created_at,
                    media_urls=[],
                    raw_data=post
                ))
            except Exception as e:
                logger.debug("Failed to parse reddit_native post: %s", e)

        return results

    # -------------------------------------------------------------------------
    # IndieHackers (GraphQL)
    # -------------------------------------------------------------------------
    async def _scrape_indiehackers_posts(self, keywords: list[str], limit: int) -> list[UnifiedPost]:
        query = """
        query PostsSearch($term: String, $first: Int!) {
          postsSearch(term: $term, first: $first) {
            edges {
              node {
                id
                title
                body
                url
                createdAt
                score
                commentCount
                author {
                  name
                  username
                }
                tags {
                  name
                }
              }
            }
          }
        }
        """
        # Take the first keyword as IH GraphQL doesn't like big boolean queries
        term = keywords[0] if keywords else ""
        variables = {"term": term, "first": limit}

        async with httpx.AsyncClient() as client:
            try:
                url = "https://www.indiehackers.com/graphql"
                payload = {"query": query, "variables": variables}
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code != 200:
                    logger.warning("[indiehackers] Search failed: HTTP %s", response.status_code)
                    return []
                # Guard against empty body — IH sometimes returns 200 with no content
                if not response.content or not response.content.strip():
                    logger.warning("[indiehackers] Empty response body — skipping")
                    return []
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.warning("[indiehackers] JSON decode failed: %s", json_err)
                    return []
            except Exception as e:
                logger.exception("[indiehackers] API error: %s", e)
                return []

        results = []
        for edge in data.get('data', {}).get('postsSearch', {}).get('edges', []):
            try:
                node = edge.get('node', {})
                object_id = str(node.get('id'))
                if not object_id:
                    continue

                created_at_str = node.get('createdAt')
                created_at = datetime.now(UTC)
                if created_at_str:
                    with contextlib.suppress(Exception):
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                results.append(UnifiedPost(
                    platform="indiehackers",
                    external_id=object_id,
                    author=node.get('author', {}).get('name', 'unknown'),
                    author_id=node.get('author', {}).get('username', 'unknown'),
                    title=node.get('title', ''),
                    body=node.get('body', ''),
                    url=f"https://indiehackers.com{node.get('url', '')}",
                    subreddit=None,
                    hashtags=[t['name'] for t in node.get('tags', [])],
                    upvotes=node.get('score', 0),
                    comments_count=node.get('commentCount', 0),
                    shares=0,
                    views=0,
                    created_at=created_at,
                    media_urls=[],
                    raw_data=node
                ))
            except Exception as e:
                logger.debug("Failed to parse indiehackers post: %s", e)

        return results
