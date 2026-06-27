import asyncio
from app.services.infrastructure.platforms.dynamic_adapter import DynamicAdapter

async def main():
    config = {
        "platform": "instagram",
        "api_host": "instagram-looter2.p.rapidapi.com",
        "search_endpoint": "/search",
        "search_param_name": "search_query",
        "items_json_path": "data.items",
        "api_key": None  # Uses default
    }
    adapter = DynamicAdapter(config)
    print("Testing health check...")
    health = await adapter.health_check()
    print(f"Health check: {health}")
    
    if health:
        print("Testing search_posts...")
        posts = await adapter.search_posts(["software engineer"], limit=2)
        print(f"Posts found: {len(posts)}")
        for p in posts:
            print(f"- {p.author}: {p.title} ({p.url})")

if __name__ == "__main__":
    asyncio.run(main())
