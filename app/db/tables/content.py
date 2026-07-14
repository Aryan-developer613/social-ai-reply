"""Content table operations: reply drafts, post drafts."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.utils import aes_gcm

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

REPLY_DRAFTS_TABLE = "reply_drafts"
POST_DRAFTS_TABLE = "post_drafts"


def _encryption_enabled() -> bool:
    return bool(get_settings().enable_response_encryption)


def _encrypt_field(value: Any, *, associated_data: str) -> Any:
    if not _encryption_enabled() or not isinstance(value, str) or aes_gcm.is_encrypted(value):
        return value
    return aes_gcm.encrypt_text(value, associated_data=associated_data)


def _decrypt_field(value: Any, *, associated_data: str) -> Any:
    if not isinstance(value, str) or not aes_gcm.is_encrypted(value):
        return value
    return aes_gcm.decrypt_text(value, associated_data=associated_data)


def _prepare_reply_draft_for_db(data: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(data)
    if "content" in prepared:
        prepared["content"] = _encrypt_field(prepared["content"], associated_data="reply_drafts.content")
    return prepared


def _prepare_post_draft_for_db(data: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(data)
    if "body" in prepared and "content" not in prepared:
        prepared["content"] = prepared["body"]
    if "content" in prepared and "body" not in prepared:
        prepared["body"] = prepared["content"]
    if "title" in prepared:
        prepared["title"] = _encrypt_field(prepared["title"], associated_data="post_drafts.title")
    if "body" in prepared:
        prepared["body"] = _encrypt_field(prepared["body"], associated_data="post_drafts.body")
    if "content" in prepared:
        prepared["content"] = _encrypt_field(prepared["content"], associated_data="post_drafts.body")
    return prepared


def _missing_column_from_error(exc: Exception) -> str | None:
    text = str(exc)
    patterns = [
        r"Could not find the '([^']+)' column",
        r"column \"([^\"]+)\" of relation",
        r"column \"([^\"]+)\" does not exist",
        r"'([^']+)' column of 'post_drafts'",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _insert_post_draft_with_compat(db: Client, draft_data: dict[str, Any]) -> dict[str, Any]:
    payload = _prepare_post_draft_for_db(draft_data)
    removed_columns: set[str] = set()

    while True:
        try:
            result = db.table(POST_DRAFTS_TABLE).insert(payload).execute()
            return result.data[0]
        except Exception as exc:
            column = _missing_column_from_error(exc)
            if column and column in payload and column not in {"id", "project_id"} and column not in removed_columns:
                logger.warning("Retrying post_draft insert without unsupported column %s", column)
                payload = dict(payload)
                payload.pop(column, None)
                removed_columns.add(column)
                continue
            raise


def _map_reply_draft(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    mapped = dict(row)
    if "content" in mapped:
        mapped["content"] = _decrypt_field(mapped["content"], associated_data="reply_drafts.content")
    return mapped


def _map_post_draft(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    mapped = dict(row)
    if "body" not in mapped and "content" in mapped:
        mapped["body"] = mapped.get("content") or ""
    if "title" in mapped:
        mapped["title"] = _decrypt_field(mapped["title"], associated_data="post_drafts.title")
    if "body" in mapped:
        mapped["body"] = _decrypt_field(mapped["body"], associated_data="post_drafts.body")
    return mapped


# Reply draft operations
def get_reply_draft_by_id(db: Client, draft_id: int) -> dict[str, Any] | None:
    """Get a reply draft by ID."""
    result = db.table(REPLY_DRAFTS_TABLE).select("*").eq("id", draft_id).execute()
    return _map_reply_draft(result.data[0]) if result.data else None


def list_reply_drafts_for_opportunity(db: Client, opportunity_id: int) -> list[dict[str, Any]]:
    """List all reply drafts for an opportunity."""
    result = (
        db.table(REPLY_DRAFTS_TABLE)
        .select("*")
        .eq("opportunity_id", opportunity_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [_map_reply_draft(row) for row in result.data]


def list_reply_drafts_for_project(
    db: Client,
    project_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List reply drafts for a project with pagination."""
    result = (
        db.table(REPLY_DRAFTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [_map_reply_draft(row) for row in result.data]


def count_reply_drafts_for_project(db: Client, project_id: int, status: str | None = None) -> int:
    """Count reply drafts for a project, optionally filtered by status."""
    query = db.table(REPLY_DRAFTS_TABLE).select("*", count="exact").eq("project_id", project_id)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.count or 0


def create_reply_draft(db: Client, draft_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new reply draft."""
    result = db.table(REPLY_DRAFTS_TABLE).insert(_prepare_reply_draft_for_db(draft_data)).execute()
    return _map_reply_draft(result.data[0])


def update_reply_draft(db: Client, draft_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a reply draft."""
    result = db.table(REPLY_DRAFTS_TABLE).update(_prepare_reply_draft_for_db(update_data)).eq("id", draft_id).execute()
    return _map_reply_draft(result.data[0]) if result.data else None


def delete_reply_draft(db: Client, draft_id: int) -> None:
    """Delete a reply draft."""
    db.table(REPLY_DRAFTS_TABLE).delete().eq("id", draft_id).execute()


def list_reply_drafts_for_opportunities(db: Client, opportunity_ids: list[int]) -> list[dict[str, Any]]:
    """List all reply drafts for a set of opportunity IDs (batch query)."""
    if not opportunity_ids:
        return []
    result = (
        db.table(REPLY_DRAFTS_TABLE)
        .select("*")
        .in_("opportunity_id", opportunity_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return [_map_reply_draft(row) for row in result.data]


def get_draft_by_project_and_opportunity(
    db: Client,
    project_id: int,
    opportunity_id: int,
) -> dict[str, Any] | None:
    """Get a reply draft by project and opportunity ID."""
    result = (
        db.table(REPLY_DRAFTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("opportunity_id", opportunity_id)
        .execute()
    )
    return _map_reply_draft(result.data[0]) if result.data else None


# Post draft operations
def get_post_draft_by_id(db: Client, draft_id: int) -> dict[str, Any] | None:
    """Get a post draft by ID."""
    result = db.table(POST_DRAFTS_TABLE).select("*").eq("id", draft_id).execute()
    return _map_post_draft(result.data[0]) if result.data else None


def list_post_drafts_for_project(
    db: Client,
    project_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List post drafts for a project with pagination."""
    result = (
        db.table(POST_DRAFTS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [_map_post_draft(row) for row in result.data]


def create_post_draft(db: Client, draft_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new post draft."""
    return _map_post_draft(_insert_post_draft_with_compat(db, draft_data))


def update_post_draft(db: Client, draft_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a post draft."""
    payload = _prepare_post_draft_for_db(update_data)
    removed_columns: set[str] = set()

    while True:
        try:
            result = db.table(POST_DRAFTS_TABLE).update(payload).eq("id", draft_id).execute()
            return _map_post_draft(result.data[0]) if result.data else None
        except Exception as exc:
            column = _missing_column_from_error(exc)
            if column and column in payload and column not in {"id", "project_id"} and column not in removed_columns:
                logger.warning("Retrying post_draft update without unsupported column %s", column)
                payload = dict(payload)
                payload.pop(column, None)
                removed_columns.add(column)
                continue
            raise


def delete_post_draft(db: Client, draft_id: int) -> None:
    """Delete a post draft."""
    db.table(POST_DRAFTS_TABLE).delete().eq("id", draft_id).execute()


def list_due_scheduled_post_drafts(db: Client, *, platforms: list[str], limit: int = 50) -> list[dict[str, Any]]:
    """List scheduled post drafts across all projects whose scheduled_at has passed."""
    from datetime import UTC, datetime

    result = (
        db.table(POST_DRAFTS_TABLE)
        .select("*")
        .eq("status", "scheduled")
        .in_("platform", platforms)
        .lte("scheduled_at", datetime.now(UTC).isoformat())
        .order("scheduled_at")
        .limit(limit)
        .execute()
    )
    return [_map_post_draft(row) for row in result.data]


def delete_draft_calendar_posts_for_project_platform(
    db: Client,
    project_id: int,
    platform: str,
) -> None:
    """Delete unapproved generated calendar suggestions for a project/platform."""
    (
        db.table(POST_DRAFTS_TABLE)
        .delete()
        .eq("project_id", project_id)
        .eq("platform", platform)
        .eq("status", "draft")
        .like("source_prompt", "Content calendar:%")
        .execute()
    )
