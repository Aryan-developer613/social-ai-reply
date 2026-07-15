"""Custom Scraper table operations."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from app.utils.encryption import decrypt_text, encrypt_text

CUSTOM_SCRAPERS_TABLE = "custom_scrapers"


def _decrypt_api_key(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Decrypt api_key in-place if present."""
    if data and data.get("api_key"):
        with contextlib.suppress(ValueError):  # if already plaintext or invalid, leave as-is
            data["api_key"] = decrypt_text(data["api_key"])
    return data


def get_custom_scraper_by_id(db: Client, scraper_id: int) -> dict[str, Any] | None:
    """Get a custom scraper configuration by ID."""
    result = db.table(CUSTOM_SCRAPERS_TABLE).select("*").eq("id", scraper_id).execute()
    return _decrypt_api_key(result.data[0] if result.data else None)


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
    return _decrypt_api_key(result.data[0] if result.data else None)


def list_custom_scrapers_for_workspace(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    """List all custom scrapers for a workspace (api_key excluded from response)."""
    result = (
        db.table(CUSTOM_SCRAPERS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = list(result.data)
    for row in rows:
        row.pop("api_key", None)
    return rows


def upsert_custom_scraper(db: Client, scraper_data: dict[str, Any]) -> dict[str, Any]:
    """Create or update a custom scraper configuration."""
    # Encrypt the API key before storing
    raw_key = scraper_data.get("api_key")
    if raw_key and not raw_key.startswith("gAAAAA"):  # Fernet tokens always start with gAAAAA
        scraper_data["api_key"] = encrypt_text(raw_key)
    # We use upsert based on the unique constraint (workspace_id, platform)
    result = db.table(CUSTOM_SCRAPERS_TABLE).upsert(scraper_data, on_conflict="workspace_id,platform").execute()
    return result.data[0]


def delete_custom_scraper(db: Client, scraper_id: int, workspace_id: int) -> bool:
    """Delete a custom scraper configuration. Returns True if a row was actually deleted."""
    result = (
        db.table(CUSTOM_SCRAPERS_TABLE)
        .delete()
        .eq("id", scraper_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    return bool(result.data)
