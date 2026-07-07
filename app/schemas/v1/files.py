from __future__ import annotations

import datetime as dt  # noqa: TC003 - Pydantic needs this at runtime for response models.
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int | None = None
    file_name: str
    file_type: str
    storage_path: str
    analysis_status: str
    analysis_result: dict[str, Any] | None = None
    created_at: dt.datetime


class FileUploadResponse(BaseModel):
    file: FileRecordResponse
    analysis: dict[str, Any]


class FileAnalysisRequest(BaseModel):
    file_id: int = Field(ge=1)
