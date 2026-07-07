"""Streaming analysis endpoint — zero-input URL enrichment via SSE.

POST /v1/analyze/stream?url=https://example.com

Streams JSON events back to the client as each enrichment step completes:
  {"type": "log",      "msg": "...", "level": "info|success|warn"}
  {"type": "data",     "key": "company_name", "value": "..."}
  {"type": "section",  "label": "Brand Intelligence"}
  {"type": "complete", "company": {...}, "keywords": [...], "competitors": [...]}
  {"type": "error",    "msg": "..."}

The client renders these as a terminal stream, then hydrates the workflow
steps automatically when "complete" arrives.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from supabase import Client

from app.api.v1.deps import get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/analyze", tags=["analyze"])


# _analysis_generator was moved to master_pipeline.py as run_full_pipeline_stream


@router.get("/stream")
async def analyze_stream(
    url: str = Query(..., description="Company website URL to analyze"),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> StreamingResponse:
    """Stream brand enrichment events as SSE while analyzing a URL.

    The client should consume this as an EventSource (or via fetch with
    ReadableStream) and render each event in the terminal UI.
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="url is required")

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    from app.services.product.master_pipeline import run_full_pipeline_stream

    async def safe_stream():
        try:
            async for chunk in run_full_pipeline_stream(url, workspace, supabase):
                yield chunk
        except Exception as exc:
            logger.exception("Analysis stream failed for %s", url)
            yield f"data: {json.dumps({'type': 'error', 'msg': f'Analysis failed on the server: {exc}'})}\n\n"

    return StreamingResponse(
        safe_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
