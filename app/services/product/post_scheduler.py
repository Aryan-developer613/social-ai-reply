"""Auto-publish scheduler — background worker for X and LinkedIn.

Polls ``post_drafts`` for rows with ``status='scheduled'`` and a past
``scheduled_at``, publishes them via the matching platform publisher, and
records the outcome. Designed to be called periodically (every few minutes)
from an asyncio background task; see ``app/main.py``'s lifespan handler.

Instagram is excluded: its Graph API requires a publicly-accessible
``media_url`` and posts here have no image hosting, so there is nothing to
auto-publish yet.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.db.tables.content import list_due_scheduled_post_drafts, update_post_draft
from app.db.tables.projects import get_project_by_id
from app.services.infrastructure.linkedin_publisher import (
    LinkedInPublisher,
    get_linkedin_author_urn,
    get_linkedin_token,
)
from app.services.infrastructure.x_publisher import XPublisher, get_x_token

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

AUTO_PUBLISH_PLATFORMS = ("x", "linkedin")


def _publish_draft(db: Client, draft: dict[str, Any]) -> bool:
    """Publish one due draft. Returns True on success, False on failure."""
    draft_id = draft["id"]
    platform = draft.get("platform")
    project = get_project_by_id(db, draft["project_id"])
    if not project:
        update_post_draft(db, draft_id, {
            "status": "needs_edit",
            "publish_error": "Project no longer exists.",
            "last_publish_attempt_at": datetime.now(UTC).isoformat(),
        })
        return False
    workspace_id = project["workspace_id"]

    try:
        if platform == "x":
            token = get_x_token(db, workspace_id)
            if not token:
                raise RuntimeError("No X/Twitter access token configured for this workspace.")
            tweets = draft.get("thread_json") or [draft["body"]]
            results = XPublisher(token).publish_thread(tweets)
            published_url = f"https://x.com/i/status/{results[0]['id']}" if results else None
        elif platform == "linkedin":
            token = get_linkedin_token(db, workspace_id)
            author_urn = get_linkedin_author_urn(db, workspace_id)
            if not token or not author_urn:
                raise RuntimeError("LinkedIn access token or author URN not configured for this workspace.")
            LinkedInPublisher(token, author_urn).publish_post(draft["body"])
            published_url = None
        else:
            raise RuntimeError(f"Auto-publish is not supported for platform {platform!r}.")
    except Exception as exc:
        logger.warning("Auto-publish failed for draft %s (%s): %s", draft_id, platform, exc)
        update_post_draft(db, draft_id, {
            "status": "needs_edit",
            "publish_error": str(exc)[:500],
            "last_publish_attempt_at": datetime.now(UTC).isoformat(),
        })
        return False

    update_post_draft(db, draft_id, {
        "status": "published",
        "posted_at": datetime.now(UTC).isoformat(),
        "published_url": published_url,
        "publish_mode": "auto",
        "publish_error": None,
        "last_publish_attempt_at": datetime.now(UTC).isoformat(),
    })
    logger.info("Auto-published draft %s via %s", draft_id, platform)
    return True


def publish_due_drafts(db: Client) -> dict[str, int]:
    """Publish every due, approved (status='scheduled') post draft.

    Returns a summary dict: ``{"attempted": N, "published": N, "failed": N}``.
    """
    due = list_due_scheduled_post_drafts(db, platforms=list(AUTO_PUBLISH_PLATFORMS))
    published = sum(1 for draft in due if _publish_draft(db, draft))
    return {"attempted": len(due), "published": published, "failed": len(due) - published}
