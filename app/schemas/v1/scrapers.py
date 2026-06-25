from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CustomScraperCreateRequest(BaseModel):
    """Payload for creating or updating a custom scraper."""
    platform: str = Field(pattern="^(instagram|twitter|linkedin|reddit)$", description="Target platform")
    api_key: str | None = Field(default=None, description="API key for the custom scraper")
    api_host: str = Field(min_length=1, description="Host of the API, e.g., instagram-scraper2.p.rapidapi.com")
    search_endpoint: str = Field(min_length=1, description="Endpoint to search for keywords")
    search_param_name: str = Field(min_length=1, description="Query parameter name for the keyword")
    comments_endpoint: str | None = Field(default=None, description="Optional endpoint to fetch comments")
    comments_param_name: str | None = Field(default=None, description="Optional parameter for the post ID")
    items_json_path: str = Field(min_length=1, description="Dot-notation path to extract items array, e.g., 'data.items'")
    is_active: bool = Field(default=True)


class CustomScraperResponse(BaseModel):
    """Response model for a custom scraper."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    platform: str
    api_host: str
    search_endpoint: str
    search_param_name: str
    comments_endpoint: str | None
    comments_param_name: str | None
    items_json_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # We do NOT return the api_key for security reasons, unless explicitly needed.
