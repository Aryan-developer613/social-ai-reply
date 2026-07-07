"""Reply and post draft endpoints."""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import (
    ensure_default_prompts,
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.content import (
    count_reply_drafts_for_project,
    create_post_draft,
    create_reply_draft,
    delete_draft_calendar_posts_for_project_platform,
    get_post_draft_by_id,
    get_reply_draft_by_id,
    list_post_drafts_for_project,
    list_reply_drafts_for_opportunities,
)
from app.db.tables.content import (
    list_reply_drafts_for_opportunity as list_reply_drafts_for_opportunity_db,
)
from app.db.tables.content import (
    update_post_draft as update_post_draft_db,
)
from app.db.tables.content import (
    update_reply_draft as update_reply_draft_db,
)
from app.db.tables.discovery import (
    count_opportunities_for_project,
    get_opportunity_by_id,
    get_subreddit_by_project_and_name,
    list_opportunities_for_project,
    update_opportunity,
)
from app.db.tables.projects import list_prompt_templates_for_project
from app.db.tables.voice_profiles import (
    get_default_voice_profile_for_project,
    get_voice_profile_by_id,
)
from app.schemas.v1.content import (
    ContentPlanRequest,
    PostDraftRequest,
    PostDraftResponse,
    PostDraftScheduleRequest,
    PostDraftUpdateRequest,
    ReplyDraftRequest,
    ReplyDraftResponse,
    ReplyDraftUpdateRequest,
)
from app.services.product.copilot import ProductCopilot
from app.services.product.copilot.reply import generate_reply
from app.services.product.scanner import revalidate_opportunity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["drafts"])

_REPLY_STYLE_PRESETS = {
    "shorter": "Rewrite this as a shorter, tighter reply. Keep only the most useful point.",
    "more_helpful": "Rewrite this to be more helpful and concrete. Add one practical next step if it fits.",
    "more_professional": "Rewrite this with a calm professional tone while keeping it human and direct.",
    "less_promotional": "Rewrite this to remove promotional phrasing. Avoid hard CTAs and product-first wording.",
}


def _opportunity_display_source(opportunity: dict) -> str:
    source = opportunity.get("subreddit_name") or opportunity.get("source_name")
    if source:
        return str(source)

    platform = str(opportunity.get("platform") or "reddit").lower()
    permalink = str(opportunity.get("permalink") or "")
    if platform == "reddit" and permalink:
        import re

        match = re.search(r"(?:^|/)r/([^/]+)", permalink)
        if match:
            return match.group(1)

    return str(opportunity.get("platform") or "")


def _reply_prompts_with_style(prompts: list[dict], style_preset: str | None) -> list[dict]:
    instructions = _REPLY_STYLE_PRESETS.get(style_preset or "")
    if not instructions:
        return prompts
    return [
        *prompts,
        {
            "prompt_type": "reply",
            "name": "Regeneration style",
            "instructions": instructions,
        },
    ]


def _next_reply_version(supabase: Client, opportunity_id: int) -> int:
    drafts = list_reply_drafts_for_opportunity_db(supabase, opportunity_id)
    return max((int(draft.get("version") or 0) for draft in drafts), default=0) + 1


