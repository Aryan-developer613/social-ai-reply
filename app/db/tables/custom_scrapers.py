"""Custom Scraper table operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

CUSTOM_SCRAPERS_TABLE = "custom_scrapers"


def get_custom_scraper_by_id(db: Client, scraper_id: int) -> dict[str, Any] | None:
    """Get a custom scraper configuration by ID."""
    result = db.table(CUSTOM_SCRAPERS_TABLE).select("*").eq("id", scraper_id).execute()
    return result.data[0] if result.data else None


def get_custom_scraper_by_platform(
    db: Client,
    workspace_id: int,
    platform: str,
) -> dict[str, Any] | None:
    """Get a custom scraper configuration by workspace ID and platform."""
    result = (
        db.table(CUSTOM_SCRAPERS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("platform", platform)
        .eq("is_active", True)
        .execute()
    )
    return result.data[0] if result.data else None


def list_custom_scrapers_for_workspace(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    """List all custom scrapers for a workspace."""
    result = (
        db.table(CUSTOM_SCRAPERS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


def upsert_custom_scraper(db: Client, scraper_data: dict[str, Any]) -> dict[str, Any]:
    """Create or update a custom scraper configuration."""
    # We use upsert based on the unique constraint (workspace_id, platform)
    result = db.table(CUSTOM_SCRAPERS_TABLE).upsert(scraper_data, on_conflict="workspace_id,platform").execute()
    return result.data[0]


def delete_custom_scraper(db: Client, scraper_id: int) -> None:
    """Delete a custom scraper configuration."""
    db.table(CUSTOM_SCRAPERS_TABLE).delete().eq("id", scraper_id).execute()
