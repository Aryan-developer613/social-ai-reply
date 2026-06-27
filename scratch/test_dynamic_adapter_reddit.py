import asyncio
from app.services.infrastructure.platforms.dynamic_adapter import DynamicAdapter

async def main():
    config = {
        "platform": "reddit",
        "api_host": "reddit3.p.rapidapi.com",
        "search_endpoint": "/subreddit",
        "search_param_name": "name",
        "items_json_path": "data.posts",
        "api_key": None  # Uses default
    }
    adapter = DynamicAdapter(config)
    print("Testing health check...")
    health = await adapter.health_check()
    print(f"Health check: {health}")
    
    if health:
        print("Testing search_posts...")
        posts = await adapter.search_posts(["SaaS"], limit=2)
        print(f"Posts found: {len(posts)}")
        for p in posts:
            print(f"- {p.author}: {p.title[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