def _jsonish_to_list(value: Any) -> list[str]:
    """Coerce JSON/string profile fields into a clean list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            import json

            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        separators = [",", ";", "\n"]
        if any(sep in text for sep in separators):
            import re

            return [part.strip() for part in re.split(r"[,;\n]+", text) if part.strip()]
        return [text]
    return [str(value).strip()] if str(value).strip() else []


def _normalise_calendar_platform(platform: str | None) -> str:
    value = (platform or "x").strip().lower()
    return "x" if value == "twitter" else value


def _calendar_brand_profile(brand_context: dict[str, Any] | None, project: dict[str, Any]) -> dict[str, Any]:
    brand = brand_context or {}
    return {
        "name": brand.get("brand_name") or project.get("name") or "the brand",
        "description": brand.get("summary") or brand.get("product_summary") or project.get("description") or "",
        "category": brand.get("business_domain") or "",
        "target_audience": brand.get("target_audience") or "",
        "pain_points": _jsonish_to_list(brand.get("pain_points")),
        "competitors": _jsonish_to_list(brand.get("competitors")),
        "features": _jsonish_to_list(brand.get("features")),
    }


def _calendar_ideas(
    supabase: Client,
    project_id: int,
    profile: dict[str, Any],
    count: int,
    campaign_goal: str | None = None,
    campaign_brief: str | None = None,
    content_template: str | None = None,
) -> list[str]:
    """Build enough content angles for a short content calendar."""
    ideas: list[str] = []
    seen: set[str] = set()
    brand = profile.get("name") or "the brand"
    category = profile.get("category") or "the market"
    audience = profile.get("target_audience") or "customers"
    competitors = profile.get("competitors") or []

    def add(text: str) -> None:
        key = text.strip().lower()
        if key and key not in seen:
            ideas.append(text.strip())
            seen.add(key)

    for pain in profile.get("pain_points") or []:
        add(f"One practical way {audience} can avoid {pain}")

    if campaign_brief:
        add(f"Campaign brief: {campaign_brief.strip()}")

    if content_template == "comparison":
        add(f"A practical comparison checklist for choosing between {brand} and other {category} options")
    elif content_template == "founder_story":
        add(f"The founder lesson behind why {brand} focuses on {audience}")
    elif content_template == "case_study":
        add(f"A customer scenario showing how {audience} can improve a {category} workflow")
    elif content_template == "offer_post":
        add(f"A clear offer-led post explaining when {audience} should consider {brand}")
    else:
        add(f"A practical product tip for getting more value from {brand}")

    if campaign_goal == "lead_generation":
        add(f"A practical checklist {audience} can use before choosing a {category} solution")
        add(f"The cost of delaying better {category} workflows")
        add(f"How to know when your current {category} process is ready for an upgrade")
    elif campaign_goal == "product_launch":
        add(f"What is new in {brand} and why it matters for {audience}")
        add(f"Behind the scenes: the customer problem {brand} is solving next")
        add(f"A quick walkthrough of the most useful {brand} improvement")
    elif campaign_goal == "competitor_switch":
        add(f"Why teams compare alternatives before choosing a {category} solution")
        add(f"What to check before switching from a familiar {category} tool")
        add(f"How {audience} can reduce risk when moving to a better {category} workflow")
    elif campaign_goal == "education":
        add(f"A simple explainer for understanding {category} options")
        add(f"Common myths {audience} hear about {category}")
        add(f"A beginner-friendly way to evaluate {category} tools")
    else:
        add(f"What {audience} should know before choosing a {category} solution")
        add(f"One trend changing how {audience} think about {category}")

    for competitor in competitors:
        add(f"What {brand} does differently from {competitor}")

    try:
        opportunities = list_opportunities_for_project(supabase, project_id, status=None, limit=100)
    except Exception as exc:
        logger.warning("Could not load opportunities for content calendar ideas: %s", exc)
        opportunities = []

    for opportunity in opportunities[:12]:
        title = str(opportunity.get("title") or "").strip()
        if title:
            add(f"A useful take on: {title[:120]}")
        body = str(opportunity.get("body_excerpt") or opportunity.get("body") or "").strip()
        if body and len(ideas) < count:
            add(f"A lesson from this customer conversation: {body[:120]}")

    add(f"Three mistakes people still make in {category}")
    add(f"A simple checklist for choosing a better {category} solution")
    add(f"What we learned building {brand} for {audience}")
    add(f"A quick product tip for getting more value from {brand}")
    add(f"The hidden cost of delaying better {category} workflows")

    while len(ideas) < count:
        add(f"Marketing insight #{len(ideas) + 1} for {audience}: small weekly improvements compound")

    return ideas[:count]


def _calendar_start(start_at: datetime | None, preferred_hour_utc: int) -> datetime:
    if start_at is None:
        now = datetime.now(UTC)
        return (now + timedelta(days=1)).replace(hour=preferred_hour_utc, minute=0, second=0, microsecond=0)
    if start_at.tzinfo is None:
        return start_at.replace(tzinfo=UTC)
    return start_at.astimezone(UTC)


def _fit_tweet(text: str) -> str:
    """Keep X calendar suggestions within the single-tweet limit."""
    compact = " ".join(text.strip().split())
    if len(compact) <= 280:
        return compact
    return compact[:277].rstrip() + "..."


def _draft_content_for_calendar(
    platform: str,
    idea: str,
    profile: dict[str, Any],
    content_type: str,
) -> dict[str, Any]:
    if platform == "linkedin":
        from app.services.agents.linkedin_agent import LinkedInAgent

        return LinkedInAgent().generate_post_draft(idea, profile, content_type)

    from app.services.agents.x_agent import XAgent

    draft = XAgent().generate_post_draft(idea, profile, content_type)
    draft["content"] = _fit_tweet(str(draft.get("content") or idea))
    return draft


def _fallback_calendar_draft(
    platform: str,
    idea: str,
    profile: dict[str, Any],
    content_type: str,
    voice_style: str | None = None,
) -> dict[str, str]:
    """Create deterministic calendar copy when the AI provider is unavailable."""
    brand = str(profile.get("name") or "the brand").strip()
    audience = str(profile.get("target_audience") or "customers").strip()
    title = idea[:90].rstrip(" .") or f"{brand} marketing update"
    voice_line = {
        "friendly": "Keep it simple, human, and easy to reply to.",
        "premium": "Make the point calmly with a polished, high-trust tone.",
        "witty": "Use a light hook, but keep the advice useful.",
    }.get(voice_style or "professional", "Keep it clear, specific, and professional.")

    if platform == "linkedin":
        body = (
            f"{idea}\n\n"
            f"For {audience}, the practical takeaway is simple: compare the real workflow cost, not only the headline feature list. "
            f"{brand} is focused on making that decision clearer, safer, and easier to act on.\n\n"
            f"{voice_line}"
        )
    else:
        body = (
            f"{idea}\n\n"
            f"Quick takeaway: {brand} helps {audience} make a clearer decision without adding extra friction. {voice_line}"
        )

    return {
        "title": title,
        "content": _fit_tweet(body) if platform == "x" else body,
        "rationale": f"Fallback {platform} calendar post for {content_type}.",
    }


@router.post("/drafts/replies", response_model=ReplyDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_reply_draft(
    payload: ReplyDraftRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ReplyDraftResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    opportunity = get_opportunity_by_id(supabase, payload.opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    # Verify workspace access
    project = get_project(supabase, workspace["id"], opportunity["project_id"])

    # Revalidation uses a Reddit-specific scoring engine (RedditPost model,
    # topical gate). Non-Reddit opportunities (Twitter, LinkedIn, Instagram)
    # were already scored during scanning and would always fail the Reddit
    # revalidation gate. Skip it for them.
    opp_platform = (opportunity.get("platform") or "reddit").lower()
    if opp_platform == "reddit":
        is_valid, _score = revalidate_opportunity(supabase, project, opportunity)
        if not is_valid:
            update_opportunity(supabase, opportunity["id"], {"status": "ignored"})
            raise HTTPException(status_code=422, detail="Opportunity no longer meets the relevance threshold.")

    ensure_default_prompts(supabase, project["id"])
    prompts = list_prompt_templates_for_project(supabase, project["id"])
    reply_prompts = _reply_prompts_with_style(prompts, payload.style_preset)

    # NOTE: project.get("brand_profile") was a bug — projects rows never had
    # that key, so AI-generated reply drafts have been produced with zero
    # brand context (no brand name, tone, audience, or pain points) on every
    # call site except the old pipeline.py auto-pipeline, which manually
    # worked around this by hydrating the dict itself. Resolve once here.
    from app.db.tables.projects import resolve_brand_context
    brand_context = resolve_brand_context(supabase, workspace["id"], project["id"])

    # Resolve the voice profile: explicit request > project default > none.
    voice_profile = None
    if payload.voice_profile_id is not None:
        voice_profile = get_voice_profile_by_id(supabase, payload.voice_profile_id)
        if not voice_profile or voice_profile["project_id"] != project["id"]:
            raise HTTPException(status_code=404, detail="Voice profile not found.")
    else:
        voice_profile = get_default_voice_profile_for_project(supabase, project["id"])

    # Load per-subreddit tone rules from the opportunity's monitored subreddit, if any.
    subreddit_tone_rules = None
    subreddit_name = opportunity.get("subreddit_name") or opportunity.get("subreddit")
    if subreddit_name:
        monitored = get_subreddit_by_project_and_name(supabase, project["id"], subreddit_name)
        if monitored:
            subreddit_tone_rules = monitored.get("tone_rules")

    # Resolve effective platform: explicit override > opportunity's platform > "reddit"
    effective_platform = payload.platform or opportunity.get("platform") or "reddit"

    if payload.variants > 1:
        # Multi-variant generation
        from app.services.product.copilot.reply import generate_reply_variants

        variants = generate_reply_variants(
            opportunity,
            brand_context,
            reply_prompts,
            voice_profile=voice_profile,
            subreddit_tone_rules=subreddit_tone_rules,
            platform=effective_platform,
            count=payload.variants,
        )
        if not variants:
            raise HTTPException(status_code=500, detail="Failed to generate any reply variants.")

        # Save all variants as drafts, return the first one
        first_draft = None
        next_version = _next_reply_version(supabase, opportunity["id"])
        for i, (content, rationale, source_prompt) in enumerate(variants):
            draft = create_reply_draft(
                supabase,
                {
                    "project_id": project["id"],
                    "opportunity_id": opportunity["id"],
                    "content": content,
                    "rationale": rationale,
                    "source_prompt": source_prompt,
                    "version": next_version + i,
                },
            )
            if first_draft is None:
                first_draft = draft

        update_opportunity(supabase, opportunity["id"], {"status": "drafting"})
        return ReplyDraftResponse.model_validate(first_draft)

    # Single reply (default path — unchanged behavior)
    try:
        content, rationale, source_prompt = generate_reply(
            opportunity,
            brand_context,
            reply_prompts,
            voice_profile=voice_profile,
            subreddit_tone_rules=subreddit_tone_rules,
            platform=effective_platform,
        )
    except TypeError as exc:
        if "unexpected keyword argument 'platform'" not in str(exc):
            raise
        content, rationale, source_prompt = generate_reply(
            opportunity,
            brand_context,
            reply_prompts,
            voice_profile=voice_profile,
            subreddit_tone_rules=subreddit_tone_rules,
        )
    except RuntimeError as exc:
        logger.warning("Reply generation failed for opportunity %s: %s", opportunity.get("id"), exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    draft = create_reply_draft(
        supabase,
        {
            "project_id": project["id"],
            "opportunity_id": opportunity["id"],
            "content": content,
            "rationale": rationale,
            "source_prompt": source_prompt,
            "version": _next_reply_version(supabase, opportunity["id"]),
        },
    )

    # Update opportunity status
    update_opportunity(supabase, opportunity["id"], {"status": "drafting"})

    return ReplyDraftResponse.model_validate(draft)


@router.get("/drafts/replies")
def list_reply_drafts(
    status_filter: str = Query(default="drafting", alias="status"),
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """List reply drafts with enriched opportunity data for Content Studio.

    FIXED: Uses batch queries instead of N+1 queries.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        return []

    # Get all opportunities for the project with the given status (batch query)
    opps = list_opportunities_for_project(supabase, proj["id"], status=status_filter, limit=200)
    if not opps:
        return []

    opportunity_ids = [o["id"] for o in opps]
    opp_by_id = {o["id"]: o for o in opps}

    # Get all reply drafts for these opportunities in a single batch query
    # Then select the latest draft for each opportunity
    all_drafts = list_reply_drafts_for_opportunities(supabase, opportunity_ids)

    # Group by opportunity and get latest
    latest_drafts = {}
    for draft in all_drafts:
        opp_id = draft["opportunity_id"]
        if opp_id not in latest_drafts or draft["id"] > latest_drafts[opp_id]["id"]:
            latest_drafts[opp_id] = draft

    results = []
    for opp_id, draft in latest_drafts.items():
        opp = opp_by_id.get(opp_id)
        if opp:
            results.append({
                "id": draft["id"],
                "opportunity_id": opp["id"],
                "content": draft["content"],
                "rationale": draft.get("rationale", ""),
                "version": draft["version"],
                "created_at": draft.get("created_at"),
                "opportunity_title": opp["title"],
                "opportunity_subreddit": _opportunity_display_source(opp),
                "permalink": opp["permalink"],
                "body_excerpt": opp.get("body_excerpt") or opp.get("body") or "",
                "platform": opp.get("platform", "reddit"),
                "score": opp.get("score"),
            })

    # Sort by created_at descending
    results.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return results


