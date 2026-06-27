import asyncio
from app.db.supabase_client import get_supabase

def main():
    db = next(get_supabase())
    res = db.table("custom_scrapers").select("*").execute()
    for row in res.data:
        print(row)

if __name__ == "__main__":
    main()
