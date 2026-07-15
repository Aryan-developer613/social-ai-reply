import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.custom_scrapers import (
    delete_custom_scraper,
    list_custom_scrapers_for_workspace,
    upsert_custom_scraper,
)
from app.schemas.v1.scrapers import (
    CustomScraperCreateRequest,
    CustomScraperResponse,
    ScraperTestRequest,
    ScraperTestResponse,
)
from app.services.infrastructure.llm.service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/scrapers", tags=["scrapers"])

class ChatMessagePayload(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessagePayload]

class ChatResponse(BaseModel):
    reply: str


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
    """Delete a custom scraper configuration belonging to the current workspace."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if not delete_custom_scraper(supabase, scraper_id, workspace["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraper not found.")


# ── Test Connection ──────────────────────────────────────────────────


def _find_largest_array(data: dict | list, prefix: str = "") -> tuple[str, int]:
    """Walk a JSON structure and find the path to the largest array.

    Returns (dot_path, array_length).  Used for auto-detecting items_json_path.
    """
    best_path = ""
    best_len = 0

    if isinstance(data, list):
        if len(data) > best_len:
            best_path = prefix or "."
            best_len = len(data)
        # Also check items inside the list for nested arrays
        if data and isinstance(data[0], dict):
            for key, val in data[0].items():
                if isinstance(val, list) and len(val) > best_len:
                    best_path = f"{prefix}.0.{key}" if prefix else f"0.{key}"
                    best_len = len(val)
        return best_path, best_len

    if isinstance(data, dict):
        for key, val in data.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(val, list):
                if len(val) > best_len:
                    best_path = child_prefix
                    best_len = len(val)
            elif isinstance(val, dict):
                nested_path, nested_len = _find_largest_array(val, child_prefix)
                if nested_len > best_len:
                    best_path = nested_path
                    best_len = nested_len

    return best_path, best_len


@router.post("/test", response_model=ScraperTestResponse)
async def test_scraper_endpoint(
    payload: ScraperTestRequest,
    current_user: dict = Depends(get_current_user),
) -> ScraperTestResponse:
    """Test a scraper configuration by making a real API call.

    Returns status, auto-detected JSON path, and warnings about common mistakes.
    """
    from app.core.config import get_settings
    settings = get_settings()

    warnings: list[str] = []

    # Validate inputs
    if not payload.search_endpoint.startswith("/"):
        warnings.append(f"Search endpoint should start with '/'. Did you mean '/{payload.search_endpoint}'?")

    if payload.items_json_path.startswith("$."):
        warnings.append("Items JSON Path should NOT start with '$.' — just use the path directly (e.g., 'body' not '$.body').")

    api_key = payload.api_key or (settings.rapidapi_key.get_secret_value() if settings.rapidapi_key else None)
    if not api_key:
        return ScraperTestResponse(
            success=False,
            error="No API key provided and no default RAPIDAPI_KEY configured.",
            warnings=warnings,
        )

    # Make the test API call
    url = f"https://{payload.api_host}{payload.search_endpoint}"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": payload.api_host,
    }
    params = {payload.search_param_name: payload.test_query}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            error_msg = response.text[:300]
            if response.status_code == 404:
                warnings.append(
                    f"Endpoint '{payload.search_endpoint}' does not exist on this API host. "
                    "Double-check the exact path from the RapidAPI playground."
                )
            elif response.status_code == 429:
                warnings.append("API rate limit reached. You may have exceeded your monthly quota.")
            elif response.status_code == 403:
                warnings.append("API key is invalid or you haven't subscribed to this API on RapidAPI.")

            return ScraperTestResponse(
                success=False,
                status_code=response.status_code,
                error=error_msg,
                warnings=warnings,
            )

        # Parse response
        data = response.json()
        sample_keys: list[str] = []
        if isinstance(data, dict):
            sample_keys = list(data.keys())[:10]
        elif isinstance(data, list):
            sample_keys = ["(root is array)"]

        # Auto-detect JSON path
        suggested_path, items_found = _find_largest_array(data)

        # Check if user's configured path actually works
        if payload.items_json_path:
            user_path = payload.items_json_path
            if user_path.startswith("$."):
                user_path = user_path[2:]

            from app.services.infrastructure.platforms.dynamic_adapter import extract_json_path
            user_items = extract_json_path(data, user_path)
            if not isinstance(user_items, list):
                warnings.append(
                    f"Your configured path '{payload.items_json_path}' did not resolve to an array in the API response. "
                    f"Suggested path: '{suggested_path}' ({items_found} items found)."
                )
            elif len(user_items) == 0:
                warnings.append(
                    f"Your configured path '{payload.items_json_path}' resolved to an empty array. "
                    f"Try the suggested path: '{suggested_path}' ({items_found} items found)."
                )

        return ScraperTestResponse(
            success=True,
            status_code=200,
            sample_keys=sample_keys,
            suggested_json_path=suggested_path if suggested_path else None,
            items_found=items_found,
            warnings=warnings,
        )

    except httpx.TimeoutException:
        return ScraperTestResponse(
            success=False,
            error="Request timed out after 15 seconds.",
            warnings=warnings,
        )
    except Exception as e:
        return ScraperTestResponse(
            success=False,
            error=str(e)[:300],
            warnings=warnings,
        )


# ── AI Setup Chat ────────────────────────────────────────────────────

_CHAT_SYSTEM_PROMPT = """\
You are a friendly API integration assistant helping users configure custom scrapers on RedditFlow.
The user needs to fill in a form with these fields:
1. **API Host** — the RapidAPI host (e.g., `reddit3.p.rapidapi.com`)
2. **Search Endpoint** — the API path (e.g., `/v1/reddit/search`). MUST start with `/`.
3. **Search Param Name** — the query parameter name (e.g., `search`, `query`, `q`)
4. **Items JSON Path** — dot-notation path to the items array (e.g., `body`, `data.items`). Do NOT use `$.` prefix.

