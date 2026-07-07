"""Scan run endpoints."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.discovery import create_scan_run, get_scan_run_by_id, list_scan_runs_for_project
from app.db.tables.projects import get_project_by_id
from app.schemas.v1.discovery import ScanRequest, ScanRunResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["scans"])


def _requested_platforms(payload: ScanRequest) -> list[str]:
    """Resolve the effective platform list from scan payload fields."""
    if payload.platforms:
        raw_platforms = list(payload.platforms)
    elif payload.platform == "all":
        raw_platforms = ["reddit", "twitter", "instagram", "linkedin", "hackernews", "github", "indiehackers"]
    else:
        raw_platforms = [payload.platform or "reddit"]

    normalized = ["twitter" if platform == "x" else platform for platform in raw_platforms]
    return list(dict.fromkeys(normalized))


def _run_scan_background(
    db: Client,
    project: dict,
    payload: ScanRequest,
    scan_run_id: str,
    platforms: list[str] | None = None,
) -> None:
    from app.db.tables.discovery import count_opportunities_for_project, get_scan_run_by_id, update_scan_run

    platforms = platforms or _requested_platforms(payload)
    posts_scanned = 0
    opportunities_found = 0
    branch_errors: list[str] = []

    try:
        if "reddit" in platforms:
            try:
                from app.services.product.scanner import run_scan

                reddit_result = run_scan(db, project, payload, scan_run_id=scan_run_id)
                posts_scanned += int(reddit_result.get("posts_scanned") or 0)
                opportunities_found += int(reddit_result.get("opportunities_found") or 0)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Reddit scan branch failed for %s", scan_run_id)
                branch_errors.append(f"Reddit scan failed: {exc}"[:180])

        platform_branches = [platform for platform in platforms if platform != "reddit"]
        if platform_branches:
            try:
                from app.services.product.platform_scanner import run_platform_scan

                platform_result = run_platform_scan(
                    db,
                    project,
                    platforms=platform_branches,
                    scan_run_id=scan_run_id,
                    limit_per_platform=payload.max_posts_per_subreddit,
                    min_score=payload.min_score,
                    time_filter=payload.time_filter,
                )
                posts_scanned += int(platform_result.get("posts_scanned") or 0)
                opportunities_found += int(platform_result.get("opportunities_found") or 0)
                if platform_result.get("error"):
                    branch_errors.append(str(platform_result["error"])[:180])
            except Exception as exc:  # noqa: BLE001
                logger.exception("Platform scan branch failed for %s", scan_run_id)
                branch_errors.append(f"Platform scan failed: {exc}"[:180])

        if not platforms:
            branch_errors.append("No platforms selected.")

    except Exception:  # noqa: BLE001
        logger.exception("Background scan %s failed", scan_run_id)
        branch_errors.append("Scan failed unexpectedly.")
    finally:
        # Guarantee the scan_run transitions out of "running".
        try:
            current = get_scan_run_by_id(db, scan_run_id)
            if current:
                existing_posts = int(current.get("posts_scanned") or 0)
                existing_opps = int(current.get("opportunities_found") or 0)
                final_posts = max(posts_scanned, existing_posts)
                saved_visible_opps = count_opportunities_for_project(db, project["id"], status="new")
                final_opps = max(opportunities_found, existing_opps, saved_visible_opps)
                update_scan_run(db, scan_run_id, {
                    "status": "completed" if final_posts > 0 or final_opps > 0 else "failed" if branch_errors else "completed",
                    "posts_scanned": final_posts,
                    "opportunities_found": final_opps,
                    "error_message": "; ".join(branch_errors)[:500] if branch_errors else current.get("error_message"),
                    "completed_at": datetime.now(UTC).isoformat(),
                })
        except Exception:  # noqa: BLE001
            logger.exception("Failed to finalize scan run %s status", scan_run_id)


@router.post("/scans", response_model=ScanRunResponse)
def create_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ScanRunResponse:
    """Start a scan and return immediately; poll GET /v1/scans/{id} for progress.

    When ``platforms`` is provided (e.g., ``["twitter", "linkedin"]``), the scan
    runs the standard Reddit scanner **plus** the multi-platform scanner in the
    same background task.  Set ``platform`` to ``"all"`` as a shortcut for all
    non-Reddit platforms.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    effective_project_id = project_id or payload.project_id
    proj = get_active_project(supabase, workspace["id"], effective_project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="No active project found.")

    # Fail fast on setup problems — these used to surface synchronously and the
    # frontend expects a 400, not a scan run that instantly errors.
    from app.db.tables.discovery import list_discovery_keywords_for_project, list_monitored_subreddits_for_project
    if not any(k.get("is_active", True) for k in list_discovery_keywords_for_project(supabase, proj["id"])):
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")

    # Only require subreddits when Reddit is actually part of the scan.
    # Non-Reddit platforms (Twitter, LinkedIn, Instagram) use keyword search
    # and don't need monitored subreddits.
    requested_platforms = _requested_platforms(payload)
    scanning_reddit = "reddit" in requested_platforms
    no_active_subreddits = scanning_reddit and not any(
        s.get("is_active", True) for s in list_monitored_subreddits_for_project(supabase, proj["id"])
    )
    if no_active_subreddits:
        if any(platform != "reddit" for platform in requested_platforms):
            # Non-Reddit platforms don't need subreddits; skip Reddit instead of blocking
            requested_platforms = [platform for platform in requested_platforms if platform != "reddit"]
        else:
            raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    run = create_scan_run(supabase, {
        "project_id": proj["id"],
        "status": "running",
        "search_window_hours": payload.search_window_hours,
        "posts_scanned": 0,
        "opportunities_found": 0,
        "started_at": datetime.now(UTC).isoformat(),
    })
    background_tasks.add_task(_run_scan_background, supabase, proj, payload, run["id"], requested_platforms)
    return ScanRunResponse.model_validate(run)


