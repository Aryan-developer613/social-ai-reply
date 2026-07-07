"""LLM client — thin adapter over the modular LLMService."""

from __future__ import annotations

import logging

from app.services.infrastructure.llm.service import LLMService

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM API calls.

    Backward-compatible adapter that delegates to LLMService.
    Existing consumers (analyzer.py, reply.py, post.py, _facade.py)
    continue to use this class unchanged.
    """

    def __init__(self, service: LLMService | None = None) -> None:
        self._service = service or LLMService()

    def call(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.2,
        model_hint: str | None = None,
        platform: str | None = None,
    ) -> dict | list | None:
        """Call the LLM API and return parsed JSON response."""
        return self._service.call_json(
            system_prompt,
            user_content,
            temperature,
            model_hint=model_hint,
            platform=platform,
        )


def _parse_json_payload(text: str) -> dict | list | None:
    """Parse JSON from LLM response text, handling markdown code blocks.

    Kept for backward compatibility — new code should use
    app.services.infrastructure.llm._json_helpers.parse_json_payload directly.
    """
    from app.services.infrastructure.llm._json_helpers import parse_json_payload

    return parse_json_payload(text)
