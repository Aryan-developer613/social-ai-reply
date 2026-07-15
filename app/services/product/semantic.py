"""Semantic similarity layer for post discovery.

Provides embedding-based matching that augments the existing lexical
scoring pipeline.  This is an **opt-in feature**: set
``ENABLE_SEMANTIC_SCORING=true`` AND provide an OpenAI-compatible
embedding API key (via ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL``).

When disabled (the default), every function degrades gracefully —
returning zero bonuses and empty variant lists — so the lexical
pipeline continues to work unchanged.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIMENSIONS = 1536
_SIMILARITY_THRESHOLD = 0.35
_MAX_SEMANTIC_BONUS = 15
_MAX_VARIANTS_PER_KEYWORD = 5

_embedding_client: httpx.Client | None = None
_embedding_client_lock = threading.Lock()
_variant_client: httpx.Client | None = None
_variant_client_lock = threading.Lock()
_gemini_client: httpx.Client | None = None
_gemini_client_lock = threading.Lock()
_anthropic_client: httpx.Client | None = None
_anthropic_client_lock = threading.Lock()


def _is_enabled() -> bool:
    settings = get_settings()
    return bool(settings.enable_semantic_scoring and settings.openai_api_key)


def _get_embedding_client() -> httpx.Client | None:
    global _embedding_client
    if not _is_enabled():
        return None
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    with _embedding_client_lock:
        if _embedding_client is not None:
            return _embedding_client
        base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        _embedding_client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return _embedding_client


def embed_texts(texts: list[str], *, model: str | None = None) -> list[list[float]] | None:
    """Embed a batch of texts via the OpenAI-compatible embeddings API.

    Returns a list of float vectors (one per input text), or ``None``
    if semantic scoring is disabled or the API call fails.
    """
    if not texts:
        return []
    if not _is_enabled():
        return None
    settings = get_settings()
    effective_model = model or settings.embedding_model or _DEFAULT_EMBEDDING_MODEL
    client = _get_embedding_client()
    if client is None:
        return None
    try:
        resp = client.post(
            "/embeddings",
            json={"input": texts, "model": effective_model, "dimensions": _EMBEDDING_DIMENSIONS},
        )
        resp.raise_for_status()
        data = resp.json()
        sorted_data = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        return [d["embedding"] for d in sorted_data]
    except Exception as exc:
        logger.warning("Embedding API call failed: %s", exc)
        return None


# ── Vector math ─────────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Semantic keyword expansion ──────────────────────────────────────────

@dataclass
class SemanticKeyword:
    """A keyword enriched with its semantic variants and embedding."""
    original: str
    variants: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


def expand_keywords_semantically(
    keywords: list[str],
    *,
    brand_context: str = "",
) -> list[SemanticKeyword]:
    """Expand each keyword with semantically similar phrases using LLM.

    Returns the originals without variants when semantic scoring is
    disabled or the LLM API is unavailable.
    """
    if not keywords:
        return []

    # If the feature is disabled, return originals without variants/embeddings
    if not _is_enabled():
        return [SemanticKeyword(original=kw) for kw in keywords]

    results: list[SemanticKeyword] = []

    # Try LLM-based variant generation
    variant_map = _generate_variants_batch(keywords, brand_context=brand_context)

    # Embed all texts (originals + variants) in a single batch
    all_texts: list[str] = []
    text_indices: list[tuple[int, int | None]] = []  # (keyword_index, variant_index or None)
    for i, kw in enumerate(keywords):
        all_texts.append(kw)
        text_indices.append((i, None))
        for j, variant in enumerate(variant_map.get(kw, [])):
            all_texts.append(variant)
            text_indices.append((i, j))

    embeddings = embed_texts(all_texts) if all_texts else None

    for i, kw in enumerate(keywords):
        kw_embedding = None
        if embeddings:
            # Find the embedding for the original keyword
            for idx, (ki, vi) in enumerate(text_indices):
                if ki == i and vi is None and idx < len(embeddings):
                    kw_embedding = embeddings[idx]
                    break

        results.append(SemanticKeyword(
            original=kw,
            variants=variant_map.get(kw, []),
            embedding=kw_embedding,
        ))

    return results


def _get_variant_client() -> httpx.Client | None:
    global _variant_client
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    with _variant_client_lock:
        if _variant_client is not None:
            return _variant_client
        base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        _variant_client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return _variant_client


def _get_gemini_client() -> httpx.Client | None:
    global _gemini_client
    with _gemini_client_lock:
        if _gemini_client is not None:
            return _gemini_client
        _gemini_client = httpx.Client(timeout=30.0)
        return _gemini_client


def _get_anthropic_client() -> httpx.Client | None:
    global _anthropic_client
    with _anthropic_client_lock:
        if _anthropic_client is not None:
            return _anthropic_client
        _anthropic_client = httpx.Client(timeout=30.0)
        return _anthropic_client


def _generate_variants_batch(
    keywords: list[str],
    *,
    brand_context: str = "",
) -> dict[str, list[str]]:
    """Generate semantic variants for a batch of keywords via the
    project's configured LLM provider."""
    if not _is_enabled():
        return {}

    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        return {}

    # Use the project's configured LLM provider for variant generation
    # rather than hardcoding a specific model.  When the provider is
    # OpenAI (or a compatible endpoint), call the chat/completions
    # endpoint directly.  For Gemini/Anthropic, use their respective
    # APIs.  Fall back to OpenAI-compatible endpoint if unsure.
    model = settings.openai_model

    # For Gemini, use the Gemini API directly via the agents module
    # to respect the project's configured provider.
    if settings.llm_provider.lower() == "gemini" and settings.gemini_api_key:
        return _generate_variants_via_gemini(keywords, brand_context=brand_context)

    # For Anthropic, use the agents module
    if settings.llm_provider.lower() in ("anthropic", "claude") and settings.anthropic_api_key:
        return _generate_variants_via_anthropic(keywords, brand_context=brand_context)

    # Default: OpenAI-compatible endpoint
    client = _get_variant_client()
    if client is None:
        return {}

    system_prompt = (
        "You generate alternative search phrases that are semantically equivalent "
        "to the given keywords. Each variant must be a different way to say the "
        "same thing — using synonyms, related jargon, or colloquial alternatives. "
        "Return a JSON object where each key is the original keyword and the value "
        "is an array of 3-5 variant strings. Do NOT include the original keyword "
        "in its variant list. Keep variants concise (1-4 words)."
    )
    if brand_context:
        system_prompt += f"\n\nBusiness context: {brand_context[:500]}"

    user_content = json.dumps(keywords)

    try:
        resp = client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return {}
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {}
        # Validate and limit
        result: dict[str, list[str]] = {}
        for kw, variants in parsed.items():
            if not isinstance(variants, list):
                continue
            result[kw] = [str(v).strip() for v in variants if str(v).strip()][:_MAX_VARIANTS_PER_KEYWORD]
        return result
    except Exception as exc:
        logger.warning("Semantic variant generation failed: %s", exc)
        return {}


