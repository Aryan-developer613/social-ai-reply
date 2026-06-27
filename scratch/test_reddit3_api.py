"""Quick test: Reddit3 API via DynamicAdapter — does it fetch + parse posts?"""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

from app.services.infrastructure.platforms.dynamic_adapter import DynamicAdapter

async def test():
    config = {
        "platform": "reddit_custom",
        "api_host": "reddit3.p.rapidapi.com",
        "search_endpoint": "/v1/reddit/search",
        "search_param_name": "search",
        "items_json_path": "",  # root is likely the array
    }
    adapter = DynamicAdapter(config)
    
    # Use a simple keyword
    posts = await adapter.search_posts(["investing"], limit=5)
    print(f"\nPosts found: {len(posts)}")
    for i, p in enumerate(posts[:3]):
        print(f"  [{i+1}] {p.title[:80]}  | by {p.author} | ⬆ {p.upvotes} | 💬 {p.comments_count}")

asyncio.run(test())
