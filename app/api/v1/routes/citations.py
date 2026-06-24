"""Citation, source domain, and source gap endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.visibility import (
    list_source_domains_for_project,
    list_source_gaps_for_project,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["citations"])


@router.get("/citations")
def list_citations(
    limit: int = 20,
    offset: int = 0,
    domain: str = None,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    from app.db.tables.visibility import get_prompt_sets_for_project

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    # Get all prompt sets for project
    prompt_sets = get_prompt_sets_for_project(supabase, proj["id"])
    if not prompt_sets:
        return {"items": [], "total": 0}

    set_ids = [s["id"] for s in prompt_sets]

    # Get all citations for these prompt sets (batch query).
    # Domain filtering is applied at the DB level before pagination so the
    # total count and page size are accurate (Issue #46).
    from app.db.tables.visibility import list_citations_for_prompt_sets
    all_citations = list_citations_for_prompt_sets(supabase, set_ids, limit=limit, offset=offset, domain=domain)

    # Run a second count query (no pagination) so callers see the real
    # total across all pages, not just the current page size (Issue: PR review).
    from app.db.tables.visibility import count_citations_for_prompt_sets
    total = count_citations_for_prompt_sets(supabase, set_ids, domain=domain)

    return {
        "items": [
            {
                "id": c["id"],
                "url": c["url"],
                "domain": c["domain"],
                "title": c.get("title", ""),
                "content_type": c.get("content_type", ""),
                "first_seen_at": c.get("first_seen_at"),
            }
            for c in all_citations
        ],
        "total": total,
        "page_count": len(all_citations),
        "limit": limit,
        "offset": offset,
    }


@router.get("/sources/domains")
def source_domains(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    results = list_source_domains_for_project(supabase, proj["id"], limit=limit)

    return {"items": [{"domain": r["domain"], "total_citations": r.get("total_citations", 0)} for r in results]}


@router.get("/sources/gaps")
def source_gaps(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    gaps = list_source_gaps_for_project(supabase, proj["id"])
    return {
        "items": [
            {
                "id": g["id"],
                "competitor_name": g.get("competitor_name", ""),
                "domain": g["domain"],
                "citation_count": g.get("citation_count", 0),
                "gap_type": g.get("gap_type", ""),
                "discovered_at": g.get("discovered_at"),
            }
            for g in gaps
        ]
    }
