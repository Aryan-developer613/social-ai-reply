"""Campaign and published post table operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

CAMPAIGNS_TABLE = "campaigns"
PUBLISHED_POSTS_TABLE = "published_posts"


# Campaign operations
def get_campaign_by_id(db: Client, campaign_id: str) -> dict[str, Any] | None:
    """Get a campaign by ID."""
    result = db.table(CAMPAIGNS_TABLE).select("*").eq("id", campaign_id).execute()
    return result.data[0] if result.data else None


def list_campaigns_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List all campaigns for a project."""
    result = (
        db.table(CAMPAIGNS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_campaign(db: Client, campaign_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new campaign."""
    result = db.table(CAMPAIGNS_TABLE).insert(campaign_data).execute()
    return result.data[0]


def update_campaign(db: Client, campaign_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a campaign."""
    result = db.table(CAMPAIGNS_TABLE).update(update_data).eq("id", campaign_id).execute()
    return result.data[0] if result.data else None


def delete_campaign(db: Client, campaign_id: str) -> None:
    """Delete a campaign."""
    db.table(CAMPAIGNS_TABLE).delete().eq("id", campaign_id).execute()


# Published post operations
def get_published_post_by_id(db: Client, post_id: str) -> dict[str, Any] | None:
    """Get a published post by ID."""
    result = db.table(PUBLISHED_POSTS_TABLE).select("*").eq("id", post_id).execute()
    return result.data[0] if result.data else None


def list_published_posts_for_project(db: Client, project_id: int, status: str | None = None) -> list[dict[str, Any]]:
    """List published posts for a project."""
    query = db.table(PUBLISHED_POSTS_TABLE).select("*").eq("project_id", project_id)
    if status:
        query = query.eq("status", status)
    result = query.order("posted_at", desc=True).execute()
    return list(result.data)


def list_published_posts_for_campaign(db: Client, campaign_id: str) -> list[dict[str, Any]]:
    """List published posts for a campaign."""
    result = (
        db.table(PUBLISHED_POSTS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("posted_at", desc=True)
        .execute()
    )
    return list(result.data)


def list_published_posts_for_reddit_account(db: Client, reddit_account_id: Any) -> list[dict[str, Any]]:
    """List published posts made through a specific Reddit account."""
    result = (
        db.table(PUBLISHED_POSTS_TABLE)
        .select("*")
        .eq("reddit_account_id", reddit_account_id)
        .order("posted_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_published_post(db: Client, post_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new published post."""
    result = db.table(PUBLISHED_POSTS_TABLE).insert(post_data).execute()
    return result.data[0]


def update_published_post(db: Client, post_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a published post."""
    result = db.table(PUBLISHED_POSTS_TABLE).update(update_data).eq("id", post_id).execute()
    return result.data[0] if result.data else None


def delete_published_post(db: Client, post_id: str) -> None:
    """Delete a published post."""
    db.table(PUBLISHED_POSTS_TABLE).delete().eq("id", post_id).execute()
