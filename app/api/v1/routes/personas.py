"""Persona management endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.discovery import (
    create_persona as create_persona_table,
)
from app.db.tables.discovery import (
    delete_persona as delete_persona_table,
)
from app.db.tables.discovery import (
    get_persona_by_id,
    list_personas_for_project,
)
from app.db.tables.discovery import (
    update_persona as update_persona_table,
)
from app.schemas.v1.personas import PersonaRequest, PersonaResponse, PersonaUpdateRequest
from app.services.product.copilot import ProductCopilot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["personas"])


@router.get("/personas", response_model=list[PersonaResponse])
def list_personas(
    project_id: int = Query(..., ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[PersonaResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    # Validate project access
    get_project(supabase, workspace["id"], project_id)
    rows = list_personas_for_project(supabase, project_id)
    return [PersonaResponse.model_validate(row) for row in rows]


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona_endpoint(
    payload: PersonaRequest,
    project_id: int = Query(..., ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PersonaResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    # Validate project access
    get_project(supabase, workspace["id"], project_id)

    persona_data = {
        "project_id": project_id,
        **payload.model_dump(),
        "source": payload.source if hasattr(payload, 'source') and payload.source else "manual",
    }
    persona = create_persona_table(supabase, persona_data)
    return PersonaResponse.model_validate(persona)


@router.post("/personas/generate", response_model=list[PersonaResponse])
def generate_personas(
    project_id: int = Query(..., ge=1),
    count: int = Query(default=4, ge=1, le=8),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[PersonaResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    get_project(supabase, workspace["id"], project_id)  # 404s if not in workspace

    # NOTE: project.get("brand_profile") was a bug — projects rows never had
    # that key, so generation always fell back to generic, non-brand-aware
    # personas. resolve_brand_context merges brand_profiles + company_profiles.
    from app.db.tables.projects import resolve_brand_context
    brand = resolve_brand_context(supabase, workspace["id"], project_id)

    generated = ProductCopilot().suggest_personas(brand, count=count)
    rows = []
    for item in generated:
        persona_data = {"project_id": project_id, **item}
        persona = create_persona_table(supabase, persona_data)
        rows.append(persona)

    return [PersonaResponse.model_validate(row) for row in rows]


@router.put("/personas/{persona_id}", response_model=PersonaResponse)
def update_persona_endpoint(
    persona_id: int,
    payload: PersonaUpdateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PersonaResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    persona = get_persona_by_id(supabase, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")

    # Verify workspace access via project
    get_project(supabase, workspace["id"], persona["project_id"])

    update_data = payload.model_dump(exclude_unset=True)
    updated = update_persona_table(supabase, persona_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found.")
    return PersonaResponse.model_validate(updated)


@router.delete("/personas/{persona_id}")
def delete_persona_endpoint(
    persona_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, bool]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    persona = get_persona_by_id(supabase, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")

    # Verify workspace access
    if persona["project_id"] != get_project(supabase, workspace["id"], persona["project_id"])["id"]:
        raise HTTPException(status_code=404, detail="Persona not found.")

    delete_persona_table(supabase, persona_id)
    return {"ok": True}
