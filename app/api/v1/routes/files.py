"""File upload, analysis, and report endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace, get_project
from app.db.supabase_client import get_supabase
from app.db.tables.files import (
    create_uploaded_file,
    get_uploaded_file_by_id,
    list_uploaded_files_for_workspace,
    update_uploaded_file,
)
from app.schemas.v1.files import FileRecordResponse, FileUploadResponse
from app.services.product.file_analysis import (
    analyze_file,
    generate_analysis_report,
    sanitize_filename,
    save_upload,
)

if TYPE_CHECKING:
    from supabase import Client

router = APIRouter(prefix="/v1/files", tags=["files"])


def _ensure_file_access(row: dict, workspace_id: int) -> None:
    if row.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="File not found.")


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file_name: str = Query(..., min_length=1, max_length=255),
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> FileUploadResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if project_id is not None:
        get_project(supabase, workspace["id"], project_id)

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Upload body is empty.")

    safe_name = sanitize_filename(file_name)
    file_type = Path(safe_name).suffix.lstrip(".").lower() or "bin"
    try:
        storage_path = save_upload(workspace_id=workspace["id"], file_name=safe_name, content=content)
        analysis = analyze_file(storage_path, file_type=file_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = create_uploaded_file(supabase, {
        "workspace_id": workspace["id"],
        "project_id": project_id,
        "file_name": safe_name,
        "file_type": file_type,
        "storage_path": str(storage_path),
        "analysis_status": analysis.get("status", "analyzed"),
        "analysis_result": analysis,
    })
    return FileUploadResponse(file=FileRecordResponse.model_validate(row), analysis=analysis)


@router.get("", response_model=list[FileRecordResponse])
def list_files(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[FileRecordResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if project_id is not None:
        get_project(supabase, workspace["id"], project_id)
    rows = list_uploaded_files_for_workspace(supabase, workspace["id"], project_id=project_id)
    return [FileRecordResponse.model_validate(row) for row in rows]


@router.post("/{file_id}/analyze", response_model=FileRecordResponse)
def analyze_uploaded_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> FileRecordResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_uploaded_file_by_id(supabase, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    _ensure_file_access(row, workspace["id"])
    analysis = analyze_file(row["storage_path"], file_type=row.get("file_type"))
    updated = update_uploaded_file(supabase, file_id, {
        "analysis_status": analysis.get("status", "analyzed"),
        "analysis_result": analysis,
    })
    return FileRecordResponse.model_validate(updated or row)


@router.get("/{file_id}/report")
def get_file_report(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> Response:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_uploaded_file_by_id(supabase, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    _ensure_file_access(row, workspace["id"])
    return Response(content=generate_analysis_report(row), media_type="text/markdown")
