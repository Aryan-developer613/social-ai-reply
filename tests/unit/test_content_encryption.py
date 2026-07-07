from __future__ import annotations

import base64
import os

from app.core.config import Settings
from app.db.tables.content import create_post_draft, create_reply_draft
from app.utils import aes_gcm


def test_reply_draft_content_encrypted_at_rest_when_enabled(mock_supabase, monkeypatch) -> None:
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    settings = Settings(encryption_key=key, enable_response_encryption=True)
    monkeypatch.setattr("app.db.tables.content.get_settings", lambda: settings)
    monkeypatch.setattr("app.utils.aes_gcm.get_settings", lambda: settings)

    row = create_reply_draft(mock_supabase, {
        "project_id": 1,
        "opportunity_id": 2,
        "content": "Helpful private draft",
        "rationale": "r",
        "source_prompt": "",
        "version": 1,
    })

    raw_value = mock_supabase._tables["reply_drafts"][0]["content"]
    assert row["content"] == "Helpful private draft"
    assert aes_gcm.is_encrypted(raw_value)
    assert raw_value != "Helpful private draft"


def test_post_draft_body_encrypted_at_rest_when_enabled(mock_supabase, monkeypatch) -> None:
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    settings = Settings(encryption_key=key, enable_response_encryption=True)
    monkeypatch.setattr("app.db.tables.content.get_settings", lambda: settings)
    monkeypatch.setattr("app.utils.aes_gcm.get_settings", lambda: settings)

    row = create_post_draft(mock_supabase, {
        "project_id": 1,
        "title": "Private title",
        "body": "Private body",
        "rationale": "r",
        "source_prompt": "",
        "version": 1,
    })

    stored = mock_supabase._tables["post_drafts"][0]
    assert row["title"] == "Private title"
    assert row["body"] == "Private body"
    assert aes_gcm.is_encrypted(stored["title"])
    assert aes_gcm.is_encrypted(stored["body"])
