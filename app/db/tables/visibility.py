"""Visibility table operations: prompt sets, prompt runs, AI responses, brand mentions, citations, source domains, source gaps."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

PROMPT_SETS_TABLE = "prompt_sets"
PROMPT_RUNS_TABLE = "prompt_runs"
AI_RESPONSES_TABLE = "ai_responses"
BRAND_MENTIONS_TABLE = "brand_mentions"
CITATIONS_TABLE = "citations"
SOURCE_DOMAINS_TABLE = "source_domains"
SOURCE_GAPS_TABLE = "source_gaps"


# Prompt set operations
def get_prompt_set_by_id(db: Client, prompt_set_id: int) -> dict[str, Any] | None:
    """Get a prompt set by ID."""
    result = db.table(PROMPT_SETS_TABLE).select("*").eq("id", prompt_set_id).execute()
    return result.data[0] if result.data else None


def list_prompt_sets_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List all prompt sets for a project."""
    result = (
        db.table(PROMPT_SETS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_prompt_set(db: Client, prompt_set_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new prompt set."""
    result = db.table(PROMPT_SETS_TABLE).insert(prompt_set_data).execute()
    return result.data[0]


def update_prompt_set(db: Client, prompt_set_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a prompt set."""
    result = db.table(PROMPT_SETS_TABLE).update(update_data).eq("id", prompt_set_id).execute()
    return result.data[0] if result.data else None


def delete_prompt_set(db: Client, prompt_set_id: int) -> None:
    """Delete a prompt set."""
    db.table(PROMPT_SETS_TABLE).delete().eq("id", prompt_set_id).execute()


# Prompt run operations
def get_prompt_run_by_id(db: Client, prompt_run_id: int) -> dict[str, Any] | None:
    """Get a prompt run by ID."""
    result = db.table(PROMPT_RUNS_TABLE).select("*").eq("id", prompt_run_id).execute()
    return result.data[0] if result.data else None


def list_prompt_runs_for_prompt_set(
    db: Client,
    prompt_set_id: int | None,
    project_id: int | None = None,
    model_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List prompt runs for a prompt set, or all prompt sets for a project."""
    query = db.table(PROMPT_RUNS_TABLE).select("*")

    if prompt_set_id is not None:
        query = query.eq("prompt_set_id", prompt_set_id)
    elif project_id is not None:
        # Get all prompt sets for project
        sets = list_prompt_sets_for_project(db, project_id)
        if sets:
            set_ids = [s["id"] for s in sets]
            query = query.in_("prompt_set_id", set_ids)
        else:
            return []

    if model_filter:
        query = query.eq("model_name", model_filter)

    result = (
        query
        .order("scheduled_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return list(result.data)


def create_prompt_run(db: Client, prompt_run_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new prompt run."""
    result = db.table(PROMPT_RUNS_TABLE).insert(prompt_run_data).execute()
    return result.data[0]


def update_prompt_run(db: Client, prompt_run_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a prompt run."""
    result = db.table(PROMPT_RUNS_TABLE).update(update_data).eq("id", prompt_run_id).execute()
    return result.data[0] if result.data else None


def delete_prompt_run(db: Client, prompt_run_id: int) -> None:
    """Delete a prompt run."""
    db.table(PROMPT_RUNS_TABLE).delete().eq("id", prompt_run_id).execute()


# AI response operations
def get_ai_response_by_id(db: Client, response_id: int) -> dict[str, Any] | None:
    """Get an AI response by ID."""
    result = db.table(AI_RESPONSES_TABLE).select("*").eq("id", response_id).execute()
    return result.data[0] if result.data else None


def list_ai_responses_for_prompt_run(db: Client, prompt_run_id: int) -> list[dict[str, Any]]:
    """List AI responses for a prompt run."""
    result = (
        db.table(AI_RESPONSES_TABLE)
        .select("*")
        .eq("prompt_run_id", prompt_run_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_ai_response(db: Client, response_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new AI response."""
    result = db.table(AI_RESPONSES_TABLE).insert(response_data).execute()
    return result.data[0]


def update_ai_response(db: Client, response_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update an AI response."""
    result = db.table(AI_RESPONSES_TABLE).update(update_data).eq("id", response_id).execute()
    return result.data[0] if result.data else None


def delete_ai_response(db: Client, response_id: int) -> None:
    """Delete an AI response."""
    db.table(AI_RESPONSES_TABLE).delete().eq("id", response_id).execute()


# Brand mention operations
def get_brand_mention_by_id(db: Client, mention_id: int) -> dict[str, Any] | None:
    """Get a brand mention by ID."""
    result = db.table(BRAND_MENTIONS_TABLE).select("*").eq("id", mention_id).execute()
    return result.data[0] if result.data else None


def list_brand_mentions_for_ai_response(db: Client, ai_response_id: int) -> list[dict[str, Any]]:
    """List brand mentions for an AI response."""
    result = (
        db.table(BRAND_MENTIONS_TABLE)
        .select("*")
        .eq("ai_response_id", ai_response_id)
        .execute()
    )
    return list(result.data)


def create_brand_mention(db: Client, mention_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new brand mention."""
    result = db.table(BRAND_MENTIONS_TABLE).insert(mention_data).execute()
    return result.data[0]


def delete_brand_mention(db: Client, mention_id: int) -> None:
    """Delete a brand mention."""
    db.table(BRAND_MENTIONS_TABLE).delete().eq("id", mention_id).execute()


# Citation operations
def get_citation_by_id(db: Client, citation_id: int) -> dict[str, Any] | None:
    """Get a citation by ID."""
    result = db.table(CITATIONS_TABLE).select("*").eq("id", citation_id).execute()
    return result.data[0] if result.data else None


def list_citations_for_ai_response(db: Client, ai_response_id: int) -> list[dict[str, Any]]:
    """List citations for an AI response."""
    result = (
        db.table(CITATIONS_TABLE)
        .select("*")
        .eq("ai_response_id", ai_response_id)
        .execute()
    )
    return list(result.data)


def create_citation(db: Client, citation_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new citation."""
    result = db.table(CITATIONS_TABLE).insert(citation_data).execute()
    return result.data[0]


def delete_citation(db: Client, citation_id: int) -> None:
    """Delete a citation."""
    db.table(CITATIONS_TABLE).delete().eq("id", citation_id).execute()


# Source domain operations
def get_source_domain_by_id(db: Client, domain_id: int) -> dict[str, Any] | None:
    """Get a source domain by ID."""
    result = db.table(SOURCE_DOMAINS_TABLE).select("*").eq("id", domain_id).execute()
    return result.data[0] if result.data else None


def list_source_domains_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List source domains for a project."""
    result = (
        db.table(SOURCE_DOMAINS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("total_citations", desc=True)
        .execute()
    )
    return list(result.data)


def create_source_domain(db: Client, domain_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new source domain."""
    result = db.table(SOURCE_DOMAINS_TABLE).insert(domain_data).execute()
    return result.data[0]


def update_source_domain(db: Client, domain_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a source domain."""
    result = db.table(SOURCE_DOMAINS_TABLE).update(update_data).eq("id", domain_id).execute()
    return result.data[0] if result.data else None


def delete_source_domain(db: Client, domain_id: int) -> None:
    """Delete a source domain."""
    db.table(SOURCE_DOMAINS_TABLE).delete().eq("id", domain_id).execute()


# Source gap operations
def get_source_gap_by_id(db: Client, gap_id: int) -> dict[str, Any] | None:
    """Get a source gap by ID."""
    result = db.table(SOURCE_GAPS_TABLE).select("*").eq("id", gap_id).execute()
    return result.data[0] if result.data else None


def list_source_gaps_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List source gaps for a project."""
    result = (
        db.table(SOURCE_GAPS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("discovered_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_source_gap(db: Client, gap_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new source gap."""
    result = db.table(SOURCE_GAPS_TABLE).insert(gap_data).execute()
    return result.data[0]


def delete_source_gap(db: Client, gap_id: int) -> None:
    """Delete a source gap."""
    db.table(SOURCE_GAPS_TABLE).delete().eq("id", gap_id).execute()


# Additional helper functions for visibility route
def list_ai_responses_for_runs(db: Client, run_ids: list[int]) -> list[dict[str, Any]]:
    """List AI responses for multiple prompt runs (batch query)."""
    result = (
        db.table(AI_RESPONSES_TABLE)
        .select("*")
        .in_("prompt_run_id", run_ids)
        .execute()
    )
    return list(result.data)


def count_prompt_runs_for_project(db: Client, project_id: int) -> int:
    """Count prompt runs for a project (via prompt sets)."""
    # Get all prompt sets for project first
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return 0
    set_ids = [s["id"] for s in sets]
    result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id", count="exact")
        .in_("prompt_set_id", set_ids)
        .eq("status", "complete")
        .execute()
    )
    return result.count if hasattr(result, "count") else 0


def count_ai_responses_with_brand_mention_for_project(db: Client, project_id: int) -> int:
    """Count AI responses with brand mention for a project."""
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return 0
    set_ids = [s["id"] for s in sets]
    # Get all prompt runs for these sets
    runs_result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id")
        .in_("prompt_set_id", set_ids)
        .eq("status", "complete")
        .execute()
    )
    run_ids = [r["id"] for r in runs_result.data]
    if not run_ids:
        return 0
    # Count AI responses with brand_mentioned=true
    result = (
        db.table(AI_RESPONSES_TABLE)
        .select("id", count="exact")
        .in_("prompt_run_id", run_ids)
        .eq("brand_mentioned", True)
        .execute()
    )
    return result.count if hasattr(result, "count") else 0


def count_citations_for_project(db: Client, project_id: int) -> int:
    """Count citations for a project."""
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return 0
    set_ids = [s["id"] for s in sets]
    # Get all prompt runs
    runs_result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id")
        .in_("prompt_set_id", set_ids)
        .eq("status", "complete")
        .execute()
    )
    run_ids = [r["id"] for r in runs_result.data]
    if not run_ids:
        return 0
    # Get all AI responses
    ai_result = (
        db.table(AI_RESPONSES_TABLE)
        .select("id")
        .in_("prompt_run_id", run_ids)
        .execute()
    )
    ai_ids = [r["id"] for r in ai_result.data]
    if not ai_ids:
        return 0
    # Count citations
    result = (
        db.table(CITATIONS_TABLE)
        .select("id", count="exact")
        .in_("ai_response_id", ai_ids)
        .execute()
    )
    return result.count if hasattr(result, "count") else 0


def count_prompt_runs_with_model(db: Client, project_id: int, model: str) -> int:
    """Count prompt runs with a specific model for a project."""
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return 0
    set_ids = [s["id"] for s in sets]
    result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id", count="exact")
        .in_("prompt_set_id", set_ids)
        .eq("model_name", model)
        .eq("status", "complete")
        .execute()
    )
    return result.count if hasattr(result, "count") else 0


def count_ai_responses_with_model_and_mention(db: Client, project_id: int, model: str) -> int:
    """Count AI responses with brand mention for a specific model."""
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return 0
    set_ids = [s["id"] for s in sets]
    # Get prompt runs with model
    runs_result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id")
        .in_("prompt_set_id", set_ids)
        .eq("model_name", model)
        .eq("status", "complete")
        .execute()
    )
    run_ids = [r["id"] for r in runs_result.data]
    if not run_ids:
        return 0
    # Count AI responses with brand_mentioned=true
    result = (
        db.table(AI_RESPONSES_TABLE)
        .select("id", count="exact")
        .in_("prompt_run_id", run_ids)
        .eq("brand_mentioned", True)
        .execute()
    )
    return result.count if hasattr(result, "count") else 0


def list_citations_for_prompt_sets(
    db: Client,
    set_ids: list[int],
    limit: int = 100,
    offset: int = 0,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """List citations for multiple prompt sets (batch query).

    When ``domain`` is set, filters at the DB level using ilike so pagination
    is accurate (Issue #46).
    """
    # Get all prompt runs for these sets
    runs_result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id")
        .in_("prompt_set_id", set_ids)
        .eq("status", "complete")
        .execute()
    )
    run_ids = [r["id"] for r in runs_result.data]
    if not run_ids:
        return []

    # Get all AI responses for these runs
    ai_result = (
        db.table(AI_RESPONSES_TABLE)
        .select("id")
        .in_("prompt_run_id", run_ids)
        .execute()
    )
    ai_ids = [r["id"] for r in ai_result.data]
    if not ai_ids:
        return []

    # Get all citations for these AI responses (with optional domain filter)
    query = (
        db.table(CITATIONS_TABLE)
        .select("*")
        .in_("ai_response_id", ai_ids)
    )
    if domain:
        query = query.ilike("domain", f"%{domain}%")
    result = query.order("first_seen_at", desc=True).range(offset, offset + limit - 1).execute()
    return list(result.data)


def count_citations_for_prompt_sets(
    db: Client,
    set_ids: list[int],
    *,
    domain: str | None = None,
) -> int:
    """Return the total number of citations across all pages.

    Mirrors ``list_citations_for_prompt_sets`` so a caller running both
    functions gets a consistent view (same domain filter applied at the DB
    level). Uses Supabase ``count="exact"`` so the returned integer reflects
    the true row count, not just the current page (Issue: PR review).
    """
    if not set_ids:
        return 0

    # Resolve the AI response IDs once (same join as the list function).
    runs_result = (
        db.table(PROMPT_RUNS_TABLE)
        .select("id")
        .in_("prompt_set_id", set_ids)
        .eq("status", "complete")
        .execute()
    )
    run_ids = [r["id"] for r in runs_result.data]
    if not run_ids:
        return 0

    ai_result = (
        db.table(AI_RESPONSES_TABLE)
        .select("id")
        .in_("prompt_run_id", run_ids)
        .execute()
    )
    ai_ids = [r["id"] for r in ai_result.data]
    if not ai_ids:
        return 0

    query = (
        db.table(CITATIONS_TABLE)
        .select("id", count="exact")
        .in_("ai_response_id", ai_ids)
    )
    if domain:
        query = query.ilike("domain", f"%{domain}%")
    result = query.execute()
    return int(result.count or 0)


def list_citations_for_project(db: Client, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """List citations for a project."""
    sets = list_prompt_sets_for_project(db, project_id)
    if not sets:
        return []
    set_ids = [s["id"] for s in sets]
    return list_citations_for_prompt_sets(db, set_ids, limit=limit)
