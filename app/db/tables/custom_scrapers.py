"""Custom Scraper table operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

CUSTOM_SCRAPERS_TABLE = "custom_scrapers"


def get_custom_scraper_by_id(db: Client, scraper_id: int) -> dict[str, Any] | None:
    return None


def get_custom_scraper_by_platform(
    db: Client,
    workspace_id: int,
    platform: str,
) -> dict[str, Any] | None:
    return None


def list_custom_scrapers_for_workspace(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    return []


def upsert_custom_scraper(db: Client, scraper_data: dict[str, Any]) -> dict[str, Any]:
    return scraper_data


def delete_custom_scraper(db: Client, scraper_id: int) -> None:
    pass
