# syntax=docker/dockerfile:1
#
# RedditFlow backend (FastAPI).
#
# uv is copied from Astral's official, content-addressed image instead of
# `pip install uv`. That avoids the recurring failures caused by pip downloading
# the 22 MB uv wheel from PyPI (empty $NIXPACKS_UV_VERSION bug, then a transient
# truncated download rejected as a SHA-256 mismatch).

# ---------- builder ----------
FROM python:3.11-slim AS builder

# Insurance only — all current deps ship manylinux wheels, so this rarely runs.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# uv, pinned to the version that generated uv.lock. Pulled as a Docker layer.
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Copy only the dependency manifests first so this layer caches independently
# of source changes. NOTE: do NOT use BuildKit --mount here — Railway's builder
# does not support --mount=type=bind, and --mount=type=cache requires a
# service-id-scoped id= that is non-portable. We rely on the standard Docker
# layer cache instead (this RUN only re-runs when uv.lock/pyproject.toml change).
COPY uv.lock pyproject.toml ./

# Install third-party dependencies only (cached layer).
RUN uv sync --frozen --no-dev --no-install-project

# Copy source, then install the project itself.
COPY . /app
RUN uv sync --frozen --no-dev

# ---------- runtime ----------
FROM python:3.11-slim

# libgomp1 is required at runtime by numpy/scikit-learn OpenMP code paths
# and is absent from -slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