@router.get("/drafts/count")
def get_draft_counts(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Count drafting and published reply drafts for a project.

    Returns accurate counts from the database rather than deriving them
    from a limited opportunity list.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        return {"drafting": 0, "published": 0, "total": 0}

    drafting = count_reply_drafts_for_project(supabase, proj["id"])
    published = count_opportunities_for_project(supabase, proj["id"], status="posted")
    return {"drafting": drafting, "published": published, "total": drafting + published}


@router.put("/drafts/replies/{draft_id}", response_model=ReplyDraftResponse)
def update_reply_draft(
    draft_id: int,
    payload: ReplyDraftUpdateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ReplyDraftResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    draft = get_reply_draft_by_id(supabase, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Reply draft not found.")

    # Verify workspace access via project
    get_project(supabase, workspace["id"], draft["project_id"])

    updated = update_reply_draft_db(
        supabase,
        draft_id,
        {
            "content": payload.content,
            "rationale": payload.rationale,
        },
    )
    return ReplyDraftResponse.model_validate(updated)


@router.post("/drafts/posts", response_model=PostDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_post_draft(
    payload: PostDraftRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PostDraftResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], payload.project_id)

    ensure_default_prompts(supabase, project["id"])
    prompts = list_prompt_templates_for_project(supabase, project["id"])

    from app.db.tables.projects import resolve_brand_context
    brand_context = resolve_brand_context(supabase, workspace["id"], project["id"])
    title, body, rationale = ProductCopilot().generate_post(brand_context, prompts)

    # Get next version - batch query
    existing_drafts = list_post_drafts_for_project(supabase, project["id"])
    version = (max((d["version"] for d in existing_drafts), default=0)) + 1

    post_prompts = [p for p in prompts if p.get("prompt_type") == "post"]
    source_prompt = "\n".join(p.get("instructions", "") for p in post_prompts)

    draft = create_post_draft(
        supabase,
        {
            "project_id": project["id"],
            "title": title,
            "body": body,
            "rationale": rationale,
            "source_prompt": source_prompt,
            "version": version,
            "platform": _normalise_calendar_platform(payload.platform),
            "status": "draft",
        },
    )
    return PostDraftResponse.model_validate(draft)


@router.post("/drafts/posts/plan", response_model=list[PostDraftResponse], status_code=status.HTTP_201_CREATED)
def generate_content_plan(
    payload: ContentPlanRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[PostDraftResponse]:
    """Generate suggested social posts for a 1-week or 1-month calendar.

    Suggestions are saved as draft post rows with proposed ``scheduled_at``
    slots. They are not treated as scheduled until the user explicitly approves
    a draft through the schedule endpoint.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], payload.project_id)
    platform = _normalise_calendar_platform(payload.platform)

    from app.db.tables.projects import resolve_brand_context

    brand_context = resolve_brand_context(supabase, workspace["id"], project["id"])
    profile = _calendar_brand_profile(brand_context, project)

    default_count = payload.horizon_days if platform == "x" else max(1, min(12, payload.horizon_days // 3 + 1))
    count = min(payload.count or default_count, payload.horizon_days, 30)
    ideas = _calendar_ideas(
        supabase,
        project["id"],
        profile,
        count,
        payload.campaign_goal,
        payload.campaign_brief,
        payload.content_template,
    )
    start_at = _calendar_start(payload.start_at, payload.preferred_hour_utc)

    try:
        delete_draft_calendar_posts_for_project_platform(supabase, project["id"], platform)
    except Exception as exc:
        logger.warning(
            "Could not clear old draft calendar posts for project %s platform %s: %s",
            project["id"],
            platform,
            exc,
        )
    existing_drafts = list_post_drafts_for_project(supabase, project["id"])
    next_version = max((int(d.get("version") or 0) for d in existing_drafts), default=0) + 1
    template_type = payload.content_template or "product_tip"
    x_types = [template_type, "original", "pain_point", "founder_update", "quote"]
    linkedin_types = [template_type, "educational", "product_update", "pain_point", "comparison", "founder_story"]

    created: list[dict[str, Any]] = []
    spacing_days = max(1, payload.horizon_days // max(count, 1))
    for index, idea in enumerate(ideas):
        content_types = linkedin_types if platform == "linkedin" else x_types
        content_type = content_types[index % len(content_types)]
        try:
            try:
                draft = _draft_content_for_calendar(platform, idea, profile, content_type)
            except Exception as exc:
                logger.warning(
                    "AI calendar suggestion failed for project %s platform %s idea %r, using fallback: %s",
                    project["id"],
                    platform,
                    idea,
                    exc,
                )
                draft = _fallback_calendar_draft(platform, idea, profile, content_type, payload.voice_style)
            scheduled_at = start_at + timedelta(days=index * spacing_days)
            body = str(draft.get("content") or idea).strip()
            if platform == "x":
                body = _fit_tweet(body)
            row = create_post_draft(
                supabase,
                {
                    "project_id": project["id"],
                    "title": str(draft.get("title") or idea)[:255],
                    "body": body,
                    "rationale": draft.get("rationale")
                    or f"Suggested {platform} calendar post for {payload.campaign_goal}.",
                    "source_prompt": (
                        f"Content calendar: {payload.campaign_goal or 'brand_awareness'} / "
                        f"{payload.voice_style or 'professional'} / {content_type}"
                    ),
                    "version": next_version + len(created),
                    "platform": platform,
                    "thread_json": [body] if platform == "x" else [],
                    "status": "draft",
                    "scheduled_at": scheduled_at.isoformat(),
                },
            )
            created.append(row)
        except Exception:
            logger.exception(
                "Content calendar suggestion failed for project %s platform %s idea %r",
                project["id"],
                platform,
                idea,
            )
            continue

    if not created:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate a content plan right now. Check the AI provider/API key and try again.",
        )

    return [PostDraftResponse.model_validate(row) for row in created]


@router.get("/drafts/posts", response_model=list[PostDraftResponse])
def list_post_drafts(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[PostDraftResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        return []

    rows = list_post_drafts_for_project(supabase, proj["id"])
    return [PostDraftResponse.model_validate(row) for row in rows]


@router.put("/drafts/posts/{draft_id}", response_model=PostDraftResponse)
def update_post_draft(
    draft_id: int,
    payload: PostDraftUpdateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PostDraftResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    draft = get_post_draft_by_id(supabase, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")

    # Verify workspace access via project
    get_project(supabase, workspace["id"], draft["project_id"])

    update_data: dict[str, Any] = {
        "title": payload.title,
        "body": payload.body,
        "rationale": payload.rationale,
    }
    if payload.status:
        update_data["status"] = payload.status

    updated = update_post_draft_db(supabase, draft_id, update_data)
    return PostDraftResponse.model_validate(updated)


@router.post("/drafts/posts/{draft_id}/schedule", response_model=PostDraftResponse)
def schedule_post_draft(
    draft_id: int,
    payload: PostDraftScheduleRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PostDraftResponse:
    """Approve a draft for the content calendar.

    This records the scheduled slot inside the app. Actual auto-publishing still
    depends on platform credentials and publishing workers.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    draft = get_post_draft_by_id(supabase, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    get_project(supabase, workspace["id"], draft["project_id"])

    scheduled_at = payload.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)

    updated = update_post_draft_db(
        supabase,
        draft_id,
        {
            "status": "scheduled",
            "scheduled_at": scheduled_at.astimezone(UTC).isoformat(),
        },
    )
    return PostDraftResponse.model_validate(updated)


@router.post("/drafts/posts/{draft_id}/unschedule", response_model=PostDraftResponse)
def unschedule_post_draft(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PostDraftResponse:
    """Move a scheduled calendar draft back to draft review."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    draft = get_post_draft_by_id(supabase, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    get_project(supabase, workspace["id"], draft["project_id"])

    updated = update_post_draft_db(supabase, draft_id, {"status": "draft"})
    return PostDraftResponse.model_validate(updated)



def list_reply_drafts_for_opportunity(supabase: Client, opportunity_id: int) -> list:
    """Helper to list reply drafts for an opportunity."""
    from app.db.tables.content import list_reply_drafts_for_opportunity as _list
    return _list(supabase, opportunity_id)
