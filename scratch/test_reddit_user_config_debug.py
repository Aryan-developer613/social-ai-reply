import asyncio
from app.services.infrastructure.platforms.dynamic_adapter import DynamicAdapter
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIError

async def main():
    config = {
        "platform": "reddit",
        "api_host": "reddit3.p.rapidapi.com",
        "search_endpoint": "/v1/search",
        "search_param_name": "search",
        "items_json_path": "body",
        "api_key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379"
    }
    adapter = DynamicAdapter(config)
    try:
        data = await adapter._get(config["search_endpoint"], params={config["search_param_name"]: "test"})
        print("Success:", data.keys())
    except RapidAPIError as e:
        print("RapidAPIError:", e)
    except Exception as e:
        print("Other Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