def _generate_variants_via_gemini(
    keywords: list[str],
    *,
    brand_context: str = "",
) -> dict[str, list[str]]:
    """Generate variants using Gemini API directly."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return {}
    api_key = settings.gemini_api_key.get_secret_value()

    system_prompt = (
        "You generate alternative search phrases that are semantically equivalent "
        "to the given keywords. Each variant must be a different way to say the "
        "same thing — using synonyms, related jargon, or colloquial alternatives. "
        "Return a JSON object where each key is the original keyword and the value "
        "is an array of 3-5 variant strings. Do NOT include the original keyword "
        "in its variant list. Keep variants concise (1-4 words)."
    )
    if brand_context:
        system_prompt += f"\n\nBusiness context: {brand_context[:500]}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={api_key}"

    try:
        client = _get_gemini_client()
        if client is None:
            return {}
        resp = client.post(
            url,
            json={
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nKeywords: {json.dumps(keywords)}"}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = ""
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                content += part.get("text", "")
        if not content:
            return {}
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, list[str]] = {}
        for kw, variants in parsed.items():
            if not isinstance(variants, list):
                continue
            result[kw] = [str(v).strip() for v in variants if str(v).strip()][:_MAX_VARIANTS_PER_KEYWORD]
        return result
    except Exception as exc:
        logger.warning("Gemini variant generation failed: %s", exc)
        return {}


def _generate_variants_via_anthropic(
    keywords: list[str],
    *,
    brand_context: str = "",
) -> dict[str, list[str]]:
    """Generate variants using Anthropic API directly."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return {}
    api_key = settings.anthropic_api_key.get_secret_value()

    system_prompt = (
        "You generate alternative search phrases that are semantically equivalent "
        "to the given keywords. Each variant must be a different way to say the "
        "same thing — using synonyms, related jargon, or colloquial alternatives. "
        "Return a JSON object where each key is the original keyword and the value "
        "is an array of 3-5 variant strings. Do NOT include the original keyword "
        "in its variant list. Keep variants concise (1-4 words)."
    )
    if brand_context:
        system_prompt += f"\n\nBusiness context: {brand_context[:500]}"

    try:
        client = _get_anthropic_client()
        if client is None:
            return {}
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": json.dumps(keywords)}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        if not content:
            return {}
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, list[str]] = {}
        for kw, variants in parsed.items():
            if not isinstance(variants, list):
                continue
            result[kw] = [str(v).strip() for v in variants if str(v).strip()][:_MAX_VARIANTS_PER_KEYWORD]
        return result
    except Exception as exc:
        logger.warning("Anthropic variant generation failed: %s", exc)
        return {}


