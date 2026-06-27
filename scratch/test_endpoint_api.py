import asyncio
from app.db.supabase_client import get_supabase
from app.api.v1.routes.scrapers import test_scraper_endpoint
from app.schemas.v1.scrapers import ScraperTestRequest

async def main():
    req = ScraperTestRequest(
        api_host="reddit3.p.rapidapi.com",
        api_key="b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
        search_endpoint="/v1/reddit/search",
        search_param_name="search",
        items_json_path="body",
        test_query="test"
    )
    res = await test_scraper_endpoint(req, current_user={"id": 1})
    print(res)

asyncio.run(main())
