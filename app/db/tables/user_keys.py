"""User API keys table operations (BYOK)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

USER_API_KEYS_TABLE = "user_api_keys"


def get_user_key(db: Client, workspace_id: int, key_type: str) -> dict[str, Any] | None:
    return None


def upsert_user_key(db: Client, workspace_id: int, key_type: str, encrypted_key: str) -> dict[str, Any]:
    return {"workspace_id": workspace_id, "key_type": key_type, "encrypted_key": encrypted_key}


def delete_user_key(db: Client, workspace_id: int, key_type: str) -> None:
    pass


def list_user_keys(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    return []