@router.get("/scans", response_model=list[ScanRunResponse])
def list_scans(
    project_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=5, ge=1, le=25),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[ScanRunResponse]:
    """List recent scan runs for the active project."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        return []
    runs = list_scan_runs_for_project(supabase, proj["id"], limit=limit)
    return [ScanRunResponse.model_validate(run) for run in runs]


@router.get("/scans/{scan_id}", response_model=ScanRunResponse)
def get_scan(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ScanRunResponse:
    """Poll the status/progress of a scan run."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    run = get_scan_run_by_id(supabase, scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found.")
    project = get_project_by_id(supabase, run["project_id"])
    if not project or project.get("workspace_id") != workspace["id"]:
        raise HTTPException(status_code=404, detail="Scan run not found.")
    return ScanRunResponse.model_validate(run)


# ── Multi-platform scanning ─────────────────────────────────────────────


class PlatformScanRequest(ScanRequest):
    """Extended scan request that supports multi-platform scanning."""
    platforms: list[str] = ["twitter"]
    limit_per_platform: int = 25


@router.post("/scans/platforms")
def create_platform_scan(
    payload: PlatformScanRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Start a multi-platform scan (Twitter/X, Instagram, etc.).

    This runs alongside the existing Reddit scanner. It uses RapidAPI-powered
    adapters to fetch posts from non-Reddit platforms, score them, and create
    opportunities.
    """
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    effective_project_id = project_id or payload.project_id
    proj = get_active_project(supabase, workspace["id"], effective_project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="No active project found.")

    run = create_scan_run(supabase, {
        "project_id": proj["id"],
        "status": "running",
        "search_window_hours": payload.search_window_hours,
        "posts_scanned": 0,
        "opportunities_found": 0,
        "started_at": datetime.now(UTC).isoformat(),
    })

    def _run_platform_scan_bg(db: Client, project: dict, platforms: list[str], scan_run_id: str, limit: int, time_filter: str = "week") -> None:
        try:
            from app.services.product.platform_scanner import run_platform_scan
            result = run_platform_scan(
                db, project,
                platforms=platforms,
                scan_run_id=scan_run_id,
                limit_per_platform=limit,
                time_filter=time_filter,
            )
            from app.db.tables.discovery import update_scan_run
            update_scan_run(db, scan_run_id, {
                "status": "completed",
                "completed_at": datetime.now(UTC).isoformat(),
                "posts_scanned": result.get("posts_scanned", 0),
                "opportunities_found": result.get("opportunities_found", 0),
            })
        except Exception:
            logger.exception("Platform scan %s failed", scan_run_id)
            try:
                from app.db.tables.discovery import update_scan_run as _update
                _update(db, scan_run_id, {
                    "status": "failed",
                    "error_message": "Platform scan failed",
                    "completed_at": datetime.now(UTC).isoformat(),
                })
            except Exception:
                pass

    background_tasks.add_task(
        _run_platform_scan_bg,
        supabase, proj, payload.platforms, run["id"], payload.limit_per_platform, payload.time_filter,
    )
    return {"scan_run_id": run["id"], "platforms": payload.platforms, "status": "running"}


@router.get("/platforms/health")
async def platform_health(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Check connectivity of all configured platform adapters.

    Returns per-platform health status, rate limit info, and search strategy.
    """
    from app.services.infrastructure.platforms.router import PLATFORM_INFO, PlatformRouter

    all_platforms = [p for p in PLATFORM_INFO if p != "x"]  # skip "x" alias
    router_instance = PlatformRouter(platforms=all_platforms)
    health_results = await router_instance.health_check_all()

    platform_details = {}
    for name in all_platforms:
        info = PLATFORM_INFO.get(name, {})
        platform_details[name] = {
            "healthy": health_results.get(name, False),
            "host": info.get("host", "unknown"),
            "search_strategy": info.get("search", "unknown"),
            "rate_limit": info.get("limit", "unknown"),
        }

    return {"platforms": platform_details}
