"""Tests for post draft generation — guards against the sync/async paths
silently diverging (they used to duplicate the same LLM-call body verbatim)."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.product.copilot.post import (
    _ai_post,
    _ai_post_async,
    _parse_post_payload,
    generate_post,
)


class TestPostPayloadParsing:
    def test_valid_payload_returns_title_body_rationale(self):
        result = _parse_post_payload({"title": "Hello", "body": "World", "rationale": "why"})
        assert result == ("Hello", "World", "why")

    def test_missing_title_returns_none(self):
        assert _parse_post_payload({"body": "World"}) is None

    def test_missing_body_returns_none(self):
        assert _parse_post_payload({"title": "Hello"}) is None

    def test_none_payload_returns_none(self):
        assert _parse_post_payload(None) is None

    def test_list_payload_uses_first_item(self):
        result = _parse_post_payload([{"title": "T", "body": "B"}])
        assert result == ("T", "B", "AI generated post draft.")


class TestSyncAsyncParity:
    """The sync (_ai_post) and async-fallback (_ai_post_async) paths share
    _build_post_prompt/_parse_post_payload — given the same LLM response,
    they must produce the same result."""

    def test_same_payload_produces_same_result(self):
        payload = {"title": "New feature", "body": "We shipped X", "rationale": "relevant"}

        with patch("app.services.product.copilot.post.LLMClient") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = payload
            mock_llm_cls.return_value = mock_llm

            sync_result = _ai_post(mock_llm, {"brand_name": "Acme"}, "context")

            async def _run_async_fallback():
                with patch(
                    "app.services.infrastructure.llm.service.generate_post_async",
                    side_effect=RuntimeError("no agent"),
                ):
                    return await _ai_post_async(mock_llm, {"brand_name": "Acme"}, "context")

            async_result = asyncio.run(_run_async_fallback())

        assert sync_result == async_result == ("New feature", "We shipped X", "relevant")


class TestGeneratePostRaisesOnEmptyResponse:
    def test_generate_post_raises_on_empty_llm_response(self):
        with patch("app.services.product.copilot.post.LLMClient") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = None
            mock_llm_cls.return_value = mock_llm

            with pytest.raises(RuntimeError, match="Failed to generate post draft"):
                generate_post({"brand_name": "Acme"}, [])
