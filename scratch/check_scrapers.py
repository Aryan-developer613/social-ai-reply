import asyncio
from app.db.supabase_client import get_supabase

def check_db():
    db = get_supabase()
    res = db.table("custom_scrapers").select("*").execute()
    print(res.data)

if __name__ == "__main__":
    check_db()
