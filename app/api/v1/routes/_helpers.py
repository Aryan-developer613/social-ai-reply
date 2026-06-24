"""Shared helpers for agent route modules (SEO, GEO, Articles, UGC, Technical-SEO).

Provides:
- ``get_company_opportunities``: batch-fetches opportunities for a company
  across all workspace projects in a single query, fixing the N+1 pattern
  where each route independently did: get_company → list_projects →
  list_opportunities_for_project → filter (Issue #19).
- ``get_first_project_for_workspace``: convenience wrapper that resolves the
  first project ID for a workspace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client


def get_first_project_for_workspace(db: Client, workspace_id: int) -> int | None:
    """Return the first project ID for a workspace, or None."""
    from app.db.tables.projects import list_projects_for_workspace

    projects = list_projects_for_workspace(db, workspace_id)
    return projects[0]["id"] if projects else None


def get_company_opportunities(
    db: Client,
    workspace_id: int,
    company_id: int,
    *,
    platform: str | None = None,
    opportunity_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Fetch filtered opportunities for a company in fewer DB calls.

    Instead of fetching per-project and filtering in Python (N+1 pattern),
    this fetches all workspace projects once and batches opportunities into a
    single query using .in_("project_id", ...) (Issue #19).

    The ``company_id`` is enforced: only opportunities whose ``company_id``
    column matches are returned, so cross-company leakage within a workspace
    is impossible (Issue: PR review).

    Args:
        platform: If set, filter to opportunities with this platform value.
        opportunity_type: If set, filter by opportunity_type.
        limit/offset: Pagination.
    """
    # Use a project_ids list passed in by callers when available, otherwise
    # resolve it from the workspace. Callers MUST validate company_id and
    # workspace membership before invoking us — we do NOT re-fetch the company
    # here (avoids a redundant DB lookup per request, PR review).
    from app.db.tables.discovery import OPPORTUNITIES_TABLE
    from app.db.tables.projects import list_projects_for_workspace

    projects = list_projects_for_workspace(db, workspace_id)
    project_ids = [p["id"] for p in projects]
    if not project_ids:
        return []

    # Fetch opportunities for ALL workspace projects in one batched query,
    # then filter by company_id in Python (no company_id column index assumed
    # across all opportunity rows). The company_id check guarantees that one
    # company's data is never returned to another company's request.
    query = (
        db.table(OPPORTUNITIES_TABLE)
        .select("*")
        .in_("project_id", project_ids)
        .eq("company_id", company_id)
    )
    if platform:
        query = query.eq("platform", platform)
    if opportunity_type:
        query = query.eq("opportunity_type", opportunity_type)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    rows: list[dict[str, Any]] = list(result.data)
    return [_normalize_opportunity(r) for r in rows]


def _normalize_opportunity(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize opportunity record fields to a consistent shape.

    Different callers expect slightly different field names (e.g. ``subreddit``
    vs ``subreddit_name``). Provide both so downstream consumers don't break
    (Issue: PR review).
    """
    normalized = dict(row)
    # Ensure subreddit_name is always present (fall back to subreddit).
    if "subreddit_name" not in normalized and "subreddit" in normalized:
        normalized["subreddit_name"] = normalized["subreddit"]
    return normalized
