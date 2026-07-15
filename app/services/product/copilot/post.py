"""Post draft generation from brand context."""

from __future__ import annotations

import json
import logging

from app.services.product.copilot.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ── Unified prompt assembly + parsing ────────────────────────────────────
# Single source of truth for the sync and async fallback paths — see the
# equivalent split in reply.py's _build_prompts/_parse_llm_payload, which
# this mirrors to avoid the two paths silently diverging on a future fix.


def _build_post_prompt(brand: dict | None, prompt_context: str) -> tuple[str, str]:
    """Build (system_prompt, user_content) for a Reddit post draft."""
    system_prompt = "Return JSON with title, body, and rationale for a non-promotional Reddit post."
    user_content = json.dumps({
        "brand_name": brand.get("brand_name") if brand else "",
        "summary": brand.get("summary") if brand else "",
        "voice_notes": brand.get("voice_notes") if brand else "",
        "prompt_context": prompt_context,
    })
    return system_prompt, user_content


def _parse_post_payload(payload: dict | list | None) -> tuple[str, str, str] | None:
    """Extract (title, body, rationale) from the LLM response payload."""
    if not payload:
        return None
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        return None
    title = (payload.get("title") or "").strip()
    body = (payload.get("body") or "").strip()
    if not title or not body:
        return None
    return title, body, payload.get("rationale") or "AI generated post draft."


def _prompt_context_from(prompts: list[dict]) -> str:
    return "\n".join(
        f"{prompt.get('name', '')}: {prompt.get('instructions', '')}"
        for prompt in prompts
        if prompt.get('prompt_type') == "post"
    )


def generate_post(
    brand: dict | None,
    prompts: list[dict],
) -> tuple[str, str, str]:
    """
    Generate a Reddit post draft from brand context.

    Returns:
        Tuple of (title, body, rationale).

    Raises:
        RuntimeError: If the LLM call fails or returns no usable content.
    """
    llm = LLMClient()
    prompt_context = _prompt_context_from(prompts)

    ai_post = _ai_post(llm, brand, prompt_context)
    if ai_post:
        return ai_post

    raise RuntimeError(
        "Failed to generate post draft — the LLM returned no usable response. "
        "Check that your LLM provider API key is configured and try again."
    )


def _ai_post(llm: LLMClient, brand: dict | None, prompt_context: str) -> tuple[str, str, str] | None:
    """Generate post using LLM."""
    try:
        system_prompt, user_content = _build_post_prompt(brand, prompt_context)
        payload = llm.call(system_prompt, user_content, temperature=0.5)
        return _parse_post_payload(payload)
    except Exception:
        logger.exception("Post generation failed")
        return None


async def generate_post_async(
    brand: dict | None,
    prompts: list[dict],
) -> tuple[str, str, str]:
    """Async version of :func:`generate_post`.

    Use this from async contexts (e.g. ``async def`` FastAPI handlers) to avoid
    the deadlock risk of the sync version, which internally calls
    :func:`_run_async`.

    Returns:
        Tuple of (title, body, rationale).

    Raises:
        RuntimeError: If the LLM call fails or returns no usable content.
    """
    llm = LLMClient()
    prompt_context = _prompt_context_from(prompts)

    ai_post = await _ai_post_async(llm, brand, prompt_context)
    if ai_post:
        return ai_post

    raise RuntimeError(
        "Failed to generate post draft — the LLM returned no usable response. "
        "Check that your LLM provider API key is configured and try again."
    )


async def _ai_post_async(llm: LLMClient, brand: dict | None, prompt_context: str) -> tuple[str, str, str] | None:
    """Async version of :func:`_ai_post`.

    Uses the Pydantic AI agent's async path directly, avoiding the
    :func:`_run_async` deadlock risk when called from an async context.
    """
    try:
        from app.services.infrastructure.llm.service import generate_post_async as llm_generate_post_async

        agent_prompts = [{"prompt_type": "post", "name": "Post", "instructions": prompt_context}]
        result = await llm_generate_post_async(brand, agent_prompts)
        if result is not None:
            return result
    except Exception as agent_error:
        logger.warning("Pydantic AI post agent failed, falling back to legacy: %s", agent_error)

    try:
        system_prompt, user_content = _build_post_prompt(brand, prompt_context)
        payload = llm.call(system_prompt, user_content, temperature=0.5)
        return _parse_post_payload(payload)
    except Exception:
        logger.exception("Post generation failed")
        return None
