"""Shared utility functions for retrieving platform credentials from integration_secrets.

Consolidates the duplicated token/secret retrieval logic that was previously
copied across x_publisher.py, instagram_publisher.py, and linkedin_publisher.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.db.tables.integrations import list_integration_secrets_for_workspace
from app.utils.encryption import decrypt_text

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)


def get_platform_token(
    db: Client,
    workspace_id: int,
    provider: str,
    fallback_provider: str | None = None,
) -> str | None:
    """Return the decrypted access token for *provider* (with optional
    *fallback_provider*), or None if not configured.

    Looks for an integration secret matching one of the given providers.
    The first match wins.
    """
    secrets = list_integration_secrets_for_workspace(db, workspace_id)
    providers = [p for p in (provider, fallback_provider) if p]
    row = None
    for prov in providers:
        row = next((s for s in secrets if s.get("provider") == prov), None)
        if row:
            break
    if not row:
        return None
    encrypted = row.get("encrypted_value")
    if not encrypted:
        return None
    try:
        return decrypt_text(encrypted)
    except ValueError as exc:
        raise RuntimeError(
            f"Stored {provider} credentials could not be decrypted. Re-save the "
            f"{provider} access token in workspace integration settings."
        ) from exc


def get_platform_secret_value(
    db: Client,
    workspace_id: int,
    provider: str,
    label: str,
) -> str | None:
    """Return a typed secret value (e.g. business_account_id, author_urn)
    for *provider* with the given *label*, or None if not configured.

    Supports both encrypted storage (via ``encrypted_value``) and
    plaintext storage (via ``value``).
    """
    secrets = list_integration_secrets_for_workspace(db, workspace_id)
    row = next(
        (
            s
            for s in secrets
            if s.get("provider") == provider and s.get("label") == label
        ),
        None,
    )
    if not row:
        return None
    encrypted = row.get("encrypted_value")
    if not encrypted:
        logger.warning(
            "Secret for provider=%s label=%s is stored in plaintext (column 'value') "
            "rather than encrypted. Store secrets in 'encrypted_value' instead.",
            provider, label,
        )
        return row.get("value")
    try:
        return decrypt_text(encrypted)
    except ValueError:
        return None
