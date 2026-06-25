from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.v1.deps import get_current_user, get_current_workspace, ensure_workspace_membership
from app.db.supabase_client import get_supabase
from app.db.tables.custom_scrapers import (
    list_custom_scrapers_for_workspace,
    upsert_custom_scraper,
    delete_custom_scraper,
)
from app.schemas.v1.scrapers import CustomScraperResponse, CustomScraperCreateRequest

router = APIRouter(prefix="/v1/scrapers", tags=["scrapers"])


@router.get("", response_model=list[CustomScraperResponse])
def list_scrapers_endpoint(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[CustomScraperResponse]:
    """List all custom scrapers for the current workspace."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    scrapers = list_custom_scrapers_for_workspace(supabase, workspace["id"])
    return [CustomScraperResponse.model_validate(s) for s in scrapers]


@router.post("", response_model=CustomScraperResponse, status_code=status.HTTP_201_CREATED)
def create_scraper_endpoint(
    payload: CustomScraperCreateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> CustomScraperResponse:
    """Create or update a custom scraper configuration for a specific platform."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    
    data = payload.model_dump()
    data["workspace_id"] = workspace["id"]
    
    scraper = upsert_custom_scraper(supabase, data)
    return CustomScraperResponse.model_validate(scraper)


@router.delete("/{scraper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scraper_endpoint(
    scraper_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> None:
    """Delete a custom scraper configuration."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    
    # Optional: verify the scraper belongs to the workspace before deleting
    # RLS handles this mostly, but good practice.
    
    delete_custom_scraper(supabase, scraper_id)
