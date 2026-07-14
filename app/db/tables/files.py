"""Uploaded file table helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

UPLOADED_FILES_TABLE = "uploaded_files"


def create_uploaded_file(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    return data


def get_uploaded_file_by_id(db: Client, file_id: int) -> dict[str, Any] | None:
    return None


def update_uploaded_file(db: Client, file_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    return None


def list_uploaded_files_for_workspace(db: Client, workspace_id: int, project_id: int | None = None) -> list[dict[str, Any]]:
    return []
