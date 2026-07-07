from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReplyDraftRequest(BaseModel):
    opportunity_id: int
    voice_profile_id: int | None = Field(default=None, ge=1)
    platform: str | None = Field(
        default=None,
        pattern="^(reddit|twitter|linkedin|instagram|x|hackernews|github|indiehackers)$",
        description="Override the opportunity's platform for tone selection",
    )
    style_preset: str | None = Field(
        default=None,
        pattern="^(shorter|more_helpful|more_professional|less_promotional)$",
        description="Optional rewrite direction for regenerated reply drafts",
    )
    variants: int = Field(
        default=1, ge=1, le=3,
        description="Number of reply variants to generate (each with slightly different style)",
    )


class ReplyDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    opportunity_id: int
    content: str
    rationale: str | None
    source_prompt: str | None
    version: int
    created_at: datetime


class ReplyDraftUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    rationale: str | None = Field(default=None, max_length=8000)


class PostDraftRequest(BaseModel):
    project_id: int
    platform: str | None = Field(default=None, pattern="^(reddit|x|twitter|linkedin)$")


class ContentPlanRequest(BaseModel):
    project_id: int = Field(ge=1)
    platform: str = Field(default="x", pattern="^(x|twitter|linkedin)$")
    horizon_days: int = Field(default=7, ge=1, le=30)
    count: int | None = Field(default=None, ge=1, le=30)
    start_at: datetime | None = None
    preferred_hour_utc: int = Field(default=14, ge=0, le=23)
    campaign_goal: str | None = Field(
        default="brand_awareness",
        pattern="^(brand_awareness|lead_generation|product_launch|competitor_switch|education)$",
    )
    campaign_brief: str | None = Field(default=None, max_length=800)
    voice_style: str | None = Field(default="professional", pattern="^(professional|friendly|premium|witty)$")
    content_template: str | None = Field(
        default="product_tip",
        pattern="^(product_tip|comparison|founder_story|case_study|offer_post)$",
    )


class PostDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    body: str
    rationale: str | None
    source_prompt: str | None
    version: int
    created_at: datetime
    platform: str = "reddit"
    thread_json: list[str] = Field(default_factory=list)
    status: str = "draft"
    scheduled_at: datetime | None = None


class PostDraftUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=40000)
    rationale: str | None = Field(default=None, max_length=8000)
    status: str | None = Field(default=None, pattern="^(draft|scheduled|needs_edit|rejected)$")


class PostDraftScheduleRequest(BaseModel):
    scheduled_at: datetime
