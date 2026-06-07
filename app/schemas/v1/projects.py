from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.v1.billing import SubscriptionResponse
from app.schemas.v1.discovery import OpportunityResponse


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class ProjectUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: str = Field(default="active", pattern="^(active|archived)$")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    slug: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class SetupStatus(BaseModel):
    brand_configured: bool = False
    personas_count: int = 0
    subreddits_count: int = 0


class DashboardResponse(BaseModel):
    projects: list[ProjectResponse]
    top_opportunities: list[OpportunityResponse]
    subscription: SubscriptionResponse
    setup_status: SetupStatus = SetupStatus()
    drafts_count: int = 0
    published_count: int = 0
