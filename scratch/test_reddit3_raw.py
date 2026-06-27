"""Test Reddit3 raw API response to understand the JSON structure."""
import asyncio
import json
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient

async def test():
    client = RapidAPIClient("reddit3.p.rapidapi.com")
    data = await client.get("/v1/reddit/search", params={"search": "investing", "filter": "posts", "timeFilter": "year", "sortType": "relevance"})
    
    # Print structure
    if isinstance(data, dict):
        print(f"Root type: dict, keys: {list(data.keys())}")
        for k, v in data.items():
            if isinstance(v, list):
                print(f"  '{k}': list of {len(v)} items")
                if v:
                    print(f"    First item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
            elif isinstance(v, dict):
                print(f"  '{k}': dict with keys: {list(v.keys())[:10]}")
            else:
                print(f"  '{k}': {type(v).__name__} = {str(v)[:100]}")
    elif isinstance(data, list):
        print(f"Root type: list of {len(data)} items")
        if data:
            first = data[0]
            if isinstance(first, dict):
                print(f"  First item keys: {list(first.keys())}")
                # Print relevant fields
                for k in ["id", "title", "selftext", "author", "subreddit", "ups", "score", "num_comments", "name"]:
                    if k in first:
                        val = str(first[k])[:100]
                        print(f"    {k}: {val}")

asyncio.run(test())