# ── Semantic scoring ─────────────────────────────────────────────────────

def semantic_similarity_score(
    post_text: str,
    semantic_keywords: list[SemanticKeyword],
    *,
    post_embedding: list[float] | None = None,
) -> tuple[int, list[str]]:
    """Compute a semantic similarity bonus score for a post.

    Compares the post's embedding against each keyword embedding cluster.
    Returns ``(bonus_score, matched_variants)`` where *bonus_score* is
    0–_MAX_SEMANTIC_BONUS and *matched_variants* lists the variant phrases
    that exceeded the similarity threshold.

    When no embeddings are available, returns ``(0, [])`` — the lexical
    pipeline still works.
    """
    # Skip if no keyword embeddings exist
    keywords_with_embeddings = [kw for kw in semantic_keywords if kw.embedding is not None]
    if not keywords_with_embeddings:
        return 0, []

    # Embed the post if not provided
    if post_embedding is None:
        post_embeddings = embed_texts([post_text])
        if not post_embeddings:
            return 0, []
        post_embedding = post_embeddings[0]

    total_score = 0
    matched_variants: list[str] = []

    for kw in keywords_with_embeddings:
        if kw.embedding is None:
            continue
        sim = _cosine_similarity(post_embedding, kw.embedding)
        if sim >= _SIMILARITY_THRESHOLD:
            # Scale: 0.35 → 3pts, 0.5 → 5pts, 0.7 → 8pts, 1.0 → 15pts
            scaled = int(min(sim / 1.0 * _MAX_SEMANTIC_BONUS, _MAX_SEMANTIC_BONUS))
            total_score += scaled
            if sim >= 0.45:
                matched_variants.append(kw.original)

        # Also check variant embeddings (lighter weight — use text match as proxy)
        for variant in kw.variants:
            if variant.lower() in post_text.lower():
                total_score += 2
                matched_variants.append(variant)

    bonus = min(total_score, _MAX_SEMANTIC_BONUS)
    return bonus, matched_variants[:5]


# ── Batch post scoring ───────────────────────────────────────────────────

def embed_posts_batch(
    posts: list[dict[str, Any]],
) -> list[list[float] | None]:
    """Embed a batch of posts (title + body) for later scoring.

    Returns a list the same length as *posts*, where each element is
    either the embedding vector or ``None`` if embedding failed.
    """
    texts = [f"{p.get('title', '')} {p.get('body', '')}" for p in posts]
    if not texts:
        return []
    embeddings = embed_texts(texts)
    if embeddings is None:
        return [None] * len(posts)
    return embeddings
