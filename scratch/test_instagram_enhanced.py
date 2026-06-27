import asyncio
from app.services.infrastructure.platforms.instagram_enhanced import InstagramEnhancedAdapter

async def main():
    config = {
        "platform": "instagram",
        "api_host": "instagram-looter2.p.rapidapi.com",
        "search_endpoint": "/search",
        "search_param_name": "query",
        "items_json_path": "",
        "api_key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379"
    }
    adapter = InstagramEnhancedAdapter(config)
    
    print("=== Health Check ===")
    health = await adapter.health_check()
    print(f"Health: {health}")
    
    if health:
        print("\n=== Smart Scan (prioritizing users) ===")
        # Use a long keyword to test shortening
        posts = await adapter.search_posts(
            ["tired of blurry property photos in gurugram", "real estate agent"],
            limit=10,
        )
        print(f"Total posts found: {len(posts)}")
        for p in posts[:5]:
            print(f"  [{p.external_id}] {p.title[:60]}")

if __name__ == "__main__":
    asyncio.run(main())
