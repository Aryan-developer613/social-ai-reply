
"""Reddit scanning and opportunity detection service."""
from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from app.db.tables.discovery import (
    batch_get_opportunities_by_reddit_posts,
    create_opportunity,
    get_scan_run_by_id,
    list_score_feedback_for_workspace,
    update_opportunity,
    update_scan_run,
)
from app.db.tables.projects import get_brand_profile_by_project

if TYPE_CHECKING:
    from supabase import Client

    from app.schemas.v1.discovery import ScanRequest
from app.core.config import get_settings
from app.services.infrastructure.http_budget import CircuitOpenError
from app.services.product.discovery import get_project_search_keywords
from app.services.product.intent_classifier import classify_intent
from app.services.product.intent_ladder import refine_stages_with_llm, stage_from_intent
from app.services.product.reddit import RedditComment, RedditPost
from app.services.product.reddit_discovery import RedditDiscoveryService
from app.services.product.relevance_v2 import CandidatePost, RelevanceEngine, RelevanceResult
from app.services.product.scoring import (
    MIN_RELEVANT_OPPORTUNITY_SCORE,
    score_post,
)

logger = logging.getLogger(__name__)

_MAX_REJECTED_PER_SCAN = 25
_MAX_PARALLEL_SUBREDDITS = 3
# Hard wall-clock cap for the scan step. Prevents the pipeline from running
# indefinitely when Reddit rate-limits or the feed scraping is slow.
_MAX_SCAN_DURATION_SECONDS = 300  # 5 minutes
# Max posts per subreddit to fetch comments from. Keeps the comment-fetch
# budget bounded (1 HTTP request per post → max 5 extra requests per sub).
_MAX_COMMENT_POSTS_PER_SUB = 5
# Scanner-calibrated semantic floor. TF-IDF on short Reddit posts gives
# exactly 0.0 cosine similarity for posts lacking shared vocabulary with
# the brand description. Setting to 0.0 disables the semantic hard-reject
# entirely, so posts are judged on keywords + intent + freshness instead.
_SCAN_SEMANTIC_THRESHOLD = 0.0
# Scanner minimum score. Lower than the global MIN_RELEVANT_OPPORTUNITY_SCORE
# because RSS feeds lack upvote/comment metadata (both = 0), which penalizes
# posts that would otherwise score well. 15 keeps obvious noise out while
# letting borderline-relevant posts surface for human review.
_SCAN_MIN_SCORE = 15


