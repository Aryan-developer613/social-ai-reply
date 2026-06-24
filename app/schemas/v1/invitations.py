from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(owner|admin|member)$")


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: int
    email: str
    role: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    email_sent: bool = False
