"""Keyword generation from brand and persona context with LLM enhancement."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.product.copilot.llm_client import LLMClient
from app.services.product.relevance import (
    AMBIGUOUS_CONTEXTLESS_TERMS,
    ROLE_TERMS,
    build_domain_context,
    check_domain_vocabulary_match,
    extract_geo_terms,
    extract_structured_phrases,
    keyword_specificity,
    normalize_phrase,
    select_high_signal_keywords,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratedKeyword:
    """A generated keyword with metadata."""

    keyword: str
    rationale: str
    priority_score: int
    specificity: int = 0


def generate_keywords(
    brand: dict | None,
    personas: list[dict],
    count: int = 25,
) -> list[GeneratedKeyword]:
    """Generate keywords from brand and persona context.

    Uses LLM to generate domain-specific keywords first, then supplements
    with heuristic extraction from brand/persona data.

    Args:
        brand: Brand profile dict containing brand_name, summary, product_summary,
               target_audience, and business_domain.
        personas: List of persona dicts with name, role, summary, pain_points, etc.
        count: Maximum number of keywords to generate (default 25).

    Returns:
        List of GeneratedKeyword dataclasses, sorted by priority score.
    """
    if not brand:
        return []

    brand_name = brand.get("brand_name", "")
    domain = brand.get("business_domain", "")
    audience = brand.get("target_audience", "")
    summary = brand.get("summary", "")
    product_summary = brand.get("product_summary", "")

    # Try LLM-generated keywords first
    llm_keywords = _llm_keywords(brand_name, domain, audience, summary, product_summary, count)

    # Supplement with heuristic extraction
    heuristic_keywords = _heuristic_keywords(brand, personas, count)

    # Merge: LLM keywords first, then heuristic ones that aren't already covered
    seen = set(k.lower() for k in llm_keywords)
    merged = list(llm_keywords)
    for kw in heuristic_keywords:
        if kw.lower() not in seen:
            merged.append(kw)
            seen.add(kw.lower())

    generated: list[GeneratedKeyword] = []
    for idx, keyword in enumerate(merged):
        spec = keyword_specificity(keyword)
        score = max(min(95 - idx * 3, 100), 10)
        generated.append(
            GeneratedKeyword(
                keyword=keyword,
                rationale=f"Domain-specific keyword for {domain or brand_name}.",
                priority_score=score,
                specificity=spec,
            )
        )
        if len(generated) >= count:
            break

    return generated


def _llm_keywords(
    brand_name: str,
    domain: str,
    audience: str,
    summary: str,
    product_summary: str,
    count: int,
) -> list[str]:
    """Use LLM to generate domain-specific keywords."""
    if not domain and not audience and not summary:
        return []

    llm = LLMClient()
    system_prompt = (
        "You generate search keywords for discovering social media opportunities. "
        "Return a JSON array of keyword strings ONLY. "
        "Each keyword should be a term or phrase that someone might use when: "
        "1. Looking for a product/service like this\n"
        "2. Complaining about a problem this business solves\n"
        "3. Comparing alternatives/competitors\n"
        "4. Asking for recommendations in this space\n"
        "5. Mentioning specific pain points this business addresses\n\n"
        "Include both short keywords and longer phrase keywords. "
        "Include competitor names if relevant. "
        "Include location-related terms if the business is location-specific.\n\n"
        f"Generate {count} high-quality keywords. Make them specific and realistic."
    )

    context = (
        f"Brand: {brand_name}\n"
        f"Domain: {domain}\n"
        f"Target Audience: {audience}\n"
        f"Summary: {summary}\n"
        f"Product: {product_summary}"
    )

    try:
        result = llm.call(system_prompt, context, temperature=0.7)
        if result and isinstance(result, list):
            keywords = []
            seen: set[str] = set()
            for item in result:
                kw = str(item).strip().strip('"').strip("'") if not isinstance(item, str) else item.strip()
                if not kw or len(kw) < 2:
                    continue
                if kw.lower() in seen:
                    continue
                seen.add(kw.lower())
                keywords.append(kw)
            return keywords
    except Exception:
        logger.exception("LLM keyword generation failed")
    return []


def _heuristic_keywords(brand: dict | None, personas: list[dict], count: int) -> list[str]:
    """Fallback heuristic keyword extraction."""
    if not brand:
        return []

    phrase_map: dict[str, tuple[str, int]] = {}

    def add_candidate(keyword: str, rationale: str, base_score: int) -> None:
        normalized = normalize_phrase(keyword)
        if not normalized:
            return
        specificity = keyword_specificity(normalized)
        # Relaxed filter — only drop very generic single words
        if normalize_phrase(brand.get("brand_name") or "") and specificity < 20:
            return
        score = max(min(base_score + specificity // 5, 100), 1)
        previous = phrase_map.get(normalized)
        if previous and previous[1] >= score:
            return
        phrase_map[normalized] = (rationale, score)

    if brand.get("brand_name"):
        add_candidate(brand.get("brand_name", ""), "Track direct brand mentions and exact product references.", 95)

    biz_domain = brand.get("business_domain", "") or ""
    summary_sources = [brand.get("product_summary") or "", brand.get("summary") or ""]
    for source in summary_sources:
        for phrase in extract_structured_phrases(source, limit=15):
            add_candidate(phrase, f"Specific product or problem phrase from the website copy: {phrase}.", 74)

    for audience in split_csv_terms(brand.get("target_audience")):
        base = 70 if len(audience.split()) > 1 else 58
        if audience in ROLE_TERMS:
            base -= 2
        add_candidate(audience, f"Audience phrase derived from the target audience: {audience}.", base)

    persona_sources: list[str] = []
    for persona in personas[:5]:
        persona_sources.extend([persona.get("name", ""), persona.get("role") or ""])
        if persona.get("source") != "generated":
            persona_sources.extend([
                persona.get("summary", ""),
                " ".join(persona.get("pain_points") or []),
                " ".join(persona.get("goals") or []),
                " ".join(persona.get("triggers") or []),
            ])
    for source in persona_sources:
        for phrase in extract_structured_phrases(source, limit=6):
            add_candidate(phrase, f"Persona-driven phrase linked to a likely pain point or goal: {phrase}.", 68)

    domain_context = build_domain_context(
        brand_name=brand.get("brand_name"),
        summary=brand.get("summary"),
        product_summary=brand.get("product_summary"),
        target_audience=brand.get("target_audience"),
        keywords=list(phrase_map),
        extra_texts=[persona.get("name", "") for persona in personas[:5]],
        business_domain=biz_domain,
    )

    geo_source = " ".join(
        part for part in [
            brand.get("website_url") or "",
            brand.get("summary") or "",
            brand.get("product_summary") or "",
            brand.get("target_audience") or "",
        ] if part
    )
    for geo in extract_geo_terms(geo_source):
        add_candidate(geo, f"Geographic qualifier from the website context: {geo}.", 55)
    for phrase in domain_context.core_phrases[:12]:
        add_candidate(phrase, f"Canonical business-domain phrase distilled from the website context: {phrase}.", 76)
    for anchor in domain_context.anchor_terms[:10]:
        add_candidate(anchor, f"High-signal domain term repeated across the website context: {anchor}.", 58)

    ranked_keywords = select_high_signal_keywords(
        list(phrase_map),
        brand_name=brand.get("brand_name"),
        limit=count * 3,
        domain_context=domain_context,
    )

    # Relaxed domain-vocabulary post-filter
    if biz_domain:
        filtered_keywords: list[str] = []
        brand_norm = normalize_phrase(brand.get("brand_name") or "")
        for kw in ranked_keywords:
            if kw == brand_norm:
                filtered_keywords.append(kw)
                continue
            tokens = kw.split()
            meaningful = [t for t in tokens if t not in AMBIGUOUS_CONTEXTLESS_TERMS]
            if not meaningful:
                continue
            kw_domain_ok, _, _ = check_domain_vocabulary_match(kw, biz_domain)
            kw_has_anchor = bool(set(meaningful) & set(domain_context.anchor_terms))
            # Only drop if it fails ALL checks AND has no meaningful content
            if not kw_domain_ok and not kw_has_anchor and all(
                t in AMBIGUOUS_CONTEXTLESS_TERMS for t in tokens
            ):
                continue
            filtered_keywords.append(kw)
        ranked_keywords = filtered_keywords

    return ranked_keywords


# Need to import this here to avoid circular dependency
from app.services.product.relevance import split_csv_terms  # noqa: E402
