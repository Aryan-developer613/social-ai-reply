"""Reddit scanning and opportunity detection service."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from app.services.product.reddit import RedditPost
from app.services.product.reddit_discovery import RedditDiscoveryService
from app.services.product.relevance_v2 import CandidatePost, RelevanceEngine, RelevanceResult
from app.services.product.scoring import (
    MIN_RELEVANT_OPPORTUNITY_SCORE,
    score_post,
)

logger = logging.getLogger(__name__)

_MAX_REJECTED_PER_SCAN = 25
_MAX_PARALLEL_SUBREDDITS = 3
# Scanner-calibrated semantic floor. The engine's default (0.45) is tuned for
# the agents pipeline with richer brand context; with TF-IDF embeddings on
# short Reddit posts it would reject nearly everything the scanner sees.
_SCAN_SEMANTIC_THRESHOLD = 0.05


def _engine_brand_profile(brand: dict[str, Any] | None) -> dict[str, Any]:
    """Map a brand_profiles row onto the dict shape RelevanceEngine expects."""
    brand = brand or {}
    description = " ".join(
        filter(None, [brand.get("summary"), brand.get("product_summary")])
    )
    return {
        "name": brand.get("brand_name", ""),
        "brand_name": brand.get("brand_name", ""),
        "description": description,
        "category": brand.get("business_domain", ""),
        "target_audience": brand.get("target_audience", ""),
        "pain_points": [],
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
        effective_min_score = max(payload.min_score, MIN_RELEVANT_OPPORTUNITY_SCORE)
        per_subreddit_errors: list[str] = []
        fatal_error = False

        engine: RelevanceEngine | None = None
        if not get_settings().use_legacy_scoring:
            engine = RelevanceEngine(
                relevance_threshold=effective_min_score,
                semantic_threshold=_SCAN_SEMANTIC_THRESHOLD,
            )
        engine_brand = _engine_brand_profile(brand)
        engine_kw = _engine_keywords(search_keywords)
        # Kept opportunities queued for the optional LLM buying-stage pass.
        stage_refine_queue: list[dict[str, Any]] = []

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
        with ThreadPoolExecutor(max_workers=min(len(active_subreddits), _MAX_PARALLEL_SUBREDDITS)) as pool:
            future_to_sub = {
                pool.submit(_scan_one_subreddit, sub): sub
                for sub in active_subreddits
            }
            for future in as_completed(future_to_sub):
                scan_results.append(future.result())
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