def _engine_brand_profile(
    brand: dict[str, Any] | None,
    personas: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Map a brand_profiles row onto the dict shape RelevanceEngine expects.

    When ``personas`` are provided, their pain_points are merged into the
    brand profile so the RelevanceEngine can match posts that reference the
    problems our buyers actually describe on social media.
    """
    brand = brand or {}
    description = " ".join(
        filter(None, [brand.get("summary"), brand.get("product_summary")])
    )
    # Aggregate pain points from personas so the relevance engine can match
    # posts that describe problems our buyers actually talk about.
    pain_points: list[str] = []
    for persona in personas or []:
        raw = persona.get("pain_points") or []
        if isinstance(raw, list):
            pain_points.extend(str(p) for p in raw if p)
        elif isinstance(raw, str) and raw:
            pain_points.extend([pt.strip() for pt in raw.split(",") if pt.strip()])
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_pain_points = []
    for pt in pain_points:
        if pt.lower() not in seen:
            seen.add(pt.lower())
            unique_pain_points.append(pt)

    return {
        "name": brand.get("brand_name", ""),
        "brand_name": brand.get("brand_name", ""),
        "description": description,
        "category": brand.get("business_domain", ""),
        "target_audience": brand.get("target_audience", ""),
        "pain_points": unique_pain_points[:20],  # cap to avoid prompt bloat
        "competitors": [],
    }


def _engine_keywords(keywords: list[str]) -> list[dict[str, Any]]:
    return [{"keyword": kw, "type": "core"} for kw in keywords]


def _candidate_from_post(post: RedditPost) -> CandidatePost:
    return CandidatePost(
        title=post.title,
        body=post.body,
        platform="reddit",
        source_name=post.subreddit,
        upvotes=post.score,
        comments_count=post.num_comments,
        created_at=post.created_at,
        author=post.author,
        post_url=post.permalink,
    )


def _candidate_from_comment(comment: RedditComment) -> CandidatePost:
    """Wrap a comment as a CandidatePost for scoring.

    Uses the parent post title as context (title) and the comment body
    as the main content, since the scorer weights both.
    """
    return CandidatePost(
        title=comment.parent_post_title,
        body=comment.body,
        platform="reddit",
        source_name=comment.subreddit,
        upvotes=comment.score,
        comments_count=0,
        created_at=comment.created_at,
        author=comment.author,
        post_url=comment.permalink,
    )


def _result_payload(result: RelevanceResult) -> dict[str, Any]:
    """Opportunity columns derived from a RelevanceResult (engine path only)."""
    stage, stage_confidence = stage_from_intent(result.intent)
    reasons = [result.reason_relevant] if result.reason_relevant else []
    if result.rejection_reason:
        reasons.insert(0, result.rejection_reason)
    return {
        "score": result.relevance_score,
        "score_reasons": reasons,
        "keyword_hits": result.matched_keywords[:5],
        "rule_risk": result.rule_risk,
        "intent": result.intent,
        # Confidence in the buying_stage classification; the optional LLM
        # refinement pass after the scan upgrades both fields.
        "intent_confidence": stage_confidence,
        "buying_stage": stage,
        "semantic_similarity": result.semantic_similarity,
        "matched_keywords": result.matched_keywords,
        "risk_flags": result.risk_flags,
        "reason_relevant": result.reason_relevant or None,
        "rejection_reason": result.rejection_reason,
        "scoring_breakdown": result.scoring_breakdown,
    }


@dataclass
class _SubredditScanResult:
    subreddit_name: str
    posts: list[RedditPost] = field(default_factory=list)
    error: str | None = None
    rules: list[str] = field(default_factory=list)


def run_scan(db: Client, project: dict, payload: ScanRequest, scan_run_id: str | None = None) -> dict:
    """Run a scan for opportunities based on project keywords and subreddits.

    When ``scan_run_id`` is provided (async route), progress is written to that
    existing scan_runs row instead of creating a new one.
    """
    brand = get_brand_profile_by_project(db, project["id"])
    workspace_id = project.get("workspace_id")
    feedback_records = _safe_feedback_records(db, workspace_id)

    # Load personas so their pain_points feed into relevance scoring
    from app.db.tables.discovery import list_personas_for_project as _list_personas
    project_personas: list[dict[str, Any]] = []
    try:
        project_personas = _list_personas(db, project["id"], include_inactive=False) or []
        logger.info(
            "Scan: loaded %d personas for project %s (pain_points fed into engine)",
            len(project_personas), project["id"]
        )
    except Exception:
        logger.warning("Could not load personas for scan — proceeding without persona context")

    # Get active keywords
    from app.db.tables.discovery import list_discovery_keywords_for_project
    active_keywords = list_discovery_keywords_for_project(db, project["id"])
    active_keywords = [k for k in active_keywords if k.get("is_active", True)]
    active_keywords.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    # Get active subreddits
    from app.db.tables.discovery import list_monitored_subreddits_for_project
    active_subreddits = list_monitored_subreddits_for_project(db, project["id"])
    active_subreddits = [s for s in active_subreddits if s.get("is_active", True)]
    active_subreddits.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    if not active_keywords:
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not active_subreddits:
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    search_keywords = get_project_search_keywords(db, project, limit=20)
    if not search_keywords:
        raise HTTPException(status_code=400, detail="Add more specific discovery keywords before scanning.")

    # Create or adopt the scan run record
    from app.db.tables.discovery import create_scan_run
    if scan_run_id:
        run = get_scan_run_by_id(db, scan_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Scan run not found.")
        update_scan_run(db, run["id"], {"subreddits_total": len(active_subreddits)})
    else:
        run = create_scan_run(db, {
            "project_id": project["id"],
            "status": "running",
            "search_window_hours": payload.search_window_hours,
            "started_at": datetime.now(UTC).isoformat(),
            "subreddits_total": len(active_subreddits),
        })

    try:
        posts_scanned = 0
        opportunities_found = 0
        rejected_saved = 0
        completed_at: str | None = None
        cutoff = datetime.now(UTC) - timedelta(hours=payload.search_window_hours)
        effective_min_score = max(payload.min_score, _SCAN_MIN_SCORE)
        per_subreddit_errors: list[str] = []
        fatal_error = False

        engine: RelevanceEngine | None = None
        use_legacy = get_settings().use_legacy_scoring
        if not use_legacy:
            engine = RelevanceEngine(
                relevance_threshold=effective_min_score,
                semantic_threshold=_SCAN_SEMANTIC_THRESHOLD,
            )
        # Always create an engine for comment scoring (legacy scorer expects
        # RedditPost objects, but comments use CandidatePost).
        comment_engine = engine or RelevanceEngine(
            relevance_threshold=effective_min_score,
            semantic_threshold=_SCAN_SEMANTIC_THRESHOLD,
        )
        engine_brand = _engine_brand_profile(brand, personas=project_personas)
        engine_kw = _engine_keywords(search_keywords)
        # Kept opportunities queued for the optional LLM buying-stage pass.
        stage_refine_queue: list[dict[str, Any]] = []

        # ── Free supplemental sources (HN + GitHub, no API key needed) ──────────
        # Run these in the background alongside the Reddit subreddit scan only
        # when explicitly requested. Normal multi-platform scans use
        # platform_scanner.py, so a Reddit-only scan should not leak HN/GitHub
        # rows into the Reddit result set.
        free_source_futures: list[Any] = []
        _free_executor = None
        if not getattr(payload, "include_free_sources", False):
            logger.info("Free source scrapers disabled for this scan")
        try:
            import concurrent.futures as _cf_free

            from app.core.config import get_settings as _gs
            from app.scrapers.free_sources import scrape_github, scrape_hackernews

            if not getattr(payload, "include_free_sources", False):
                raise RuntimeError("free sources disabled")

            _settings = _gs()
            _hn_enabled = getattr(_settings, "enable_hn_scraper", True)
            _gh_enabled = getattr(_settings, "enable_github_scraper", True)
            _gh_token   = getattr(_settings, "github_token", None)

            _kw_strs = [k.get("keyword", "") for k in active_keywords if k.get("keyword")][:8]

            _free_executor = _cf_free.ThreadPoolExecutor(max_workers=2, thread_name_prefix="free_src")
            if _hn_enabled:
                free_source_futures.append(
                    (_free_executor.submit(scrape_hackernews, _kw_strs, payload.search_window_hours), "hackernews")
                )
            if _gh_enabled:
                free_source_futures.append(
                    (_free_executor.submit(scrape_github, _kw_strs, payload.search_window_hours, 15, _gh_token), "github")
                )
            logger.info("Free source scrapers queued: HN=%s GitHub=%s", _hn_enabled, _gh_enabled)
        except RuntimeError as _free_skip:
            logger.debug("%s", _free_skip)
        except Exception as _free_err:
            logger.warning("Could not start free source scrapers: %s", _free_err)
        if not free_source_futures:
            free_source_futures = []

        def _scan_one_subreddit(subreddit: dict[str, Any]) -> _SubredditScanResult:
            name = subreddit["name"]
            local_reddit = RedditDiscoveryService()
            try:
                rules = _safe_subreddit_rules(local_reddit, name)
                posts = local_reddit.search_posts(
                    search_keywords,
                    subreddits=[name],
                    limit=payload.max_posts_per_subreddit,
                )
                return _SubredditScanResult(subreddit_name=name, posts=posts, rules=rules)
            except CircuitOpenError as exc:
                return _SubredditScanResult(
                    subreddit_name=name,
                    error=f"{name}: Reddit temporarily rate-limited; retry in ~{exc.retry_in / 60:.0f} min",
                )
            except Exception as exc:  # noqa: BLE001
                return _SubredditScanResult(
                    subreddit_name=name,
                    error=f"{name}: {type(exc).__name__}: {exc}"[:200],
                )
            finally:
                local_reddit.close()

        scan_results: list[_SubredditScanResult] = []
        scan_deadline = time.monotonic() + _MAX_SCAN_DURATION_SECONDS
        # Sequential queue with cool-down between subreddits.
        # Parallel execution hammered Reddit (3 subs × 3 HTTP calls each = 9
        # concurrent requests), triggering instant 429 on all of them.
        # Sequential scanning lets each subreddit's requests finish before
        # starting the next, staying under Reddit's ~10 req/min limit.
        inter_subreddit_delay = 3.0  # seconds between subreddits
        for i, sub in enumerate(active_subreddits):
            if time.monotonic() > scan_deadline:
                logger.warning(
                    "Scan hit %ds time cap — stopping with %d/%d subreddits scanned",
                    _MAX_SCAN_DURATION_SECONDS, len(scan_results), len(active_subreddits),
                )
                break

            # Cool-down between subreddits (skip before the first one)
            if i > 0:
                time.sleep(inter_subreddit_delay)

            result = _scan_one_subreddit(sub)
            scan_results.append(result)

            try:
                update_scan_run(db, run["id"], {"subreddits_scanned": len(scan_results)})
            except Exception:  # noqa: BLE001 — progress reporting must not kill the scan
                logger.warning("Failed to update scan progress for run %s", run["id"])

        subreddit_map = {s["name"]: s for s in active_subreddits}
        for result in scan_results:
            subreddit = subreddit_map.get(result.subreddit_name)
            if not subreddit:
                continue

            if result.error:
                per_subreddit_errors.append(result.error)
                logger.warning("Scan: error querying r/%s: %s", result.subreddit_name, result.error)
                continue

            rules = result.rules

            # Batch-fetch existing opportunities for all posts in this result set
            post_ids = [post.post_id for post in result.posts]
            existing_opps = batch_get_opportunities_by_reddit_posts(db, project["id"], post_ids)

            for post in result.posts:
                if post.created_at and post.created_at < cutoff.replace(tzinfo=None if post.created_at.tzinfo is None else UTC):
                    continue
                posts_scanned += 1

                if engine is not None:
                    relevance = engine.score(
                        _candidate_from_post(post),
                        engine_brand,
                        engine_kw,
                        source_meta=subreddit,
                        source_rules=rules,
                        feedback_records=feedback_records,
                    )
                    keep = relevance.should_keep
                    score_payload = _result_payload(relevance)
                else:
                    score = score_post(post, brand, subreddit, search_keywords, rules, feedback_records=feedback_records)
                    keep = score.eligible and score.total >= effective_min_score
                    full_text = f"{post.title} {post.body}"
                    intent_result = classify_intent(full_text, brand_profile=brand)
                    stage_name, stage_conf = stage_from_intent(intent_result.intent)
                    score_payload = {
                        "score": score.total,
                        "score_reasons": score.reasons,
                        "keyword_hits": score.keyword_hits,
                        "rule_risk": score.rule_risk,
                        "intent": intent_result.intent,
                        "buying_stage": stage_name,
                        "scoring_breakdown": {},
                        "semantic_similarity": 0.0,
                        "risk_flags": [],
                    }

                # Dict lookup instead of per-post DB query
                existing = existing_opps.get(post.post_id)

                if keep:
                    new_status = existing.get("status", "new") if existing else "new"
                    if new_status == "rejected":
                        new_status = "new"
                    payload_data = {
                        **score_payload,
                        "body_excerpt": post.body[:1200],
                        "permalink": post.permalink,
                        "status": new_status,
                    }
                    if existing:
                        update_opportunity(db, existing["id"], payload_data)
                        opp_id = existing["id"]
                    else:
                        created = create_opportunity(db, {
                            "project_id": project["id"],
                            "scan_run_id": run["id"],
                            "reddit_post_id": post.post_id,
                            "title": post.title,
                            "author": post.author,
                            "subreddit_name": subreddit["name"],
                            "platform": "reddit",
                            **payload_data,
                        })
                        opp_id = created["id"]
                        opportunities_found += 1
                    if engine is not None:
                        stage_refine_queue.append({
                            "index": opp_id,
                            "title": post.title,
                            "body": post.body[:800],
                        })
                elif not existing and rejected_saved < _MAX_REJECTED_PER_SCAN:
                    # Persist rejected posts so the user can review what Reddit returned.
                    create_opportunity(db, {
                        "project_id": project["id"],
                        "scan_run_id": run["id"],
                        "reddit_post_id": post.post_id,
                        "title": post.title,
                        "author": post.author,
                        "subreddit_name": subreddit["name"],
                        "platform": "reddit",
                        "body_excerpt": post.body[:1200],
                        "permalink": post.permalink,
                        "status": "rejected",
                        **score_payload,
                    })
                    rejected_saved += 1

            try:
                update_scan_run(db, run["id"], {
                    "posts_scanned": posts_scanned,
                    "opportunities_found": opportunities_found,
                })
            except Exception:  # noqa: BLE001
                logger.warning("Failed to update scan progress for run %s", run["id"])

            # ── Comment-level opportunity discovery ──────────────────
            # Fetch comments from the top N posts (by score) and score them.
            # One HTTP request per post yields ~15-25 comments.
            if time.monotonic() < scan_deadline:
                # Pick the top posts by relevance score (or post score if no engine score)
                scored_posts = sorted(
                    result.posts,
                    key=lambda p: p.score,
                    reverse=True,
                )[:_MAX_COMMENT_POSTS_PER_SUB]

                comment_reddit = RedditDiscoveryService()
                try:
                    for ci, post in enumerate(scored_posts):
                        if time.monotonic() > scan_deadline:
                            break
                        # Space out comment-fetch requests to avoid 429
                        if ci > 0:
                            time.sleep(2.0)
                        comments = comment_reddit.fetch_post_comments(
                            post.permalink,
                            post_id=post.post_id,
                            subreddit=post.subreddit,
                            parent_post_title=post.title,
                            limit=15,
                        )
                        for comment in comments:
                            # Use the comment's unique ID as the reddit_post_id
                            comment_reddit_id = f"comment_{comment.comment_id}"
                            existing_comment_opp = existing_opps.get(comment_reddit_id)
                            if existing_comment_opp:
                                continue  # Already tracked

                            relevance = comment_engine.score(
                                _candidate_from_comment(comment),
                                engine_brand,
                                engine_kw,
                                source_meta=subreddit,
                                source_rules=rules,
                                feedback_records=feedback_records,
                            )
                            if relevance.should_keep:
                                comment_payload = _result_payload(relevance)
                                created_opp = create_opportunity(db, {
                                    "project_id": project["id"],
                                    "scan_run_id": run["id"],
                                    "reddit_post_id": comment_reddit_id,
                                    "title": f"[Comment] {post.title}",
                                    "author": comment.author,
                                    "subreddit_name": subreddit["name"],
                                    "platform": "reddit",
                                    "body_excerpt": comment.body[:1200],
                                    "permalink": comment.permalink,
                                    "status": "new",
                                    "source_type": "comment",
                                    **comment_payload,
                                })
                                opportunities_found += 1
                                stage_refine_queue.append({
                                    "index": created_opp["id"],
                                    "title": post.title,
                                    "body": comment.body[:800],
                                })
                finally:
                    comment_reddit.close()

        # ── Optional LLM buying-stage refinement for kept opportunities ──
        if stage_refine_queue:
            refined = refine_stages_with_llm(stage_refine_queue, brand)
            for opp_id, (stage, confidence) in refined.items():
                try:
                    update_opportunity(db, opp_id, {
                        "buying_stage": stage,
                        "intent_confidence": confidence,
                    })
                except Exception:  # noqa: BLE001 — refinement is best-effort
                    logger.warning("Failed to persist refined stage for opportunity %s", opp_id)

        subreddits_queried = sum(1 for r in scan_results if not r.error)

        error_message: str | None = None
        if subreddits_queried == 0 and per_subreddit_errors:
            fatal_error = True
            error_message = (
                "All subreddit discovery requests failed across external search and "
                "public Reddit feeds. Sample errors: "
                + "; ".join(per_subreddit_errors[:3])
            )[:500]
        elif per_subreddit_errors and posts_scanned == 0:
            error_message = (
                f"No posts found. {len(per_subreddit_errors)} subreddit(s) errored "
                f"and {subreddits_queried} returned zero matches. "
                + "; ".join(per_subreddit_errors[:2])
            )[:500]

        # Update scan run with results
        completed_at = datetime.now(UTC).isoformat()
        # ── Merge free-source results (HN, GitHub) ───────────────────────────────
        if free_source_futures:
            try:
                for future, src_name in free_source_futures:
                    try:
                        free_posts = future.result(timeout=25)
                        logger.info("Free source %r returned %d posts", src_name, len(free_posts))
                        for fp in free_posts:
                            fp_dict = fp.to_dict()
                            candidate = CandidatePost(
                                title=fp_dict.get("title", ""),
                                body=fp_dict.get("body", ""),
                                platform=src_name,
                                source_name=fp_dict.get("subreddit", src_name),
                                upvotes=fp_dict.get("score", 0),
                                comments_count=fp_dict.get("num_comments", 0),
                                created_at=fp.created_at,
                                author=fp_dict.get("author", ""),
                                post_url=fp_dict.get("url", ""),
                            )
                            posts_scanned += 1
                            if comment_engine:
                                result: RelevanceResult = comment_engine.score(
                                    candidate, engine_brand, engine_kw
                                )
                                if result.relevance_score >= effective_min_score:
                                    ext_id = fp.external_id or fp.id
                                    create_opportunity(db, {
                                        "project_id": project["id"],
                                        "platform": src_name,
                                        "reddit_post_id": f"{src_name}_{ext_id}",
                                        "title": fp_dict.get("title", ""),
                                        "body_excerpt": fp_dict.get("body", "")[:1200],
                                        "permalink": fp_dict.get("url", ""),
                                        "author": fp_dict.get("author", ""),
                                        "subreddit_name": src_name,
                                        "source_type": "post",
                                        "status": "new",
                                        **_result_payload(result),
                                    })
                                    opportunities_found += 1
                    except Exception as _fe:
                        logger.warning("Free source %r merge error: %s", src_name, _fe)
            except Exception as _free_merge_err:
                logger.warning("Free source merge failed: %s", _free_merge_err)
            finally:
                with contextlib.suppress(Exception):
                    _free_executor.shutdown(wait=False, cancel_futures=True)

        # ── Competitor Intelligence ────────────────────────────────────────────
        # Previously this only ran from the legacy auto-pipeline orchestrator,
        # so the Competitor Intel page stayed empty for manual scans run from
        # Social Radar / the Launch step. Wiring it here makes every scan path
        # (auto-pipeline, master_pipeline, manual scan) populate the same page.
        if opportunities_found > 0:
            try:
                from app.db.tables.discovery import list_opportunities_for_project
                from app.services.product.competitor_intel import (
                    get_project_competitors,
                    process_competitor_opportunities,
                )

                competitors = get_project_competitors(db, project["id"])
                if competitors:
                    recent_opps = list_opportunities_for_project(db, project["id"], limit=100)
                    post_dicts = [
                        {
                            "title": o.get("title", ""),
                            "body": o.get("body_excerpt", "") or o.get("body_text", ""),
                            "selftext": o.get("body_excerpt", "") or o.get("body_text", ""),
                            "platform": o.get("platform", "reddit"),
                            "url": o.get("permalink") or o.get("post_url", ""),
                        }
                        for o in recent_opps
                    ]
                    # run_scan is synchronous, so spin up a fresh event loop
                    # rather than trying to await inside a sync function.
                    import asyncio as _asyncio_comp
                    _comp_loop = _asyncio_comp.new_event_loop()
                    try:
                        comp_mentions = _comp_loop.run_until_complete(
                            process_competitor_opportunities(db, project["id"], post_dicts, competitors)
                        )
                    finally:
                        _comp_loop.close()
                    logger.info("Competitor intel: %d mentions detected during scan", len(comp_mentions))
                else:
                    logger.info("No competitors configured for project %s — skipping competitor intel", project["id"])
            except Exception as _comp_err:
                logger.warning("Competitor intelligence scan failed (non-fatal): %s", _comp_err)

        # Persist final scan results (always runs, regardless of free sources)
        update_scan_run(db, run["id"], {
            "status": "completed",
            "posts_scanned": posts_scanned,
            "opportunities_found": opportunities_found,
            "error_message": error_message,
            "completed_at": completed_at,
        })

        # Return full scan run record
        updated_run = get_scan_run_by_id(db, run["id"])
        response = _hydrate_scan_run_response(
            updated_run or run,
            search_window_hours=payload.search_window_hours,
            posts_scanned=posts_scanned,
            completed_at=completed_at,
        )
        response["fatal_error"] = fatal_error
        return response
    except Exception as e:
        logger.exception("Scan failed")
        completed_at = datetime.now(UTC).isoformat()
        update_scan_run(db, run["id"], {
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": completed_at,
        })
        raise


def _safe_feedback_records(db: Client, workspace_id: int | None) -> list[dict[str, Any]] | None:
    """Score-feedback calibration is best-effort — a missing table must not kill scans."""
    if not workspace_id:
        return None
    try:
        return list_score_feedback_for_workspace(db, workspace_id)
    except Exception:  # noqa: BLE001
        logger.warning("score_feedback unavailable; scanning without calibration", exc_info=True)
        return None


def _safe_subreddit_rules(reddit: RedditDiscoveryService, subreddit_name: str) -> list[str]:
    """Safely fetch subreddit rules with a timeout."""
    try:
        return reddit.subreddit_rules(subreddit_name)
    except Exception:
        return []


def revalidate_opportunity(db: Client, project: dict, opportunity: dict) -> tuple[bool, int]:
    """Re-score an opportunity to ensure it still meets the threshold.

    Uses stored opportunity data since we don't have real-time Reddit access.
    """
    brand = get_brand_profile_by_project(db, project["id"])
    workspace_id = project.get("workspace_id")
    feedback_records = _safe_feedback_records(db, workspace_id)

    from app.db.tables.discovery import list_discovery_keywords_for_project, list_monitored_subreddits_for_project
    keywords = [k["keyword"] for k in list_discovery_keywords_for_project(db, project["id"]) if k.get("is_active", True)]
    subreddit = next(
        (s for s in list_monitored_subreddits_for_project(db, project["id"]) if s["name"] == opportunity["subreddit_name"]),
        None,
    )

    # Create a RedditPost from stored opportunity data
    from datetime import datetime
    post_created = opportunity.get("post_created_at")
    if post_created is None:
        post_created = opportunity.get("created_utc", datetime.now(UTC))
    elif isinstance(post_created, str):
        post_created = datetime.fromisoformat(post_created.replace("Z", "+00:00"))
    post = RedditPost(
        post_id=opportunity.get("reddit_post_id", ""),
        subreddit=opportunity.get("subreddit_name", ""),
        title=opportunity.get("title", ""),
        author=opportunity.get("author", ""),
        permalink=opportunity.get("permalink", ""),
        body=opportunity.get("body_excerpt", ""),
        created_at=post_created,
        num_comments=opportunity.get("comments_count", 0) or 0,
        score=opportunity.get("score", 0),
    )

    if get_settings().use_legacy_scoring:
        score = score_post(post, brand, subreddit, keywords, [], feedback_records=feedback_records)
        return score.eligible, score.total

    engine = RelevanceEngine(
        relevance_threshold=MIN_RELEVANT_OPPORTUNITY_SCORE,
        semantic_threshold=_SCAN_SEMANTIC_THRESHOLD,
    )
    result = engine.score(
        _candidate_from_post(post),
        _engine_brand_profile(brand),
        _engine_keywords(keywords),
        source_meta=subreddit,
        feedback_records=feedback_records,
    )
    return result.should_keep, result.relevance_score


def _hydrate_scan_run_response(
    record: dict,
    *,
    search_window_hours: int,
    posts_scanned: int,
    completed_at: str | None,
) -> dict:
    hydrated = dict(record)
    hydrated.setdefault("search_window_hours", search_window_hours)
    hydrated.setdefault("posts_scanned", posts_scanned)
    hydrated.setdefault("opportunities_found", 0)
    if completed_at and not hydrated.get("completed_at"):
        hydrated["completed_at"] = completed_at
    return hydrated
