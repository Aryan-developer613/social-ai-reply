import logging
from datetime import UTC, datetime
from typing import Any

from apify_client import ApifyClient

from app.core.config import get_settings
from app.services.product.reddit import RedditPost, RedditSubredditMatch

logger = logging.getLogger(__name__)

# Usually "trudax/reddit-scraper" or "apify/reddit-scraper"
DEFAULT_ACTOR_ID = "trudax/reddit-scraper"


class ApifyRedditClient:
    """Wrapper around Apify Client to scrape Reddit.
    
    This avoids Reddit's aggressive 429/403 blocks on anonymous scraping by routing
    requests through Apify's managed infrastructure (proxies/headless browsers).
    """

    def __init__(self, api_token: str | None = None, actor_id: str = DEFAULT_ACTOR_ID):
        self._token = api_token or get_settings().apify_api_token
        self._actor_id = actor_id
        self._client = ApifyClient(self._token) if self._token else None

    @property
    def available(self) -> bool:
        """Whether the Apify token is configured."""
        return bool(self._token)

    def search_posts(
        self,
        keywords: list[str],
        subreddits: list[str] | None = None,
        *,
        limit: int = 20,
    ) -> list[RedditPost]:
        """Search Reddit posts across multiple keywords and subreddits using Apify."""
        if not self.available:
            raise RuntimeError("APIFY_API_TOKEN is not configured.")

        # Build searches list
        # Trudax scraper accepts a list of "searches" where each is a keyword,
        # or we can construct startUrls if we want to be explicit.
        # It's safer to pass explicit Reddit search URLs as startUrls to support most Apify actors.
        
        start_urls = []
        for kw in keywords:
            query = kw.replace(" ", "+")
            if subreddits:
                for sub in subreddits:
                    sub_clean = sub.strip().lstrip("r/")
                    if sub_clean:
                        start_urls.append({"url": f"https://www.reddit.com/r/{sub_clean}/search/?q={query}&restrict_sr=1&sort=relevance&t=month"})
            else:
                start_urls.append({"url": f"https://www.reddit.com/search/?q={query}&sort=relevance&t=month"})

        run_input = {
            "startUrls": start_urls,
            "maxItems": limit * max(len(subreddits or []), 1),
            "skipComments": True,
            "proxyConfiguration": {"useApifyProxy": True},
        }

        logger.info("Starting Apify Actor %s with %d startUrls", self._actor_id, len(start_urls))
        
        # Run the Actor and wait for it to finish
        run = self._client.actor(self._actor_id).call(run_input=run_input)
        
        # Fetch results from the dataset
        dataset_id = run["defaultDatasetId"]
        items = self._client.dataset(dataset_id).list_items().items
        
        logger.info("Apify Actor %s finished, fetched %d items", self._actor_id, len(items))

        posts = []
        for item in items:
            # Parse output. Apify actors usually return standard fields.
            post_id = item.get("id") or item.get("postId") or ""
            if not post_id:
                continue
                
            subreddit = item.get("subreddit") or ""
            if not subreddit and "url" in item:
                # Fallback: extract from URL
                parts = str(item["url"]).split("/")
                if "r" in parts:
                    idx = parts.index("r")
                    if idx + 1 < len(parts):
                        subreddit = parts[idx + 1]

            created_utc_val = item.get("createdAt", item.get("created_utc", 0))
            if isinstance(created_utc_val, (int, float)):
                dt = datetime.fromtimestamp(created_utc_val, tz=UTC)
            elif isinstance(created_utc_val, str):
                try:
                    dt = datetime.fromisoformat(created_utc_val.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.now(UTC)
            else:
                dt = datetime.now(UTC)

            # Map the response item to our domain model
            post = RedditPost(
                post_id=post_id,
                subreddit=subreddit,
                title=item.get("title", ""),
                author=item.get("author", item.get("authorName", "")),
                permalink=item.get("url", ""),
                body=item.get("text", item.get("body", item.get("selftext", ""))),
                created_at=dt,
                num_comments=int(item.get("numComments", item.get("commentsCount", 0))),
                score=int(item.get("score", item.get("upvotes", 0))),
            )
            posts.append(post)

        # De-duplicate by post_id just in case
        seen = set()
        unique_posts = []
        for p in posts:
            if p.post_id not in seen:
                seen.add(p.post_id)
                unique_posts.append(p)

        return unique_posts

    def search_subreddits(self, keyword: str, limit: int = 10) -> list[RedditSubredditMatch]:
        """Search subreddits using Apify.
        
        Note: The trudax scraper is primarily for posts. To discover subreddits,
        we run a search for posts on the keyword and aggregate the subreddits
        from the results.
        """
        posts = self.search_posts(keywords=[keyword], subreddits=[], limit=limit * 3)
        
        subreddit_counts = {}
        for post in posts:
            sub = post.subreddit.lower()
            if sub:
                subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1
                
        # Sort by frequency
        sorted_subs = sorted(subreddit_counts.keys(), key=lambda k: subreddit_counts[k], reverse=True)
        
        matches = []
        for sub in sorted_subs[:limit]:
            matches.append(RedditSubredditMatch(
                name=sub,
                title=sub,
                description="",  # We don't have descriptions from post scraping alone
                subscribers=0,
            ))
            
        return matches

    def close(self) -> None:
        """Cleanup resources if needed."""
        pass