KNOWN WORKING CONFIGURATIONS (suggest these when relevant):

**Reddit (reddit3.p.rapidapi.com):**
- Search Endpoint: `/v1/reddit/search`
- Search Param Name: `search`
- Items JSON Path: `body`
- Note: Our system automatically discovers subreddits from search results and fetches comments on top posts!

**Instagram (instagram-looter2.p.rapidapi.com):**
- Search Endpoint: `/search`
- Search Param Name: `query`
- Items JSON Path: (leave empty or `.` — root response has `users` and `hashtags`)
- Note: Our system prioritizes user profiles over hashtags automatically!

COMMON MISTAKES TO WARN ABOUT:
- ❌ `$.body` → ✅ `body` (no dollar-dot prefix)
- ❌ `/v1/search` vs `/v1/reddit/search` — check the EXACT path in RapidAPI playground
- ❌ Forgetting the leading `/` in endpoints
- ❌ Using the wrong param name (e.g., `q` vs `query` vs `search`)

IMPORTANT TIPS:
- Tell users to click "Test Connection" after filling in the form — it will validate everything
- If they paste a cURL command, extract the host, endpoint, and param name from it
- If they paste a JSON response, help them identify the items array path
- Do NOT give individual field mappings (external_id, title, etc.) — our app parses those automatically with AI

Be concise, friendly, and assume zero technical knowledge.\
"""


@router.post("/chat", response_model=ChatResponse)
def scrapers_chat_endpoint(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Setup Assistant chat endpoint to help map API responses to JSON paths."""
    # Format messages into a single prompt string since LLMService.call_text expects a string
    prompt_lines = []
    for msg in payload.history:
        role_label = "Assistant" if msg.role == "assistant" else "User"
        prompt_lines.append(f"{role_label}: {msg.content}")

    prompt_lines.append(f"User: {payload.message}")
    prompt_lines.append("Assistant:")

    final_prompt = "\n\n".join(prompt_lines)

    llm = LLMService()
    reply = llm.call_text(
        prompt=final_prompt,
        system_message=_CHAT_SYSTEM_PROMPT,
        temperature=0.3
    )
    if not reply:
        reply = "Sorry, I couldn't process that right now."

    return ChatResponse(reply=reply)


# ── Presets ───────────────────────────────────────────────────────────

PLATFORM_PRESETS = {
    "reddit": [
        {
            "name": "Reddit3 API (Recommended)",
            "api_host": "reddit3.p.rapidapi.com",
            "search_endpoint": "/v1/reddit/search",
            "search_param_name": "search",
            "items_json_path": "body",
            "comments_endpoint": "/v1/reddit/post-details",
            "comments_param_name": "post_id",
        },
    ],
    "instagram": [
        {
            "name": "Instagram Looter 2 (Recommended)",
            "api_host": "instagram-looter2.p.rapidapi.com",
            "search_endpoint": "/search",
            "search_param_name": "query",
            "items_json_path": "",
        },
    ],
    "twitter": [
        {
            "name": "Twitter154 (The Old Bird API)",
            "api_host": "twitter154.p.rapidapi.com",
            "search_endpoint": "/search/search",
            "search_param_name": "query",
            "items_json_path": "results",
        },
    ],
    "linkedin": [
        {
            "name": "Fresh LinkedIn Scraper",
            "api_host": "fresh-linkedin-scraper-api.p.rapidapi.com",
            "search_endpoint": "/jobs/search",
            "search_param_name": "keywords",
            "items_json_path": "jobs",
        },
    ],
}


@router.get("/presets")
def get_presets_endpoint(
    current_user: dict = Depends(get_current_user),
) -> dict[str, list[dict]]:
    """Return known working API presets for each platform."""
    return PLATFORM_PRESETS

