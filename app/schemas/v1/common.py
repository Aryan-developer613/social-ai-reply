"""Common shared schemas used across multiple route modules."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BackgroundTaskResponse(BaseModel):
    """Standard response for endpoints that spawn background tasks (Issue #43).

    All routes returning a 202 with a started background task should use this
    model for a consistent API contract.
    """

    status: str = Field(default="running", description="Task status, e.g. 'running'.")
    agent: str | None = Field(default=None, description="Agent/task name, if applicable.")
    task_id: str | int | None = Field(default=None, description="Optional task/run identifier.")
    message: str | None = Field(default=None, description="Optional human-readable message.")


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses (Issue #27)."""

    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool = False


class EmptyResultResponse(BaseModel):
    """Structured response for empty results with an explanatory reason (Issue #47).

    Allows callers to distinguish "no results found" from "quota exhausted"
    or other business-rule-driven empty results.
    """

    items: list = Field(default_factory=list)
    reason: str | None = Field(default=None, description="Why items is empty, e.g. 'quota_exhausted', 'no_results'.")
