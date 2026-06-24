from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.services.product.relevance import (
    DomainContext,
    assess_domain_match,
    build_domain_context,
    check_domain_vocabulary_match,
    find_intent_hits,
    find_offtopic_signals,
    find_self_promo_signals,
    has_meaningful_phrase_overlap,
    intent_quality_score,
    keyword_specificity,
    normalize_phrase,
    score_title_keyword_match,
    select_high_signal_keywords,
    split_csv_terms,
    tokenize,
)

if TYPE_CHECKING:
    from app.models.project import BrandProfile
    from app.services.product.reddit import RedditPost


# Tuned down 2026-04-19 after users reported scans returning only a single
# opportunity. Prior floor (35) combined with the multi-AND eligibility gate
# below (keyword + domain_match + domain_vocab) still rejected the majority
# of posts Reddit returned. 25 keeps obvious noise out while giving the
# human reviewer enough candidates to judge. The eligibility gates below
# were also relaxed — see the "hard gates" block in `score_post`.
MIN_RELEVANT_OPPORTUNITY_SCORE = 25
# Subreddits below this fit score are scored with a penalty rather than
# skipped entirely. A lower floor keeps mid-fit subreddits in the running.
MIN_SUBREDDIT_FIT_FOR_AUTOMATION = 25


@dataclass
class OpportunityScore:
    total: int
    keyword_hits: list[str]
    reasons: list[str]
    rule_risk: list[str]
    eligible: bool
    eligibility_reasons: list[str] = field(default_factory=list)


