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
    platform: str | None = Field(default=None, pattern="^(reddit|x|twitter|linkedin|instagram|threads|facebook)$")


class ContentPlanRequest(BaseModel):
    project_id: int = Field(ge=1)
    platform: str = Field(default="x", pattern="^(x|twitter|linkedin|instagram|threads|facebook)$")
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
    published_at: datetime | None = None
    published_url: str | None = None
    publish_mode: str | None = None
    publish_error: str | None = None
    publish_note: str | None = None
    last_publish_attempt_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict) -> "PostDraftResponse":
        """Build a response while tolerating databases missing newer optional columns."""
        data = dict(row)
        if "body" not in data and "content" in data:
            data["body"] = data.get("content") or ""
        optional_defaults = {
            "title": data.get("body") or "Untitled post",
            "body": data.get("content") or "",
            "rationale": None,
            "source_prompt": None,
            "version": 1,
            "platform": "reddit",
            "thread_json": [],
            "status": "draft",
            "scheduled_at": None,
            "published_at": None,
            "published_url": None,
            "publish_mode": None,
            "publish_error": None,
            "publish_note": None,
            "last_publish_attempt_at": None,
        }
        for key, value in optional_defaults.items():
            data.setdefault(key, value)
        return cls.model_validate(data)


class PostDraftUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=40000)
    rationale: str | None = Field(default=None, max_length=8000)
    status: str | None = Field(default=None, pattern="^(draft|scheduled|needs_edit|rejected|published)$")


class PostDraftScheduleRequest(BaseModel):
    scheduled_at: datetime


class PostDraftManualPublishRequest(BaseModel):
    published_url: str | None = Field(default=None, max_length=2000)
    publish_note: str | None = Field(default=None, max_length=2000)
