import asyncio
from app.services.infrastructure.platforms.reddit3_adapter import Reddit3Adapter

async def main():
    config = {
        "platform": "reddit",
        "api_host": "reddit3.p.rapidapi.com",
        "search_endpoint": "/v1/reddit/search",
        "search_param_name": "search",
        "items_json_path": "body",
        "api_key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379"
    }
    adapter = Reddit3Adapter(config)
    
    print("=== Health Check ===")
    health = await adapter.health_check()
    print(f"Health: {health}")
    
    if health:
        print("\n=== Smart Scan (keywords -> subreddits) ===")
        posts = await adapter.search_posts(
            ["SaaS", "marketing"],
            limit=10,
        )
        print(f"Total posts found: {len(posts)}")
        for p in posts[:5]:
            print(f"  [{p.subreddit or 'n/a'}] {p.title[:60]}")

if __name__ == "__main__":
    asyncio.run(main())
