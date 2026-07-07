from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs this at runtime for response models.
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    project_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=10, ge=1, le=50)
    use_cache: bool = True


class RedditSearchRequest(SearchRequest):
    subreddits: list[str] = Field(default_factory=list, max_length=10)


class SearchCitation(BaseModel):
    title: str
    url: str
    snippet: str | None = None


class SearchItem(BaseModel):
    title: str
    url: str
    source: str
    snippet: str | None = None
    author: str | None = None
    score: int | None = None
    comments_count: int | None = None
    created_at: dt.datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    provider: str
    query: str
    cache_key: str
    cached: bool
    results: list[SearchItem] = Field(default_factory=list)
    citations: list[SearchCitation] = Field(default_factory=list)


class SearchCacheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cache_key: str
    provider: str
    query: str
    result: dict[str, Any]
    expires_at: dt.datetime
