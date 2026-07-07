"""Enhanced search endpoints for Reddit, X/Twitter, and web citations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace, get_project
from app.core.config import get_settings
from app.db.supabase_client import get_supabase
from app.db.tables.search_cache import get_cached_search_result
from app.schemas.v1.search import (
    RedditSearchRequest,
    SearchCacheResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.search.service import EnhancedSearchService

if TYPE_CHECKING:
    from supabase import Client

router = APIRouter(prefix="/v1/search", tags=["search"])


def _ensure_enabled() -> None:
    if not get_settings().enable_enhanced_search:
        raise HTTPException(status_code=404, detail="Enhanced search is disabled.")


def _validate_project_if_present(db: Client, workspace_id: int, project_id: int | None) -> None:
    if project_id is not None:
        get_project(db, workspace_id, project_id)


@router.post("/reddit", response_model=SearchResponse)
def search_reddit(
    payload: RedditSearchRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SearchResponse:
    _ensure_enabled()
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    _validate_project_if_present(supabase, workspace["id"], payload.project_id)
    return EnhancedSearchService(supabase, workspace["id"]).search_reddit(
        payload.query,
        subreddits=payload.subreddits,
        limit=payload.limit,
        use_cache=payload.use_cache,
    )


@router.post("/x", response_model=SearchResponse)
def search_x(
    payload: SearchRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SearchResponse:
    _ensure_enabled()
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    _validate_project_if_present(supabase, workspace["id"], payload.project_id)
    return EnhancedSearchService(supabase, workspace["id"]).search_x(
        payload.query,
        limit=payload.limit,
        use_cache=payload.use_cache,
    )


@router.post("/web", response_model=SearchResponse)
def search_web(
    payload: SearchRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SearchResponse:
    _ensure_enabled()
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    _validate_project_if_present(supabase, workspace["id"], payload.project_id)
    return EnhancedSearchService(supabase, workspace["id"]).search_web(
        payload.query,
        limit=payload.limit,
        use_cache=payload.use_cache,
    )


@router.get("/cache/{cache_key}", response_model=SearchCacheResponse)
def get_search_cache(
    cache_key: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SearchCacheResponse:
    _ensure_enabled()
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_cached_search_result(supabase, cache_key)
    if not row or row.get("workspace_id") != workspace["id"]:
        raise HTTPException(status_code=404, detail="Search cache entry not found.")
    return SearchCacheResponse.model_validate(row)
