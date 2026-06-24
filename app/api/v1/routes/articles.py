"""Articles agent API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.api.v1.routes._helpers import get_company_opportunities
from app.db.supabase_client import get_supabase
from app.db.tables.company import get_company_by_id, get_company_by_workspace
from app.db.tables.discovery import get_opportunity_by_id, update_opportunity
from app.schemas.v1.common import BackgroundTaskResponse
from app.services.agents.articles_agent import ArticlesAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["articles"])

agent = ArticlesAgent()


def _run_articles_task(company_id: int, config: dict[str, Any], db: Client) -> None:
    try:
        agent.run(company_id, db, config)
    except Exception:
        logger.exception("Background articles run failed")


@router.post("/articles/run", status_code=status.HTTP_202_ACCEPTED, response_model=BackgroundTaskResponse)
def run_articles(
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

    background_tasks.add_task(_run_articles_task, company_id, payload, supabase)
    return BackgroundTaskResponse(status="running", agent="articles")


@router.get("/articles")
def list_articles(
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
        supabase, workspace["id"], company_id, platform="article", opportunity_type="article_brief",
        limit=limit, offset=offset,
    )


@router.get("/articles/{opportunity_id}/export")
def export_article(
    opportunity_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, str]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    opp = get_opportunity_by_id(supabase, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    markdown = agent.export_brief(opportunity_id, supabase)
    return {"markdown": markdown}


@router.post("/articles/{opportunity_id}/regenerate")
def regenerate_article(
    opportunity_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, Any]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    opp = get_opportunity_by_id(supabase, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    company = get_company_by_id(supabase, opp.get("company_id", 0))
    if not company:
        company = get_company_by_workspace(supabase, workspace["id"])

    title = opp.get("title", "")
    keyword = _extract_keyword(title)

    brief = agent.generate_brief(title, keyword, company or {})
    brief_json = str(brief)
    update_opportunity(
        supabase,
        opportunity_id,
        {
            "body": brief_json[:4000],
            "draft_article": brief_json,
        },
    )
    return {"status": "regenerated", "brief": brief}


def _extract_keyword(title: str) -> str:
    words = title.split()
    if len(words) > 3:
        return " ".join(words[2:-1])
    return title
