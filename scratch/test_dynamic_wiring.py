"""Test dynamic scraper wiring."""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.db.supabase_client import get_supabase
from app.services.product.platform_scanner import run_platform_scan

from app.core.config import get_settings
from supabase import create_client

def test_dynamic():
    settings = get_settings()
    db = create_client(settings.supabase_url, settings.supabase_secret_key)
    # We need a project ID to test. Let's list projects first.
    projects = db.table("projects").select("*").limit(1).execute()
    if not projects.data:
        print("No projects found in DB.")
        return
        
    project = projects.data[0]
    workspace_id = project["workspace_id"]
    
    print(f"Testing with Project ID {project['id']} (Workspace {workspace_id})")
    
    import app.services.product.platform_scanner
    app.services.product.platform_scanner.get_project_search_keywords = lambda db, project, limit=30: ["investing"]
    
    # Let's insert a dummy custom scraper for "reddit_custom"
    db.table("custom_scrapers").upsert({
        "workspace_id": workspace_id,
        "platform": "reddit_custom",
        "api_host": "reddit3.p.rapidapi.com",
        "search_endpoint": "/v1/reddit/search",
        "search_param_name": "search",
        "items_json_path": "body",
        "is_active": True
    }, on_conflict="workspace_id,platform").execute()
    
    print("Inserted custom scraper configuration.")
    
    try:
        # Run scan just for the custom platform
        print("Running scan...")
        result = run_platform_scan(
            db=db,
            project=project,
            platforms=["reddit_custom"],
            limit_per_platform=5
        )
        print("Scan result:", result)
    finally:
        # Cleanup
        print("Cleaning up...")
        db.table("custom_scrapers").delete().eq("workspace_id", workspace_id).eq("platform", "reddit_custom").execute()

if __name__ == "__main__":
    test_dynamic()
