"""Amplification endpoints: repurpose Reddit replies into X threads / LinkedIn posts."""
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.campaigns import create_published_post
from app.db.tables.content import (
    create_post_draft,
    get_post_draft_by_id,
    get_reply_draft_by_id,
    list_post_drafts_for_project,
    update_post_draft,
)
from app.db.tables.discovery import get_opportunity_by_id
from app.schemas.v1.amplify import (
    TWEET_MAX_CHARS,
    AmplifyDraftResponse,
    AmplifyRequest,
    AmplifyUpdateRequest,
    PublishedTweet,
    PublishResponse,
)
from app.services.infrastructure.x_publisher import XPublisher, get_x_token
from app.services.product.amplify import amplify_to_linkedin, amplify_to_x_thread

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["amplify"])


def _load_source(
    supabase: Client,
    workspace_id: int,
    payload: AmplifyRequest,
) -> tuple[dict[str, Any], dict[str, Any], int | None, int | None]:
    """Resolve the amplification source and verify workspace access.

    Returns (source dict, project, source_reply_draft_id, source_opportunity_id).
    """
    if payload.reply_draft_id is not None:
        draft = get_reply_draft_by_id(supabase, payload.reply_draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Reply draft not found.")
        project = get_project(supabase, workspace_id, draft["project_id"])
        opportunity = (
            get_opportunity_by_id(supabase, draft["opportunity_id"])
            if draft.get("opportunity_id")
            else None
        ) or {}
        source = {
            "title": opportunity.get("title", ""),
            "body": opportunity.get("body_excerpt") or opportunity.get("body") or "",
            "subreddit": opportunity.get("subreddit_name") or opportunity.get("subreddit") or "",
            "content": draft.get("content", ""),
        }
        return source, project, draft["id"], opportunity.get("id")

    opportunity = get_opportunity_by_id(supabase, payload.opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    project = get_project(supabase, workspace_id, opportunity["project_id"])
    source = {
        "title": opportunity.get("title", ""),
        "body": opportunity.get("body_excerpt") or opportunity.get("body") or "",
        "subreddit": opportunity.get("subreddit_name") or opportunity.get("subreddit") or "",
        "content": opportunity.get("draft_post") or "",
    }
    return source, project, None, opportunity["id"]


def _load_voice_profile(
    supabase: Client,
    project_id: int,
    voice_profile_id: int | None,
) -> dict[str, Any] | None:
    """Load a voice profile if requested; tolerate the module not existing yet."""
    if voice_profile_id is None:
        return None
    try:
        from app.db.tables.voice_profiles import get_voice_profile_by_id
    except ImportError:
        logger.warning("voice_profiles table helpers unavailable; proceeding without voice.")
        return None
    profile = get_voice_profile_by_id(supabase, voice_profile_id)
    if not profile or profile.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    return profile


def _to_response(row: dict[str, Any]) -> AmplifyDraftResponse:
    platform = row.get("platform") or "reddit"
    thread = row.get("thread_json") or []
    return AmplifyDraftResponse(
        id=row["id"],
        project_id=row["project_id"],
        platform=platform,
        thread_json=[str(t) for t in thread],
        content=row.get("body") if platform == "linkedin" else None,
        status=row.get("status") or "draft",
        source_reply_draft_id=row.get("source_reply_draft_id"),
        source_opportunity_id=row.get("source_opportunity_id"),
        created_at=row["created_at"],
    )


def _validate_tweets(tweets: list[str]) -> None:
    for index, tweet in enumerate(tweets):
        if len(tweet) > TWEET_MAX_CHARS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Tweet {index + 1} is {len(tweet)} characters; "
                    f"the limit is {TWEET_MAX_CHARS}."
                ),
            )


