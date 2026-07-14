"""SignalFlow API - AI Visibility and Community Engagement Platform.

Backend API server using FastAPI with Supabase for authentication and database.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.supabase_client import get_supabase_client
from app.middleware import RateLimitMiddleware, RequestTracingMiddleware
from app.services.infrastructure.llm.providers._registry import get_configured_providers

logger = logging.getLogger(__name__)


async def auto_publish_loop() -> None:
    """Background loop: publish due, approved (scheduled) calendar posts every 5 minutes."""
    from app.services.product.post_scheduler import publish_due_drafts

    logger.info("Auto-publish scheduler started (interval=300s)")
    while True:
        try:
            await asyncio.sleep(300)
            db = get_supabase_client()
            outcome = await asyncio.to_thread(publish_due_drafts, db)
            if outcome["attempted"]:
                logger.info(
                    "Auto-publish: attempted=%d published=%d failed=%d",
                    outcome["attempted"], outcome["published"], outcome["failed"],
                )
        except asyncio.CancelledError:
            logger.info("Auto-publish scheduler cancelled")
            raise
        except Exception:
            logger.exception("Auto-publish scheduler iteration failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    In the Supabase era, we don't create tables automatically since
    Supabase manages the schema. Tables should be created via Supabase
    dashboard, migrations, or SQL scripts.
    """
    logger.info("Starting SignalFlow API...")
    workers = os.environ.get("WEB_CONCURRENCY") or os.environ.get("UVICORN_WORKERS") or "1"
    if workers.isdigit() and int(workers) > 1:
        logger.warning(
            "Running with %s workers: the in-memory rate limiter and HTTP budget are "
            "per-process, so effective limits multiply by the worker count. Swap in a "
            "shared RateLimitBackend (app/middleware.py) before scaling out.",
            workers,
        )
    if settings.environment == "development" and not settings.supabase_secret_key:
        logger.warning(
            "SUPABASE_SECRET_KEY is not configured. Falling back to SUPABASE_PUBLISHABLE_KEY for local DB access; "
            "email/password registration and other admin-only auth flows will remain unavailable until the service role key is set."
        )
    configured_providers = get_configured_providers()
    if configured_providers:
        logger.info("Configured LLM providers: %s", ", ".join(sorted(configured_providers)))
    else:
        logger.warning(
            "No LLM provider is configured. Set GEMINI_API_KEY in the repo root .env.local, "
            "or configure another provider and restart the backend."
        )
    # Run pending schema migrations (run_migrations handles its own exceptions)
    try:
        from app.db.run_migrations import run_migrations

        applied = run_migrations()
        if applied:
            logger.info("Applied %d migration(s): %s", len(applied), ", ".join(applied))
        else:
            logger.info("No pending migrations.")
    except Exception:
        logger.exception("Migration runner import failed — continuing startup")
    scheduler_task = asyncio.create_task(auto_publish_loop())
    logger.info("SignalFlow API started successfully.")
    yield
    scheduler_task.cancel()
    logger.info("Shutting down SignalFlow API.")


settings = get_settings()
# Configure logging AFTER settings load so log_level/log_format/environment take
# effect. A few logger calls above (module import) used stdlib defaults; that's
# fine — once setup runs, the structlog ProcessorFormatter owns the root handler.
setup_logging(settings)

app = FastAPI(
    title="SignalFlow API",
    description="AI Visibility and Community Engagement Platform",
    version="2.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in (settings.cors_origins_raw or "http://localhost:3000").split(",")]

# Starlette executes middleware in REVERSE order of addition, so the add-order
# below yields this inbound execution chain:
#   CORS  ->  RequestTracing  ->  RateLimit  ->  handler
# CORSMiddleware is added LAST so it runs FIRST (CORS headers land on every
# response, including 429s, or the browser blocks them). RequestTracing must run
# BEFORE RateLimit so the request_id is bound onto the log context BEFORE a 429
# is returned — otherwise rate-limited responses carry no request_id.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
logger.info("CORS allow_origins=%s", origins)
app.include_router(v1_router)


@app.exception_handler(AppError)
async def app_exception_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc: RuntimeError):
    """Catch LLM/provider runtime errors and return a structured 503 response."""
    logger.error("RuntimeError in request handler: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """Catch-all for any unhandled exception. Returns a generic 500.

    Logs the full traceback so the error is debuggable without leaking
    internals to the client (Issue #61).
    """
    logger.exception("Unhandled %s in %s %s", type(exc).__name__, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


def _service_checks() -> dict[str, str]:
    """Check service health (API + Supabase database)."""
    checks = {"api": "ok"}
    try:
        supabase = get_supabase_client()
        # Actually query the database to verify connectivity
        supabase.table("account_users").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Supabase health check failed: %s", e)
        checks["database"] = "error"
    return checks


@app.get("/health")
def health_check():
    """Health check endpoint."""
    checks = _service_checks()
    status = "healthy" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/ready")
def readiness_check():
    """Readiness check endpoint."""
    checks = _service_checks()
    ready = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(content=payload, status_code=200 if ready else 503)


@app.get("/")
def root():
    """Root endpoint."""
    return {"name": "SignalFlow API", "version": "2.1.0", "status": "running"}
