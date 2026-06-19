"""User table operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

# Table name constant
USERS_TABLE = "account_users"


def get_user_by_id(db: Client, user_id: int) -> dict[str, Any] | None:
    """Get a user by ID."""
    result = db.table(USERS_TABLE).select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_user_by_supabase_id(db: Client, supabase_user_id: str) -> dict[str, Any] | None:
    """Get a user by Supabase user ID."""
    result = db.table(USERS_TABLE).select("*").eq("supabase_uid", supabase_user_id).execute()
    return result.data[0] if result.data else None


def get_user_by_email(db: Client, email: str) -> dict[str, Any] | None:
    """Get a user by email."""
    result = db.table(USERS_TABLE).select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


def create_user(db: Client, user_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new user."""
    result = db.table(USERS_TABLE).insert(user_data).execute()
    return result.data[0]


def update_user(db: Client, user_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a user."""
    result = db.table(USERS_TABLE).update(update_data).eq("id", user_id).execute()
    return result.data[0] if result.data else None


def delete_user(db: Client, user_id: int) -> None:
    """Delete a user."""
    db.table(USERS_TABLE).delete().eq("id", user_id).execute()


def list_users_by_workspace(
    db: Client,
    workspace_id: int,
) -> list[dict[str, Any]]:
    """List all users in a workspace via membership join."""
    # First get memberships
    memberships_result = db.table("memberships").select("user_id").eq("workspace_id", workspace_id).execute()
    user_ids = [m["user_id"] for m in memberships_result.data]

    if not user_ids:
        return []

    result = db.table(USERS_TABLE).select("*").in_("id", user_ids).execute()
    return list(result.data)