def score_post(
    post: RedditPost,
    brand_profile: dict[str, Any] | None,
    subreddit: dict[str, Any] | None,
    keywords: list[str],
    subreddit_rules: list[str],
    *,
    feedback_records: list[dict[str, Any]] | None = None,
) -> OpportunityScore:
    """Score a Reddit post for engagement opportunity.

    Evaluates a post based on keyword matching, domain alignment, intent signals,
    audience overlap, thread freshness, competition level, and subreddit rules.

    Args:
        post: RedditPost object with title, body, author, score, num_comments, etc.
        brand_profile: Brand profile dict with brand_name, summary, product_summary,
                       target_audience, and business_domain.
        subreddit: Monitored subreddit dict with name, fit_score, rules_summary.
        keywords: List of discovery keywords to match against.
        subreddit_rules: List of subreddit rule strings.
        feedback_records: Optional list of score_feedback dicts with ``action``
            and ``original_score`` keys. When provided, ``calibration_adjustment``
            is applied to the final score.

    Returns:
        OpportunityScore dataclass with total score, keyword hits, reasons,
        rule_risk indicators, and eligibility status.

    Scoring factors:
        - Keyword matches (exact and partial)
        - Domain vocabulary alignment
        - Intent signals (questions, recommendations, comparisons)
        - Audience overlap
        - Thread age (freshness bonus, staleness penalty)
        - Comment count (low competition bonus)
        - Upvote score (visibility indicator)
        - Self-promotion detection (penalty)
        - Off-topic detection (penalty)
    """
    text = normalize_phrase(f"{post.title} {post.body}")
    domain_context = build_domain_context(
        brand_name=brand_profile.get("brand_name") if brand_profile else None,
        summary=brand_profile.get("summary") if brand_profile else None,
        product_summary=brand_profile.get("product_summary") if brand_profile else None,
        target_audience=brand_profile.get("target_audience") if brand_profile else None,
        keywords=keywords,
        business_domain=brand_profile.get("business_domain", "") or "",
    )
    search_keywords = select_high_signal_keywords(
        keywords,
        brand_name=brand_profile.get("brand_name") if brand_profile else None,
        limit=12,
        domain_context=domain_context,
    )
    keyword_hits, topic_score, direct_brand_match = _score_topic_match(
        text, search_keywords, brand_profile, domain_context=domain_context,
    )
    domain_match = assess_domain_match(f"{post.title} {post.body}", domain_context)

    reasons: list[str] = []
    rule_risk: list[str] = []
    eligibility_reasons: list[str] = []

    intent_hits = find_intent_hits(f"{post.title} {post.body}")
    intent_score = min(len(intent_hits) * 9, 27)
    if "direct question" in intent_hits:
        intent_score = min(intent_score + 4, 30)
    # Intent quality bonus — recommendations/comparisons are higher value
    intent_score += intent_quality_score(intent_hits)

    if keyword_hits:
        reasons.append(f"Matched {len(keyword_hits)} high-signal keyword phrase(s).")
    if direct_brand_match:
        reasons.append("Direct brand mention detected in the thread.")
    elif domain_match.aligned:
        reasons.append("The thread matches the project's business domain, not just loose keywords.")
    if intent_hits:
        reasons.append("The post shows explicit help-seeking, recommendation, or comparison intent.")

    # ── Domain-vocabulary gate ──────────────────────────────────────────
    # When the business domain is known (e.g. "real estate"), verify
    # that the post actually discusses that domain.  A post about "VR
    # gaming" should not match a real-estate site just because the site
    # mentions VR tours.
    post_text_raw = f"{post.title} {post.body}"
    domain_vocab_ok, domain_vocab_count, _ = check_domain_vocabulary_match(
        post_text_raw, domain_context.business_domain,
    )

    # ── Topical / domain gates (hard, but OR'd) ────────────────────────
    # 2026-04-19: Relaxed from multi-AND to single-OR. Previously a post
    # had to satisfy keyword_hits AND domain_match AND domain_vocab AND
    # no-self-promo — in practice the intersection was nearly empty and
    # users saw only 1 opportunity per scan. Now a post is eligible if
    # ANY of the three topical signals is present: high-signal keyword
    # hits, curated domain-vocabulary terms, or a direct brand mention.
    # Domain-match and domain-vocab absence are still penalised later in
    # this function so weakly-aligned posts drop below the score floor.
    has_topical_signal = bool(
        keyword_hits
        or direct_brand_match
        or domain_match.aligned
        or (domain_context.business_domain and domain_vocab_ok)
    )
    if not has_topical_signal:
        eligibility_reasons.append(
            "Rejected: no high-signal topical overlap, no domain-specific overlap "
            "with the business context, and no brand mention."
        )

    # Soft-quality signals (missing intent / weak subreddit fit) are
    # tracked here but applied as score penalties *after* `score` is
    # initialized below. Thin-context already has a dedicated penalty
    # further down in this function.
    has_missing_intent = not intent_hits and not direct_brand_match
    has_weak_fit = bool(
        subreddit
        and subreddit.get("fit_score", 0) < MIN_SUBREDDIT_FIT_FOR_AUTOMATION
        and not direct_brand_match
    )

    # ── Self-promotion gate (still hard) ───────────────────────────────
    # Posts where the author is showcasing their own work are not
    # opportunities — the user is promoting, not seeking help. This
    # stays a hard rejection because a reply to a self-promo post is
    # never the right move.
    promo_signals = find_self_promo_signals(post_text_raw)
    if promo_signals and not direct_brand_match:
        eligibility_reasons.append(
            f"Rejected: post appears to be self-promotion ({promo_signals[0]!r}) — not a help-seeking opportunity."
        )

    score = topic_score

    # Apply the soft-quality penalties tracked above. These used to be
    # hard rejections — now they just push the score down so the post
    # can still surface if everything else about it is strong.
    if has_missing_intent:
        score -= 8
        reasons.append("No explicit help-seeking language — reply will need to offer value unprompted.")
    if has_weak_fit:
        score -= 10
        reasons.append("Subreddit fit is weak — proceed carefully.")

    # ── Title-weighted bonus ───────────────────────────────────────────
    # Keywords matched in the title are a stronger signal than body-only
    # matches because the title captures the core topic of the post.
    title_kw_hits, title_bonus = score_title_keyword_match(
        post.title, search_keywords,
    )
    score += title_bonus
    if title_kw_hits:
        reasons.append(f"Title directly matches {len(title_kw_hits)} keyword(s) — strong topical signal.")
    if domain_match.aligned and not direct_brand_match:
        score += min(domain_match.score, 22)
    if direct_brand_match and not intent_hits:
        score += 18

    score += intent_score

    audience_terms = split_csv_terms(brand_profile.get("target_audience") if brand_profile else None)
    matched_audience = [term for term in audience_terms if term in text]
    if matched_audience:
        score += min(len(matched_audience) * 4, 12)
        reasons.append("Audience overlap detected from the brand profile.")

    created_at = post.created_at if post.created_at.tzinfo else post.created_at.replace(tzinfo=UTC)
    age_hours = max((datetime.now(UTC) - created_at).total_seconds() / 3600, 0.0)
    if age_hours <= 6:
        score += 10
        reasons.append("Fresh thread with a strong chance of timely engagement.")
    elif age_hours <= 24:
        score += 7
        reasons.append("Recent thread that is still likely to be actionable.")
    elif age_hours <= 72:
        score += 4
    elif age_hours > 168:  # older than 7 days
        score -= 8
        reasons.append("Stale thread — engagement window has likely closed.")
    elif age_hours > 120:  # older than 5 days
        score -= 4
        reasons.append("Aging thread — diminishing engagement opportunity.")

    if post.num_comments <= 15:
        score += 8
        reasons.append("Low competition thread with room for a visible reply.")
    elif post.num_comments <= 40:
        score += 5
    elif post.num_comments >= 120:
        score -= 12
        reasons.append("Very crowded thread — reply will likely be buried.")
    elif post.num_comments >= 80:
        score -= 8
        reasons.append("Busy thread with heavy reply competition.")

    # ── Upvote / visibility signal ─────────────────────────────────────
    # High-upvote posts have more visibility = more value for engagement.
    upvotes = post.score
    if upvotes >= 100:
        score += 8
        reasons.append("High-visibility thread with strong community engagement.")
    elif upvotes >= 30:
        score += 5
    elif upvotes >= 10:
        score += 2
    elif upvotes <= 0:
        score -= 4
        reasons.append("Downvoted or zero-visibility thread.")

    if subreddit:
        score += min(subreddit.get("fit_score", 0) // 8, 12)
        if subreddit.get("rules_summary"):
            rule_risk.append("Review subreddit rules before posting.")

    rules_penalty = 0
    lowered_rules = " ".join(rule.lower() for rule in subreddit_rules)
    if any(term in lowered_rules for term in [
        "self-promo", "promotion", "no solicitation", "no advertising",
        "no commercial", "no business", "no marketing",
    ]):
        rule_risk.append("Subreddit appears sensitive to promotional replies.")
        rules_penalty += 8
    if any(term in lowered_rules for term in ["no external link", "no link", "no url"]):
        rule_risk.append("Subreddit rules restrict external links.")
        rules_penalty += 4
    elif "link" in lowered_rules:
        rule_risk.append("Subreddit rules mention external links.")
        rules_penalty += 3
    score -= rules_penalty

    offtopic_hits = find_offtopic_signals(post_text_raw)
    if offtopic_hits and not direct_brand_match:
        score -= min(len(offtopic_hits) * 6, 18)
        reasons.append(f"Off-topic chatter reduced confidence: {', '.join(offtopic_hits[:3])}.")

    # ── Self-promotion penalty ─────────────────────────────────────────
    if promo_signals and not direct_brand_match:
        score -= min(len(promo_signals) * 8, 20)
        reasons.append(f"Self-promotion detected ({promo_signals[0]!r}) — not a genuine opportunity.")

    # ── Domain vocabulary bonus / penalty ──────────────────────────────
    if domain_context.business_domain and not direct_brand_match:
        if domain_vocab_count >= 3:
            score += min(domain_vocab_count * 3, 14)
            reasons.append(f"Strong {domain_context.business_domain} domain vocabulary present.")
        elif domain_vocab_count == 1:
            pass  # Single domain term — neutral, neither bonus nor penalty
        elif domain_vocab_count == 0:
            score -= 14
            reasons.append(f"No {domain_context.business_domain} domain vocabulary detected — likely off-topic.")

    if _is_low_context(post):
        score -= 6
        reasons.append("Thin post context lowers reply confidence.")

    eligible = not eligibility_reasons
    final_score = max(min(score, 100), 0)
    if not eligible:
        final_score = min(final_score, MIN_RELEVANT_OPPORTUNITY_SCORE - 15)
        reasons = eligibility_reasons + reasons

    if feedback_records:
        delta = calibration_adjustment(final_score, feedback_records)
        if delta != 0:
            final_score = max(min(final_score + delta, 100), 0)
            if delta > 0:
                reasons.append(f"Score calibration: +{delta} (based on your past feedback).")
            else:
                reasons.append(f"Score calibration: {delta} (based on your past feedback).")

    return OpportunityScore(
        total=final_score,
        keyword_hits=keyword_hits,
        reasons=reasons,
        rule_risk=rule_risk,
        eligible=eligible,
        eligibility_reasons=eligibility_reasons,
    )


def _score_topic_match(
    text: str,
    keywords: list[str],
    brand_profile: BrandProfile | None,
    *,
    domain_context: DomainContext | None = None,
) -> tuple[list[str], int, bool]:
    token_set = set(tokenize(text))
    hits: list[str] = []
    score = 0

    for keyword in keywords:
        specificity = keyword_specificity(keyword)
        keyword_tokens = keyword.split()

        # ── Exact phrase match ──────────────────────────────────────
        if keyword in text:
            # For single-word or low-specificity keywords, verify the
            # match is contextually relevant — the post should also
            # contain at least one domain anchor term nearby.
            if len(keyword_tokens) == 1 and specificity < 50 and domain_context and not _keyword_has_domain_context(keyword, token_set, domain_context):
                continue
            hits.append(keyword)
            score += max(12, specificity // 3)
            continue

        # ── Partial overlap match (multi-word keywords) ─────────────
        if len(keyword_tokens) > 1 and has_meaningful_phrase_overlap(keyword, token_set):
            # For partial matches, require stricter overlap: ALL
            # non-generic tokens must be present.
            non_generic = [t for t in keyword_tokens if t not in _WEAK_MATCH_TOKENS]
            if non_generic and all(t in token_set for t in non_generic):
                hits.append(keyword)
                score += max(8, specificity // 5)

    direct_brand_match = False
    if brand_profile and brand_profile.get("brand_name"):
        brand_phrase = normalize_phrase(brand_profile.get("brand_name", ""))
        if brand_phrase and len(brand_phrase) >= 3 and brand_phrase in text:
            # Verify the brand mention isn't a substring of a longer
            # unrelated word (e.g. "acme" inside "acmeology").
            import re as _re
            if _re.search(rf"\b{_re.escape(brand_phrase)}\b", text):
                direct_brand_match = True
                if brand_phrase not in hits:
                    hits.insert(0, brand_phrase)
                score = max(score, 36)

    deduped_hits: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        if hit in seen:
            continue
        deduped_hits.append(hit)
        seen.add(hit)
    return deduped_hits[:5], min(score, 48), direct_brand_match


# Tokens that should not count as "meaningful" when checking partial
# keyword overlap — they appear too frequently across all domains.
# Note: domain-critical abbreviations ("ai", "ml", "llm", "ar", "vr") are
# intentionally NOT included here. Stripping them makes AI/ML SaaS keywords
# like "AI tool" or "ML model" impossible to match (Issue #17).
_WEAK_MATCH_TOKENS = {
    "best", "tool", "tools", "find",
    "help", "need", "real", "smart", "online", "digital", "modern",
    "first", "next", "new", "free", "top", "good", "great",
}


def _keyword_has_domain_context(
    keyword: str,
    post_tokens: set[str],
    domain_context: DomainContext,
) -> bool:
    """Return True if *post_tokens* contain at least one domain anchor
    term alongside the matched *keyword*.  This prevents a single-word
    keyword like ``rent`` from matching posts about car rentals when the
    brand is in real estate."""
    anchor_overlap = post_tokens & set(domain_context.anchor_terms)
    if anchor_overlap:
        return True
    # Also accept if post contains any core phrase token (multi-word)
    for phrase in domain_context.core_phrases:
        phrase_tokens = set(phrase.split())
        if len(phrase_tokens & post_tokens) >= min(len(phrase_tokens), 2):
            return True
    return False


def _is_low_context(post: RedditPost) -> bool:
    """A post with very thin content is unreliable for scoring and drafting.

    Changed from AND to OR logic: a post is thin if the title is very
    short *or* the body is essentially empty.  Previously a 3-word title
    with a 9-word body would pass, which isn't enough context.
    """
    title_tokens = tokenize(post.title)
    body_tokens = tokenize(post.body)
    total_tokens = len(title_tokens) + len(body_tokens)
    return total_tokens < 8 or (len(title_tokens) < 3 and len(body_tokens) < 6)


_CALIBRATION_MIN_SAMPLES = 20
_CALIBRATION_MAX_ADJUSTMENT = 5


def calibration_adjustment(score: int, feedback_records: list[dict[str, Any]]) -> int:
    """Compute a score adjustment based on user feedback history.

    When users consistently save/accept posts at a certain score level and
    ignore others, this function shifts scores up or down accordingly.

    Args:
        score: The original (uncalibrated) score.
        feedback_records: List of feedback dicts with ``action`` and
            ``original_score`` keys.

    Returns:
        An integer delta (−_CALIBRATION_MAX_ADJUSTMENT to +_CALIBRATION_MAX_ADJUSTMENT)
        to apply to the score. Returns 0 when insufficient data exists.
    """
    if len(feedback_records) < _CALIBRATION_MIN_SAMPLES:
        return 0

    accepted_scores: list[int] = []
    rejected_scores: list[int] = []
    for record in feedback_records:
        action = record.get("action", "")
        original = record.get("original_score", 0)
        if not isinstance(original, (int, float)):
            continue
        original = int(original)
        if action in ("saved", "replied", "drafting"):
            accepted_scores.append(original)
        elif action in ("ignored", "rejected"):
            rejected_scores.append(original)

    if not accepted_scores and not rejected_scores:
        return 0

    avg_accepted = sum(accepted_scores) / len(accepted_scores) if accepted_scores else 0
    avg_rejected = sum(rejected_scores) / len(rejected_scores) if rejected_scores else 100

    gap = avg_accepted - avg_rejected

    if abs(gap) < 5:
        return 0

    if score >= avg_accepted:
        return min(int(gap / 10), _CALIBRATION_MAX_ADJUSTMENT)
    elif score <= avg_rejected:
        return max(-int(abs(gap) / 10), -_CALIBRATION_MAX_ADJUSTMENT)
    else:
        return 0