@router.post("/amplify", response_model=AmplifyDraftResponse, status_code=status.HTTP_201_CREATED)
def create_amplified_draft(
    payload: AmplifyRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> AmplifyDraftResponse:
    """Generate an X thread or LinkedIn post from a reply draft / opportunity."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    source, project, source_reply_draft_id, source_opportunity_id = _load_source(
        supabase, workspace["id"], payload
    )
    voice_profile = _load_voice_profile(supabase, project["id"], payload.voice_profile_id)
    # NOTE: project.get("brand_profile") was a bug — projects rows never had
    # that key, so amplified X/LinkedIn posts were generated with zero brand
    # context (no name, tone, or audience) every single time.
    from app.db.tables.projects import resolve_brand_context
    brand = resolve_brand_context(supabase, project["workspace_id"], project["id"])

    if payload.target == "x":
        tweets = amplify_to_x_thread(source, brand, voice_profile=voice_profile)
        thread_json = tweets
        body = "\n\n".join(tweets)
    else:
        content = amplify_to_linkedin(source, brand, voice_profile=voice_profile)
        thread_json = []
        body = content

    existing = list_post_drafts_for_project(supabase, project["id"])
    version = (max((d.get("version") or 0 for d in existing), default=0)) + 1

    title = (source.get("title") or "Amplified post")[:255]
    row = create_post_draft(
        supabase,
        {
            "project_id": project["id"],
            "title": title,
            "body": body,
            "rationale": f"Amplified from Reddit content for {payload.target}.",
            "source_prompt": None,
            "version": version,
            "platform": payload.target,
            "thread_json": thread_json,
            "status": "draft",
            "source_reply_draft_id": source_reply_draft_id,
            "source_opportunity_id": source_opportunity_id,
        },
    )
    return _to_response(row)


@router.put("/amplify/{post_draft_id}", response_model=AmplifyDraftResponse)
def update_amplified_draft(
    post_draft_id: int,
    payload: AmplifyUpdateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> AmplifyDraftResponse:
    """Update an amplified draft's thread tweets or LinkedIn content after edits."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    draft = get_post_draft_by_id(supabase, post_draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    get_project(supabase, workspace["id"], draft["project_id"])

    update_data: dict[str, Any] = {}
    if payload.thread_json is not None:
        _validate_tweets(payload.thread_json)
        update_data["thread_json"] = payload.thread_json
        update_data["body"] = "\n\n".join(payload.thread_json)
    if payload.content is not None:
        update_data["body"] = payload.content

    updated = update_post_draft(supabase, post_draft_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    return _to_response(updated)


@router.post("/amplify/{post_draft_id}/publish", response_model=PublishResponse)
def publish_amplified_draft(
    post_draft_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PublishResponse:
    """Publish an X thread draft to X. LinkedIn drafts must be posted manually."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    draft = get_post_draft_by_id(supabase, post_draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    project = get_project(supabase, workspace["id"], draft["project_id"])

    platform = draft.get("platform") or "reddit"
    if platform == "linkedin":
        raise HTTPException(status_code=400, detail="LinkedIn publishing is manual — use copy.")
    if platform != "x":
        raise HTTPException(status_code=400, detail="Only X thread drafts can be published here.")

    tweets = [str(t) for t in (draft.get("thread_json") or []) if str(t).strip()]
    if not tweets:
        raise HTTPException(status_code=400, detail="Draft has no tweets to publish.")
    _validate_tweets(tweets)

    token = get_x_token(supabase, workspace["id"])
    if not token:
        raise HTTPException(
            status_code=400,
            detail=(
                "No X credentials configured for this workspace. Add an X access "
                "token under integration settings (provider 'x')."
            ),
        )

    results = XPublisher(token).publish_thread(tweets)

    posted_at = datetime.now(UTC).isoformat()
    published_tweets: list[PublishedTweet] = []
    for item in results:
        url = f"https://x.com/i/web/status/{item['id']}"
        published_tweets.append(PublishedTweet(id=item["id"], text=item["text"], url=url))
        create_published_post(
            supabase,
            {
                "project_id": project["id"],
                "platform": "x",
                "type": "tweet",
                "external_id": item["id"],
                "title": draft.get("title"),
                "content": item["text"],
                "permalink": url,
                "status": "published",
                "posted_at": posted_at,
            },
        )

    update_post_draft(supabase, post_draft_id, {"status": "posted"})

    return PublishResponse(
        post_draft_id=post_draft_id,
        platform="x",
        tweet_ids=[t.id for t in published_tweets],
        tweets=published_tweets,
    )
