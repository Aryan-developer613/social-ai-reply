"""SEO agent API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.api.v1.routes._helpers import get_company_opportunities
from app.db.supabase_client import get_supabase
from app.db.tables.agent_runs import get_last_agent_run
from app.db.tables.company import get_company_by_id
from app.schemas.v1.common import BackgroundTaskResponse
from app.services.agents.seo_agent import SEOAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["seo"])

agent = SEOAgent()


def _run_seo_task(company_id: int, config: dict[str, Any], db: Client) -> None:
    try:
        agent.run(company_id, db, config)
    except Exception:
        logger.exception("Background SEO run failed")


@router.post("/seo/run", status_code=status.HTTP_202_ACCEPTED, response_model=BackgroundTaskResponse)
def run_seo(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> BackgroundTaskResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    company_id = payload.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required.")

    company = get_company_by_id(supabase, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    if company.get("workspace_id") != workspace["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    background_tasks.add_task(_run_seo_task, company_id, payload, supabase)
    return BackgroundTaskResponse(status="running", agent="seo")


@router.get("/seo/audit")
def get_seo_audit(
    company_id: int = Query(..., ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, Any]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    company = get_company_by_id(supabase, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    run = get_last_agent_run(supabase, company_id, "seo")
    seo_opps = get_company_opportunities(
        supabase, workspace["id"], company_id, platform="seo", opportunity_type="seo_issue",
        limit=limit, offset=offset,
    )

    return {
        "last_run": run,
        "issues": seo_opps,
        "issue_count": len(seo_opps),
    }


@router.get("/seo/gaps")
def get_seo_gaps(
    company_id: int = Query(..., ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[dict[str, Any]]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    company = get_company_by_id(supabase, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    return get_company_opportunities(
        supabase, workspace["id"], company_id, platform="seo", opportunity_type="keyword_gap",
        limit=limit, offset=offset,
    )
