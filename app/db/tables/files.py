"""Uploaded file table helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

UPLOADED_FILES_TABLE = "uploaded_files"


def create_uploaded_file(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    result = db.table(UPLOADED_FILES_TABLE).insert(data).execute()
    return result.data[0]


def get_uploaded_file_by_id(db: Client, file_id: int) -> dict[str, Any] | None:
    result = db.table(UPLOADED_FILES_TABLE).select("*").eq("id", file_id).execute()
    return result.data[0] if result.data else None


def update_uploaded_file(db: Client, file_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    result = db.table(UPLOADED_FILES_TABLE).update(data).eq("id", file_id).execute()
    return result.data[0] if result.data else None


def list_uploaded_files_for_workspace(db: Client, workspace_id: int, project_id: int | None = None) -> list[dict[str, Any]]:
    query = db.table(UPLOADED_FILES_TABLE).select("*").eq("workspace_id", workspace_id)
    if project_id is not None:
        query = query.eq("project_id", project_id)
    result = query.order("created_at", desc=True).execute()
    return list(result.data)
